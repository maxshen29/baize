"""ORM 模型（与 db/schema.sql 一一对应）。

实体关系（见 07_数据模型与存储设计）：
    Template 1──* TemplateSection
    ReferenceDocument(documents) 1──* DocumentChunk(chunks)
    WritingTask 1──1 Template ; WritingTask 1──* WritingSection
    WritingSection *──* DocumentChunk (citations，存于 JSON 数组)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .config import settings


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# 能力①：可复用参考结构模板
# --------------------------------------------------------------------------- #
class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(String(50), index=True)  # 投标/技术/实施
    name: Mapped[str] = mapped_column(String(200))
    scenario: Mapped[str | None] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    author: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    sections: Mapped[list["TemplateSection"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class TemplateSection(Base):
    __tablename__ = "template_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    template_id: Mapped[str] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("template_sections.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    level: Mapped[int] = mapped_column(Integer, default=1)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    guidance: Mapped[str] = mapped_column(Text, default="")
    placeholders: Mapped[list] = mapped_column(JSON, default=list)
    source_tags: Mapped[list] = mapped_column(JSON, default=list)

    template: Mapped["Template"] = relationship(back_populates="sections")


# --------------------------------------------------------------------------- #
# 能力②：参考文档 + 能力③：知识库切片（同一份数据，见 11_本地知识库建设方案）
# --------------------------------------------------------------------------- #
class ReferenceDocument(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(50), index=True)  # docx/pdf/md/url
    original_path: Mapped[str | None] = mapped_column(String(500))
    parsed_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="imported")  # imported/parsing/ready/error
    checksum: Mapped[str | None] = mapped_column(String(64), index=True)  # 去重
    tags: Mapped[list] = mapped_column(JSON, default=list)
    classification: Mapped[str | None] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    heading_path: Mapped[str | None] = mapped_column(String(500))  # 三、技术方案 > 3.1 架构
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    facets: Mapped[dict] = mapped_column(JSON, default=dict)  # {domain, applicable_template, source_type}
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active/merged/deprecated
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True
    )

    document: Mapped["ReferenceDocument"] = relationship(back_populates="chunks")


# --------------------------------------------------------------------------- #
# 能力④：基于知识库按需撰写
# --------------------------------------------------------------------------- #
class WritingTask(Base):
    __tablename__ = "writing_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    template_id: Mapped[str] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    kb_scope: Mapped[list] = mapped_column(JSON, default=list)  # 限定检索文档/标签
    global_facts: Mapped[dict] = mapped_column(JSON, default=dict)  # 项目级事实
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/generating/done
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    sections: Mapped[list["WritingSection"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", order_by="WritingSection.order"
    )


class WritingSection(Base):
    __tablename__ = "writing_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(
        ForeignKey("writing_tasks.id", ondelete="CASCADE"), index=True
    )
    template_section_id: Mapped[str | None] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(200))
    level: Mapped[int] = mapped_column(Integer, default=1)
    order: Mapped[int] = mapped_column(Integer, default=0)
    guidance: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/review/done
    citations: Mapped[list] = mapped_column(JSON, default=list)  # DocumentChunk.id 列表
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    task: Mapped["WritingTask"] = relationship(back_populates="sections")
