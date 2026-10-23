"""AI 文档提炼 · 提示词装配。

四类任务：
  summary  摘要（可按篇幅调节）
  translate 翻译（指定目标语言）
  extract  要点抽取（层级化要点）
  outline  脑图大纲（Markdown 多级列表）
"""
from __future__ import annotations

TASK_LABELS: dict[str, str] = {
    "summary": "摘要",
    "translate": "翻译",
    "extract": "要点抽取",
    "outline": "脑图大纲",
}

LENGTH_GUIDE: dict[str, str] = {
    "简短": "1-2 句话，不超过 120 字，只保留核心结论。",
    "标准": "要点式，约 300 字内，保留关键论据与数据。",
    "详细": "分段叙述，约 600-800 字，保留结构、数据与出处。",
}


def build_messages(
    task: str,
    text: str,
    *,
    target_lang: str = "",
    length: str = "标准",
    model: str = "",
) -> list[dict]:
    """返回 OpenAI 兼容 messages 列表。model 参数当前预留（由调用方决定具体模型）。"""
    content = (text or "").strip()
    if task == "translate":
        tgt = target_lang or "中文"
        system = (
            f"你是一名专业翻译。请将用户提供的文本准确翻译为{tgt}，"
            "保持术语准确、语气一致；尽量保留原文的 Markdown / 列表 / 表格格式。"
            "只输出译文，不要添加解释或前言。"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": content}]

    if task == "extract":
        system = (
            "你是信息抽取专家。从用户文本中提取关键要点，以层级化要点列表呈现"
            "（核心结论 → 支撑论据），保留数字、专有名词与关键事实；剔除冗余与广告用语。"
            "使用 Markdown 无序 / 有序列表。"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": content}]

    if task == "outline":
        system = (
            "你是结构化整理助手。将用户文本整理为思维导图大纲，使用 Markdown 多级列表："
            "第一级为总主题，逐级展开关键分支与要点；保留关键数据。不要添加解释性前言。"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": content}]

    # summary（默认）
    lg = LENGTH_GUIDE.get(length, LENGTH_GUIDE["标准"])
    lang_note = "使用原文语言输出。" if not target_lang else f"用{target_lang}输出。"
    system = (
        "你是一名专业的文档摘要助手。请将用户提供的文本提炼为摘要："
        f"{lg}{lang_note}保留关键信息、结论与数据，去除冗余与重复。"
        "使用 Markdown 格式。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]
