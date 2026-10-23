"""鉴权路由：注册 / 登录 / 刷新 / 登出 / 当前用户。"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.deps import get_current_user
from ..core.security import (
    create_token, decode_token, hash_password, password_meets_policy, verify_password,
)
from ..core.config import settings
from ..models import TokenBlacklist, User, UserRole, Role
from ..schemas import (
    LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserInfo,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DB = Depends(get_db)


@router.post("/register", response_model=dict)
async def register(req: RegisterRequest, db: AsyncSession = DB):
    if not password_meets_policy(req.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="密码强度不足（需≥8位，含大小写、数字、特殊字符）",
        )
    exists = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if exists.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名或邮箱已存在")
    user = User(
        username=req.username,
        email=req.email,
        display_name=req.display_name,
        password_hash=hash_password(req.password),
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"code": 0, "data": {"id": str(user.id), "username": user.username, "status": user.status}, "message": "ok"}


@router.post("/login", response_model=dict)
async def login(req: LoginRequest, db: AsyncSession = DB):
    user = (
        await db.execute(
            select(User).where((User.username == req.account) | (User.email == req.account))
        )
    ).scalars().first()
    now = datetime.now(timezone.utc)

    if not user or user.deleted_at or not verify_password(req.password, user.password_hash):
        # 失败计数（仅当账号存在）
        if user and not user.deleted_at:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.status = "locked"
                user.locked_until = now + timedelta(minutes=settings.LOCK_MINUTES)
            await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    if user.status == "disabled":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    if user.status == "locked" and user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="账号已锁定，请稍后重试")

    # 登录成功，重置失败计数
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    await db.commit()

    access = create_token(str(user.id), "access", extra={"username": user.username})
    refresh = create_token(str(user.id), "refresh", extra={"username": user.username})
    # 计算真实角色与权限，避免硬编码空列表导致前端菜单/守卫为空
    from ..core.deps import _user_permission_codes

    role_codes = (
        await db.execute(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        )
    ).scalars().all()
    perm_codes = await _user_permission_codes(db, user)
    return {
        "code": 0,
        "data": TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserInfo(
                id=user.id, username=user.username, email=user.email,
                display_name=user.display_name, avatar_url=user.avatar_url,
                status=user.status, roles=list(role_codes), permissions=sorted(perm_codes),
            ),
        ).model_dump(),
        "message": "ok",
    }


@router.post("/refresh", response_model=dict)
async def refresh(req: RefreshRequest, db: AsyncSession = DB):
    try:
        payload = decode_token(req.refresh_token, expected_type="refresh")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效")
    blk = await db.get(TokenBlacklist, payload.get("jti"))
    if blk:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 已吊销")
    user = await db.get(User, payload["sub"])
    if not user or user.deleted_at or user.status == "disabled":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不可用")
    access = create_token(str(user.id), "access", extra={"username": user.username})
    return {"code": 0, "data": {"access_token": access, "token_type": "bearer",
                                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}, "message": "ok"}


@router.post("/logout", response_model=dict)
async def logout(req: RefreshRequest, db: AsyncSession = DB):
    try:
        payload = decode_token(req.refresh_token, expected_type="refresh")
        db.add(TokenBlacklist(jti=payload["jti"], expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)))
        await db.commit()
    except Exception:
        pass
    return {"code": 0, "message": "ok"}


@router.get("/me", response_model=dict)
async def me(user=Depends(get_current_user), db: AsyncSession = DB):
    from ..core.deps import _user_permission_codes
    role_codes = [r.code for r in user.roles]
    perm_codes = await _user_permission_codes(db, user)
    return {
        "code": 0,
        "data": UserInfo(
            id=user.id, username=user.username, email=user.email,
            display_name=user.display_name, avatar_url=user.avatar_url,
            status=user.status, roles=role_codes, permissions=sorted(perm_codes),
        ).model_dump(),
        "message": "ok",
    }
