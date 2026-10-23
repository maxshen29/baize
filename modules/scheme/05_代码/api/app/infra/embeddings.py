"""本地嵌入网关（默认 Ollama bge-m3，参考 11_本地知识库建设方案 §5）。

接口可插拔：配置切换为云端 OpenAI-like 时只需改 embed_model / ollama_base_url。
数据库在远程服务器，但嵌入推理默认在本地/内网 Ollama，敏感资料不出域。
"""
from __future__ import annotations

import httpx

from ..config import settings


def _embed_one(text: str) -> list[float]:
    url = f"{settings.ollama_base_url}/api/embeddings"
    resp = httpx.post(
        url, json={"model": settings.embed_model, "prompt": text}, timeout=120
    )
    resp.raise_for_status()
    return list(resp.json()["embedding"])


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量嵌入（带简单重试）。"""
    out: list[list[float]] = []
    for t in texts:
        last: Exception | None = None
        for _ in range(3):
            try:
                out.append(_embed_one(t))
                break
            except Exception as e:  # noqa: BLE001
                last = e
        else:
            # 嵌入失败不阻断整体：以零向量兜底（检索时该切片仅走 FTS）
            out.append([0.0] * settings.embedding_dim)
            print(f"[embeddings] 嵌入失败，已兜底零向量: {last}")
    return out


def embed_query(text: str) -> list[float]:
    """单条查询嵌入，返回 pgvector 可直接 CAST 的方括号字符串。"""
    vec = _embed_one(text)
    return vec


def vector_literal(vec: list[float]) -> str:
    """转为 pgvector 文本字面量 '[0.1,0.2,...]'。"""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
