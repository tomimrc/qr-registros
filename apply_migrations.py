"""
Script para aplicar migraciones Alembic a la BD de producción.

Para ambiente de producción:
    python apply_migration.py

Para rollback:
    python apply_migration.py --downgrade
    
Para ver estado:
    python apply_migration.py --status
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# URL de BD (con asyncpg)
DATABASE_URL = settings.DATABASE_URL


async def get_sync_connection_url():
    """Convierte la URL async a sync para Alembic"""
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://")


async def apply_migrations():
    """Aplica las migraciones usando Alembic CLI"""
    import subprocess
    import os
    
    os.chdir(".")  # Asegura que estamos en la raíz del proyecto
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--downgrade":
            print("[*] Realizando downgrade de la última migración...")
            result = subprocess.run(["python", "-m", "alembic", "downgrade", "-1"], capture_output=True, text=True)
        elif sys.argv[1] == "--status":
            print("[*] Estado actual de migraciones:")
            result = subprocess.run(["python", "-m", "alembic", "current"], capture_output=True, text=True)
        else:
            print(f"❓ Comando desconocido: {sys.argv[1]}")
            result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
    else:
        print("[+] Aplicando migraciones...")
        result = subprocess.run(["python", "-m", "alembic", "upgrade", "head"], capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("Error:", result.stderr)
    
    return result.returncode == 0


async def test_connection():
    """Verifica que la conexión a BD funciona"""
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        print("✓ Conexión a BD verificada")
        return True
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
        return False


async def main():
    """Función principal"""
    print("[*] QR Registros - Gestor de Migraciones")
    print("=" * 50)
    
    # Verifica conexión
    if not await test_connection():
        sys.exit(1)
    
    # Aplica migraciones
    success = await apply_migrations()
    
    if success:
        print("\n✓ Migraciones aplicadas exitosamente!")
    else:
        print("\n✗ Error al aplicar migraciones")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
