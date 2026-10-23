"""AI 方案生成 · 路由。

前缀 /modules/scheme：
  模板：GET/POST /templates，PUT/DELETE /templates/{id}
  案例：GET/POST /cases，PUT/DELETE /cases/{id}
  RAG ：POST /search        素材 → 匹配的模板与案例（含相关度）
  生成：POST /generate      流式生成方案正文（SSE，OpenAI 兼容）
  导出：POST /export        由 Markdown 导出 md / docx / html
  方案库：GET /projects，GET/DELETE /projects/{id}，POST /projects 保存

权限：使用类端点由 app:scheme:use 守护；模板/案例写操作由 app:scheme:manage 守护。
"""
from __future__ import annotations

import urllib.parse
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.deps import OptionalPermission, RequirePermission
from ...models import SchemeCase, SchemeProject, SchemeTemplate
from . import service as svc
from .export import build_export
from .manifest import MANIFEST

router = APIRouter(prefix=MANIFEST["api_prefix"], tags=["app:scheme"])
DB = Depends(get_db)
PERM = RequirePermission(MANIFEST["use_permission"])
MANAGE = RequirePermission("app:scheme:manage")
# 管理员（拥有 app:scheme:view_all）可见全部方案；普通用户仅可见自己。不报错，返回布尔。
VIEW_ALL = OptionalPermission(MANIFEST["view_all_permission"])

BRIEF_KEYS = ("goal", "background", "audience", "constraints", "budget", "timeline", "extra")


def brief_to_text(brief: dict | None) -> str:
    if not brief:
        return ""
    return " ".join(str(brief.get(k) or "") for k in BRIEF_KEYS).strip()


# ------------------------------- 模板 ------------------------------- #
class SectionIn(BaseModel):
    title: str
    hint: str | None = None


class TemplateIn(BaseModel):
    name: str
    code: str | None = None
    category: str = "通用"
    description: str | None = None
    sections: list[SectionIn] = []
    tags: list[str] = []
    status: str = "active"


@router.get("/templates", response_model=dict)
async def get_templates(_: PERM, db: AsyncSession = DB):
    await svc.ensure_seeded(db)
    rows = await svc.list_templates(db)
    return {"code": 0, "data": [svc.tpl_out(t) for t in rows], "message": "ok"}


@router.post("/templates", response_model=dict)
async def create_template(body: TemplateIn, _: MANAGE, db: AsyncSession = DB):
    code = (body.code or "").strip() or f"custom_{uuid.uuid4().hex[:8]}"
    dup = (await db.execute(select(SchemeTemplate).where(SchemeTemplate.code == code))).scalars().first()
    if dup:
        raise HTTPException(status_code=400, detail="模板编码已存在")
    t = SchemeTemplate(
        code=code, name=body.name, category=body.category, description=body.description,
        sections=[s.model_dump() for s in body.sections], tags=body.tags,
        is_system=False, status=body.status,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"code": 0, "data": svc.tpl_out(t), "message": "ok"}


@router.put("/templates/{tid}", response_model=dict)
async def update_template(tid: str, body: TemplateIn, _: MANAGE, db: AsyncSession = DB):
    t = await db.get(SchemeTemplate, svc._as_uuid(tid))
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    t.name = body.name
    t.category = body.category
    t.description = body.description
    t.sections = [s.model_dump() for s in body.sections]
    t.tags = body.tags
    t.status = body.status
    await db.commit()
    await db.refresh(t)
    return {"code": 0, "data": svc.tpl_out(t), "message": "ok"}


@router.delete("/templates/{tid}", response_model=dict)
async def delete_template(tid: str, _: MANAGE, db: AsyncSession = DB):
    t = await db.get(SchemeTemplate, svc._as_uuid(tid))
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.is_system:
        raise HTTPException(status_code=400, detail="内置模板不可删除，可复制后修改")
    await db.delete(t)
    await db.commit()
    return {"code": 0, "message": "ok"}


# ------------------------------- 案例 ------------------------------- #
class CaseIn(BaseModel):
    title: str
    industry: str | None = None
    category: str | None = None
    summary: str | None = None
    content: str = ""
    tags: list[str] = []
    quality: int = 3
    source: str | None = None
    status: str = "active"


@router.get("/cases", response_model=dict)
async def get_cases(_: PERM, db: AsyncSession = DB):
    await svc.ensure_seeded(db)
    rows = await svc.list_cases(db)
    return {"code": 0, "data": [svc.case_out(c) for c in rows], "message": "ok"}


@router.post("/cases", response_model=dict)
async def create_case(body: CaseIn, _: MANAGE, db: AsyncSession = DB):
    c = SchemeCase(
        title=body.title, industry=body.industry, category=body.category,
        summary=body.summary, content=body.content, tags=body.tags,
        quality=max(1, min(5, body.quality)), source=body.source, status=body.status,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"code": 0, "data": svc.case_out(c), "message": "ok"}


@router.put("/cases/{cid}", response_model=dict)
async def update_case(cid: str, body: CaseIn, _: MANAGE, db: AsyncSession = DB):
    c = await db.get(SchemeCase, svc._as_uuid(cid))
    if not c:
        raise HTTPException(status_code=404, detail="案例不存在")
    c.title = body.title
    c.industry = body.industry
    c.category = body.category
    c.summary = body.summary
    c.content = body.content
    c.tags = body.tags
    c.quality = max(1, min(5, body.quality))
    c.source = body.source
    c.status = body.status
    await db.commit()
    await db.refresh(c)
    return {"code": 0, "data": svc.case_out(c), "message": "ok"}


@router.delete("/cases/{cid}", response_model=dict)
async def delete_case(cid: str, _: MANAGE, db: AsyncSession = DB):
    c = await db.get(SchemeCase, svc._as_uuid(cid))
    if not c:
        raise HTTPException(status_code=404, detail="案例不存在")
    await db.delete(c)
    await db.commit()
    return {"code": 0, "message": "ok"}


# ------------------------------- RAG 检索 ------------------------------- #
class SearchIn(BaseModel):
    brief: dict = {}
    topk_templates: int = 3
    topk_cases: int = 4


@router.post("/search", response_model=dict)
async def search_endpoint(body: SearchIn, _: PERM, db: AsyncSession = DB):
    await svc.ensure_seeded(db)
    text = brief_to_text(body.brief) or str(body.brief.get("materials") or "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="请先填写方案目标或素材")
    return {"code": 0, "data": await svc.search(db, text, body.topk_templates, body.topk_cases), "message": "ok"}


# ------------------------------- 生成 ------------------------------- #
class GenerateIn(BaseModel):
    brief: dict = {}
    template_id: str | None = None
    case_ids: list[str] = []
    tone: str = "专业正式"
    length: str = "标准（约 1500-2500 字）"
    model: str | None = None


@router.post("/generate")
async def generate_endpoint(body: GenerateIn, _: PERM, db: AsyncSession = DB):
    """RAG 流式生成。未显式指定模板/案例时，自动按素材检索召回（复用）。"""
    await svc.ensure_seeded(db)
    provider = await svc.get_default_provider(db)
    if provider is None:
        return {"code": 404, "message": "未配置默认大模型，请先在「系统管理 → 大模型接入」接入并设为默认。"}

    template = None
    template_id = body.template_id
    case_ids = list(body.case_ids or [])

    if not template_id or not case_ids:
        text = brief_to_text(body.brief)
        if text:
            hits = await svc.search(db, text, 1, 4)
            if not template_id and hits["templates"]:
                template_id = hits["templates"][0]["id"]
            if not case_ids:
                case_ids = [c["id"] for c in hits["cases"]]

    if template_id:
        t = await db.get(SchemeTemplate, svc._as_uuid(template_id))
        if t:
            template = svc.tpl_dict(t)

    cases: list[dict] = []
    for cid in case_ids:
        c = await db.get(SchemeCase, svc._as_uuid(cid))
        if c and c.status == "active":
            cases.append(svc.case_dict(c))

    messages = svc.generation_messages(body.brief, template, cases, body.tone, body.length)
    return StreamingResponse(
        svc.stream(provider, messages, model=body.model, temperature=0.6),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            # 便于前端展示本次实际引用的模板 / 案例
            "X-Scheme-Template": urllib.parse.quote(str(template_id or "")),
            "X-Scheme-Cases": urllib.parse.quote(",".join(str(c) for c in case_ids)),
            "Access-Control-Expose-Headers": "X-Scheme-Template, X-Scheme-Cases",
        },
    )


# ------------------------------- 导出 ------------------------------- #
class ExportIn(BaseModel):
    content: str
    fmt: str = "docx"
    title: str = "方案"


@router.post("/export")
async def export_endpoint(body: ExportIn, _: PERM):
    ext, media, data = build_export(body.content, body.fmt, body.title)
    fname = f"{body.title or '方案'}.{ext}"
    quoted = urllib.parse.quote(fname)
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )


# ------------------------------- 方案库 ------------------------------- #
class ProjectIn(BaseModel):
    title: str = "未命名方案"
    brief: dict = {}
    template_id: str | None = None
    case_ids: list[str] = []
    content: str = ""
    model: str | None = None


@router.get("/projects", response_model=dict)
async def get_projects(
    user: PERM,
    can_view_all: VIEW_ALL,
    limit: int = 30,
    offset: int = 0,
    scope: str = "all",
    db: AsyncSession = DB,
):
    """方案历史列表。

    - 普通用户：强制只看自己创建的方案（scope 参数被忽略）。
    - 管理员（app:scheme:view_all）：scope=all 看全部；scope=mine 仅看自己。
    """
    rows, total = await svc.list_projects(
        db, limit, offset, user_id=user.id, scope=scope, view_all=can_view_all
    )
    owner_map = await svc.list_owner_names(db, [p.created_by for p in rows if p.created_by])
    items = []
    for p in rows:
        d = svc.project_out(p, False)
        d["created_by_name"] = owner_map.get(str(p.created_by)) if p.created_by else None
        items.append(d)
    return {"code": 0, "data": {"total": total, "items": items}, "message": "ok"}


@router.get("/projects/{pid}", response_model=dict)
async def get_project(pid: str, user: PERM, can_view_all: VIEW_ALL, db: AsyncSession = DB):
    p = await db.get(SchemeProject, svc._as_uuid(pid))
    if not p:
        raise HTTPException(status_code=404, detail="方案不存在")
    # 非管理员只能看自己的方案；返回 404 而非 403，避免泄露他人方案的存在。
    if not can_view_all and p.created_by != user.id:
        raise HTTPException(status_code=404, detail="方案不存在")
    d = svc.project_out(p, True)
    if p.created_by:
        owner_map = await svc.list_owner_names(db, [p.created_by])
        d["created_by_name"] = owner_map.get(str(p.created_by))
    return {"code": 0, "data": d, "message": "ok"}


@router.delete("/projects/{pid}", response_model=dict)
async def delete_project(pid: str, user: PERM, can_view_all: VIEW_ALL, db: AsyncSession = DB):
    p = await db.get(SchemeProject, svc._as_uuid(pid))
    if not p:
        raise HTTPException(status_code=404, detail="方案不存在")
    # 非管理员只能删除自己的方案；返回 404 而非 403，避免泄露他人方案的存在。
    if not can_view_all and p.created_by != user.id:
        raise HTTPException(status_code=404, detail="方案不存在")
    await db.delete(p)
    await db.commit()
    return {"code": 0, "message": "ok"}


@router.post("/projects", response_model=dict)
async def create_project(body: ProjectIn, user: PERM, db: AsyncSession = DB):
    p = await svc.save_project(
        db,
        title=body.title,
        brief=body.brief,
        template_id=body.template_id,
        case_ids=body.case_ids,
        content=body.content,
        model=body.model,
        user_id=getattr(user, "id", None),
    )
    return {"code": 0, "data": svc.project_out(p, False), "message": "ok"}
