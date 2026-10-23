"""安全工具：密码哈希、JWT 签发与校验。"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from .config import settings


# ---------- 密码 ----------
# 直接调用 bcrypt，避免 passlib 与 bcrypt>=4.1 删除 __about__ 模块导致的兼容性问题。
# 产出的 $2b$... 哈希与 passlib-bcrypt 完全兼容，已存在的账号哈希无需重设。
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def password_meets_policy(password: str) -> bool:
    """≥8 位，含大小写、数字、特殊字符。"""
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    return has_lower and has_upper and has_digit and has_special


# ---------- JWT ----------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_token(
    subject: str,
    token_type: str = "access",
    expires_delta: timedelta | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    if expires_delta is None:
        expires_delta = (
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            if token_type == "access"
            else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": _now(),
        "exp": _now() + expires_delta,
        "jti": f"{subject}-{token_type}-{int(_now().timestamp())}",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("token type mismatch")
    return payload
