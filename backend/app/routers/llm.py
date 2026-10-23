"""大模型接入管理（系统管理）：按 OpenAI 兼容规范接入并链接大模型。

端点（前缀 /llm）：
  GET    /providers              列出全部接入配置（api_key 脱敏）
  POST   /providers              新增接入
  PUT    /providers/{id}         更新接入
  DELETE /providers/{id}         删除接入
  POST   /providers/{id}/test    连通性测试
  POST   /providers/{id}/set-default  设为默认
  GET    /default                获取默认接入 + 其模型列表
  GET    /models                 默认接入的模型列表
  POST   /chat                   流式对话（SSE，被 AI 应用市场的对话应用调用）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.deps import RequirePermission
from ..core.llm import chat_stream, list_models, test_connection
from ..models import LlmProvider

router = APIRouter(prefix="/llm", tags=["system:llm"])
DB = Depends(get_db)
READ = RequirePermission("llm:provider:read")
WRITE = RequirePermission("llm:provider:write")
CHAT_PERM = RequirePermission("app:chat:use")


class ProviderIn(BaseModel):
    name: str
    base_url: str
    api_key: str
    model: str = "gpt-3.5-turbo"
    is_default: bool = False
    notes: str | None = None


def _mask(p: LlmProvider) -> dict:
    key = p.api_key or ""
    masked = (key[:4] + "****" + key[-4:]) if len(key) > 8 else "****"
    return {
        "id": str(p.id),
        "name": p.name,
        "base_url": p.base_url,
        "api_key_masked": masked,
        "model": p.model,
        "is_default": p.is_default,
        "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


async def _clear_other_defaults(db: AsyncSession, except_id: str | None = None) -> None:
    stmt = select(LlmProvider).where(LlmProvider.is_default == True)  # noqa: E712
    if except_id:
        stmt = stmt.where(LlmProvider.id != except_id)
    for p in (await db.execute(stmt)).scalars().all():
        p.is_default = False


async def _get_default(db: AsyncSession) -> LlmProvider | None:
    return (
        await db.execute(select(LlmProvider).where(LlmProvider.is_default == True))  # noqa: E712
    ).scalars().first()


@router.get("/providers", response_model=dict)
async def list_providers(_: READ, db: AsyncSession = DB):
    rows = (await db.execute(select(LlmProvider).order_by(LlmProvider.created_at))).scalars().all()
    return {"code": 0, "data": [_mask(p) for p in rows], "message": "ok"}


@router.post("/providers", response_model=dict)
async def create_provider(body: ProviderIn, _: WRITE, db: AsyncSession = DB):
    if body.is_default:
        await _clear_other_defaults(db)
    provider = LlmProvider(
        name=body.name,
        base_url=body.base_url,
        api_key=body.api_key,
        model=body.model,
        is_default=body.is_default,
        notes=body.notes,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return {"code": 0, "data": _mask(provider), "message": "ok"}


@router.put("/providers/{pid}", response_model=dict)
async def update_provider(pid: str, body: ProviderIn, _: WRITE, db: AsyncSession = DB):
    provider = await db.get(LlmProvider, pid)
    if not provider:
        return {"code": 404, "message": "未找到该接入配置"}
    if body.is_default and not provider.is_default:
        await _clear_other_defaults(db, except_id=pid)
    provider.name = body.name
    provider.base_url = body.base_url
    # 编辑时若前端传 '__KEEP__' 表示保留原密钥不变
    if body.api_key and body.api_key != "__KEEP__":
        provider.api_key = body.api_key
    provider.model = body.model
    provider.is_default = body.is_default
    provider.notes = body.notes
    await db.commit()
    await db.refresh(provider)
    return {"code": 0, "data": _mask(provider), "message": "ok"}


@router.delete("/providers/{pid}", response_model=dict)
async def delete_provider(pid: str, _: WRITE, db: AsyncSession = DB):
    provider = await db.get(LlmProvider, pid)
    if not provider:
        return {"code": 404, "message": "未找到该接入配置"}
    await db.delete(provider)
    await db.commit()
    return {"code": 0, "message": "ok"}


@router.post("/providers/{pid}/test", response_model=dict)
async def test_provider(pid: str, _: WRITE, db: AsyncSession = DB):
    provider = await db.get(LlmProvider, pid)
    if not provider:
        return {"code": 404, "message": "未找到该接入配置"}
    result = await test_connection(provider)
    return {
        "code": 0,
        "data": result,
        "message": "连接成功" if result["ok"] else (result.get("error") or "连接失败"),
    }


@router.post("/providers/{pid}/set-default", response_model=dict)
async def set_default(pid: str, _: WRITE, db: AsyncSession = DB):
    provider = await db.get(LlmProvider, pid)
    if not provider:
        return {"code": 404, "message": "未找到该接入配置"}
    await _clear_other_defaults(db, except_id=pid)
    provider.is_default = True
    await db.commit()
    return {"code": 0, "message": "ok"}


@router.get("/default", response_model=dict)
async def get_default(_: READ, db: AsyncSession = DB):
    provider = await _get_default(db)
    if not provider:
        return {"code": 0, "data": None, "message": "ok"}
    try:
        models = await list_models(provider)
    except Exception:  # noqa: BLE001
        models = []
    return {"code": 0, "data": {**_mask(provider), "models": models}, "message": "ok"}


@router.get("/models", response_model=dict)
async def get_models(_: READ, db: AsyncSession = DB):
    provider = await _get_default(db)
    if not provider:
        return {"code": 0, "data": [], "message": "未配置默认大模型"}
    models = await list_models(provider)
    return {"code": 0, "data": models, "message": "ok"}


class ChatIn(BaseModel):
    messages: list[dict]
    model: str | None = None
    provider_id: str | None = None
    temperature: float = 0.7


@router.post("/chat")
async def chat(body: ChatIn, _: CHAT_PERM, db: AsyncSession = DB):
    """流式对话（透传 OpenAI 兼容 SSE）。被 AI 应用市场的对话应用调用。"""
    provider = None
    if body.provider_id:
        provider = await db.get(LlmProvider, body.provider_id)
    if provider is None:
        provider = await _get_default(db)
    if provider is None:
        return {"code": 404, "message": "未配置可用的大模型接入，请先在系统管理中接入。"}

    return StreamingResponse(
        chat_stream(provider, body.messages, model=body.model, temperature=body.temperature),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
