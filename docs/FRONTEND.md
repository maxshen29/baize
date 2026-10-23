# 前端路由与组件划分（Vue 3）

> 技术栈：Vue 3 + Vite + TypeScript + Pinia + Vue Router 4 + Element Plus + Axios
> 路由策略：**静态基础路由 + 动态模块路由**。登录后根据 `/modules` 返回的启用模块与用户权限码动态 `addRoute`。

---

## 1. 目录结构

```
frontend/src/
├── main.ts                  # 入口，挂载 App + Pinia + Router
├── App.vue                  # 根组件（含 <router-view>）
├── router/
│   ├── index.ts             # 路由实例 + 守卫
│   ├── routes.ts            # 静态路由（登录/404/框架布局）
│   └── moduleRoutes.ts      # 依据模块清单生成动态路由
├── store/
│   ├── user.ts              # 用户信息 + 权限码（Pinia）
│   ├── modules.ts           # 已启用模块清单
│   └── app.ts              # 侧边栏折叠等 UI 状态
├── layouts/
│   ├── BlankLayout.vue      # 登录页等无框架页
│   └── MainLayout.vue       # 顶部栏 + 侧边菜单 + 内容区
├── views/
│   ├── LoginView.vue
│   ├── DashboardView.vue
│   ├── system/
│   │   ├── UserListView.vue
│   │   ├── RoleListView.vue
│   │   ├── PermissionTree.vue
│   │   ├── ModuleManageView.vue
│   │   └── AuditLogView.vue
│   └── modules/             # 业务模块宿主（iframe 或微前端挂载）
│       └── ModuleHost.vue   # 通用宿主：按 module.code 以 iframe 加载 /modules/{code}/index.html
├── components/
│   ├── UserFormDialog.vue
│   ├── RolePermissionDrawer.vue
│   ├── ModuleConfigForm.vue
│   ├── StatusTag.vue        # 状态彩色标签（启用/禁用/锁定）
│   └── DataTable.vue        # 通用分页表格封装
├── api/
│   ├── http.ts              # Axios 实例 + 拦截器（JWT/错误）
│   ├── auth.ts
│   ├── users.ts
│   ├── rbac.ts              # roles/permissions
│   └── modules.ts
└── utils/
    ├── auth.ts             # token 存取
    └── permission.ts       # hasPerm(code) 指令/函数
```

---

## 2. 路由划分

### 静态路由（始终存在）
| path | name | component | meta |
|------|------|-----------|------|
| /login | login | LoginView | public |
| /404 | notfound | NotFound | public |
| / | layout | MainLayout | 需登录 |

### 框架内路由（需登录，位于 MainLayout）
| path | name | 组件 | 权限 |
|------|------|------|------|
| /dashboard | dashboard | DashboardView | 登录即可 |
| /system/users | sys-users | UserListView | user:user:read |
| /system/roles | sys-roles | RoleListView | perm:role:read |
| /system/permissions | sys-perms | PermissionTree | perm:permission:read |
| /system/modules | sys-modules | ModuleManageView | module:module:read |
| /system/audit | sys-audit | AuditLogView | audit:log:read |

### 动态模块路由（登录后注入）
| path | name | 组件 | 来源 |
|------|------|------|------|
| /modules/scheme | mod-scheme | ModuleHost | modules 清单 |
| /modules/protein-analysis | mod-protein | ModuleHost | modules 清单 |
| /modules/data-analytics | mod-analytics | ModuleHost | modules 清单 |

> 三类业务模块统一由 `ModuleHost` 以 iframe 嵌入 `/modules/{code}/index.html`，按 `module.code` 区分；宿主通过 `postMessage` 注入用户 token，业务模块据此调用平台接口。

> 模块路由在 `router.beforeEach` 中按需 `addRoute('layout', ...)`，仅当模块 `status=enabled` 且用户拥有对应 `*:read` 权限时展示菜单项。

---

## 3. 核心组件职责

| 组件 | 职责 |
|------|------|
| `MainLayout` | 顶部用户区 + 侧边菜单（按权限过滤）+ 面包屑 + 内容 `<router-view>` |
| `ModuleHost` | 业务模块容器：根据 `module.entry` 以 iframe 或微前端方式加载 `modules/{code}/` 静态资源 |
| `DataTable` | 通用分页/筛选/排序表格，封装加载态与空态 |
| `UserFormDialog` | 新建/编辑用户表单，含状态、角色多选 |
| `RolePermissionDrawer` | 角色权限抽屉，树形勾选权限点并保存 |
| `ModuleConfigForm` | 按 `config_schema` 动态渲染模块配置表单 |
| `StatusTag` | 账号/模块状态彩色标签 |

---

## 4. 鉴权与权限控制（前端）

- **路由守卫**：`router.beforeEach` 校验 `token` 存在；无 token → `/login`；有 token 拉取 `/auth/me` 写入 `user` store。
- **权限指令**：`v-perm="user:user:create"` 控制按钮显隐；`<el-menu>` 按 `hasPerm()` 过滤菜单。
- **HTTP 拦截器**：`http.ts` 自动附加 `Authorization: Bearer <token>`；`401` 尝试 refresh，失败跳登录；统一 `code≠0` 提示。
- **动态菜单**：侧边栏由 `modules` + `user.permissions` 生成，禁用/无权限模块不出现。

---

## 5. 与后端契约

- 所有请求走 `Axios` 封装，baseURL=`/api/v1`。
- 业务模块以"独立静态包 + iframe/微前端"接入，通过 `postMessage` 向宿主传递当前用户 token，宿主代理调用平台接口，业务模块自身不直连 DB。
- 模块需声明权限码清单，前端据此控制菜单与按钮可见性。
