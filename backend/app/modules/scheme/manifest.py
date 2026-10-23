"""AI 方案生成 · 应用清单。"""
MANIFEST = {
    "code": "scheme",
    "name": "AI 方案生成",
    "description": "输入素材，基于模板与历史案例（RAG 检索复用）自动生成完整方案，支持导出 Markdown / Word / HTML。",
    "version": "2.0.0",
    "icon": "MagicStick",
    "order": 10,
    "api_prefix": "/modules/scheme",
    "entry": "/apps/scheme",
    "use_permission": "app:scheme:use",
    "use_permission_name": "使用 AI 方案生成",
    "view_all_permission": "app:scheme:view_all",
    "view_all_permission_name": "查看全部方案（管理员）",
}
