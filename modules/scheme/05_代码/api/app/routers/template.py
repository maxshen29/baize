"""能力①路由：可复用参考结构模板。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import TemplateIn, TemplateOut
from ..services import template_service

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(type_: str | None = None, db: Session = Depends(get_db)):
    return template_service.list_templates(db, type_)


@router.post("", response_model=TemplateOut, status_code=201)
def create_template(data: TemplateIn, db: Session = Depends(get_db)):
    return template_service.create_template(db, data)


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: Session = Depends(get_db)):
    tpl = template_service.get_template(db, template_id)
    if not tpl:
        raise HTTPException(404, "template not found")
    return tpl


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    if not template_service.delete_template(db, template_id):
        raise HTTPException(404, "template not found")
    return {"ok": True}
