"""AI 数据分析 · 路由（均以 app:data-analytics:use 守护）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.deps import RequirePermission
from ...core.llm import chat_stream
from ...models import LlmProvider
from .manifest import MANIFEST
from .service import get_dataset, insights, list_datasets

router = APIRouter(prefix=MANIFEST["api_prefix"], tags=["app:data-analytics"])
DB = Depends(get_db)
PERM = RequirePermission(MANIFEST["use_permission"])


class InsightsReq(BaseModel):
    dataset_id: str


class DataChatIn(BaseModel):
    messages: list[dict]
    data_profile: str = ""
    model: str | None = None
    temperature: float = 0.6


@router.get("/datasets", response_model=dict)
async def datasets(_: PERM, db: AsyncSession = DB):
    return {"code": 0, "data": list_datasets(), "message": "ok"}


@router.get("/datasets/{ds_id}", response_model=dict)
async def dataset(ds_id: str, _: PERM, db: AsyncSession = DB):
    d = get_dataset(ds_id)
    if not d:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return {"code": 0, "data": d, "message": "ok"}


@router.post("/insights", response_model=dict)
async def insights_endpoint(req: InsightsReq, _: PERM, db: AsyncSession = DB):
    return {"code": 0, "data": insights(req.dataset_id), "message": "ok"}


async def _get_default_provider(db: AsyncSession) -> LlmProvider | None:
    return (
        await db.execute(select(LlmProvider).where(LlmProvider.is_default == True))  # noqa: E712
    ).scalars().first()


@router.post("/ai/chat")
async def data_chat(body: DataChatIn, _: PERM, db: AsyncSession = DB):
    """基于已上传数据画像的流式对话（SSE，透传 OpenAI 兼容大模型）。"""
    provider = await _get_default_provider(db)
    if provider is None:
        return {"code": 404, "message": "未配置默认大模型，请先在系统管理接入并设为默认。"}
    system = (
        "你是专业的数据分析助手，服务于「AI 数据分析」模块。\n"
        "以下是用户上传数据的基本画像（由系统自动计算，请据此作答）：\n\n"
        f"{body.data_profile}\n\n"
        "要求：\n"
        "1. 仅基于上述数据给出科学、可操作的结论，不要编造数据中没有的信息；\n"
        "2. 涉及数值时给出具体指标，必要时建议合适的图表类型；\n"
        "3. 若数据不足以回答，请明确说明并给出补充采集建议；\n"
        "4. 使用简体中文，Markdown 排版，结论前置。"
    )
    messages = [{"role": "system", "content": system}, *body.messages]
    return StreamingResponse(
        chat_stream(provider, messages, model=body.model, temperature=body.temperature),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
