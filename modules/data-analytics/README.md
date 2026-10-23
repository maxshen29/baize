# 数据分析（data-analytics）

基于 ECharts / ECharts-GL 的数据可视化与分析工作台，迁移自 `E:/project/Baize/数据分析`。

## 模块信息
- **code**: `data-analytics`
- **entry**: `/modules/data-analytics`（前端 `ModuleHost` 以 iframe 加载本目录 `index.html`）
- **api_prefix**: `/api/v1/modules/data-analytics`
- **状态**: enabled
- **依赖**: 无（被 `scheme` 模块依赖）

## 目录说明（迁移后）
- `datascope-analytics/`：分析应用本体
  - `web/index.html`：应用入口
  - `web/js/app.js`、`charts.js`、`data.js`：应用逻辑
  - `web/css/styles.css`：样式
  - `lib/echarts.min.js`、`echarts-gl.min.js`：图表库
  - `_archive/`：SSR/测试存档
- `echarts-gl.min.js`：图表库副本
- `module.yaml`：平台模块注册元数据（见 `docs/MODULE_SPEC.md`）

## 接入平台
1. 平台「模块管理」提交 `module.yaml` 完成注册。
2. 将 `analytics:dataset:read` / `analytics:dataset:write` / `analytics:chart:read` 权限码分配至角色。
3. 在「模块配置」设置 `chart_lib`、`default_theme` 等运行参数。
4. 前端菜单出现「数据分析」，点击经 `ModuleHost` 加载本模块。
5. 其它模块（如 `scheme`）可通过依赖声明复用本模块的可视化能力。

## 说明
本模块为前端可视化应用；若需服务端数据聚合，可在 `api_prefix` 下挂载 FastAPI 路由包，由平台 RBAC 统一纳管接口权限。
