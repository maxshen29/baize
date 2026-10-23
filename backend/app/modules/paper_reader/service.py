"""综合论文阅读 · 业务装配：提示词组装、大文件分块流式、基于 BM25 的问答召回。"""
from __future__ import annotations

from ..paper_common import parse as docparse
from ..paper_common import service as svc
from .prompts import (
    READER_SYSTEMS,
    READER_TEMPS,
    READER_NEEDS_LANG,
    CHUNK_ACTIONS,
    SINGLE_MAX,
    ASK_SYSTEM,
)

_TRANSLATE_CHUNK = 4000


def build_user(action: str, text: str, target_lang: str) -> str:
    if action in READER_NEEDS_LANG and target_lang:
        return f"请将以下内容翻译为{target_lang}：\n\n{text}"
    return text


def run_action(provider, action: str, text: str, target_lang: str = "", model: str | None = None):
    """返回 SSE 字节流：摘要/脑图/提炼单次处理；全文翻译分块流式。"""
    temperature = READER_TEMPS.get(action, 0.5)
    system = READER_SYSTEMS[action]

    if action in CHUNK_ACTIONS and len(text) > _TRANSLATE_CHUNK:
        blocks = docparse.chunk_text(text, _TRANSLATE_CHUNK)
        return svc.stream_blocks(provider, system, blocks, model=model, temperature=temperature)

    work = text
    if len(work) > SINGLE_MAX:
        work = work[:SINGLE_MAX] + "\n\n（注：原文过长已截断至安全长度以保证稳定。）"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": build_user(action, work, target_lang)},
    ]
    return svc.stream(provider, messages, temperature=temperature, model=model)


def run_ask(provider, text: str, question: str, history: list[dict] | None = None, model: str | None = None, topk: int = 4):
    """交互问答：BM25 召回与问题最相关的 top-k 片段，注入上下文，多轮对话。"""
    chunks = svc.retrieve(text, question, topk=topk)
    context = "\n\n---\n\n".join(chunks) if chunks else text[:SINGLE_MAX]
    system = f"{ASK_SYSTEM}\n\n【文献相关片段】\n{context}"
    messages: list[dict] = [{"role": "system", "content": system}]
    for h in history or []:
        role = h.get("role")
        if role in ("user", "assistant") and h.get("content"):
            messages.append({"role": role, "content": h["content"]})
    messages.append({"role": "user", "content": question})
    return svc.stream(provider, messages, temperature=0.5, model=model)
