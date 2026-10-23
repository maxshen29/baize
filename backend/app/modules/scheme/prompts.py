"""方案生成 · 提示词构建（纯函数，无框架依赖）。

RAG 装配顺序：角色设定 → 输出契约 → 模板骨架 → 历史案例片段 → 用户素材 → 风格要求。
"""
from __future__ import annotations

SYSTEM_PROMPT = (
    "你是资深方案架构师，擅长把零散素材整理为结构完整、可直接交付的正式方案。\n"
    "你会收到：方案模板（章节骨架）、历史案例片段（供借鉴做法与措辞）、用户素材。\n"
    "写作要求：\n"
    "1. 严格按模板的章节顺序与小节标题输出，保持标题层级一致；\n"
    "2. 充分吸收历史案例中可复用的做法、指标口径与表述，但不要照抄与本次目标无关的内容；\n"
    "3. 素材未提供的信息，给出合理的行业惯例建议并标注「（待确认）」，不得编造具体数据、人名或价格；\n"
    "4. 尽量给出可执行的细节：步骤、里程碑、交付物、验收标准、风险与应对；\n"
    "5. 使用简体中文；输出**纯 Markdown 正文**（从一级标题开始），不要输出解释性前言或代码围栏包裹全文；\n"
    "6. 适当使用表格（如里程碑、预算、风险登记册）与有序/无序列表提升可读性。"
)

BRIEF_LABELS = [
    ("goal", "方案目标"),
    ("background", "背景与现状"),
    ("audience", "目标受众/客户"),
    ("constraints", "约束条件"),
    ("budget", "预算/资源"),
    ("timeline", "时间要求"),
    ("extra", "其他补充"),
]


def _lines(items: list[tuple[str, str]]) -> str:
    return "\n".join(f"- {k}：{v}" for k, v in items if v)


def build_generation_messages(
    brief: dict,
    template: dict | None,
    cases: list[dict],
    tone: str = "专业正式",
    length: str = "标准（约 1500-2500 字）",
) -> list[dict]:
    """构建 RAG 生成消息，返回 OpenAI 兼容 messages 列表。"""
    parts: list[str] = []

    if template:
        sec_lines = []
        for i, s in enumerate(template.get("sections") or [], 1):
            if isinstance(s, dict):
                hint = s.get("hint") or ""
                sec_lines.append(f"{i}. {s.get('title', '')}" + (f"（{hint}）" if hint else ""))
            else:
                sec_lines.append(f"{i}. {s}")
        parts.append(
            "【方案模板】" + str(template.get("name", ""))
            + (f"（类别：{template.get('category')}）" if template.get("category") else "")
            + "\n章节骨架：\n" + "\n".join(sec_lines)
        )
    else:
        parts.append(
            "【方案模板】未指定，请采用通用商务方案骨架：项目背景与目标、需求分析、总体方案、"
            "实施计划与里程碑、资源与预算、风险与应对、预期收益、附录。"
        )

    if cases:
        ref = []
        for i, c in enumerate(cases, 1):
            head = f"案例{i}：{c.get('title', '')}"
            meta = " / ".join(x for x in [c.get("industry"), c.get("category")] if x)
            if meta:
                head += f"（{meta}）"
            ref.append(head + "\n" + (c.get("excerpt") or ""))
        parts.append("【历史案例参考（按与本次目标的相关度排序）】\n" + "\n\n".join(ref))
    else:
        parts.append("【历史案例参考】无匹配案例，请依据行业通用最佳实践撰写。")

    brief_items = [(label, str(brief.get(key) or "").strip()) for key, label in BRIEF_LABELS]
    parts.append("【用户素材】\n" + (_lines(brief_items) or "- 目标：未填写（请先给出合理假设）"))

    parts.append(f"【风格要求】语气：{tone}；篇幅：{length}。")

    parts.append(
        "【任务】请基于以上模板骨架、案例参考与用户素材，生成一份完整的方案正文 Markdown。"
        "开头用一级标题写出方案名称，随后按模板章节展开；结尾附「待确认事项」清单。"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


def build_title(brief: dict, template: dict | None) -> str:
    """从素材/模板推导方案标题。"""
    goal = str(brief.get("goal") or "").strip()
    if goal:
        return goal if len(goal) <= 30 else goal[:30] + "…"
    if template and template.get("name"):
        return str(template["name"])
    return "未命名方案"
