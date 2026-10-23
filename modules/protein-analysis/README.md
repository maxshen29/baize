# 蛋白质界面分析（protein-analysis）

抗体 / 蛋白质界面相互作用、埋藏面积与热点分析单页应用，迁移自 `E:/project/Baize/蛋白质界面分析`。

## 模块信息
- **code**: `protein-analysis`
- **entry**: `/modules/protein-analysis`（前端 `ModuleHost` 以 iframe 加载本目录 `index.html`）
- **api_prefix**: `/api/v1/modules/protein-analysis`
- **状态**: enabled
- **依赖**: 无

## 目录说明（迁移后）
- `index.html`：分析主程序（单页应用，含 3D/界面可视化与导出）
- `_tmp_cdrcheck.js`：CDR 区检测辅助脚本
- `公众号指南/`：系列科普 HTML（封面、开篇、快速上手、抗体与CDR、相互作用、埋藏面积与热点、多结构对比与导出）
- `module.yaml`：平台模块注册元数据（见 `docs/MODULE_SPEC.md`）

## 接入平台
1. 平台「模块管理」提交 `module.yaml` 完成注册。
2. 将 `protein:analysis:read` / `protein:analysis:run` 权限码分配至相应角色。
3. 在「模块配置」设置 `pdb_mirror` 等运行参数。
4. 前端菜单出现「蛋白质界面分析」，点击经 `ModuleHost` 加载本模块。

## 说明
本模块为前端单页应用，分析逻辑在浏览器端完成；如需后端算力（如批量结构比对），可后续在 `api_prefix` 下挂载 FastAPI 路由包，复用平台鉴权与审计。
