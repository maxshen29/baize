"""AI 文档提炼 · 路由。

前缀 /modules/digest：
  提炼：POST /refine    SSE 流式；task ∈ {summary, translate, extract, outline}
  健康：GET  /health

权限：由 app:digest:use 守护（register_apps 自动建权限并授予超级管理员）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.deps import RequirePermission
from .manifest import MANIFEST
from . import service as svc

router = APIRouter(prefix=MANIFEST["api_prefix"], tags=["app:digest"])
DB = Depends(get_db)
PERM = RequirePermission(MANIFEST["use_permission"])

VALID_TASKS = ("summary", "translate", "extract", "outline")


class RefineIn(BaseModel):
    text: str
    task: str = "summary"
    target_lang: str = ""
    length: str = "标准"
    model: str | None = None


@router.post("/refine")
async def refine_endpoint(body: RefineIn, _: PERM, db: AsyncSession = DB):
    if not (body.text or "").strip():
        raise HTTPException(status_code=400, detail="请输入需要提炼的文档 / 网页文本")
    if body.task not in VALID_TASKS:
        raise HTTPException(status_code=400, detail="不支持的提炼任务")

    provider = await svc.get_default_provider(db)
    if provider is None:
        return {
            "code": 404,
            "message": "未配置默认大模型，请先在「系统管理 → 大模型接入」接入并设为默认。",
        }

    messages = svc.build(
        body.task,
        body.text,
        target_lang=body.target_lang,
        length=body.length,
        model=body.model or "",
    )
    return StreamingResponse(
        svc.stream(provider, messages, model=body.model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/health", response_model=dict)
async def health():
    return {"code": 0, "data": {"name": MANIFEST["name"]}, "message": "ok"}
