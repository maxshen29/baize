"""模块管理路由：注册 / 配置 / 启停 / 依赖 / 注销。"""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.deps import CurrentUser, RequirePermission, invalidate_perm_cache
from ..models import (
    Module, ModuleConfig, ModuleDependency, Permission, RolePermission, UserRole,
)
from ..schemas import ModuleConfigUpdate, ModuleOut, ModuleRegister

router = APIRouter(prefix="/modules", tags=["modules"])
DB = Depends(get_db)


def _semver_ok(required: str, have: str) -> bool:
    """极简 semver 范围匹配：支持 * / ^MAJOR.MINOR.PATCH / >=x / 精确。"""
    def parse(v: str):
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", v)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)
    try:
        h = parse(have)
        if required in ("*", "", None):
            return True
        if required.startswith("^"):
            base = parse(required[1:])
            return h[0] == base[0] and h >= base
        if required.startswith(">="):
            return h >= parse(required[2:])
        if required.startswith("=="):
            return have == required[2:].strip()
        return have == required  # 精确
    except Exception:
        return False


async def _check_dependencies(db: AsyncSession, deps: list[dict] | None, self_code: str) -> None:
    if not deps:
        return
    for d in deps:
        code = d.get("code")
        if code == self_code:
            raise HTTPException(status_code=409, detail="模块不能依赖自身")
        mod = (await db.execute(select(Module).where(Module.code == code))).scalars().first()
        if not mod or mod.status == "stopped":
            raise HTTPException(status_code=409, detail=f"依赖模块不存在或已停用: {code}")
        if not _semver_ok(d.get("version", "*"), mod.version):
            raise HTTPException(status_code=409, detail=f"依赖版本不满足: {code} 需要 {d.get('version')} 当前 {mod.version}")


@router.get("", response_model=dict)
async def list_modules(_: RequirePermission("module:module:read"), db: AsyncSession = DB):
    rows = (await db.execute(select(Module).order_by(Module.order_index))).scalars().all()
    return {"code": 0, "data": [ModuleOut.model_validate(m).model_dump() for m in rows], "message": "ok"}


@router.post("/register", response_model=dict, status_code=201)
async def register_module(req: ModuleRegister, _: RequirePermission("module:module:create"), db: AsyncSession = DB):
    exists = await db.execute(select(Module).where((Module.code == req.code) | (Module.api_prefix == req.api_prefix)))
    if exists.scalars().first():
        raise HTTPException(status_code=409, detail="模块 code 或 api_prefix 已存在")
    await _check_dependencies(db, req.dependencies, req.code)

    mod = Module(
        code=req.code, name=req.name, description=req.description, version=req.version,
        entry=req.entry, api_prefix=req.api_prefix, icon=req.icon, order_index=req.order,
        config_schema=req.config_schema, dependencies=req.dependencies, status="registered",
    )
    db.add(mod)
    await db.flush()

    # 写入声明权限点（去重）
    for p in (req.permissions or []):
        existing = (await db.execute(select(Permission).where(Permission.code == p["code"]))).scalars().first()
        if not existing:
            db.add(Permission(
                code=p["code"], name=p.get("name", p["code"]), module=req.code,
                resource=p.get("resource", req.api_prefix), action=p.get("action", "*"),
                description=p.get("description"),
            ))
    # 写入依赖
    for d in (req.dependencies or []):
        dep_mod = (await db.execute(select(Module).where(Module.code == d["code"]))).scalars().first()
        if dep_mod:
            db.add(ModuleDependency(module_id=mod.id, depends_on_id=dep_mod.id, required_version=d.get("version", "*")))

    await db.commit()
    await db.refresh(mod)
    return {"code": 0, "data": ModuleOut.model_validate(mod).model_dump(), "message": "ok"}


@router.get("/{code}", response_model=dict)
async def get_module(code: str, _: RequirePermission("module:module:read"), db: AsyncSession = DB):
    mod = (await db.execute(select(Module).where(Module.code == code))).scalars().first()
    if not mod:
        raise HTTPException(status_code=404, detail="模块不存在")
    return {"code": 0, "data": ModuleOut.model_validate(mod).model_dump(), "message": "ok"}


async def _set_module_status(code: str, new_status: str, db: AsyncSession, perm: str):
    mod = (await db.execute(select(Module).where(Module.code == code))).scalars().first()
    if not mod:
        raise HTTPException(status_code=404, detail="模块不存在")
    if new_status == "enabled":
        # 启用前再次校验依赖
        deps = (await db.execute(
            select(Module.code, ModuleDependency.required_version, Module.status)
            .join(ModuleDependency, ModuleDependency.depends_on_id == Module.id)
            .where(ModuleDependency.module_id == mod.id)
        )).all()
        for dcode, ver, dstatus in deps:
            if dstatus != "enabled":
                raise HTTPException(status_code=409, detail=f"依赖未启用: {dcode}")
    mod.status = new_status
    await db.commit()
    return {"code": 0, "data": ModuleOut.model_validate(mod).model_dump(), "message": "ok"}


@router.post("/{code}/enable", response_model=dict)
async def enable(code: str, _: RequirePermission("module:module:update"), db: AsyncSession = DB):
    return await _set_module_status(code, "enabled", db, "module:module:update")


@router.post("/{code}/disable", response_model=dict)
async def disable(code: str, _: RequirePermission("module:module:update"), db: AsyncSession = DB):
    return await _set_module_status(code, "disabled", db, "module:module:update")


@router.post("/{code}/stop", response_model=dict)
async def stop(code: str, _: RequirePermission("module:module:update"), db: AsyncSession = DB):
    return await _set_module_status(code, "stopped", db, "module:module:update")


@router.post("/{code}/restart", response_model=dict)
async def restart(code: str, _: RequirePermission("module:module:update"), db: AsyncSession = DB):
    mod = (await db.execute(select(Module).where(Module.code == code))).scalars().first()
    if not mod:
        raise HTTPException(status_code=404, detail="模块不存在")
    # 触发配置重载（此处为占位，真实环境发信号/重启 worker）
    mod.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    await db.commit()
    return {"code": 0, "data": ModuleOut.model_validate(mod).model_dump(), "message": "ok"}


@router.get("/{code}/config", response_model=dict)
async def get_config(code: str, _: RequirePermission("module:module:read"), db: AsyncSession = DB):
    rows = (await db.execute(select(ModuleConfig).where(ModuleConfig.module_code == code))).scalars().all()
    return {"code": 0, "data": [
        {"config_key": c.config_key, "config_value": c.config_value, "config_type": c.config_type, "scope": c.scope}
        for c in rows
    ], "message": "ok"}


@router.put("/{code}/config", response_model=dict)
async def set_config(code: str, req: ModuleConfigUpdate, _: RequirePermission("module:module:update"), db: AsyncSession = DB):
    mod = (await db.execute(select(Module).where(Module.code == code))).scalars().first()
    if not mod:
        raise HTTPException(status_code=404, detail="模块不存在")
    for it in req.items:
        existing = (await db.execute(
            select(ModuleConfig).where(
                ModuleConfig.module_code == code, ModuleConfig.config_key == it.config_key, ModuleConfig.scope == it.scope
            )
        )).scalars().first()
        if existing:
            existing.config_value = it.config_value
            existing.config_type = it.config_type
        else:
            db.add(ModuleConfig(module_code=code, config_key=it.config_key, config_value=it.config_value,
                                config_type=it.config_type, scope=it.scope))
    await db.commit()
    return {"code": 0, "message": "ok"}


@router.get("/{code}/dependencies", response_model=dict)
async def get_dependencies(code: str, _: RequirePermission("module:module:read"), db: AsyncSession = DB):
    mod = (await db.execute(select(Module).where(Module.code == code))).scalars().first()
    if not mod:
        raise HTTPException(status_code=404, detail="模块不存在")
    rows = (
        await db.execute(
            select(Module.code, Module.name, Module.version, ModuleDependency.required_version)
            .join(ModuleDependency, ModuleDependency.depends_on_id == Module.id)
            .where(ModuleDependency.module_id == mod.id)
        )
    ).all()
    return {"code": 0, "data": [
        {"code": c, "name": n, "version": v, "required_version": rv} for c, n, v, rv in rows
    ], "message": "ok"}


@router.delete("/{code}", response_model=dict)
async def unregister(code: str, _: RequirePermission("module:module:delete"), db: AsyncSession = DB):
    mod = (await db.execute(select(Module).where(Module.code == code))).scalars().first()
    if not mod:
        raise HTTPException(status_code=404, detail="模块不存在")
    await db.delete(mod)
    await db.commit()
    return {"code": 0, "message": "ok"}
