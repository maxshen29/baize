"""Pydantic v2 请求/响应模型（数据校验层）。"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- 通用响应 ----------
class APIResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: object | None = None


# ---------- 鉴权 ----------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)


class LoginRequest(BaseModel):
    account: str  # username 或 email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserInfo"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- 用户 ----------
class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    status: str
    roles: list[str] = []
    permissions: list[str] = []


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)
    role_ids: list[UUID] = []


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    avatar_url: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    status: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    status: str
    created_at: datetime
    last_login_at: datetime | None = None


class Paginated(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


# ---------- 角色 / 权限 ----------
class RoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(max_length=128)
    description: str | None = None
    permission_ids: list[UUID] = []


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool
    status: str


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    module: str
    resource: str
    action: str
    description: str | None = None


class PermAssign(BaseModel):
    permission_ids: list[UUID]


class RoleAssign(BaseModel):
    role_ids: list[UUID]


# ---------- 模块 ----------
class ConfigItem(BaseModel):
    config_key: str
    config_value: object | None = None
    config_type: str = "string"
    scope: str = "global"


class ModuleRegister(BaseModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    name: str = Field(max_length=128)
    version: str = Field(default="0.1.0", pattern=r"^\d+\.\d+\.\d+.*")
    description: str | None = None
    entry: str = Field(pattern=r"^/modules/.*")
    api_prefix: str = Field(pattern=r"^/api/v1/modules/.*")
    icon: str | None = None
    order: int = 0
    config_schema: list[dict] | None = None
    dependencies: list[dict] | None = None
    permissions: list[dict] | None = None


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    description: str | None = None
    version: str
    entry: str | None = None
    api_prefix: str | None = None
    status: str
    icon: str | None = None
    order_index: int
    dependencies: list | None = None
    config_schema: list | None = None


class ModuleConfigUpdate(BaseModel):
    items: list[ConfigItem]


# ---------- 审计 ----------
class OperationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: UUID | None = None
    username: str | None = None
    action: str | None = None
    resource: str | None = None
    method: str | None = None
    path: str | None = None
    ip: str | None = None
    request_body: dict | None = None
    response_code: int | None = None
    duration_ms: int | None = None
    module_code: str | None = None
    created_at: datetime
