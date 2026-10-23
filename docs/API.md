# RESTful API 接口定义

> 版本：`/api/v1` ｜ 鉴权：Bearer JWT（Access Token）置于 `Authorization` 头
> 通用约定：
> - 成功：`200/201` + `{ "code": 0, "data": ..., "message": "ok" }`
> - 校验失败：`422` + 字段级错误
> - 未认证：`401` ｜ 无权限：`403` ｜ 资源不存在：`404`
> - 鉴权标记：`🔓 公开` / `🔒 需登录` / `🔒 perm:xxx` 需特定权限

---

## 1. 鉴权 Auth（`/api/v1/auth`）

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | /api/v1/auth/register | 🔓 | 注册新用户 |
| POST | /api/v1/auth/login | 🔓 | 密码登录，返回双令牌 |
| POST | /api/v1/auth/refresh | 🔓(refresh) | 用 refresh_token 换 access |
| POST | /api/v1/auth/logout | 🔒 | 吊销 refresh token |
| GET  | /api/v1/auth/me | 🔒 | 当前用户信息+权限码 |

### POST /auth/register
请求：
```json
{ "username": "zhang", "email": "z@x.com", "password": "Abc#1234", "display_name": "张三" }
```
- 校验：`username` 3-32 位、`password` 强度（≥8 位含大小写+数字+特殊符）、邮箱格式。
响应 `201`：
```json
{ "code":0, "data": { "id":"uuid", "username":"zhang", "status":"active" }, "message":"ok" }
```

### POST /auth/login
请求：`{ "account": "zhang|z@x.com", "password": "..." }`
响应 `200`：
```json
{ "code":0, "data": {
  "access_token":"eyJ...", "refresh_token":"eyJ...", "token_type":"bearer",
  "expires_in":900, "user": {"id":"uuid","username":"zhang","status":"active"}
}, "message":"ok" }
```
- 失败：累计 `failed_login_attempts`，达 5 次锁定 `locked_until=now+15min`，返回 `423 Locked`。

### POST /auth/refresh
请求：`{ "refresh_token": "eyJ..." }` → 响应同 login（新 access）。

### GET /auth/me
响应 `200`：`{ "code":0, "data": { "id","username","display_name","status","roles":["super_admin"], "permissions":["user:user:read", ...] } }`

---

## 2. 用户管理 Users（`/api/v1/users`）

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/v1/users | 🔒 perm:user:user:read | 分页列表 |
| POST | /api/v1/users | 🔒 perm:user:user:create | 新建 |
| GET | /api/v1/users/{id} | 🔒 perm:user:user:read | 详情 |
| PATCH | /api/v1/users/{id} | 🔒 perm:user:user:update | 改资料/重置密码 |
| DELETE | /api/v1/users/{id} | 🔒 perm:user:user:delete | 软删除 |
| POST | /api/v1/users/{id}/enable | 🔒 perm:user:user:update | 启用 |
| POST | /api/v1/users/{id}/disable | 🔒 perm:user:user:update | 禁用 |
| POST | /api/v1/users/{id}/lock | 🔒 perm:user:user:update | 锁定 |
| POST | /api/v1/users/{id}/unlock | 🔒 perm:user:user:update | 解锁 |
| POST | /api/v1/users/{id}/reset-password | 🔒 perm:user:user:update | 管理员重置密码 |
| GET | /api/v1/users/{id}/roles | 🔒 perm:user:user:read | 用户角色 |
| PUT | /api/v1/users/{id}/roles | 🔒 perm:user:user:update | 设置角色 |

### GET /users（查询参数）
`?page=1&page_size=20&status=active&keyword=zhang&sort=-created_at`
响应：`{ "code":0, "data": { "items":[...], "total":132, "page":1, "page_size":20 } }`

### POST /users
请求：`{ "username","email","password","display_name","role_ids":["uuid"] }`
响应 `201`：用户对象（不含 `password_hash`）。

### PATCH /users/{id}
请求（部分字段）：`{ "display_name":"新名", "avatar_url":"..." }` 或 `{ "password":"新密码(需管理员或原密码)" }`

---

## 3. 权限管理 Permissions（`/api/v1/permissions`）

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/v1/permissions | 🔒 perm:perm:permission:read | 按模块列出权限点 |
| POST | /api/v1/permissions | 🔒 perm:perm:permission:create | 新建权限点 |
| GET | /api/v1/roles | 🔒 perm:perm:role:read | 角色列表 |
| POST | /api/v1/roles | 🔒 perm:perm:role:create | 新建角色 |
| GET | /api/v1/roles/{id} | 🔒 perm:perm:role:read | 角色详情 |
| PATCH | /api/v1/roles/{id} | 🔒 perm:perm:role:update | 改角色 |
| DELETE | /api/v1/roles/{id} | 🔒 perm:perm:role:delete | 删角色（系统角色禁止） |
| GET | /api/v1/roles/{id}/permissions | 🔒 perm:perm:role:read | 角色权限 |
| PUT | /api/v1/roles/{id}/permissions | 🔒 perm:perm:role:update | 设置角色权限 |
| GET | /api/v1/permissions/tree | 🔒 perm:perm:permission:read | 模块→权限树（前端用） |

### GET /permissions
`?module=scheme` → `[{ "id","code":"user:user:read","name","module","resource","action" }]`

### PUT /roles/{id}/permissions
请求：`{ "permission_ids":["uuid","uuid"] }` → 全量替换角色权限。

---

## 4. 模块管理 Modules（`/api/v1/modules`）

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/v1/modules | 🔒 perm:module:module:read | 模块清单 |
| POST | /api/v1/modules/register | 🔒 perm:module:module:create | 注册模块（提交 module.yaml） |
| GET | /api/v1/modules/{code} | 🔒 perm:module:module:read | 模块详情 |
| PATCH | /api/v1/modules/{code} | 🔒 perm:module:module:update | 改配置/元数据 |
| POST | /api/v1/modules/{code}/enable | 🔒 perm:module:module:update | 启用 |
| POST | /api/v1/modules/{code}/disable | 🔒 perm:module:module:update | 禁用 |
| POST | /api/v1/modules/{code}/stop | 🔒 perm:module:module:update | 停用 |
| POST | /api/v1/modules/{code}/restart | 🔒 perm:module:module:update | 重启（重载配置） |
| GET | /api/v1/modules/{code}/config | 🔒 perm:module:module:read | 读配置 |
| PUT | /api/v1/modules/{code}/config | 🔒 perm:module:module:update | 写配置 |
| GET | /api/v1/modules/{code}/dependencies | 🔒 perm:module:module:read | 依赖图 |
| DELETE | /api/v1/modules/{code} | 🔒 perm:module:module:delete | 注销模块 |

### POST /modules/register
请求（提交注册描述，等价于 `module.yaml`）：
```json
{
  "code":"scheme", "name":"方案系统", "version":"1.0.0",
  "entry":"/modules/scheme", "api_prefix":"/api/v1/modules/scheme",
  "description":"企业方案/投标生成系统",
  "dependencies":[{"code":"data-analytics","version":"^1.0.0"}],
  "config_schema":[{"key":"llm_model","label":"默认模型","type":"select","options":["gpt-4","deepseek"],"default":"deepseek"}]
}
```
- 校验：依赖是否存在、版本是否匹配、是否成环；`api_prefix` 唯一。
- 响应 `201`：模块对象（含 `status:"registered"`）。

### PUT /modules/{code}/config
请求：`{ "items":[{"config_key":"llm_model","config_value":"deepseek","scope":"global"}] }`

---

## 5. 操作日志 Audit（`/api/v1/audit`）

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | /api/v1/audit/logs | 🔒 perm:audit:log:read | 审计日志查询 |
| GET | /api/v1/audit/logs/export | 🔒 perm:audit:log:read | 导出 CSV |

### GET /audit/logs
`?user_id=&module_code=&method=&path=&from=&to=&page=&page_size=`
响应：`{ "code":0, "data": { "items":[...], "total":N } }`
`items[].request_body` 已脱敏（无 password/token 键）。

---

## 6. 业务模块接口（示例前缀 `/api/v1/modules/{code}`）

业务模块自有接口由模块自带路由包挂载于其 `api_prefix`，并复用平台鉴权依赖。例如：
- `GET /api/v1/modules/scheme/plans` → 方案系统方案列表（需 `scheme:plan:read`）
- `POST /api/v1/modules/protein/analyze` → 蛋白质界面分析（需 `protein:analysis:run`）
- `GET /api/v1/modules/data-analytics/datasets` → 数据分析数据集（需 `analytics:dataset:read`）

> 模块接口必须在注册时声明所需权限码，由平台统一纳入 `permissions` 表与 RBAC 控制。

---

## 鉴权依赖速查

| 依赖 | 行为 |
|------|------|
| `get_current_user` | 解析 JWT → 用户；校验 `status`；锁定/禁用返回 403/423 |
| `RequirePermission("x:y:z")` | 校验用户（含角色+用户覆盖）是否拥有该权限码，否则 403 |
| `get_db` | 注入异步 Session |
| `OperationLogMiddleware` | 自动记录请求到 `operation_logs` |
