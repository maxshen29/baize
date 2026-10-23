"""综合论文阅读 · 路由：文件/URL 解析、提炼/翻译/脑图/摘要、交互问答。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from ...core.database import get_db
from ...core.deps import CurrentUser, User, _user_permission_codes
from ..paper_common import parse as docparse
from ..paper_common import service as svc
from .manifest import MANIFEST
from . import service as reader_svc
from .prompts import READER_SYSTEMS

router = APIRouter(prefix=MANIFEST["api_prefix"], tags=[f"app:{MANIFEST['code']}"])
DB = Depends(get_db)
perm_code = MANIFEST["use_permission"]

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}

MAX_UPLOAD = 30 * 1024 * 1024  # 30MB

_READER_NO_MODEL = "未配置默认大模型，请先在「系统管理 → 大模型接入」接入并设为默认。"


async def _check_perm(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    codes = await _user_permission_codes(db, user)
    if perm_code not in codes:
        raise HTTPException(status_code=403, detail=f"缺少权限: {perm_code}")
    return user


class RunIn(BaseModel):
    action: str
    text: str
    target_lang: str = ""
    model: str | None = None


class UrlIn(BaseModel):
    url: str


class AskIn(BaseModel):
    text: str
    question: str
    history: list[dict] = []
    model: str | None = None


@router.post("/upload")
async def upload_endpoint(
    file: UploadFile = File(...),
    _: User = Depends(_check_perm),
    db: AsyncSession = DB,
):
    name = (file.filename or "").lower()
    if not (name.endswith(".pdf") or name.endswith(".docx")):
        raise HTTPException(status_code=400, detail="仅支持 PDF / DOCX 文件")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="文件过大（上限 30MB）")
    fid, path = docparse.save_upload("paper_reader", file.filename or "doc", content)
    try:
        if name.endswith(".pdf"):
            text = docparse.extract_pdf(path)
        else:
            text = docparse.extract_docx(path)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"文档解析失败：{e}")
    return {
        "code": 0,
        "data": {"text": text, "char_count": len(text), "file_id": fid, "filename": file.filename},
        "message": "ok",
    }


@router.post("/url")
async def url_endpoint(body: UrlIn, _: User = Depends(_check_perm), db: AsyncSession = DB):
    if not (body.url or "").strip():
        raise HTTPException(status_code=400, detail="请输入 URL")
    try:
        text = docparse.extract_url(body.url)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"URL 抓取/解析失败：{e}")
    if not text.strip():
        raise HTTPException(status_code=422, detail="未能从该 URL 提取到正文内容")
    return {
        "code": 0,
        "data": {"text": text, "char_count": len(text), "url": body.url},
        "message": "ok",
    }


@router.post("/run")
async def run_endpoint(body: RunIn, _: User = Depends(_check_perm), db: AsyncSession = DB):
    if body.action not in READER_SYSTEMS:
        raise HTTPException(status_code=400, detail="未知操作")
    if not (body.text or "").strip():
        raise HTTPException(status_code=400, detail="请输入需要处理的内容")
    provider = await svc.get_default_provider(db)
    if provider is None:
        return {"code": 404, "message": _READER_NO_MODEL}
    return StreamingResponse(
        reader_svc.run_action(provider, body.action, body.text, body.target_lang, body.model),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/ask")
async def ask_endpoint(body: AskIn, _: User = Depends(_check_perm), db: AsyncSession = DB):
    if not (body.text or "").strip():
        raise HTTPException(status_code=400, detail="请先上传/输入文献内容")
    if not (body.question or "").strip():
        raise HTTPException(status_code=400, detail="请输入问题")
    provider = await svc.get_default_provider(db)
    if provider is None:
        return {"code": 404, "message": _READER_NO_MODEL}
    return StreamingResponse(
        reader_svc.run_ask(provider, body.text, body.question, body.history, body.model),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.get("/health")
async def health():
    return {"code": 0, "data": {"name": MANIFEST["name"]}, "message": "ok"}
