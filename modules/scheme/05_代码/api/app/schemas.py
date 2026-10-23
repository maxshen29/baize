"""Pydantic 入参/出参模型（API 契约）。

对应 OpenBidKit 的 ipc 通信 payload；前端按 OpenAPI 生成类型，避免契约漂移。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ---- 通用 ----
class HealthOut(BaseModel):
    status: str
    app_name: str
    db: str


# --------------------------------------------------------------------------- #
# 能力①：模板
# --------------------------------------------------------------------------- #
class TemplateSectionIn(BaseModel):
    title: str
    level: int = 1
    required: bool = True
    order: int = 0
    guidance: str = ""
    placeholders: list[str] = []
    source_tags: list[str] = []
    parent_id: str | None = None


class TemplateSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    template_id: str
    parent_id: str | None
    title: str
    level: int
    required: bool
    order: int
    guidance: str
    placeholders: list[str]
    source_tags: list[str]


class TemplateIn(BaseModel):
    type: str
    name: str
    scenario: str | None = None
    author: str | None = None
    tags: list[str] = []
    sections: list[TemplateSectionIn] = []


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    name: str
    scenario: str | None
    version: int
    author: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    sections: list[TemplateSectionOut] = []


# --------------------------------------------------------------------------- #
# 能力②：参考文档
# --------------------------------------------------------------------------- #
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    source_type: str
    status: str
    checksum: str | None
    tags: list[str]
    classification: str | None
    version: int
    chunk_count: int
    imported_at: datetime


class DocumentParseOut(BaseModel):
    id: str
    title: str
    status: str
    chunk_count: int
    preview: str  # 解析后的 markdown 预览（前若干字符）


# --------------------------------------------------------------------------- #
# 能力③：知识库
# --------------------------------------------------------------------------- #
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    domain: str | None = None
    applicable_template: str | None = None
    source_type: str | None = None
    document_ids: list[str] = []


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    heading_path: str | None
    content: str
    score: float
    keywords: list[str]


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


# --------------------------------------------------------------------------- #
# 能力④：撰写
# --------------------------------------------------------------------------- #
class WritingTaskIn(BaseModel):
    template_id: str | None = None
    title: str
    kb_scope: list[str] = []        # 限定检索的文档 id / 标签
    global_facts: dict[str, Any] = {}


class WritingSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    template_section_id: str | None
    title: str
    level: int
    order: int
    guidance: str
    content: str
    status: str
    citations: list[str]
    version: int
    updated_at: datetime


class WritingTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    template_id: str | None
    title: str
    kb_scope: list[str]
    global_facts: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    sections: list[WritingSectionOut] = []


class GenerateSectionRequest(BaseModel):
    regenerate: bool = False


class GenerateSectionResponse(BaseModel):
    section: WritingSectionOut
    used_hits: int
