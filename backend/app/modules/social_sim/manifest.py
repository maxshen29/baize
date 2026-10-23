"""社会推演 · 数字沙盘 · 应用清单。

参考 MiroFish（群体智能预测引擎）的核心思路，提供一个轻量、自包含的多智能体推演应用：
  种子材料 → LLM 抽取世界观与人物画像 → 多智能体多轮推演（上帝视角注入变量）
  → 预测报告 → 与数字世界对话。

不依赖 OASIS / Zep 等重型外部组件，全部基于本平台已接入的 OpenAI 兼容大模型。
"""
MANIFEST = {
    "code": "social_sim",
    "name": "社会推演 · 数字沙盘",
    "description": "上传种子材料、提出预测需求，自动构建平行数字世界，让一群具备独立人格的智能体自由演化，推演未来走向并生成预测报告。",
    "version": "1.0.0",
    "icon": "Connection",
    "order": 40,
    "api_prefix": "/modules/social_sim",
    "entry": "/apps/social_sim",
    "use_permission": "app:social_sim:use",
    "use_permission_name": "使用 社会推演 · 数字沙盘",
}
