# 业务模块目录（modules/）

> 本目录承载所有已注册的业务模块，每个子目录即一个独立模块，遵循 `../docs/MODULE_SPEC.md` 的注册与配置规范。
> 平台启动时可扫描本目录并自动登记（见 `backend/scripts/scan_modules.py`）。

| 目录 | code | name | version | 来源 | 说明 |
|------|------|------|--------|------|------|
| [scheme](./scheme/) | scheme | 方案系统 | 1.0.0 | `E:/project/Baize/方案系统` | 方案/投标生成与知识库 |
| [protein-analysis](./protein-analysis/) | protein-analysis | 蛋白质界面分析 | 1.0.0 | `E:/project/Baize/蛋白质界面分析` | 蛋白质界面相互作用分析 |
| [data-analytics](./data-analytics/) | data-analytics | 数据分析 | 1.0.0 | `E:/project/Baize/数据分析` | ECharts 数据可视化工作台 |

## 模块目录约定
每个模块子目录至少包含：
- `module.yaml`：注册元数据（必填）
- `README.md`：模块说明（必填）
- `index.html`：前端入口（由平台 `ModuleHost` 以 iframe 加载 `/modules/{code}/index.html`）
- 业务资源：前端静态包 / 后端路由包 / 文档

## 注册方式
1. **自动扫描**：运行 `python backend/scripts/scan_modules.py`（需可连接数据库），读取各 `module.yaml` 并 upsert 到 `modules` 表与 `permissions` 表。
2. **热注册**：`POST /api/v1/modules/register`，请求体即 `module.yaml` 对应 JSON。

注册后记得在「角色管理」中将模块声明的权限码分配给相应用户角色。
