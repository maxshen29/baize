"""操作日志（审计）路由。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.deps import RequirePermission
from ..models import OperationLog
from ..schemas import OperationLogOut, Paginated

router = APIRouter(prefix="/audit", tags=["audit"])
DB = Depends(get_db)


@router.get("/logs", response_model=dict)
async def list_logs(
    _: RequirePermission("audit:log:read"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user_id: str | None = None,
    module_code: str | None = None,
    method: str | None = None,
    path: str | None = None,
    from_time: str | None = None,
    to_time: str | None = None,
    db: AsyncSession = DB,
):
    stmt = select(OperationLog)
    if user_id:
        stmt = stmt.where(OperationLog.user_id == user_id)
    if module_code:
        stmt = stmt.where(OperationLog.module_code == module_code)
    if method:
        stmt = stmt.where(OperationLog.method == method.upper())
    if path:
        stmt = stmt.where(OperationLog.path.ilike(f"%{path}%"))
    if from_time:
        stmt = stmt.where(OperationLog.created_at >= datetime.fromisoformat(from_time))
    if to_time:
        stmt = stmt.where(OperationLog.created_at <= datetime.fromisoformat(to_time))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar()
    rows = (
        await db.execute(stmt.order_by(OperationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return {"code": 0, "data": Paginated(
        items=[OperationLogOut.model_validate(r).model_dump() for r in rows],
        total=total or 0, page=page, page_size=page_size,
    ).model_dump(), "message": "ok"}
