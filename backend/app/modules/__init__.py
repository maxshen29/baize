"""AI 应用发现与挂载。

每个应用以子包形式放在 backend/modules/<pkg>/，需暴露：
  - MANIFEST: dict  应用元信息（code / name / api_prefix / entry / use_permission ...）
  - router:   APIRouter  应用路由，端点用 RequirePermission(MANIFEST["use_permission"]) 守护

discover_apps() 负责收集；mount_apps() 在 main.py 中挂载；
register_apps() 把应用 upsert 进 modules 表并写入「使用权限」、授予超级管理员。
"""
from __future__ import annotations

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

# 已知应用包（顺序即侧边栏/市场展示顺序）
APP_PACKAGES = [
    "data_analytics",
    "protein_analysis",
    "scheme",
    "digest",
    "academic_polish",
    "academic_translate",
    "academic_grammar",
    "academic_review",
    "academic_abstract",
    "academic_code",
    "academic_survey",
    "academic_explain",
    "paper_writer",
    "paper_reader",
    "chat",
    "social_sim",
]


def discover_apps() -> list[dict[str, Any]]:
    apps: list[dict[str, Any]] = []
    for pkg in APP_PACKAGES:
        try:
            mod = importlib.import_module(f"app.modules.{pkg}")
        except Exception as e:  # 单个应用导入失败不应阻断整体，但需记录以便排查
            logger.warning("[modules] 跳过应用包 %s（导入失败）：%s", pkg, e)
            continue
        manifest = getattr(mod, "MANIFEST", None)
        router = getattr(mod, "router", None)
        if manifest and router:
            apps.append({"manifest": manifest, "router": router})
            logger.info("[modules] 发现应用：%s（%s）", manifest.get("code"), manifest.get("name"))
        else:
            logger.warning("[modules] 应用包 %s 缺少 MANIFEST 或 router，已忽略", pkg)
    return apps


def mount_apps(app: FastAPI, api_prefix: str) -> None:
    # router 自身已带 MANIFEST["api_prefix"]（如 /modules/data-analytics），
    # 此处只需再叠加 API 版本前缀（如 /api/v1）。
    for a in discover_apps():
        app.include_router(a["router"], prefix=api_prefix)


async def register_apps(db: AsyncSession) -> None:
    """把应用注册进 modules 表，并写入使用权限、授予超级管理员。"""
    from sqlalchemy import select

    from ..core.deps import invalidate_perm_cache
    from ..models import Module, Permission, Role, RolePermission

    super_role = (
        await db.execute(select(Role).where(Role.code == "super_admin"))
    ).scalars().first()

    for a in discover_apps():
        m = a["manifest"]
        mod = (
            await db.execute(select(Module).where(Module.code == m["code"]))
        ).scalars().first()
        if not mod:
            mod = Module(
                code=m["code"],
                name=m["name"],
                description=m.get("description"),
                version=m.get("version", "1.0.0"),
                entry=m.get("entry"),
                api_prefix=m.get("api_prefix"),
                icon=m.get("icon"),
                order_index=m.get("order", 0),
                status="enabled",
            )
            db.add(mod)
            await db.flush()
        else:
            mod.name = m["name"]
            mod.description = m.get("description")
            mod.version = m.get("version", "1.0.0")
            mod.entry = m.get("entry")
            mod.api_prefix = m.get("api_prefix")
            mod.icon = m.get("icon")
            mod.order_index = m.get("order", 0)
            mod.status = "enabled"

        # 写入「使用权限」点（约定码：app:<code>:use）
        perm = (
            await db.execute(select(Permission).where(Permission.code == m["use_permission"]))
        ).scalars().first()
        if not perm:
            perm = Permission(
                code=m["use_permission"],
                name=m.get("use_permission_name", "使用 " + m["name"]),
                module=m["code"],
                resource=m.get("api_prefix"),
                action="use",
            )
            db.add(perm)
            await db.flush()

        # 超级管理员自动获得全部应用使用权
        if super_role:
            exists = (
                await db.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == super_role.id,
                        RolePermission.permission_id == perm.id,
                    )
                )
            ).scalars().first()
            if not exists:
                db.add(RolePermission(role_id=super_role.id, permission_id=perm.id))

    await db.commit()
    if super_role:
        invalidate_perm_cache("admin")
