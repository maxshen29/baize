"""AI 蛋白分析 · 路由（以 app:protein-analysis:use 守护）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.deps import RequirePermission
from .manifest import MANIFEST
from .service import analyze

router = APIRouter(prefix=MANIFEST["api_prefix"], tags=["app:protein-analysis"])
DB = Depends(get_db)
PERM = RequirePermission(MANIFEST["use_permission"])


class AnalyzeReq(BaseModel):
    sequence: str


@router.post("/analyze", response_model=dict)
async def analyze_endpoint(req: AnalyzeReq, _: PERM, db: AsyncSession = DB):
    return {"code": 0, "data": analyze(req.sequence), "message": "ok"}
