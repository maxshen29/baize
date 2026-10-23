"""依赖注入：当前用户、权限校验。"""
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .security import decode_token
from ..models import (
    Module, Permission, Role, RolePermission, TokenBlacklist, User, UserPermission, UserRole,
)

bearer_scheme = HTTPBearer(auto_error=False)

# 权限缓存（演示用内存缓存；生产建议用 Redis + 事件失效）
_perm_cache: dict[str, set[str]] = {}


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供凭证")
    try:
        payload = decode_token(creds.credentials, expected_type="access")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效或已过期")

    # 吊销校验（refresh 登出后 jti 入黑名单）
    jti = payload.get("jti")
    if jti:
        blk = await db.get(TokenBlacklist, jti)
        if blk:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌已吊销")

    user = await db.get(User, payload["sub"])
    if not user or user.deleted_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if user.status == "disabled":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    if user.status == "locked":
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="账号已锁定")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def _user_permission_codes(db: AsyncSession, user: User) -> set[str]:
    if user.username in _perm_cache:
        return _perm_cache[user.username]

    codes: set[str] = set()
    # 角色权限
    role_ids = (await db.execute(select(UserRole.role_id).where(UserRole.user_id == user.id))).scalars().all()
    if role_ids:
        perms = (
            await db.execute(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id.in_(role_ids))
            )
        ).scalars().all()
        codes.update(perms)

    # 用户级覆盖（grant/deny 优先）
    overrides = (
        await db.execute(
            select(Permission.code, UserPermission.effect)
            .join(UserPermission, UserPermission.permission_id == Permission.id)
            .where(UserPermission.user_id == user.id)
        )
    ).all()
    for code, effect in overrides:
        if effect == "grant":
            codes.add(code)
        else:
            codes.discard(code)

    _perm_cache[user.username] = codes
    return codes


def RequirePermission(perm_code: str) -> "Annotated[User, Depends]":
    """权限依赖工厂：返回 Annotated 类型，校验当前用户是否拥有 perm_code。"""
    async def checker(
        user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        codes = await _user_permission_codes(db, user)
        if perm_code not in codes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限: {perm_code}")
        return user

    return Annotated[User, Depends(checker)]


def OptionalPermission(perm_code: str) -> "Annotated[bool, Depends]":
    """可选权限依赖工厂：不报错，返回当前用户是否「拥有」该权限（布尔）。

    用于「管理员可见全部、普通用户仅可见自己」这类降级分支判断。
    """
    async def checker(
        user: CurrentUser,
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> bool:
        codes = await _user_permission_codes(db, user)
        return perm_code in codes

    return Annotated[bool, Depends(checker)]


def invalidate_perm_cache(username: str) -> None:
    _perm_cache.pop(username, None)
