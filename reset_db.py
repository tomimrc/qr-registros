# reset_db.py

import asyncio
from app.database import engine
from app.models import *  # noqa: F401 - importa todos los modelos
from sqlalchemy.orm import DeclarativeBase
from app.database import Base


async def reset():
    async with engine.begin() as conn:
        print("🗑️  Borrando todas las tablas...")
        await conn.run_sync(Base.metadata.drop_all)
        print("🔨 Creando tablas con la nueva estructura...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Listo! Tablas recreadas con tenant_id")

    await engine.dispose()


asyncio.run(reset())