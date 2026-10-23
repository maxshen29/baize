-- ============================================================
-- 白泽企业级应用开发平台 — PostgreSQL 初始化 DDL
-- 数据库版本: PostgreSQL 16
-- 说明: 所有主键使用 UUID；时间统一用 timestamptz(UTC)；
--       枚举用 ENUM 类型；模块配置与依赖用 jsonb 灵活存储。
-- ============================================================

-- 扩展
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- 提供 gen_random_uuid()

-- ============================================================
-- 枚举类型
-- ============================================================
CREATE TYPE user_status   AS ENUM ('active', 'disabled', 'locked');
CREATE TYPE module_status AS ENUM ('registered', 'enabled', 'disabled', 'stopped');
CREATE TYPE perm_effect   AS ENUM ('grant', 'deny');

-- ============================================================
-- 1. 用户表 users
-- ============================================================
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username            VARCHAR(64)  NOT NULL UNIQUE,
    email               VARCHAR(255) UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    display_name        VARCHAR(128),
    avatar_url          VARCHAR(512),
    status              user_status NOT NULL DEFAULT 'active',
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until        TIMESTAMPTZ,
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          UUID REFERENCES users(id),
    deleted_at          TIMESTAMPTZ            -- 软删除
);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_deleted ON users(deleted_at);

-- ============================================================
-- 2. 角色表 roles
-- ============================================================
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(64) NOT NULL UNIQUE,   -- 机器名，如 super_admin
    name        VARCHAR(128) NOT NULL,
    description VARCHAR(255),
    is_system   BOOLEAN NOT NULL DEFAULT FALSE, -- 系统角色不可删除
    status      user_status NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_roles_status ON roles(status);

-- ============================================================
-- 3. 权限表 permissions（细粒度）
--    code 约定: {module}:{resource}:{action}
--    例: user:user:read / module:module:stop
-- ============================================================
CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(128) NOT NULL UNIQUE,  -- 如 user:user:read
    name        VARCHAR(128) NOT NULL,
    module      VARCHAR(64)  NOT NULL,          -- 所属模块 code
    resource    VARCHAR(255) NOT NULL,          -- 受控资源/接口前缀
    action      VARCHAR(32)  NOT NULL,          -- read/write/delete/...
    description VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_perms_module ON permissions(module);
CREATE INDEX idx_perms_resource ON permissions(resource);

-- ============================================================
-- 4. 用户-角色 user_roles（多对多）
-- ============================================================
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id)   ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- ============================================================
-- 5. 角色-权限 role_permissions（多对多）
-- ============================================================
CREATE TABLE role_permissions (
    role_id      UUID NOT NULL REFERENCES roles(id)      ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- ============================================================
-- 6. 用户级权限覆盖 user_permissions
--    支持对单个用户显式授权(grant)或拒绝(deny)，覆盖角色结果
-- ============================================================
CREATE TABLE user_permissions (
    user_id       UUID NOT NULL REFERENCES users(id)      ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    effect        perm_effect NOT NULL,                    -- grant / deny
    PRIMARY KEY (user_id, permission_id)
);

-- ============================================================
-- 7. 模块表 modules（模块注册中心）
-- ============================================================
CREATE TABLE modules (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code          VARCHAR(64)  NOT NULL UNIQUE,            -- 模块唯一标识
    name          VARCHAR(128) NOT NULL,
    description   VARCHAR(512),
    version       VARCHAR(32)  NOT NULL DEFAULT '0.1.0',   -- 语义化版本
    entry         VARCHAR(255),                            -- 前端入口路由
    api_prefix    VARCHAR(128) UNIQUE,                     -- 后端接口前缀
    status        module_status NOT NULL DEFAULT 'registered',
    config_schema JSONB,                                   -- 配置表单 schema
    icon          VARCHAR(64),
    order_index   INTEGER NOT NULL DEFAULT 0,
    dependencies  JSONB,                                    -- 冗余快照 {code,version}
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    UUID REFERENCES users(id)
);
CREATE INDEX idx_modules_status ON modules(status);

-- ============================================================
-- 8. 模块依赖 module_dependencies（版本化依赖图）
-- ============================================================
CREATE TABLE module_dependencies (
    module_id       UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    depends_on_id   UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    required_version VARCHAR(64) NOT NULL DEFAULT '*',    -- semver 约束
    PRIMARY KEY (module_id, depends_on_id)
);

-- ============================================================
-- 9. 模块配置 module_configs
-- ============================================================
CREATE TABLE module_configs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_code  VARCHAR(64) NOT NULL REFERENCES modules(code) ON DELETE CASCADE,
    config_key   VARCHAR(128) NOT NULL,
    config_value JSONB,
    config_type  VARCHAR(32)  NOT NULL DEFAULT 'string',
    scope        VARCHAR(32)  NOT NULL DEFAULT 'global',  -- global/tenant/user
    description  VARCHAR(255),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by   UUID REFERENCES users(id),
    UNIQUE (module_code, config_key, scope)
);
CREATE INDEX idx_module_configs ON module_configs(module_code);

-- ============================================================
-- 10. 操作日志 operation_logs（审计）
-- ============================================================
CREATE TABLE operation_logs (
    id           BIGSERIAL PRIMARY KEY,
    user_id      UUID,
    username     VARCHAR(64),
    action       VARCHAR(128),              -- 动作描述/权限码
    resource     VARCHAR(255),
    method       VARCHAR(16),
    path         VARCHAR(512),
    ip           VARCHAR(64),
    user_agent   TEXT,
    request_body JSONB,                     -- 脱敏后的请求体
    response_code INTEGER,
    duration_ms  INTEGER,
    module_code  VARCHAR(64),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_op_logs_user ON operation_logs(user_id);
CREATE INDEX idx_op_logs_created ON operation_logs(created_at DESC);
CREATE INDEX idx_op_logs_module ON operation_logs(module_code);

-- ============================================================
-- 11. 令牌黑名单 token_blacklist（Refresh 吊销）
-- ============================================================
CREATE TABLE token_blacklist (
    jti        VARCHAR(64) PRIMARY KEY,     -- JWT 唯一标识
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_token_blacklist_exp ON token_blacklist(expires_at);

-- ============================================================
-- 初始化种子数据：超级管理员角色 + 内置权限（示例）
-- ============================================================
INSERT INTO roles (code, name, description, is_system, status)
VALUES ('super_admin', '超级管理员', '拥有平台全部权限的系统角色', TRUE, 'active')
ON CONFLICT (code) DO NOTHING;
