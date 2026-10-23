"""AI 文档提炼 · 服务层：默认模型获取、提示词装配、SSE 透传。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.llm import chat_stream
from ...models import LlmProvider
from .prompts import build_messages


async def get_default_provider(db: AsyncSession) -> LlmProvider | None:
    return (
        await db.execute(select(LlmProvider).where(LlmProvider.is_default == True))  # noqa: E712
    ).scalars().first()


def build(
    task: str,
    text: str,
    *,
    target_lang: str = "",
    length: str = "标准",
    model: str = "",
) -> list[dict]:
    return build_messages(task, text, target_lang=target_lang, length=length, model=model)


def stream(
    provider: LlmProvider,
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
):
    """透传大模型 SSE（OpenAI 兼容原始字节）。"""
    return chat_stream(provider, messages, model=model, temperature=temperature)
