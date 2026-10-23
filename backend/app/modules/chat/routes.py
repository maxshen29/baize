"""AI 对话应用 · 路由。

对话本身由系统级大模型服务（/api/v1/llm/chat）提供流式补全；本模块仅作为 AI 应用市场的
一个应用入口被自动注册（生成 app:chat:use 权限并挂载前端视图）。保留一个健康检查端点。
"""
from __future__ import annotations

from fastapi import APIRouter

from .manifest import MANIFEST

router = APIRouter(prefix=MANIFEST["api_prefix"], tags=["app:chat"])


@router.get("/health", response_model=dict)
async def health():
    return {"code": 0, "data": {"name": MANIFEST["name"]}, "message": "ok"}
