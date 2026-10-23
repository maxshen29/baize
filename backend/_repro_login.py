import sys, os, traceback
sys.path.insert(0, "E:/project/Baize/Baize/backend")

# 用真实库连接串（来自 .env）
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:HM372Y9TpGQj@192.168.101.220:5432/baize"

from app.routers.auth import login
from app.schemas import LoginRequest
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        try:
            result = await login(LoginRequest(account="admin", password="Admin@123456"), db)
            print("LOGIN_OK")
            print("roles:", result["data"]["user"]["roles"])
            print("perms count:", len(result["data"]["user"]["permissions"]))
        except Exception:
            traceback.print_exc()

import asyncio
asyncio.run(main())
