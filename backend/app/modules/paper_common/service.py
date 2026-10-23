"""论文应用 · 共享服务层：默认模型获取、SSE 透传、大文件分块流式、片段检索。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.llm import chat_stream
from ...models import LlmProvider
from .retrieval import retrieve_chunks


async def get_default_provider(db: AsyncSession) -> LlmProvider | None:
    return (
        await db.execute(select(LlmProvider).where(LlmProvider.is_default == True))  # noqa: E712
    ).scalars().first()


def stream(
    provider: LlmProvider,
    messages: list[dict],
    temperature: float = 0.7,
    model: str | None = None,
):
    """透传大模型 SSE（OpenAI 兼容原始字节）。"""
    return chat_stream(provider, messages, model=model, temperature=temperature)


async def stream_blocks(
    provider: LlmProvider,
    system: str,
    blocks: list[str],
    model: str | None = None,
    temperature: float = 0.7,
):
    """对多个文本块分别调用 LLM 并逐块流式透传（大文件稳定处理）。

    每个块是一次独立对话（system 一致、user 为该块），前端按连续 SSE 帧解析即可。
    """
    for block in blocks:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": block},
        ]
        async for chunk in chat_stream(provider, messages, model=model, temperature=temperature):
            yield chunk


def retrieve(text: str, query: str, topk: int = 4) -> list[str]:
    """召回与查询最相关的 top-k 文献片段（阅读工具问答用）。"""
    return retrieve_chunks(text, query, topk=topk)
