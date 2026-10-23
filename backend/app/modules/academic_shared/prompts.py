"""学术工具 · 共享提示词与元信息。

TOOLS：工具 key -> {label, desc, needs_lang}（顺序即侧边栏展示顺序）
ICONS：每个工具对应的前端图标（Element Plus 图标名）
TOOL_TEMPS：创作 / 发散类略高，校对 / 代码类偏低
build_messages(tool, text, target_lang) -> OpenAI 兼容 messages

参考 chatgpt_academic 的核心学术能力，拆为可独立上线的工具模块。
所有工具均保留原文 Markdown / 列表 / 表格 / 公式($...$) / 代码块格式。
"""
from __future__ import annotations

# 工具顺序即侧边栏 / 展示顺序
TOOLS: dict[str, dict] = {
    "polish": {
        "label": "论文润色",
        "desc": "提升学术表达、逻辑连贯与用词精准，保留原意",
        "needs_lang": False,
    },
    "translate": {
        "label": "中英互译",
        "desc": "学术级中英互译，术语准确、保留格式",
        "needs_lang": True,
    },
    "grammar": {
        "label": "语法纠错",
        "desc": "拼写 / 语法 / 标点校对，给出修改对照",
        "needs_lang": False,
    },
    "review": {
        "label": "审稿意见",
        "desc": "模拟审稿人给出优缺点、疑问与修改建议",
        "needs_lang": False,
    },
    "abstract": {
        "label": "摘要与亮点",
        "desc": "从全文提炼结构化摘要 + 创新点 + 关键词",
        "needs_lang": False,
    },
    "code": {
        "label": "代码解释",
        "desc": "逐段讲解代码逻辑并给出关键注释建议",
        "needs_lang": False,
    },
    "survey": {
        "label": "文献综述",
        "desc": "基于主题 / 文献生成 related works 草稿",
        "needs_lang": False,
    },
    "explain": {
        "label": "概念讲解",
        "desc": "通俗 + 严谨地讲解专业概念或公式",
        "needs_lang": False,
    },
}

# 前端侧边栏图标（Element Plus 图标名）
ICONS: dict[str, str] = {
    "polish": "EditPen",
    "translate": "Document",
    "grammar": "Edit",
    "review": "Stamp",
    "abstract": "Memo",
    "code": "DataAnalysis",
    "survey": "Collection",
    "explain": "Reading",
}

# 创作 / 发散类略高，校对 / 代码类偏低
TOOL_TEMPS: dict[str, float] = {
    "polish": 0.4,
    "translate": 0.3,
    "grammar": 0.2,
    "review": 0.6,
    "abstract": 0.4,
    "code": 0.2,
    "survey": 0.7,
    "explain": 0.5,
}


def _system_prompt(tool: str) -> str:
    if tool == "polish":
        return (
            "你是一名严谨的学术论文润色专家，具备母语级中英文写作能力。"
            "请在不改变原意、不增删核心论据的前提下对用户文本进行学术润色："
            "提升表达的准确性与学术性、优化句式与逻辑连贯、统一术语。"
            "保留原文 Markdown / 列表 / 表格 / 公式($...$) / 代码块格式。"
            "仅输出润色后的全文，不要写修改说明或前言。"
        )
    if tool == "translate":
        return (
            "你是一名专业学术翻译。请将用户文本准确翻译为目标语言，遵循学术写作规范："
            "术语精准、语气客观、句式自然；保留引用标记 [1]、公式 $...$、代码块与 Markdown "
            "列表 / 表格格式。仅输出译文，不要添加解释或前言。"
        )
    if tool == "grammar":
        return (
            "你是一名类似 Grammarly 的中英文校对专家。请对用户文本进行拼写、语法、"
            "标点与用词校对：逐处指出问题并给出修改建议；最后附上修订后的完整文本。"
            "用 Markdown：先列「问题清单」（位置 + 问题类型 + 修改建议），再给「修订全文」。"
            "保留公式与代码块原样。"
        )
    if tool == "review":
        return (
            "你是一名该领域的资深审稿人(reviewer)。请对用户提供的研究内容 / 论文草稿给出"
            "结构化审稿意见：① 总体评价；② 主要优点(Strengths)；③ 主要缺陷与疑问"
            "(Weaknesses & Major Concerns)；④ 次要问题(Minor Issues)；"
            "⑤ 可复现性 / 实验充分性；⑥ 具体修改建议与优先级。"
            "客观、专业、可操作，使用 Markdown。"
        )
    if tool == "abstract":
        return (
            "你是一名学术论文写作助手。请基于用户提供的全文 / 章节生成："
            "① 一段结构化摘要（研究背景、目的、方法、关键结果、结论），约 200-300 字；"
            "② 3-5 条核心创新点 / 贡献(Key Contributions)；③ 3-5 个关键词。"
            "使用 Markdown，简明、学术。"
        )
    if tool == "code":
        return (
            "你是一名资深软件工程师与技术写作者。请对用户提供的代码进行讲解："
            "① 用一段自然语言概述代码整体功能与输入输出；② 按逻辑块逐段说明其作用；"
            "③ 在关键位置补充分类型注释建议（以注释形式写出，不要改写原代码）。"
            "若代码有明显问题或改进点，单独列出。保留代码块格式，使用 Markdown。"
        )
    if tool == "survey":
        return (
            "你是一名文献综述写作助手。请基于用户提供的主题或若干文献摘要 / 笔记，"
            "起草一段 related works（相关工作）章节：按主题或时间脉络组织、对比不同工作的"
            "异同与演进、指出研究空白。使用 Markdown，给出可引用的综述框架"
            "（用 [作者 年份] 占位引用）。若信息不足，明确说明并给出建议补充的方向。"
        )
    if tool == "explain":
        return (
            "你是一名善于把复杂问题讲清楚的老师。请对用户提出的专业概念或公式进行讲解："
            "先用一句话通俗类比建立直觉，再给出严谨定义，随后拆解关键要素 / 推导步骤，"
            "最后给出典型示例或易错点。使用 Markdown；公式用 $...$ 书写并解释符号含义。"
        )
    return "你是一名专业的学术助手，请基于用户提供的文本完成任务，使用 Markdown 输出。"


def build_messages(tool: str, text: str, *, target_lang: str = "") -> list[dict]:
    """返回 OpenAI 兼容 messages 列表。translate 时 target_lang 生效。"""
    content = (text or "").strip()
    if tool == "translate":
        tgt = target_lang or "中文"
        system = (
            f"你是一名专业学术翻译。请将用户文本准确翻译为「{tgt}」，遵循学术写作规范："
            "术语精准、语气客观、句式自然；保留引用标记 [1]、公式 $...$、代码块与 Markdown "
            "列表 / 表格格式。仅输出译文，不要添加解释或前言。"
        )
    else:
        system = _system_prompt(tool)
    return [{"role": "system", "content": system}, {"role": "user", "content": content}]
