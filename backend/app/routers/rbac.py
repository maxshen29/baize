"""权限管理路由：角色与权限点的 CRUD + 授权。"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.deps import CurrentUser, RequirePermission, invalidate_perm_cache
from ..models import Permission, Role, RolePermission, UserRole
from ..schemas import (
    Paginated, PermAssign, PermissionOut, RoleCreate, RoleOut, RoleUpdate,
)

router = APIRouter(tags=["rbac"])
DB = Depends(get_db)


# ---------- 角色 ----------
@router.get("/roles", response_model=dict)
async def list_roles(_: RequirePermission("perm:role:read"), db: AsyncSession = DB):
    rows = (await db.execute(select(Role).order_by(Role.code))).scalars().all()
    return {"code": 0, "data": [RoleOut.model_validate(r).model_dump() for r in rows], "message": "ok"}


@router.post("/roles", response_model=dict, status_code=201)
async def create_role(req: RoleCreate, _: RequirePermission("perm:role:create"), db: AsyncSession = DB):
    exists = await db.execute(select(Role).where(Role.code == req.code))
    if exists.scalars().first():
        raise HTTPException(status_code=409, detail="角色 code 已存在")
    role = Role(code=req.code, name=req.name, description=req.description)
    db.add(role)
    await db.flush()
    for pid in req.permission_ids:
        if await db.get(Permission, pid):
            db.add(RolePermission(role_id=role.id, permission_id=pid))
    await db.commit()
    await db.refresh(role)
    return {"code": 0, "data": RoleOut.model_validate(role).model_dump(), "message": "ok"}


@router.get("/roles/{role_id}", response_model=dict)
async def get_role(role_id: UUID, _: RequirePermission("perm:role:read"), db: AsyncSession = DB):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"code": 0, "data": RoleOut.model_validate(role).model_dump(), "message": "ok"}


@router.patch("/roles/{role_id}", response_model=dict)
async def update_role(role_id: UUID, req: RoleUpdate, _: RequirePermission("perm:role:update"), db: AsyncSession = DB):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if req.name is not None:
        role.name = req.name
    if req.description is not None:
        role.description = req.description
    if req.status is not None:
        role.status = req.status
    await db.commit()
    return {"code": 0, "data": RoleOut.model_validate(role).model_dump(), "message": "ok"}


@router.delete("/roles/{role_id}", response_model=dict)
async def delete_role(role_id: UUID, _: RequirePermission("perm:role:delete"), db: AsyncSession = DB):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统角色不可删除")
    await db.delete(role)
    await db.commit()
    return {"code": 0, "message": "ok"}


@router.get("/roles/{role_id}/permissions", response_model=dict)
async def role_permissions(role_id: UUID, _: RequirePermission("perm:role:read"), db: AsyncSession = DB):
    rows = (
        await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
    ).scalars().all()
    return {"code": 0, "data": [PermissionOut.model_validate(p).model_dump() for p in rows], "message": "ok"}


@router.put("/roles/{role_id}/permissions", response_model=dict)
async def set_role_permissions(role_id: UUID, req: PermAssign, _: RequirePermission("perm:role:update"), db: AsyncSession = DB):
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    await db.execute(RolePermission.__table__.delete().where(RolePermission.role_id == role_id))
    for pid in req.permission_ids:
        if await db.get(Permission, pid):
            db.add(RolePermission(role_id=role_id, permission_id=pid))
    # 失效受影响的用户权限缓存
    users = (await db.execute(select(UserRole.user_id).where(UserRole.role_id == role_id))).scalars().all()
    for uid in users:
        u = await db.get(User, uid)
        if u:
            invalidate_perm_cache(u.username)
    await db.commit()
    return {"code": 0, "message": "ok"}


# ---------- 权限点 ----------
@router.get("/permissions", response_model=dict)
async def list_permissions(_: RequirePermission("perm:permission:read"), module: str | None = None, db: AsyncSession = DB):
    stmt = select(Permission)
    if module:
        stmt = stmt.where(Permission.module == module)
    rows = (await db.execute(stmt.order_by(Permission.module, Permission.code))).scalars().all()
    return {"code": 0, "data": [PermissionOut.model_validate(p).model_dump() for p in rows], "message": "ok"}


@router.post("/permissions", response_model=dict, status_code=201)
async def create_permission(
    code: str, name: str, module: str, resource: str, action: str,
    description: str | None = None, _: RequirePermission("perm:permission:create") = None, db: AsyncSession = DB,
):
    if await db.get(Permission, None) is not None:
        pass
    exists = await db.execute(select(Permission).where(Permission.code == code))
    if exists.scalars().first():
        raise HTTPException(status_code=409, detail="权限 code 已存在")
    perm = Permission(code=code, name=name, module=module, resource=resource, action=action, description=description)
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return {"code": 0, "data": PermissionOut.model_validate(perm).model_dump(), "message": "ok"}


@router.get("/permissions/tree", response_model=dict)
async def permission_tree(_: RequirePermission("perm:permission:read"), db: AsyncSession = DB):
    rows = (await db.execute(select(Permission).order_by(Permission.module))).scalars().all()
    tree: dict[str, list] = {}
    for p in rows:
        tree.setdefault(p.module, []).append(PermissionOut.model_validate(p).model_dump())
    return {"code": 0, "data": tree, "message": "ok"}
