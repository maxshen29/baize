"""能力②：参考文档导入与管理（对标 OpenBidKit doc2markdown + duplicateCheck）。

导入流程：保存原始文件 -> 解析为 Markdown -> 切片 -> 本地嵌入 -> 落库。
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..infra import embeddings, parser
from ..infra.parser import checksum_text
from ..models import DocumentChunk, ReferenceDocument
from ..services import knowledge_service


def _save_upload(filename: str, data: bytes) -> str:
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    # 避免覆盖：加前缀
    safe = f"{abs(hash(filename)) % 100000:05d}_{filename}"
    path = os.path.join(settings.upload_dir, safe)
    with open(path, "wb") as f:
        f.write(data)
    return path


def import_upload(
    db: Session, filename: str, data: bytes, source_type: str | None = None
) -> ReferenceDocument:
    """导入一份参考文档：解析 + 切片 + 嵌入 + 落库。"""
    source_type = source_type or Path(filename).suffix.lstrip(".").lower()
    original_path = _save_upload(filename, data)
    raw_md = parser.parse_file(original_path, source_type)
    checksum = checksum_text(raw_md)

    # 去重：同校验和直接返回已有文档（借鉴 OpenBidKit duplicateCheckService）
    existing = db.scalars(
        select(ReferenceDocument).where(ReferenceDocument.checksum == checksum)
    ).first()
    if existing:
        return existing

    doc = ReferenceDocument(
        title=Path(filename).stem,
        source_type=source_type,
        original_path=original_path,
        parsed_path=original_path + ".md",
        status="parsing",
        checksum=checksum,
    )
    db.add(doc)
    db.flush()

    # 解析产物落盘（便于预览与再切片）
    with open(doc.parsed_path, "w", encoding="utf-8") as f:
        f.write(raw_md)

    # 切片
    chunks = knowledge_service.chunk_markdown(raw_md, classification=doc.classification)
    if chunks:
        # 批量嵌入
        vecs = embeddings.embed_texts([c["content"] for c in chunks])
        for c, vec in zip(chunks, vecs):
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    heading_path=c["heading_path"],
                    content=c["content"],
                    chunk_index=c["chunk_index"],
                    keywords=c["keywords"],
                    facets=c["facets"],
                    embedding=vec,
                )
            )
        doc.chunk_count = len(chunks)

    doc.status = "ready"
    db.commit()
    db.refresh(doc)
    return doc


def list_documents(db: Session) -> list[ReferenceDocument]:
    return list(
        db.scalars(select(ReferenceDocument).order_by(ReferenceDocument.imported_at.desc())).all()
    )


def get_document(db: Session, doc_id: str) -> ReferenceDocument | None:
    return db.get(ReferenceDocument, doc_id)


def delete_document(db: Session, doc_id: str) -> bool:
    doc = db.get(ReferenceDocument, doc_id)
    if not doc:
        return False
    db.delete(doc)  # 级联删除 chunks
    db.commit()
    return True


def parse_preview(db: Session, doc_id: str, length: int = 2000) -> str:
    doc = db.get(ReferenceDocument, doc_id)
    if not doc or not doc.parsed_path:
        return ""
    try:
        with open(doc.parsed_path, "r", encoding="utf-8") as f:
            return f.read()[:length]
    except OSError:
        return ""
