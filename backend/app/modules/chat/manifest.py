"""AI 对话应用 · 应用清单。"""
MANIFEST = {
    "code": "chat",
    "name": "AI 对话",
    "description": "基于已接入大模型的对话助手，支持多轮流式对话与模型切换。",
    "version": "1.0.0",
    "icon": "ChatDotRound",
    "order": 30,
    "api_prefix": "/modules/chat",
    "entry": "/apps/chat",
    "use_permission": "app:chat:use",
    "use_permission_name": "使用 AI 对话",
}
