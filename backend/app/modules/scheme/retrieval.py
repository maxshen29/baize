"""方案生成 · RAG 检索内核（纯函数，无框架依赖，可独立测试）。

设计要点：
- 中文友好分词：ASCII 词 + 中文二元组（bigram）+ 中文单字，无需 jieba 等外部依赖。
- 字段加权：把不同字段的 token 按权重重复注入文档，实现「标题/标签优先」的检索倾向。
- BM25 排序：经典 Okapi BM25（k1=1.5, b=0.75），返回归一化得分（0~1）便于前端展示。
- 可扩展：若接入方提供 embedding 能力，可在 service 层用 `rank_by_vector` 替换 `bm25_rank`，
  本模块的接口形状（返回 [{index, score}]）保持不变。
"""
from __future__ import annotations

import math
import re

_ASCII_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# 常见停用词（中英），避免「的/了/和/the/and」等稀释相关性
STOPWORDS = {
    "的", "了", "和", "与", "及", "或", "在", "是", "对", "为", "以", "等", "中", "我", "们",
    "the", "and", "for", "with", "of", "to", "a", "an", "in", "on", "by", "is", "are",
}


def tokenize(text: str) -> list[str]:
    """中文友好分词：ASCII 词 + 中文 bigram + 中文单字。"""
    if not text:
        return []
    s = str(text).lower()
    tokens: list[str] = []
    for m in _ASCII_RE.finditer(s):
        w = m.group()
        if w not in STOPWORDS and len(w) > 1:
            tokens.append(w)
    cjk = _CJK_RE.findall(s)
    for ch in cjk:
        if ch not in STOPWORDS:
            tokens.append(ch)
    for i in range(len(cjk) - 1):
        bigram = cjk[i] + cjk[i + 1]
        tokens.append(bigram)
    return tokens


def weighted_field(text: str, weight: int) -> list[str]:
    """按权重重复字段 token，实现字段级加权。"""
    toks = tokenize(text)
    if weight <= 1:
        return toks
    out: list[str] = []
    for _ in range(weight):
        out.extend(toks)
    return out


def _join(*parts: object) -> str:
    return " ".join(str(p) for p in parts if p)


def template_doc(t: dict) -> list[str]:
    """模板文档：名称×3、分类/标签/描述×2、章节标题与提示×1。"""
    toks: list[str] = []
    toks += weighted_field(t.get("name", ""), 3)
    toks += weighted_field(t.get("category", ""), 2)
    toks += weighted_field(t.get("description", ""), 2)
    toks += weighted_field(_join(*(t.get("tags") or [])), 2)
    for sec in t.get("sections") or []:
        if isinstance(sec, dict):
            toks += tokenize(_join(sec.get("title"), sec.get("hint")))
        else:
            toks += tokenize(str(sec))
    return toks


def case_doc(c: dict) -> list[str]:
    """案例文档：标题×3、行业/分类/标签/摘要×2、正文×1（截断，避免长文主导）。"""
    toks: list[str] = []
    toks += weighted_field(c.get("title", ""), 3)
    toks += weighted_field(c.get("industry", ""), 2)
    toks += weighted_field(c.get("category", ""), 2)
    toks += weighted_field(_join(*(c.get("tags") or [])), 2)
    toks += weighted_field(c.get("summary", ""), 2)
    toks += tokenize(str(c.get("content", ""))[:4000])
    return toks


class BM25:
    """Okapi BM25 评分器。"""

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.n_docs = len(corpus)
        self.doc_len = [len(d) for d in corpus]
        self.avgdl = (sum(self.doc_len) / self.n_docs) if self.n_docs else 1.0
        self.tf: list[dict[str, int]] = []
        df: dict[str, int] = {}
        for doc in corpus:
            counts: dict[str, int] = {}
            for tok in doc:
                counts[tok] = counts.get(tok, 0) + 1
            self.tf.append(counts)
            for tok in counts:
                df[tok] = df.get(tok, 0) + 1
        # BM25 概率 IDF（平滑，保证非负）
        self.idf = {
            tok: math.log(1 + (self.n_docs - n + 0.5) / (n + 0.5))
            for tok, n in df.items()
        }

    def score(self, query_tokens: list[str], idx: int) -> float:
        if idx >= self.n_docs:
            return 0.0
        tf = self.tf[idx]
        dl = self.doc_len[idx] or 1
        s = 0.0
        seen: set[str] = set()
        for tok in query_tokens:
            if tok in seen:
                continue
            seen.add(tok)
            f = tf.get(tok)
            if not f:
                continue
            idf = self.idf.get(tok, 0.0)
            denom = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            s += idf * (f * (self.k1 + 1)) / denom
        return s


def bm25_rank(query_tokens: list[str], corpus: list[list[str]], topk: int = 5) -> list[dict]:
    """返回 [{index, score(已归一化 0~1), raw}]，按相关度降序。"""
    if not corpus:
        return []
    bm = BM25(corpus)
    scored = [{"index": i, "raw": bm.score(query_tokens, i)} for i in range(len(corpus))]
    scored = [x for x in scored if x["raw"] > 0]
    scored.sort(key=lambda x: x["raw"], reverse=True)
    top = scored[:topk] if topk and topk > 0 else scored
    mx = top[0]["raw"] if top else 0.0
    for x in top:
        x["score"] = round(x["raw"] / mx, 4) if mx > 0 else 0.0
    return top


def excerpt(text: str, limit: int = 300) -> str:
    """截取摘要片段，供提示词注入（避免超长）。"""
    t = (text or "").strip().replace("\r", "")
    t = re.sub(r"\n{2,}", "\n", t)
    return t[:limit] + ("…" if len(t) > limit else "")


def retrieve(
    brief_text: str,
    templates: list[dict],
    cases: list[dict],
    topk_templates: int = 3,
    topk_cases: int = 4,
) -> dict:
    """对素材文本做统一检索，返回命中的模板与案例（含相关度与片段）。"""
    q = tokenize(brief_text)
    t_corpus = [template_doc(t) for t in templates]
    c_corpus = [case_doc(c) for c in cases]

    hits_t = bm25_rank(q, t_corpus, topk_templates)
    hits_c = bm25_rank(q, c_corpus, topk_cases)

    matched_templates = []
    for h in hits_t:
        t = templates[h["index"]]
        matched_templates.append({
            "id": str(t.get("id")),
            "code": t.get("code"),
            "name": t.get("name"),
            "category": t.get("category"),
            "score": h["score"],
            "sections": [s.get("title") if isinstance(s, dict) else str(s) for s in (t.get("sections") or [])],
        })

    matched_cases = []
    for h in hits_c:
        c = cases[h["index"]]
        matched_cases.append({
            "id": str(c.get("id")),
            "title": c.get("title"),
            "industry": c.get("industry"),
            "category": c.get("category"),
            "quality": c.get("quality", 3),
            "score": h["score"],
            "excerpt": excerpt(c.get("summary") or c.get("content") or "", 260),
        })

    return {"templates": matched_templates, "cases": matched_cases, "query_tokens": len(q)}
