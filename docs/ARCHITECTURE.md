# 白泽企业级应用开发平台 — 总体架构设计

> 技术栈：Vue 3 + Vite + TypeScript（前端） / FastAPI + SQLAlchemy 2.0 + Pydantic v2（后端） / PostgreSQL 16（数据库）
> 架构风格：前后端分离 + 模块化插件式平台（Module-as-a-Service）

---

## 1. 平台定位

白泽平台是一个**可插拔的企业级应用开发底座**。它内置三大核心治理能力（用户、权限、模块），并以"模块注册制"承载任意业务系统。业务方只需按规范提供 `module.yaml` 注册文件与资源包，即可被平台纳管（注册、配置、启停、版本与依赖管理），无需重复建设账号与权限体系。

设计目标优先级：**安全性 > 可扩展性 > 可维护性 > 性能**。

---

## 2. 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 前端框架 | Vue 3（`<script setup>` + TS） | 组合式 API |
| 构建工具 | Vite 5 | 快、支持微前端式模块注入 |
| 状态管理 | Pinia | 用户态、权限码、模块清单 |
| 路由 | Vue Router 4 | 动态路由（按权限/模块注入） |
| UI 组件 | Element Plus | 企业后台风格 |
| HTTP 客户端 | Axios（封装拦截器） | 自动携带 JWT、统一错误处理 |
| 后端框架 | FastAPI | 异步、自带 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0（async） | 声明式模型 |
| 校验 | Pydantic v2 | 请求/响应强类型校验 |
| 鉴权 | PyJWT + passlib(bcrypt) | Access/Refresh 双令牌 |
| 数据库 | PostgreSQL 16 | 主库；UUID 主键、枚举、jsonb |
| 迁移 | Alembic | 版本化表结构 |
| 网关/部署 | Nginx（反向代理 + 静态托管） | 前端静态 + 后端 `/api` 反代 |

---

## 3. 总体分层架构

```
┌──────────────────────────────────────────────────────────────┐
│                        浏览器 / 客户端                          │
└───────────────┬──────────────────────────────────────────────┘
                │  HTTPS
┌───────────────▼──────────────────────────────────────────────┐
│                  Nginx（反向代理 + 静态资源）                  │
│   /            → 前端 dist 静态资源                            │
│   /api/v1/*    → 后端 FastAPI（upstream: backend:8000）        │
└───────────────┬──────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────┐
│                    FastAPI 应用层（Backend）                   │
│                                                                │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐  │
│  │ 中间件链   │  │ 依赖注入层  │  │ 路由层（Routers）       │  │
│  │ CORS       │  │ AuthDep     │  │  auth / users / roles   │  │
│  │ 操作日志   │  │ PermDep     │  │  permissions / modules  │  │
│  │ 请求校验   │  │ DB Session  │  │  audit                  │  │
│  └────────────┘  └────────────┘  └─────────────────────────┘  │
│        │                │                    │                 │
│  ┌─────▼────────────────▼────────────────────▼─────────────┐  │
│  │              服务层（Services / 业务逻辑）                │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                              │                                  │
│  ┌───────────────────────────▼──────────────────────────────┐ │
│  │        数据访问层（SQLAlchemy Models / Repositories）      │ │
│  └───────────────────────────┬──────────────────────────────┘ │
└──────────────────────────────┼─────────────────────────────────┘
                               │  asyncpg
┌──────────────────────────────▼─────────────────────────────────┐
│                       PostgreSQL 16                              │
│  users / roles / permissions / user_roles / role_permissions    │
│  modules / module_dependencies / module_configs                 │
│  operation_logs / token_blacklist                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. 三大核心模块

### 4.1 用户管理（User Management）
- **注册**：邮箱/用户名 + 密码（强度策略校验），默认状态 `active`。
- **登录**：用户名/邮箱 + 密码，错误次数累计锁定（`failed_login_attempts` / `locked_until`）。
- **个人信息维护**：昵称、头像、密码修改（需原密码）。
- **账号状态控制**：`active` / `disabled`（管理员禁用）/ `locked`（异常锁定），统一由状态机控制，影响鉴权放行。

### 4.2 权限管理（Permission Management）
- **角色定义**：角色为权限集合，支持系统角色（不可删）与自定义角色。
- **细粒度权限**：权限以 `module:resource:action` 编码（如 `user:user:read`），归属某模块。
- **基于角色的访问控制（RBAC）**：用户←多对多→角色←多对多→权限；并支持用户级直接授权/拒绝覆盖。
- **资源与接口访问控制**：后端依赖 `RequirePermission` 守卫，前端按权限码隐藏/禁用按钮与路由。

### 4.3 模块管理（Module Management）
- **注册**：提交 `module.yaml`（code、name、version、entry、api_prefix、dependencies…）。
- **配置**：`module_configs` 表存键值配置，前端按 `config_schema` 渲染表单。
- **启停**：`status` 字段（`registered`/`enabled`/`disabled`/`stopped`）；禁用后路由与接口均不可达。
- **版本与依赖**：`module_dependencies` 声明语义化版本约束，注册/启用时做依赖环与版本冲突校验。

---

## 5. 通用能力

### 5.1 鉴权机制（Authentication & Authorization）
- **双令牌**：Access Token（JWT，15min，含 `sub`/`roles`/`perms`/`jti`）+ Refresh Token（JWT，7d，存 `token_blacklist` 支持吊销）。
- **密码**：bcrypt 单向哈希，盐内置。
- **权限校验**：装饰器/依赖 `RequirePermission("user:user:read")`，未授权返回 `403`。
- **账号状态**：登录与每个受保护请求校验 `status`，被禁用/锁定返回 `403`/`423`。

### 5.2 操作日志（Operation Logging）
- **中间件**自动记录：用户、动作、资源、HTTP 方法、路径、IP、UA、请求体（脱敏）、响应码、耗时。
- 入库 `operation_logs`，提供审计查询接口与前端审计页。
- 敏感字段（密码、token）在落库前脱敏。

### 5.3 数据校验（Validation）
- **入参**：Pydantic v2 模型强校验（类型、范围、枚举、正则），错误统一返回 `422` + 字段级信息。
- **出参**：响应模型保证对外字段稳定。
- **业务规则**：服务层做唯一性、状态机、依赖校验，不依赖前端信任。

### 5.4 可扩展性设计
- **模块化**：业务模块 = `module.yaml` + 前端资源 + 后端路由包，平台动态加载。
- **插件式路由**：前端 `router` 根据 `/api/v1/modules` 返回启用的模块清单，动态 `addRoute`；后端按 `api_prefix` 挂载 `APIRouter`。
- **配置驱动**：模块配置存 `module_configs`，运行时读取，无需改代码。
- **事件/钩子**：操作日志、模块启停预留 Webhook/信号扩展点。

### 5.5 安全性设计
- CORS 白名单、HTTPS 强制、响应头安全（CSP/HSTS 由 Nginx 配）。
- JWT 短期有效 + 刷新吊销；登录失败锁定防暴破。
- 最小权限原则：默认无权限，显式授权。
- 输入校验 + 参数化查询（SQLAlchemy，防注入）。
- 软删除 + 审计留痕；敏感字段脱敏。
- 数据库最小权限账号、密钥环境隔离（`.env` + secrets）。

---

## 6. 目录结构（本仓库）

```
Baize/
├── docs/                      # 设计文档（本文档 + DATABASE/API/FRONTEND/MODULE_SPEC）
├── backend/                   # FastAPI 后端
│   ├── app/
│   │   ├── core/              # config / security / database / deps / logging
│   │   ├── models/            # SQLAlchemy 模型（9 张核心表）
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── routers/           # auth / users / roles / permissions / modules / audit
│   │   └── services/          # 业务逻辑
│   ├── sql/                   # PostgreSQL DDL（init.sql）
│   └── requirements.txt
├── frontend/                  # Vue3 前端
│   └── src/
│       ├── router/  store/  layouts/  views/  api/  components/
└── modules/                   # 已注册业务模块（迁移而来）
    ├── scheme/                # 方案系统
    ├── protein-analysis/      # 蛋白质界面分析
    └── data-analytics/        # 数据分析
```

详细内容见：
- [数据库表结构](./DATABASE.md)
- [RESTful API 接口定义](./API.md)
- [前端路由与组件划分](./FRONTEND.md)
- [模块注册与配置规范](./MODULE_SPEC.md)
