"""能力④路由：基于知识库按需撰写。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import (
    GenerateSectionRequest,
    GenerateSectionResponse,
    WritingSectionOut,
    WritingTaskIn,
    WritingTaskOut,
)
from ..services import writing_service

router = APIRouter(prefix="/api/writing", tags=["writing"])


@router.get("/tasks", response_model=list[WritingTaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return writing_service.list_tasks(db)


@router.post("/tasks", response_model=WritingTaskOut, status_code=201)
def create_task(data: WritingTaskIn, db: Session = Depends(get_db)):
    return writing_service.create_task(db, data)


@router.get("/tasks/{task_id}", response_model=WritingTaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = writing_service.get_task(db, task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    if not writing_service.delete_task(db, task_id):
        raise HTTPException(404, "task not found")
    return {"ok": True}


@router.post("/tasks/{task_id}/sections/{section_id}/generate",
             response_model=GenerateSectionResponse)
def generate_section(
    task_id: str, section_id: str,
    req: GenerateSectionRequest | None = None,
    db: Session = Depends(get_db),
):
    try:
        section, used = writing_service.generate_section(
            db, task_id, section_id, regenerate=bool(req and req.regenerate)
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    return GenerateSectionResponse(section=section, used_hits=used)
