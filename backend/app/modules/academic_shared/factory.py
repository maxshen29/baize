"""学术工具 · 模块工厂。

make_module(tool) 依据共享 TOOLS 元信息，为一个学术工具生成完整的 (MANIFEST, router)，
供各独立后端包 `academic_<tool>/__init__.py` 直接暴露：

    from ..academic_shared.factory import make_module
    MANIFEST, router = make_module("polish")

每个独立模块拥有自己的权限码 `app:academic_<tool>:use`、侧边栏项与 API 前缀
`/modules/academic_<tool>`，可由 register_apps 自动建权限并授予超级管理员。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from ...core.database import get_db
from ...core.deps import CurrentUser, User, _user_permission_codes
from .prompts import TOOLS, ICONS
from . import service as svc

TOOL_ORDER: list[str] = list(TOOLS.keys())
ORDER_BASE = 21


class RunIn(BaseModel):
    """学术工具通用请求体（各工具共用）。"""

    text: str
    target_lang: str = ""
    model: str | None = None


def make_module(tool: str):
    if tool not in TOOLS:
        raise ValueError(f"unknown academic tool: {tool}")

    meta = TOOLS[tool]
    code = f"academic_{tool}"
    name = f"学术·{meta['label']}"
    order = ORDER_BASE + TOOL_ORDER.index(tool)

    MANIFEST = {
        "code": code,
        "name": name,
        "description": meta["desc"],
        "version": "1.0.0",
        "icon": ICONS.get(tool, "Reading"),
        "order": order,
        "api_prefix": f"/modules/{code}",
        "entry": f"/apps/{code}",
        "use_permission": f"app:{code}:use",
        "use_permission_name": f"使用{name}",
    }

    router = APIRouter(prefix=MANIFEST["api_prefix"], tags=[f"app:{code}"])
    DB = Depends(get_db)
    perm_code = MANIFEST["use_permission"]

    # 权限校验依赖：闭包捕获本模块的 perm_code（避免把局部变量当注解引发 Pydantic 前向引用错误）
    async def _check_perm(
        user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        codes = await _user_permission_codes(db, user)
        if perm_code not in codes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限: {perm_code}")
        return user

    @router.post("/run")
    async def run_endpoint(body: RunIn, _: User = Depends(_check_perm), db: AsyncSession = DB):
        if not (body.text or "").strip():
            raise HTTPException(status_code=400, detail="请输入需要处理的内容")
        provider = await svc.get_default_provider(db)
        if provider is None:
            return {
                "code": 404,
                "message": "未配置默认大模型，请先在「系统管理 → 大模型接入」接入并设为默认。",
            }
        messages = svc.build(tool, body.text, target_lang=body.target_lang)
        return StreamingResponse(
            svc.stream(provider, messages, tool=tool, model=body.model),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @router.get("/health")
    async def health():
        return {"code": 0, "data": {"name": name}, "message": "ok"}

    return MANIFEST, router
