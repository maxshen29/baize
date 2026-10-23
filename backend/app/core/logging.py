"""操作日志中间件：自动审计所有请求（脱敏 + 落库）。"""
import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .database import AsyncSessionLocal
from .security import decode_token
from ..models import OperationLog

_SENSITIVE = re.compile(r"(password|token|secret|authorization|pwd|credential)", re.I)
_SKIP_PATHS = ("/docs", "/openapi.json", "/redoc", "/health")


def redact(body: Any) -> Any:
    """递归剔除敏感键。"""
    if isinstance(body, dict):
        return {k: ("***" if _SENSITIVE.search(k) else redact(v)) for k, v in body.items()}
    if isinstance(body, list):
        return [redact(i) for i in body]
    return body


def extract_module_code(path: str) -> str | None:
    m = re.match(r"/api/v1/modules/([a-z0-9-]+)", path)
    return m.group(1) if m else None


class OperationLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = datetime.now(timezone.utc)
        # 读取请求体（仅 JSON）。Starlette 会缓存 body，后续端点可再次读取。
        body = None
        try:
            raw = await request.body()
            if raw:
                try:
                    body = redact(json.loads(raw))
                except Exception:
                    body = None
        except Exception:
            body = None

        response = await call_next(request)

        # 解析用户（尽力而为，失败不影响主流程）
        user_id = username = None
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = decode_token(auth[7:])
                user_id = payload.get("sub")
                username = payload.get("username") or payload.get("sub")
            except Exception:
                pass

        duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        module_code = extract_module_code(request.url.path)

        # 异步写库（不阻塞响应）
        try:
            async with AsyncSessionLocal() as db:
                log = OperationLog(
                    user_id=user_id,
                    username=username,
                    action=request.url.path,
                    resource=request.url.path,
                    method=request.method,
                    path=str(request.url.path),
                    ip=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    request_body=body,
                    response_code=response.status_code,
                    duration_ms=duration_ms,
                    module_code=module_code,
                )
                db.add(log)
                await db.commit()
        except Exception:
            pass  # 审计失败不阻断业务

        return response
