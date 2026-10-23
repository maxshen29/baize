"""论文应用 · 轻量 BM25 检索（复用 scheme 的中文分词思路，无向量库依赖）。

用于阅读工具的「交互问答」：把全文分块建索引，提问时召回 top-k 相关片段注入上下文。
"""
from __future__ import annotations

import math
import re

from .parse import chunk_text

_ASCII_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

STOPWORDS = {
    "的", "了", "和", "与", "及", "或", "在", "是", "对", "为", "以", "等", "中", "我", "们",
    "the", "and", "for", "with", "of", "to", "a", "an", "in", "on", "by", "is", "are",
}


def tokenize(text: str) -> list[str]:
    """中文友好分词：ASCII 词 + 中文单字 + 中文 bigram。"""
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


class BM25:
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


def retrieve_chunks(text: str, query: str, topk: int = 4, chunk_size: int = 1400) -> list[str]:
    """对全文分块，按查询召回 top-k 相关片段原文。"""
    chunks = chunk_text(text, chunk_size)
    if not chunks:
        return []
    q = tokenize(query)
    if not q:
        return chunks[:topk]
    hits = bm25_rank(q, [tokenize(c) for c in chunks], topk)
    return [chunks[h["index"]] for h in hits]
