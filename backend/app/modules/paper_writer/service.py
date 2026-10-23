"""综合论文编写 · 业务装配：提示词组装、大文件分块流式、长度保护。"""
from __future__ import annotations

from ..paper_common import parse as docparse
from ..paper_common import service as svc
from .prompts import (
    WRITER_SYSTEMS,
    WRITER_TEMPS,
    WRITER_NEEDS_LANG,
    CHUNK_ACTIONS,
    CHUNK_SIZE,
    SINGLE_MAX,
)


def build_user(action: str, text: str, target_lang: str) -> str:
    if action in WRITER_NEEDS_LANG and target_lang:
        return f"请将以下内容翻译为{target_lang}：\n\n{text}"
    return text


def run_action(provider, action: str, text: str, target_lang: str = "", model: str | None = None):
    """返回 SSE 字节流（async generator）。

    - 改写/润色/互译/提炼：超长自动分块，逐块流式（大文件稳定）。
    - 结构重组/参考文献整理：需全局视角，单次处理，超长截断保护。
    """
    temperature = WRITER_TEMPS.get(action, 0.6)
    system = WRITER_SYSTEMS[action]

    if action in CHUNK_ACTIONS and len(text) > CHUNK_SIZE:
        blocks = docparse.chunk_text(text, CHUNK_SIZE)
        return svc.stream_blocks(provider, system, blocks, model=model, temperature=temperature)

    work = text
    if action not in CHUNK_ACTIONS and len(work) > SINGLE_MAX:
        work = work[:SINGLE_MAX] + "\n\n（注：原文过长已截断至安全长度以保证稳定，完整结构重组建议分章节处理。）"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": build_user(action, work, target_lang)},
    ]
    return svc.stream(provider, messages, temperature=temperature, model=model)
