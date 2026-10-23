"""一次性迁移：为已存在的 social_simulations 表补加 graph_json 列。

原因：social_sim 模块先创建、表已建好，之后才新增 graph_json 字段。
SQLAlchemy 的 create_all 只建"不存在的表"，不会给已有表加列，
因此运行期报 column social_simulations.graph_json does not exist。

用法（在项目 backend 目录、激活对应 python 后）：
    python migrate_add_graph_json.py
可重复运行，已存在则跳过。
"""
import asyncio

from sqlalchemy import text

from app.core.database import Base, engine
from app.models import SocialSimulation  # noqa: F401 确保模型已注册到 Base.metadata


async def main() -> None:
    # 1) 确保表存在（若不存在则创建；已存在则无操作，也不会补列）
    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'social_simulations' AND column_name = 'graph_json'"
            )
        )
        exists = res.scalar() is not None
        if exists:
            print("graph_json 列已存在，无需迁移。")
            return

        # 2) 补加列：JSONB 允许为空（旧数据默认 NULL，前端按 {} 兜底）
        await conn.execute(
            text("ALTER TABLE social_simulations ADD COLUMN graph_json JSONB")
        )
        print("已为 social_simulations 表添加 graph_json 列。")


if __name__ == "__main__":
    asyncio.run(main())
