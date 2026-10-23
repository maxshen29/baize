"""导出路由：撰写任务 -> Word（保留章节与引用）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import writing_service

router = APIRouter(prefix="/api/writing", tags=["export"])


@router.get("/tasks/{task_id}/export")
def export_task(task_id: str, db: Session = Depends(get_db)):
    try:
        data = writing_service.export_docx(db, task_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    filename = f"方案_{task_id[:8]}.docx"
    return Response(
        content=data,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
