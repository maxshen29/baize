# 模块注册与配置规范（Module Management Spec）

> 平台以"注册制"纳管业务系统。任何业务模块 = **`module.yaml` 注册文件 + 资源包**，放置于 `modules/{code}/`。
> 平台启动时扫描 `modules/` 目录并登记到 `modules` 表；也可经 `POST /api/v1/modules/register` 热注册。

---

## 1. 目录约定

```
modules/{code}/
├── module.yaml            # 必填：模块注册元数据（平台读取）
├── README.md              # 必填：模块说明
├── frontend/              # 可选：前端静态资源（构建后 dist 或源码）
├── backend/               # 可选：后端路由包（FastAPI APIRouter）
└── assets/               # 可选：图标、文档等
```

---

## 2. module.yaml 字段规范

```yaml
code: scheme                       # 必填，模块唯一标识，正则 ^[a-z][a-z0-9-]{1,63}$
name: 方案系统                      # 必填，展示名
version: 1.0.0                     # 必填，语义化版本 MAJOR.MINOR.PATCH
description: 企业方案/投标生成系统    # 可选
entry: /modules/scheme             # 必填，前端入口路由
api_prefix: /api/v1/modules/scheme # 必填，后端接口前缀（全局唯一）
icon: Document                     # 可选，菜单图标名
order: 10                          # 可选，菜单排序
status: enabled                    # 可选，registered|enabled|disabled|stopped
maintainers:                       # 可选
  - name: 张三
    email: z@x.com
# 配置表单 schema：驱动前端 ModuleConfigForm 动态渲染
config_schema:
  - key: llm_model
    label: 默认大模型
    type: select                   # string|number|boolean|select|textarea
    options: [gpt-4, deepseek]
    default: deepseek
    required: true
  - key: max_tokens
    label: 单次最大 Token
    type: number
    default: 4096
# 依赖：声明所依赖的其它模块及版本约束（semver）
dependencies:
  - code: data-analytics
    version: "^1.0.0"
# 权限码清单：模块自带的细粒度权限点（注册时写入 permissions 表）
permissions:
  - code: scheme:plan:read
    name: 查看方案
    resource: /api/v1/modules/scheme/plans
    action: read
  - code: scheme:plan:write
    name: 编辑方案
    resource: /api/v1/modules/scheme/plans
    action: write
```

### 字段校验规则
| 字段 | 规则 |
|------|------|
| `code` | `^[a-z][a-z0-9-]{1,63}$`，全局唯一 |
| `version` | 符合 SemVer 2.0 |
| `api_prefix` | 以 `/api/v1/modules/` 开头，全局唯一 |
| `entry` | 以 `/modules/` 开头 |
| `dependencies[].version` | semver 范围（npm-style，如 `^1.2.0`、`>=1.0.0`） |
| `permissions[].code` | 形如 `{code}:{resource}:{action}` |

---

## 3. 生命周期与状态机

```
registered ──enable──▶ enabled ──disable──▶ disabled
   │                     │  ▲                  │
   │                     │  └──enable----------│
   └────(register)───────┘                     │
                                 disabled ──stop──▶ stopped
                                 stopped  ──enable─▶ enabled
```

- `registered`：已登记未启用，路由/接口不可达。
- `enabled`：正常服务，菜单与接口可见。
- `disabled`：管理员临时禁用，保留配置与数据。
- `stopped`：停止运行（如维护），等效不可达。

> 任何状态切换均写 `operation_logs`（action=`module:module:*`），并触发模块启停 Webhook（扩展点）。

---

## 4. 配置管理

- 模块配置存 `module_configs` 表，按 `(module_code, config_key, scope)` 唯一。
- `scope`：`global`（全局）/ `tenant`（租户）/ `user`（用户级）。
- 读取优先级：`user > tenant > global`；前端 `ModuleConfigForm` 按 `config_schema` 渲染。
- 修改配置后调用 `POST /api/v1/modules/{code}/restart` 触发运行 reload。

---

## 5. 依赖与版本校验

- 注册/启用时校验：
  1. 依赖模块存在且 `status != stopped`；
  2. 依赖版本满足 `required_version`（semver 匹配）；
  3. 无循环依赖（拓扑排序检测）。
- 校验失败返回 `409 Conflict` 并说明冲突项。

---

## 6. 与平台集成契约

1. **鉴权**：模块后端路由必须挂载平台 `RequirePermission` 依赖；前端通过宿主注入的 token 调用平台接口。
2. **权限**：模块声明的 `permissions` 在注册时写入 `permissions` 表，可被角色分配。
3. **审计**：模块关键写操作经平台 `OperationLogMiddleware` 自动留痕（需透传 `module_code`）。
4. **数据**：业务数据表须加 `module` 前缀或独立 schema（如 `scheme_*`），避免与平台表冲突。
5. **资源托管**：前端静态包由平台 Nginx 在 `/modules/{code}/` 路径托管。

---

## 7. 已注册模块索引（本仓库迁移而来）

| code | name | version | entry | api_prefix | 来源 |
|------|------|--------|-------|-----------|------|
| scheme | 方案系统 | 1.0.0 | /modules/scheme | /api/v1/modules/scheme | `E:/project/Baize/方案系统` |
| protein-analysis | 蛋白质界面分析 | 1.0.0 | /modules/protein-analysis | /api/v1/modules/protein-analysis | `E:/project/Baize/蛋白质界面分析` |
| data-analytics | 数据分析 | 1.0.0 | /modules/data-analytics | /api/v1/modules/data-analytics | `E:/project/Baize/数据分析` |

详见各模块 `modules/{code}/module.yaml` 与 `modules/{code}/README.md`。
