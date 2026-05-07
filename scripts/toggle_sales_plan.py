#!/usr/bin/env python
"""
Script operativo para activar/desactivar el plan de Sales Analytics por tenant.

Uso:
    python scripts/toggle_sales_plan.py --enable <tenant_slug> <months>
    python scripts/toggle_sales_plan.py --disable <tenant_slug>
    python scripts/toggle_sales_plan.py --status <tenant_slug>

Ejemplos:
    python scripts/toggle_sales_plan.py --enable don-pepe 1    # Activar 1 mes
    python scripts/toggle_sales_plan.py --disable don-pepe      # Desactivar
    python scripts/toggle_sales_plan.py --status don-pepe       # Ver estado
"""

import asyncio
import argparse
import sys
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import uuid
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Permite ejecutar este script desde scripts/ o desde la raíz del proyecto.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from app.core.config import settings
from app.models.tenant import Tenant
from app.models.subscription import Subscription


async def get_session():
    """Crear sesión async a la DB"""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session


async def enable_plan(tenant_slug: str, months: int):
    """Activar Sales Analytics para un tenant por N meses"""
    async_session = await get_session()
    
    async with async_session() as session:
        # 1. Buscar tenant
        result = await session.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print(f"❌ Tenant '{tenant_slug}' no encontrado")
            return
        
        print(f"✓ Tenant encontrado: {tenant.name} ({tenant.id})")
        
        # 2. Buscar o crear suscripción
        sub_result = await session.execute(
            select(Subscription).where(Subscription.tenant_id == tenant.id)
        )
        subscription = sub_result.scalar_one_or_none()
        
        period_start = date.today()
        period_end = period_start + relativedelta(months=months) - timedelta(days=1)
        
        if subscription:
            # Actualizar existente
            subscription.active = True
            subscription.period_start = period_start
            subscription.period_end = period_end
            print(f"✓ Suscripción actualizada")
        else:
            # Crear nueva
            subscription = Subscription(
                tenant_id=tenant.id,
                plan_code="sales_analytics",
                active=True,
                period_start=period_start,
                period_end=period_end
            )
            session.add(subscription)
            print(f"✓ Suscripción creada")
        
        await session.commit()
        print(f"\n📊 PLAN ACTIVADO")
        print(f"  Tenant: {tenant.name}")
        print(f"  Plan: Sales Analytics")
        print(f"  Vigencia: {period_start} a {period_end}")
        print(f"  Estado: ACTIVO")


async def disable_plan(tenant_slug: str):
    """Desactivar Sales Analytics para un tenant"""
    async_session = await get_session()
    
    async with async_session() as session:
        # 1. Buscar tenant
        result = await session.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print(f"❌ Tenant '{tenant_slug}' no encontrado")
            return
        
        # 2. Buscar suscripción
        sub_result = await session.execute(
            select(Subscription).where(Subscription.tenant_id == tenant.id)
        )
        subscription = sub_result.scalar_one_or_none()
        
        if not subscription:
            print(f"⚠️  Tenant '{tenant_slug}' no tiene suscripción activa")
            return
        
        subscription.active = False
        await session.commit()
        
        print(f"\n📊 PLAN DESACTIVADO")
        print(f"  Tenant: {tenant.name}")
        print(f"  Estado: INACTIVO")


async def status_plan(tenant_slug: str):
    """Ver estado del plan de un tenant"""
    async_session = await get_session()
    
    async with async_session() as session:
        # 1. Buscar tenant
        result = await session.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print(f"❌ Tenant '{tenant_slug}' no encontrado")
            return
        
        # 2. Buscar suscripción
        sub_result = await session.execute(
            select(Subscription).where(Subscription.tenant_id == tenant.id)
        )
        subscription = sub_result.scalar_one_or_none()
        
        print(f"\n📊 ESTADO DEL PLAN")
        print(f"  Tenant: {tenant.name} ({tenant.slug})")
        
        if not subscription:
            print(f"  Estado: SIN SUSCRIPCIÓN")
            return
        
        status_text = "✓ ACTIVO" if subscription.active else "✗ INACTIVO"
        today = date.today()
        expired = today > subscription.period_end
        expired_text = " (EXPIRADO)" if expired else ""
        
        print(f"  Plan: {subscription.plan_code}")
        print(f"  Estado: {status_text}{expired_text}")
        print(f"  Vigencia: {subscription.period_start} a {subscription.period_end}")


async def main():
    parser = argparse.ArgumentParser(
        description="Gestión de planes Sales Analytics"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--enable",
        nargs=2,
        metavar=("TENANT_SLUG", "MONTHS"),
        help="Activar plan por N meses"
    )
    group.add_argument(
        "--disable",
        nargs=1,
        metavar=("TENANT_SLUG",),
        help="Desactivar plan"
    )
    group.add_argument(
        "--status",
        nargs=1,
        metavar=("TENANT_SLUG",),
        help="Ver estado del plan"
    )

    args = parser.parse_args()

    if args.enable:
        tenant_slug, months_raw = args.enable
        await enable_plan(tenant_slug, int(months_raw))
    elif args.disable:
        await disable_plan(args.disable[0])
    elif args.status:
        await status_plan(args.status[0])


if __name__ == "__main__":
    asyncio.run(main())
