"""能力①：可复用参考结构模板服务（对标 OpenBidKit templateStore）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Template, TemplateSection
from ..schemas import TemplateIn


def list_templates(db: Session, type_: str | None = None) -> list[Template]:
    stmt = select(Template)
    if type_:
        stmt = stmt.where(Template.type == type_)
    return list(db.scalars(stmt.order_by(Template.created_at.desc())).all())


def get_template(db: Session, template_id: str) -> Template | None:
    return db.get(Template, template_id)


def create_template(db: Session, data: TemplateIn) -> Template:
    tpl = Template(
        type=data.type,
        name=data.name,
        scenario=data.scenario,
        author=data.author,
        tags=list(data.tags),
    )
    db.add(tpl)
    db.flush()  # 取得 tpl.id

    for sec in data.sections:
        db.add(
            TemplateSection(
                template_id=tpl.id,
                parent_id=sec.parent_id,
                title=sec.title,
                level=sec.level,
                required=sec.required,
                order=sec.order,
                guidance=sec.guidance,
                placeholders=list(sec.placeholders),
                source_tags=list(sec.source_tags),
            )
        )
    db.commit()
    db.refresh(tpl)
    return tpl


def delete_template(db: Session, template_id: str) -> bool:
    tpl = db.get(Template, template_id)
    if not tpl:
        return False
    db.delete(tpl)
    db.commit()
    return True
