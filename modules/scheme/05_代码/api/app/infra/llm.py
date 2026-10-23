"""生成 LLM 网关（OpenAI-like 兼容，默认指向本地 Ollama /v1）。

对应 OpenBidKit 的 aiService / agentService；本平台用同步 httpx 调用，
便于部署在服务器上稳定生成章节正文。
"""
from __future__ import annotations

import httpx

from ..config import settings


def chat(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """调用 chat/completions，返回纯文本回复。"""
    url = f"{settings.llm_base_url}/chat/completions"
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature if temperature is not None else settings.llm_temperature,
        "max_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    resp = httpx.post(url, json=payload, headers=headers, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def complete(prompt: str, **kw) -> str:
    return chat([{"role": "user", "content": prompt}], **kw)
