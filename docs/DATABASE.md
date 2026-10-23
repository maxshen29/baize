# 数据库表结构设计（PostgreSQL）

> 配套 DDL 见 `backend/sql/init.sql`。所有主键为 UUID，时间字段统一 `timestamptz`（UTC）。
> 命名约定：权限 `code = {module}:{resource}:{action}`。

## 核心表清单

| 表 | 作用 |
|----|------|
| `users` | 用户与账号状态 |
| `roles` | 角色定义 |
| `permissions` | 细粒度权限点 |
| `user_roles` | 用户↔角色（多对多） |
| `role_permissions` | 角色↔权限（多对多） |
| `user_permissions` | 用户级权限覆盖（grant/deny） |
| `modules` | 模块注册中心 |
| `module_dependencies` | 模块版本化依赖图 |
| `module_configs` | 模块键值配置 |
| `operation_logs` | 操作/审计日志 |
| `token_blacklist` | Refresh Token 吊销表 |

---

## 字段说明（节选关键表）

### users（用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | VARCHAR(64) | 登录名，唯一 |
| email | VARCHAR(255) | 邮箱，唯一，可空 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| display_name | VARCHAR(128) | 昵称 |
| status | ENUM | `active`/`disabled`/`locked` |
| failed_login_attempts | INT | 连续失败次数（达阈值锁定） |
| locked_until | TIMESTAMPTZ | 锁定解除时间 |
| last_login_at | TIMESTAMPTZ | 最近登录时间 |
| created_by | UUID | 创建者（审计） |
| deleted_at | TIMESTAMPTZ | 软删除标记 |

### roles（角色）
| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(64) | 机器名，唯一；如 `super_admin` |
| is_system | BOOLEAN | 系统角色，禁止删除 |
| status | ENUM | 同用户状态语义 |

### permissions（权限点）
| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(128) | 唯一，如 `user:user:read` |
| module | VARCHAR(64) | 所属模块 code |
| resource | VARCHAR(255) | 受控资源/接口前缀 |
| action | VARCHAR(32) | `read`/`write`/`delete`/`*` |

### modules（模块注册中心）
| 字段 | 类型 | 说明 |
|------|------|------|
| code | VARCHAR(64) | 模块唯一标识 |
| version | VARCHAR(32) | 语义化版本 `MAJOR.MINOR.PATCH` |
| entry | VARCHAR(255) | 前端入口路由，如 `/modules/scheme` |
| api_prefix | VARCHAR(128) | 后端接口前缀，如 `/api/v1/modules/scheme` |
| status | ENUM | `registered`/`enabled`/`disabled`/`stopped` |
| config_schema | JSONB | 配置表单 schema（驱动前端渲染） |
| dependencies | JSONB | 依赖快照 `[{code,version}]` |

### module_dependencies（依赖）
| 字段 | 类型 | 说明 |
|------|------|------|
| module_id / depends_on_id | UUID | 依赖关系两端 |
| required_version | VARCHAR(64) | semver 约束，如 `^1.2.0` |

### operation_logs（审计）
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id / username | UUID/VARCHAR | 操作人 |
| action / resource | VARCHAR | 动作与资源 |
| method / path | VARCHAR | HTTP 方法/路径 |
| ip / user_agent | VARCHAR/TEXT | 来源 |
| request_body | JSONB | 脱敏请求体 |
| response_code / duration_ms | INT | 响应码/耗时 |
| module_code | VARCHAR(64) | 所属模块 |

### token_blacklist（令牌吊销）
| 字段 | 类型 | 说明 |
|------|------|------|
| jti | VARCHAR(64) | JWT ID，主键 |
| expires_at | TIMESTAMPTZ | 原过期时间，用于清理 |

---

## 关系图（ER 概览）

```
users ──< user_roles >── roles ──< role_permissions >── permissions
  │            │                     │
  └──< user_permissions >────────────┘ (effect: grant/deny)

modules ──< module_dependencies >── modules  (自引用依赖图)
modules ──< module_configs

operation_logs ──(user_id)──> users
token_blacklist (独立，按 jti 校验)
```

## 设计要点
- **RBAC + 用户覆盖**：角色批量授权，用户级 `user_permissions` 可做精细化拒绝/追加。
- **软删除**：`users.deleted_at` 保留审计链，不物理删除。
- **配置与依赖解耦**：`module_configs` 按 `scope` 支持全局/租户/用户级；`module_dependencies` 支持版本约束与环检测。
- **审计脱敏**：`operation_logs.request_body` 落库前剔除 `password`/`token` 等敏感键。
