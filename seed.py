# seed.py

import asyncio
import uuid
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.employee import Employee
# Al inicio del seed.py agregá el import
from app.core.config import settings



async def seed():
    async with AsyncSessionLocal() as db:
        # 1. CREAR TENANT
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="Restaurante Don Pepe",
            slug="don-pepe",
            is_active=True
        )
        db.add(tenant)

        # 2. CREAR EMPLEADOS
        empleados = [
            Employee(
                tenant_id=tenant_id,
                nombre="Juan Pérez",
                sector="Cocina",
                convenio="Gastronómico",
                valor_hora=1500.00,
                activo=True
            ),
            Employee(
                tenant_id=tenant_id,
                nombre="María García",
                sector="Salón",
                convenio="Gastronómico",
                valor_hora=1400.00,
                activo=True
            ),
            Employee(
                tenant_id=tenant_id,
                nombre="Pedro López",
                sector="Barra",
                convenio="Gastronómico",
                valor_hora=1450.00,
                activo=True
            ),
        ]
        db.add_all(empleados)
        await db.commit()

        # 3. IMPRIMIR INFO
        print("\n" + "=" * 50)
        print("🌱 SEED COMPLETADO")
        print("=" * 50)
        print(f"\n🏢 Tenant: {tenant.name}")
        print(f"   ID:     {tenant.id}")
        print(f"\n👥 Empleados creados:")
        for emp in empleados:
            print(f"   - {emp.nombre} ({emp.sector})")
        print(f"\n📱 URL para probar:")
        print(f"   {settings.BASE_URL}/app?tenant_id={tenant.id}")
        print("=" * 50 + "\n")


asyncio.run(seed())