import asyncio
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.admin import Admin
from app.core.security import hash_password
import re

def generar_slug(nombre: str) -> str:
    """Convierte 'Tomi Lomos' en 'tomi-lomos' para la base de datos"""
    slug = nombre.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    return re.sub(r'[\s_-]+', '-', slug)

async def main():
    print("\n" + "="*50)
    print("🚀 PANEL SUPERADMIN - ALTA DE NUEVO CLIENTE SaaS")
    print("="*50 + "\n")

    # 1. Pedir datos por consola
    tenant_name = input("🏢 Nombre de la empresa (Ej: Tomi Lomos): ").strip()
    admin_name = input("👤 Nombre del dueño/administrador: ").strip()
    admin_email = input("📧 Email de acceso: ").strip()
    admin_password = input("🔑 Contraseña: ").strip()

    if not all([tenant_name, admin_name, admin_email, admin_password]):
        print("\n❌ Error: Todos los campos son obligatorios.")
        return

    tenant_slug = generar_slug(tenant_name)

    # 2. Conectarse a la BD e insertar los datos
    print("\n⏳ Conectando a la base de datos y encriptando...")
    
    async with AsyncSessionLocal() as db:
        try:
            # A) Crear la Empresa (Tenant)
            nuevo_tenant = Tenant(
                name=tenant_name,
                slug=tenant_slug,
                is_active=True
            )
            db.add(nuevo_tenant)
            await db.commit()
            await db.refresh(nuevo_tenant) # Para obtener su ID (UUID) generado

            # B) Crear la cuenta del Administrador
            nuevo_admin = Admin(
                tenant_id=nuevo_tenant.id,
                email=admin_email,
                hashed_password=hash_password(admin_password),
                nombre=admin_name,
                is_active=True
            )
            db.add(nuevo_admin)
            await db.commit()

            print("\n✅ ¡ÉXITO TOTAL!")
            print("-" * 30)
            print(f"🏢 Empresa registrada: {tenant_name}")
            print(f"🆔 Tenant ID: {nuevo_tenant.id}")
            print(f"📧 Usuario Admin: {admin_email}")
            print("-" * 30)
            print("👉 Ya podés ir a http://localhost:8000/dashboard e iniciar sesión.")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Ocurrió un error al guardar en la base de datos: {e}")
            print("¿Ese email o slug ya están registrados?")

if __name__ == "__main__":
    # Ejecutar la función asíncrona
    asyncio.run(main())