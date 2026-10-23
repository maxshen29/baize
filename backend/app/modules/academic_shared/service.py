"""学术工具 · 共享服务层：默认模型获取、提示词装配、SSE 透传。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.llm import chat_stream
from ...models import LlmProvider
from .prompts import build_messages, TOOL_TEMPS


async def get_default_provider(db: AsyncSession) -> LlmProvider | None:
    return (
        await db.execute(select(LlmProvider).where(LlmProvider.is_default == True))  # noqa: E712
    ).scalars().first()


def build(tool: str, text: str, *, target_lang: str = "") -> list[dict]:
    return build_messages(tool, text, target_lang=target_lang)


def stream(
    provider: LlmProvider,
    messages: list[dict],
    tool: str = "",
    model: str | None = None,
):
    """透传大模型 SSE（OpenAI 兼容原始字节）。温度随工具类型调整。"""
    temperature = TOOL_TEMPS.get(tool, 0.5)
    return chat_stream(provider, messages, model=model, temperature=temperature)
