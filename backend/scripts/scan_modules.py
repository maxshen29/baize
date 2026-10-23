"""扫描并注册 AI 应用（backend/modules/ 下的应用包）。

用法（需可连接数据库）：
    python backend/scripts/scan_modules.py

说明：把各应用的 MANIFEST 注册进平台 modules 表，并写入「使用权限」点、授予超级管理员。
新增一个 AI 应用只需在 backend/modules/<pkg>/ 下放置 __init__.py（暴露 MANIFEST 与 router），
并在 backend/app/modules/__init__.py 的 APP_PACKAGES 中登记即可。
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.modules import register_apps


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await register_apps(db)
    print("AI 应用注册完成。")


if __name__ == "__main__":
    asyncio.run(main())
