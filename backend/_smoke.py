import asyncio
import traceback

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.modules import register_apps
from app.models import Module, Permission


async def main():
    async with AsyncSessionLocal() as db:
        await register_apps(db)
        mods = (
            await db.execute(
                select(Module).where(
                    Module.code.in_(["data-analytics", "protein-analysis", "scheme"])
                )
            )
        ).scalars().all()
        perms = (
            await db.execute(
                select(Permission).where(
                    Permission.module.in_(["data-analytics", "protein-analysis", "scheme"])
                )
            )
        ).scalars().all()
        lines = []
        for m in mods:
            lines.append("%s status=%s entry=%s" % (m.code, m.status, m.entry))
        out = "REGISTER_OK mods=%d perms=%s\n%s" % (
            len(mods),
            [p.code for p in perms],
            "\n".join(lines),
        )
    with open(r"C:\project\代码研究\Baize\Baize\backend\.smoke.txt", "w", encoding="utf-8") as f:
        f.write(out)


try:
    asyncio.run(main())
except Exception:
    with open(r"C:\project\代码研究\Baize\Baize\backend\.smoke.txt", "w", encoding="utf-8") as f:
        f.write("REGISTER_FAIL\n" + traceback.format_exc())
