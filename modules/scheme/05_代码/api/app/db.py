"""数据库引擎与会话（SQLAlchemy 2.0 同步模式）。

远程 PostgreSQL（含 pgvector）：通过 settings.database_url 注入，
不在本机起库；建表由 db/schema.sql 在服务器执行，应用侧不自动 create_all。
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


class Base(DeclarativeBase):
    """所有模型基类。"""


def get_db():
    """FastAPI 依赖：提供请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
