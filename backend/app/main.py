"""FastAPI 应用入口：装配中间件、路由、生命周期。"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .core.database import AsyncSessionLocal, Base, engine
from .core.logging import OperationLogMiddleware
from .core.security import hash_password
from .models import User, Role, Permission, RolePermission, UserRole
from .routers import auth, users, rbac, modules, audit, llm, theme


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表（演示用；生产用 Alembic 迁移）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_superadmin()
    # 注册 AI 应用（upsert 进 modules 表 + 写入使用权限）
    from .modules import register_apps

    async with AsyncSessionLocal() as db:
        await register_apps(db)
    yield
    await engine.dispose()


async def _seed_superadmin():
    """播种超级管理员 + 内置权限（幂等：已初始化的库也会补齐新增权限）。"""
    from sqlalchemy import select
    from .core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        # 1) 内置权限：缺则创建（幂等，避免已初始化库缺失新权限）
        builtin = [
            ("user:user:read", "查看用户", "user", "/api/v1/users", "read"),
            ("user:user:create", "新建用户", "user", "/api/v1/users", "write"),
            ("user:user:update", "编辑用户", "user", "/api/v1/users", "write"),
            ("user:user:delete", "删除用户", "user", "/api/v1/users", "delete"),
            ("perm:role:read", "查看角色", "rbac", "/api/v1/roles", "read"),
            ("perm:role:create", "新建角色", "rbac", "/api/v1/roles", "write"),
            ("perm:role:update", "编辑角色", "rbac", "/api/v1/roles", "write"),
            ("perm:role:delete", "删除角色", "rbac", "/api/v1/roles", "delete"),
            ("perm:permission:read", "查看权限", "rbac", "/api/v1/permissions", "read"),
            ("perm:permission:create", "新建权限", "rbac", "/api/v1/permissions", "write"),
            ("module:module:read", "查看模块", "module", "/api/v1/modules", "read"),
            ("module:module:create", "注册模块", "module", "/api/v1/modules", "write"),
            ("module:module:update", "配置模块", "module", "/api/v1/modules", "write"),
            ("module:module:delete", "注销模块", "module", "/api/v1/modules", "delete"),
            ("audit:log:read", "查看审计", "audit", "/api/v1/audit", "read"),
            # 大模型接入管理
            ("llm:provider:read", "查看大模型接入", "llm", "/api/v1/llm", "read"),
            ("llm:provider:write", "管理大模型接入", "llm", "/api/v1/llm", "write"),
            # 配色方案配置
            ("theme:config", "配置配色方案", "theme", "/api/v1/theme", "write"),
            # AI 方案生成：模板与案例管理
            ("app:scheme:manage", "管理方案模板与案例", "scheme", "/api/v1/modules/scheme", "write"),
            # AI 方案生成：查看全部方案（管理员可见所有人的方案历史）
            ("app:scheme:view_all", "查看全部方案（管理员）", "scheme", "/api/v1/modules/scheme", "read"),
        ]
        perm_ids = []
        for code, name, module, res, action in builtin:
            p = (await db.execute(select(Permission).where(Permission.code == code))).scalars().first()
            if not p:
                p = Permission(code=code, name=name, module=module, resource=res, action=action)
                db.add(p)
                await db.flush()
            perm_ids.append(p.id)

        # 2) 超级管理员角色 + 授权全部内置权限
        role = (await db.execute(select(Role).where(Role.code == "super_admin"))).scalars().first()
        if not role:
            role = Role(code="super_admin", name="超级管理员", is_system=True, status="active")
            db.add(role)
            await db.flush()
        owned = set(
            (await db.execute(select(RolePermission.permission_id).where(RolePermission.role_id == role.id))).scalars().all()
        )
        for pid in perm_ids:
            if pid not in owned:
                db.add(RolePermission(role_id=role.id, permission_id=pid))

        # 3) 超级管理员用户
        admin = (await db.execute(select(User).where(User.username == "admin"))).scalars().first()
        if not admin:
            admin = User(username="admin", email="admin@baize.local", display_name="超级管理员",
                         password_hash=hash_password("Admin@123456"), status="active")
            db.add(admin)
            await db.flush()
            db.add(UserRole(user_id=admin.id, role_id=role.id))
        await db.commit()


app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(OperationLogMiddleware)

# 统一响应包装（将异常转 APIResponse 结构在中间件/异常处理器完成，此处直接挂载路由）
API_V1 = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=API_V1)
app.include_router(users.router, prefix=API_V1)
app.include_router(rbac.router, prefix=API_V1)
app.include_router(modules.router, prefix=API_V1)
app.include_router(audit.router, prefix=API_V1)

# 系统管理：大模型接入 / 配色方案默认配置
app.include_router(llm.router, prefix=API_V1)
app.include_router(theme.router, prefix=API_V1)

# 挂载 AI 应用（backend/modules/ 下各应用子包的路由）
from .modules import mount_apps

mount_apps(app, API_V1)

# 业务模块静态资源：平台根 modules/ 下的独立业务应用（如蛋白质界面分析 index.html）。
# 让 /modules/<code>/index.html 及其相对资源（_tmp_cdrcheck.js、公众号指南/*.html 等）可直接被前端 iframe 加载。
# 注意：API 路由位于 /api/v1/modules/*，与这里的 /modules 静态挂载互不冲突。
_MODULES_DIR = os.environ.get(
    "MODULES_DIR",
    os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "modules")
    ),
)
if os.path.isdir(_MODULES_DIR):
    app.mount("/modules", StaticFiles(directory=_MODULES_DIR, html=True), name="modules-static")


@app.get("/health", tags=["meta"])
async def health():
    return {"code": 0, "message": "ok"}
