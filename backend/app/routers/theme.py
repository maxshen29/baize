"""站点配色方案：平台默认主题配置（系统管理）。

默认主题存于 site_settings(theme.default)；用户在界面中的自选切换保存在浏览器本地，
不影响平台默认。管理员在此设定新用户/未自选用户的默认配色。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.deps import RequirePermission
from ..models import SiteSetting

router = APIRouter(prefix="/theme", tags=["system:theme"])
DB = Depends(get_db)
CONF = RequirePermission("theme:config")

DEFAULT_KEY = "theme.default"


class ThemeDefaultIn(BaseModel):
    theme: str


@router.get("/default", response_model=dict)
async def get_default(db: AsyncSession = DB):
    """公开端点：返回平台默认配色（登录前后均需读取，故不做鉴权）。"""
    row = await db.get(SiteSetting, DEFAULT_KEY)
    return {"code": 0, "data": (row.value if row else None), "message": "ok"}


@router.put("/default", response_model=dict)
async def set_default(body: ThemeDefaultIn, _: CONF, db: AsyncSession = DB):
    row = await db.get(SiteSetting, DEFAULT_KEY)
    if not row:
        row = SiteSetting(key=DEFAULT_KEY, value={"theme": body.theme})
        db.add(row)
    else:
        row.value = {"theme": body.theme}
    await db.commit()
    return {"code": 0, "data": {"theme": body.theme}, "message": "ok"}
