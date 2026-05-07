from datetime import date
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.tenant_feature import TenantFeature


class FeatureService:
    @staticmethod
    async def has_active_feature_access(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        feature_code: str,
    ) -> bool:
        today = date.today()

        result = await db.execute(
            select(TenantFeature).where(
                TenantFeature.tenant_id == tenant_id,
                TenantFeature.feature_code == feature_code,
                TenantFeature.active == True,
            )
        )
        feature = result.scalar_one_or_none()
        if feature:
            return feature.period_start <= today <= feature.period_end

        # Compatibilidad con implementación legacy de sales_analytics
        if feature_code == "sales_analytics":
            legacy_result = await db.execute(
                select(Subscription).where(
                    Subscription.tenant_id == tenant_id,
                    Subscription.active == True,
                )
            )
            subscription = legacy_result.scalar_one_or_none()
            if not subscription:
                return False
            return subscription.period_start <= today <= subscription.period_end

        return False
