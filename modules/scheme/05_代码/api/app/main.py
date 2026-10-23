"""FastAPI 应用入口：CORS、路由挂载、健康检查。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import document, export, knowledge, template, writing
from .schemas import HealthOut


app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(template.router)
app.include_router(document.router)
app.include_router(knowledge.router)
app.include_router(writing.router)
app.include_router(export.router)


@app.get("/api/health", response_model=HealthOut, tags=["system"])
def health() -> HealthOut:
    return HealthOut(status="ok", app_name=settings.app_name, db="connected")
