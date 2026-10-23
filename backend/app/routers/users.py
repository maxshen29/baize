"""用户管理路由：CRUD + 状态控制 + 角色分配。"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.deps import CurrentUser, RequirePermission, invalidate_perm_cache
from ..core.security import hash_password, password_meets_policy
from ..models import Role, User, UserRole
from ..schemas import Paginated, RoleAssign, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])
DB = Depends(get_db)


@router.get("", response_model=dict)
async def list_users(
    _: RequirePermission("user:user:read"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    db: AsyncSession = DB,
):
    stmt = select(User).where(User.deleted_at.is_(None))
    if status_filter:
        stmt = stmt.where(User.status == status_filter)
    if keyword:
        stmt = stmt.where((User.username.ilike(f"%{keyword}%")) | (User.display_name.ilike(f"%{keyword}%")))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar()
    rows = (
        await db.execute(stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return {"code": 0, "data": Paginated(
        items=[UserOut.model_validate(u).model_dump() for u in rows],
        total=total or 0, page=page, page_size=page_size,
    ).model_dump(), "message": "ok"}


@router.post("", response_model=dict, status_code=201)
async def create_user(
    req: UserCreate, _: RequirePermission("user:user:create"), db: AsyncSession = DB,
):
    if not password_meets_policy(req.password):
        raise HTTPException(status_code=422, detail="密码强度不足")
    exists = await db.execute(select(User).where((User.username == req.username) | (User.email == req.email)))
    if exists.scalars().first():
        raise HTTPException(status_code=409, detail="用户名或邮箱已存在")
    user = User(username=req.username, email=req.email, display_name=req.display_name,
                password_hash=hash_password(req.password), status="active")
    db.add(user)
    await db.flush()
    for rid in req.role_ids:
        role = await db.get(Role, rid)
        if role:
            db.add(UserRole(user_id=user.id, role_id=rid))
    await db.commit()
    await db.refresh(user)
    return {"code": 0, "data": UserOut.model_validate(user).model_dump(), "message": "ok"}


@router.get("/{user_id}", response_model=dict)
async def get_user(user_id: UUID, _: RequirePermission("user:user:read"), db: AsyncSession = DB):
    user = await db.get(User, user_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 0, "data": UserOut.model_validate(user).model_dump(), "message": "ok"}


@router.patch("/{user_id}", response_model=dict)
async def update_user(user_id: UUID, req: UserUpdate, _: RequirePermission("user:user:update"), db: AsyncSession = DB):
    user = await db.get(User, user_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="用户不存在")
    if req.display_name is not None:
        user.display_name = req.display_name
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url
    if req.status is not None:
        user.status = req.status
        if req.status != "locked":
            user.locked_until = None
            user.failed_login_attempts = 0
    if req.password is not None:
        if not password_meets_policy(req.password):
            raise HTTPException(status_code=422, detail="密码强度不足")
        user.password_hash = hash_password(req.password)
        invalidate_perm_cache(user.username)
    await db.commit()
    return {"code": 0, "data": UserOut.model_validate(user).model_dump(), "message": "ok"}


@router.delete("/{user_id}", response_model=dict)
async def delete_user(user_id: UUID, _: RequirePermission("user:user:delete"), db: AsyncSession = DB):
    user = await db.get(User, user_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.deleted_at = func.now()
    invalidate_perm_cache(user.username)
    await db.commit()
    return {"code": 0, "message": "ok"}


async def _set_status(user_id: UUID, new_status: str, db: AsyncSession):
    user = await db.get(User, user_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = new_status
    if new_status != "locked":
        user.locked_until = None
        user.failed_login_attempts = 0
    await db.commit()
    return {"code": 0, "data": UserOut.model_validate(user).model_dump(), "message": "ok"}


@router.post("/{user_id}/enable", response_model=dict)
async def enable(user_id: UUID, _: RequirePermission("user:user:update"), db: AsyncSession = DB):
    return await _set_status(user_id, "active", db)


@router.post("/{user_id}/disable", response_model=dict)
async def disable(user_id: UUID, _: RequirePermission("user:user:update"), db: AsyncSession = DB):
    return await _set_status(user_id, "disabled", db)


@router.post("/{user_id}/lock", response_model=dict)
async def lock(user_id: UUID, _: RequirePermission("user:user:update"), db: AsyncSession = DB):
    return await _set_status(user_id, "locked", db)


@router.post("/{user_id}/unlock", response_model=dict)
async def unlock(user_id: UUID, _: RequirePermission("user:user:update"), db: AsyncSession = DB):
    return await _set_status(user_id, "active", db)


@router.put("/{user_id}/roles", response_model=dict)
async def set_roles(user_id: UUID, req: RoleAssign, _: RequirePermission("user:user:update"), db: AsyncSession = DB):
    user = await db.get(User, user_id)
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="用户不存在")
    await db.execute(UserRole.__table__.delete().where(UserRole.user_id == user_id))
    for rid in req.role_ids:
        if await db.get(Role, rid):
            db.add(UserRole(user_id=user_id, role_id=rid))
    invalidate_perm_cache(user.username)
    await db.commit()
    return {"code": 0, "message": "ok"}
