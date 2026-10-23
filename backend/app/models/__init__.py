"""SQLAlchemy 模型：9 张核心表。对应 backend/sql/init.sql。"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    BigInteger,
    DateTime,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


# ---------- 枚举 ----------
class UserStatus(str):
    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"


class ModuleStatus(str):
    REGISTERED = "registered"
    ENABLED = "enabled"
    DISABLED = "disabled"
    STOPPED = "stopped"


class PermEffect(str):
    GRANT = "grant"
    DENY = "deny"


# ---------- 用户 ----------
class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(Enum("active", "disabled", "locked", name="user_status"), default="active", server_default=text("'active'"), nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles", back_populates="users", lazy="selectin"
    )


# ---------- 角色 ----------
class Role(Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    status: Mapped[str] = mapped_column(Enum("active", "disabled", "locked", name="user_status"), default="active", server_default=text("'active'"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users: Mapped[list["User"]] = relationship(secondary="user_roles", back_populates="roles", lazy="selectin")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions", back_populates="roles", lazy="selectin"
    )


# ---------- 权限 ----------
class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    roles: Mapped[list["Role"]] = relationship(secondary="role_permissions", back_populates="permissions", lazy="selectin")


# ---------- 关联表 ----------
class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class UserPermission(Base):
    __tablename__ = "user_permissions"
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    effect: Mapped[str] = mapped_column(Enum("grant", "deny", name="perm_effect"), nullable=False)


# ---------- 模块 ----------
class Module(Base):
    __tablename__ = "modules"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    version: Mapped[str] = mapped_column(String(32), default="0.1.0", nullable=False)
    entry: Mapped[str | None] = mapped_column(String(255))
    api_prefix: Mapped[str | None] = mapped_column(String(128), unique=True)
    status: Mapped[str] = mapped_column(
        Enum("registered", "enabled", "disabled", "stopped", name="module_status"),
        default="registered", nullable=False,
    )
    config_schema: Mapped[dict | None] = mapped_column(JSONB)
    icon: Mapped[str | None] = mapped_column(String(64))
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dependencies: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class ModuleDependency(Base):
    __tablename__ = "module_dependencies"
    module_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True)
    depends_on_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True)
    required_version: Mapped[str] = mapped_column(String(64), default="*", nullable=False)


class ModuleConfig(Base):
    __tablename__ = "module_configs"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    module_code: Mapped[str] = mapped_column(String(64), ForeignKey("modules.code", ondelete="CASCADE"), nullable=False)
    config_key: Mapped[str] = mapped_column(String(128), nullable=False)
    config_value: Mapped[dict | None] = mapped_column(JSONB)
    config_type: Mapped[str] = mapped_column(String(32), default="string", nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="global", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("module_code", "config_key", "scope", name="uq_module_config"),)


# ---------- 审计 / 令牌 ----------
class OperationLog(Base):
    __tablename__ = "operation_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True))
    username: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str | None] = mapped_column(String(128))
    resource: Mapped[str | None] = mapped_column(String(255))
    method: Mapped[str | None] = mapped_column(String(16))
    path: Mapped[str | None] = mapped_column(String(512))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    request_body: Mapped[dict | None] = mapped_column(JSONB)
    response_code: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    module_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ---------- 大模型接入（OpenAI 兼容规范） ----------
class LlmProvider(Base):
    """按 OpenAI 兼容规范接入的大模型服务（/v1/chat/completions、/v1/models）。"""
    __tablename__ = "llm_providers"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)  # 兼容 /v1 的基地址
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="gpt-3.5-turbo")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ---------- 站点设置（默认主题等） ----------
class SiteSetting(Base):
    __tablename__ = "site_settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ---------- AI 方案生成：模板 / 案例 / 方案 ----------
class SchemeTemplate(Base):
    """方案模板：章节骨架（sections）+ 占位提示，用于约束生成结构与风格。"""
    __tablename__ = "scheme_templates"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="通用")
    description: Mapped[str | None] = mapped_column(String(512))
    # [{ "title": "项目背景", "hint": "说明业务现状与痛点", "weight": 1 }]
    sections: Mapped[list | None] = mapped_column(JSONB)
    tags: Mapped[list | None] = mapped_column(JSONB)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default=text("'active'"), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SchemeCase(Base):
    """历史案例：既往方案的正文与画像，供 RAG 检索复用。"""
    __tablename__ = "scheme_cases"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(64))
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list | None] = mapped_column(JSONB)
    quality: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1-5，影响排序权重
    source: Mapped[str | None] = mapped_column(String(255))
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default=text("'active'"), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SchemeProject(Base):
    """生成的方案：素材快照 + 引用的模板/案例 + 正文（Markdown）。"""
    __tablename__ = "scheme_projects"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名方案")
    brief: Mapped[dict | None] = mapped_column(JSONB)          # 素材快照
    template_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("scheme_templates.id"))
    case_ids: Mapped[list | None] = mapped_column(JSONB)       # 引用的案例 id 列表
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="generated", server_default=text("'generated'"), nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SocialSimulation(Base):
    """社会推演 · 数字沙盘：种子素材 + 世界观 + 人物画像 + 推演记录 + 预测报告。"""
    __tablename__ = "social_simulations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="未命名推演")
    seed_text: Mapped[str] = mapped_column(Text, nullable=False, default="")     # 种子材料
    question: Mapped[str] = mapped_column(Text, nullable=False, default="")       # 预测需求
    world: Mapped[str] = mapped_column(Text, nullable=False, default="")          # 世界观/背景摘要
    setting: Mapped[str] = mapped_column(Text, nullable=False, default="")        # 时间地点群体设定
    personas: Mapped[list | None] = mapped_column(JSONB)                          # 人物画像列表
    transcript: Mapped[list | None] = mapped_column(JSONB)                        # 推演记录（逐条动作）
    report: Mapped[str] = mapped_column(Text, nullable=False, default="")         # 预测报告（Markdown）
    graph_json: Mapped[dict | None] = mapped_column(JSONB)                        # GraphRAG 节点/边 {nodes, edges}
    params: Mapped[dict | None] = mapped_column(JSONB)                            # {agents, rounds, god_events}
    model: Mapped[str | None] = mapped_column(String(128))
    created_by: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("idx_users_status", User.status)
Index("idx_modules_status", Module.status)
Index("idx_scheme_cases_status", SchemeCase.status)
Index("idx_scheme_projects_created", SchemeProject.created_at)
Index("idx_scheme_projects_owner", SchemeProject.created_by)
Index("idx_social_sim_created", SocialSimulation.created_at)
Index("idx_social_sim_owner", SocialSimulation.created_by)
