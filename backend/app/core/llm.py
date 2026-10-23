"""大模型客户端：依据 OpenAI 兼容规范（/v1/chat/completions、/v1/models）接入任意大模型服务。

任意兼容 OpenAI API 的服务（OpenAI / DeepSeek / 通义千问 / 本地 vLLM / Ollama 等）均可按此规范接入：
  - 鉴权：Authorization: Bearer <api_key>
  - 模型列表：GET  {base_url}/v1/models
  - 对话补全：POST {base_url}/v1/chat/completions  (stream=true 返回 SSE)
"""
from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import LlmProvider

OPENAI_CHAT_PATH = "/chat/completions"
OPENAI_MODELS_PATH = "/models"


def _normalize_base_url(base_url: str) -> str:
    """统一基地址：去掉末尾斜杠，并剥离可能的 /v1 后缀（调用时再补回）。"""
    base = (base_url or "").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base or ""


def _headers(provider: LlmProvider) -> dict:
    return {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }


async def list_models(provider: LlmProvider) -> list[str]:
    """获取该服务下的模型 id 列表。"""
    url = f"{_normalize_base_url(provider.base_url)}{OPENAI_MODELS_PATH}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, headers=_headers(provider))
        resp.raise_for_status()
        data = resp.json()
        return [m.get("id") for m in data.get("data", []) if m.get("id")]


async def test_connection(provider: LlmProvider) -> dict:
    """连通性测试：拉取模型列表，返回可用模型数。"""
    try:
        models = await list_models(provider)
        return {"ok": True, "model_count": len(models), "models": models[:50]}
    except Exception as e:  # noqa: BLE001 - 需要把任意异常转成可读结果
        return {"ok": False, "error": str(e)}


async def chat_stream(
    provider: LlmProvider,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
):
    """以 SSE 方式流式调用 /chat/completions，逐块透传上游原始字节（OpenAI SSE 格式）。"""
    url = f"{_normalize_base_url(provider.base_url)}{OPENAI_CHAT_PATH}"
    payload = {
        "model": model or provider.model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=20.0)) as client:
        async with client.stream("POST", url, headers=_headers(provider), json=payload) as resp:
            async for chunk in resp.aiter_raw():
                yield chunk
