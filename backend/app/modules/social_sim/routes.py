"""社会推演 · 路由。

前缀 /modules/social_sim：
  构建世界：POST /build-world            （JSON）
  推演沙盘：POST /simulate               （SSE 事件流）
  预测报告：POST /report                 （SSE 文本流，OpenAI 风格）
  深度互动：POST /chat                   （SSE 文本流，OpenAI 风格）
  历史存档：GET/POST /projects，GET/DELETE /projects/{id}
  健康：    GET  /health

权限：由 app:social_sim:use 守护（register_apps 自动建权限并授予超级管理员）。
历史按创建人隔离：列表与详情仅返回当前用户自己的推演。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.deps import RequirePermission
from ...models import SocialSimulation
from .manifest import MANIFEST
from . import service as svc

router = APIRouter(prefix=MANIFEST["api_prefix"], tags=["app:social_sim"])
DB = Depends(get_db)
PERM = RequirePermission(MANIFEST["use_permission"])


# --------------------------------------------------------------------------- #
# 请求体
# --------------------------------------------------------------------------- #
class BuildWorldIn(BaseModel):
    seed_text: str = ""
    question: str = ""
    num_agents: int = 8
    model: str | None = None


class ExtractGraphIn(BaseModel):
    seed_text: str = ""
    question: str = ""
    model: str | None = None


class SimulateIn(BaseModel):
    world: str = ""
    setting: str = ""
    personas: list = []
    question: str = ""
    rounds: int = 6
    god_events: dict = {}   # {round(int): event_text}
    model: str | None = None


class ReportIn(BaseModel):
    world: str = ""
    setting: str = ""
    personas: list = []
    question: str = ""
    transcript: list = []
    model: str | None = None


class ChatIn(BaseModel):
    world: str = ""
    setting: str = ""
    personas: list = []
    question: str = ""
    transcript: list = []
    report_text: str = ""
    messages: list = []     # 对话历史 [{role, content}]
    focus: str = ""         # 聚焦的虚拟居民代称（可选）
    model: str | None = None


class ProjectIn(BaseModel):
    title: str = "未命名推演"
    seed_text: str = ""
    question: str = ""
    world: str = ""
    setting: str = ""
    personas: list = []
    transcript: list = []
    report: str = ""
    graph_json: dict = {"nodes": [], "edges": []}
    params: dict = {}
    model: str | None = None


# --------------------------------------------------------------------------- #
# 通用 SSE 封装
# --------------------------------------------------------------------------- #
async def _sse_events(gen):
    async for ev in gen:
        yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


async def _sse_text(gen):
    async for delta in gen:
        yield f"data: {json.dumps({'choices': [{'delta': {'content': delta}}]}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


# --------------------------------------------------------------------------- #
# 1) 构建世界
# --------------------------------------------------------------------------- #
@router.post("/build-world")
async def build_world_endpoint(body: BuildWorldIn, _: PERM, db: AsyncSession = DB):
    provider = await svc.get_default_provider(db)
    if provider is None:
        return {
            "code": 404,
            "message": "未配置默认大模型，请先在「系统管理 → 大模型接入」接入并设为默认。",
        }
    data = await svc.build_world(
        provider, body.seed_text, body.question, body.num_agents, model=body.model,
    )
    return {"code": 0, "data": data, "message": "ok"}


# --------------------------------------------------------------------------- #
# 1b) GraphRAG：数字世界预览（抽取实体关系图谱）
# --------------------------------------------------------------------------- #
@router.post("/extract-graph")
async def extract_graph_endpoint(body: ExtractGraphIn, _: PERM, db: AsyncSession = DB):
    provider = await svc.get_default_provider(db)
    if provider is None:
        return {
            "code": 404,
            "message": "未配置默认大模型，请先在「系统管理 → 大模型接入」接入并设为默认。",
        }
    data = await svc.extract_graph(provider, body.seed_text, body.question, model=body.model)
    return {"code": 0, "data": data, "message": "ok"}


# --------------------------------------------------------------------------- #
# 2) 推演沙盘
# --------------------------------------------------------------------------- #
@router.post("/simulate")
async def simulate_endpoint(body: SimulateIn, _: PERM, db: AsyncSession = DB):
    provider = await svc.get_default_provider(db)
    if provider is None:
        return {"code": 404, "message": "未配置默认大模型，请先接入并设为默认。"}
    if not body.personas:
        raise HTTPException(status_code=400, detail="请先构建世界（personas 不能为空）")
    # god_events 键可能是字符串，统一转 int
    god_events = {}
    for k, v in (body.god_events or {}).items():
        try:
            god_events[int(k)] = str(v)
        except (ValueError, TypeError):
            continue
    gen = svc.simulate(
        provider, body.world, body.setting, body.personas, body.question,
        body.rounds, god_events, model=body.model,
    )
    return StreamingResponse(
        _sse_events(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# --------------------------------------------------------------------------- #
# 3) 预测报告
# --------------------------------------------------------------------------- #
@router.post("/report")
async def report_endpoint(body: ReportIn, _: PERM, db: AsyncSession = DB):
    provider = await svc.get_default_provider(db)
    if provider is None:
        return {"code": 404, "message": "未配置默认大模型，请先接入并设为默认。"}
    if not body.transcript:
        raise HTTPException(status_code=400, detail="请先完成推演（transcript 不能为空）")
    gen = svc.report(
        provider, body.world, body.setting, body.personas, body.question,
        body.transcript, model=body.model, rounds=body.rounds,
        agent_count=len(body.personas or []),
    )
    return StreamingResponse(
        _sse_text(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# --------------------------------------------------------------------------- #
# 4) 深度互动
# --------------------------------------------------------------------------- #
@router.post("/chat")
async def chat_endpoint(body: ChatIn, _: PERM, db: AsyncSession = DB):
    provider = await svc.get_default_provider(db)
    if provider is None:
        return {"code": 404, "message": "未配置默认大模型，请先接入并设为默认。"}
    gen = svc.chat(
        provider, body.world, body.setting, body.personas, body.question,
        body.transcript, body.report_text, body.messages, focus=body.focus, model=body.model,
    )
    return StreamingResponse(
        _sse_text(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# --------------------------------------------------------------------------- #
# 5) 历史存档（按创建人隔离）
# --------------------------------------------------------------------------- #
@router.get("/projects")
async def get_projects(user: PERM, limit: int = 30, offset: int = 0, db: AsyncSession = DB):
    rows, total = await svc.list_simulations(db, limit, offset, user_id=user.id)
    return {"code": 0, "data": {"total": total, "items": [svc.sim_out(p, False) for p in rows]}, "message": "ok"}


@router.get("/projects/{sid}")
async def get_project(sid: str, user: PERM, db: AsyncSession = DB):
    s = await db.get(SocialSimulation, svc._as_uuid(sid)) if svc._as_uuid(sid) else None
    if not s:
        raise HTTPException(status_code=404, detail="推演不存在")
    # 仅本人可查看自己的推演；返回 404 而非 403，避免泄露他人推演的存在。
    if s.created_by != user.id:
        raise HTTPException(status_code=404, detail="推演不存在")
    return {"code": 0, "data": svc.sim_out(s, True), "message": "ok"}


@router.delete("/projects/{sid}")
async def delete_project(sid: str, user: PERM, db: AsyncSession = DB):
    s = await db.get(SocialSimulation, svc._as_uuid(sid)) if svc._as_uuid(sid) else None
    if not s:
        raise HTTPException(status_code=404, detail="推演不存在")
    if s.created_by != user.id:
        raise HTTPException(status_code=404, detail="推演不存在")
    await db.delete(s)
    await db.commit()
    return {"code": 0, "message": "ok"}


@router.post("/projects")
async def create_project(body: ProjectIn, user: PERM, db: AsyncSession = DB):
    s = await svc.save_simulation(
        db,
        title=body.title,
        seed_text=body.seed_text,
        question=body.question,
        world=body.world,
        setting=body.setting,
        personas=body.personas,
        transcript=body.transcript,
        report=body.report,
        graph_json=body.graph_json,
        params=body.params,
        model=body.model,
        user_id=user.id,
    )
    return {"code": 0, "data": svc.sim_out(s, False), "message": "ok"}


@router.put("/projects/{sid}")
async def update_project(sid: str, body: ProjectIn, user: PERM, db: AsyncSession = DB):
    s = await svc.update_simulation(
        db, sid,
        title=body.title,
        seed_text=body.seed_text,
        question=body.question,
        world=body.world,
        setting=body.setting,
        personas=body.personas,
        transcript=body.transcript,
        report=body.report,
        graph_json=body.graph_json,
        params=body.params,
        model=body.model,
    )
    if not s:
        raise HTTPException(status_code=404, detail="推演不存在")
    if s.created_by != user.id:
        raise HTTPException(status_code=404, detail="推演不存在")
    return {"code": 0, "data": svc.sim_out(s, False), "message": "ok"}


@router.get("/health")
async def health():
    return {"code": 0, "data": {"name": MANIFEST["name"]}, "message": "ok"}
