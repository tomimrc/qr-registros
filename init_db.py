import asyncio

from app.database import Base, engine
from app.models import *  # noqa: F401 - asegura que todos los modelos queden registrados


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
