"""能力④：基于知识库按需撰写（对标 OpenBidKit contentGenerationTask /
outlineGenerationTaskV2 / templateExtractionTask）。

流程：选模板 -> 生成大纲骨架 -> 逐章检索知识库 -> LLM 生成带引用的正文 -> 导出。
详见 06_模块设计_按需撰写.md 与 11_本地知识库建设方案 §11。
"""
from __future__ import annotations

import io
from docx import Document as DocxDocument
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..infra import llm
from ..models import Template, WritingSection, WritingTask
from ..schemas import WritingTaskIn
from . import knowledge_service


def create_task(db: Session, data: WritingTaskIn) -> WritingTask:
    task = WritingTask(
        template_id=data.template_id,
        title=data.title,
        kb_scope=list(data.kb_scope),
        global_facts=data.global_facts,
    )
    db.add(task)
    db.flush()

    if data.template_id:
        tpl = db.get(Template, data.template_id)
        if tpl:
            for sec in sorted(tpl.sections, key=lambda s: (s.order, s.level)):
                db.add(
                    WritingSection(
                        task_id=task.id,
                        template_section_id=sec.id,
                        title=sec.title,
                        level=sec.level,
                        order=sec.order,
                        guidance=sec.guidance,
                    )
                )
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session) -> list[WritingTask]:
    return list(db.scalars(select(WritingTask).order_by(WritingTask.created_at.desc())).all())


def get_task(db: Session, task_id: str) -> WritingTask | None:
    return db.get(WritingTask, task_id)


def delete_task(db: Session, task_id: str) -> bool:
    task = db.get(WritingTask, task_id)
    if not task:
        return False
    db.delete(task)
    db.commit()
    return True


def generate_section(
    db: Session, task_id: str, section_id: str, regenerate: bool = False
) -> tuple[WritingSection, int]:
    task = db.get(WritingTask, task_id)
    section = db.get(WritingSection, section_id)
    if not task or not section:
        raise ValueError("task or section not found")

    # 构造检索查询
    query = " ".join(filter(None, [section.title, section.guidance]))
    applicable = None
    if task.template_id:
        tpl = db.get(Template, task.template_id)
        if tpl:
            applicable = tpl.type

    class _Req:
        query: str = query
        top_k: int = 8
        domain = None
        applicable_template = applicable
        source_type = None
        document_ids = list(task.kb_scope)

    hits = knowledge_service.search(db, _Req())

    # 组装提示词
    facts = "\n".join(f"- {k}: {v}" for k, v in (task.global_facts or {}).items()) or "（无）"
    kb_block = "\n\n".join(
        f"【参考资料 {i+1}】（来源：{h['document_title']} / {h['heading_path'] or '全文'}）\n{h['content']}"
        for i, h in enumerate(hits)
    ) or "（未检索到相关资料，请仅依据通用知识撰写并标注假设）"

    prompt = (
        "你是资深方案撰写专家。请依据「项目事实」与「参考资料」撰写下述章节的专业中文正文，"
        "要求：准确、连贯、可落地；不得编造参考资料中未出现的具体数据；"
        "在正文后另起一行用『引用：[1][2]』标注所用资料编号。\n\n"
        f"# 章节：{section.title}\n"
        f"# 撰写要点：{section.guidance or '（无）'}\n\n"
        f"# 项目事实：\n{facts}\n\n"
        f"# 参考资料：\n{kb_block}\n"
    )
    try:
        content = llm.complete(prompt, max_tokens=2400)
    except Exception as e:  # noqa: BLE001
        content = f"（生成失败：{e}）"

    section.content = content
    section.citations = [h["chunk_id"] for h in hits]
    section.status = "review"
    section.version += 1
    task.status = "generating"
    db.commit()
    db.refresh(section)
    return section, len(hits)


def export_docx(db: Session, task_id: str) -> bytes:
    """将撰写任务导出为 Word（保留章节层级与参考资料清单）。"""
    task = db.get(WritingTask, task_id)
    if not task:
        raise ValueError("task not found")

    doc = DocxDocument()
    doc.add_heading(task.title, level=0)
    for sec in sorted(task.sections, key=lambda s: (s.order, s.level)):
        if not sec.content:
            continue
        doc.add_heading(sec.title, level=min(sec.level + 1, 6))
        # 去掉引用标注尾巴，单独列出
        body = sec.content
        cites = ""
        if "引用：" in body:
            body, cites = body.split("引用：", 1)
            cites = cites.strip()
        doc.add_paragraph(body.strip())
        if cites:
            doc.add_paragraph(f"（引用：{cites}）", style="Intense Quote")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
