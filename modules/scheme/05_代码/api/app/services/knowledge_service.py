"""能力③：知识库服务（对标 OpenBidKit knowledgeBaseService / knowledgeBaseStore）。

实现：按标题层级递归切片 -> 本地嵌入 -> 混合检索（FTS + 向量 ANN + RRF 融合 + 分面过滤）。
详见 11_本地知识库建设方案 §4~§7。
"""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..infra import embeddings
from ..models import DocumentChunk, ReferenceDocument

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


# --------------------------------------------------------------------------- #
# 切片
# --------------------------------------------------------------------------- #
def chunk_markdown(
    md: str,
    *,
    classification: str | None = None,
    source_type: str = "doc",
    applicable_template: str | None = None,
    overlap: int | None = None,
    min_c: int | None = None,
    max_c: int | None = None,
) -> list[dict[str, Any]]:
    """按标题层级递归切片，相邻块带重叠；返回带溯源元数据的切片列表。"""
    overlap = overlap or settings.chunk_overlap
    min_c = min_c or settings.chunk_min_chars
    max_c = max_c or settings.chunk_max_chars

    lines = md.split("\n")
    stack: list[tuple[int, str]] = []
    buf: list[str] = []
    chunks: list[dict[str, Any]] = []
    idx = 0

    def heading_path() -> str | None:
        return " > ".join(t for _, t in stack) or None

    def emit(text: str):
        nonlocal idx
        text = text.strip()
        if len(text) < 20:  # 过短噪声片段丢弃
            return
        chunks.append(
            {
                "heading_path": heading_path(),
                "content": text,
                "chunk_index": idx,
                "keywords": [t for _, t in stack],
                "facets": {
                    "domain": classification,
                    "applicable_template": [applicable_template] if applicable_template else [],
                    "source_type": source_type,
                },
            }
        )
        idx += 1

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            lvl = len(m.group(1))
            title = m.group(2).strip()
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            stack.append((lvl, title))
        buf.append(line)
        if len("\n".join(buf)) >= max_c:
            text = "\n".join(buf)
            emit(text)
            buf = [text[-overlap:]] if overlap else []

    if buf:
        emit("\n".join(buf))

    # 末段若过短，合并到最后一条
    if chunks and len(chunks[-1]["content"]) < min_c and len(chunks) > 1:
        pass  # 保持简单，不强制合并
    return chunks


# --------------------------------------------------------------------------- #
# 检索（混合：FTS + 向量 + RRF）
# --------------------------------------------------------------------------- #
def _build_facet_clause(req) -> tuple[str, dict]:
    conds: list[str] = []
    params: dict[str, Any] = {}
    if getattr(req, "domain", None):
        conds.append("c.facets->>'domain' = :domain")
        params["domain"] = req.domain
    if getattr(req, "applicable_template", None):
        conds.append("c.facets->'applicable_template' @> CAST(:apt AS jsonb)")
        params["apt"] = json.dumps([req.applicable_template])
    if getattr(req, "source_type", None):
        conds.append("c.facets->>'source_type' = :st")
        params["st"] = req.source_type
    if getattr(req, "document_ids", None):
        conds.append("c.document_id = ANY(:docs)")
        params["docs"] = list(req.document_ids)
    clause = (" AND " + " AND ".join(conds)) if conds else ""
    return clause, params


def _rrf(ranked_lists: list[list[str]], k: int) -> list[str]:
    """Reciprocal Rank Fusion：融合多路召回。"""
    fused: dict[str, float] = {}
    for hits in ranked_lists:
        for rank, cid in enumerate(hits):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return [cid for cid, _ in sorted(fused.items(), key=lambda x: -x[1])]


def search(db: Session, req) -> list[dict[str, Any]]:
    """混合检索，返回带溯源的命中列表（含文档标题）。"""
    q_vec = embeddings.vector_literal(embeddings.embed_query(req.query))
    facet_clause, fparams = _build_facet_clause(req)
    k = getattr(req, "top_k", None) or settings.hybrid_top_k

    vec_sql = text(
        f"""
        SELECT c.id, c.document_id, c.heading_path, c.content, c.keywords,
               1 - (c.embedding <=> CAST(:q_vec AS vector)) AS score
        FROM chunks c
        WHERE c.status='active' AND c.embedding IS NOT NULL {facet_clause}
        ORDER BY c.embedding <=> CAST(:q_vec AS vector)
        LIMIT :k
        """
    )
    fts_sql = text(
        f"""
        SELECT c.id, c.document_id, c.heading_path, c.content, c.keywords,
               ts_rank(to_tsvector('simple', c.content),
                       plainto_tsquery('simple', :q_txt)) AS score
        FROM chunks c
        WHERE c.status='active'
          AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', :q_txt) {facet_clause}
        ORDER BY ts_rank(to_tsvector('simple', c.content),
                         plainto_tsquery('simple', :q_txt)) DESC
        LIMIT :k
        """
    )

    vec_params = {"q_vec": q_vec, "k": k, **fparams}
    fts_params = {"q_txt": req.query, "k": k, **fparams}

    vec_rows = db.execute(vec_sql, vec_params).mappings().all()
    # FTS 仅在查询可分词时召回
    try:
        fts_rows = db.execute(fts_sql, fts_params).mappings().all()
    except Exception:  # noqa: BLE001
        fts_rows = []

    vec_ids = [r["id"] for r in vec_rows]
    fts_ids = [r["id"] for r in fts_rows]
    ordered = _rrf([vec_ids, fts_ids], settings.rrf_k)

    meta = {r["id"]: r for r in (*vec_rows, *fts_rows)}
    doc_ids = {r["document_id"] for r in meta.values()}
    titles = dict(
        db.execute(
            select(ReferenceDocument.id, ReferenceDocument.title).where(
                ReferenceDocument.id.in_(doc_ids)
            )
        ).all()
    )

    hits: list[dict[str, Any]] = []
    for cid in ordered:
        r = meta[cid]
        hits.append(
            {
                "chunk_id": r["id"],
                "document_id": r["document_id"],
                "document_title": titles.get(r["document_id"], ""),
                "heading_path": r["heading_path"],
                "content": r["content"],
                "score": round(float(meta[cid].get("score", 0.0)), 4),
                "keywords": list(r["keywords"] or []),
            }
        )
    return hits
