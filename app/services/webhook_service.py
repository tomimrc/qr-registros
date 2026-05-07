import logging
from datetime import datetime, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    @staticmethod
    async def send_event(event_type: str, payload: dict):
        if not settings.N8N_WEBHOOK_ENABLED or not settings.N8N_WEBHOOK_URL:
            return

        body = {
            "event_type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.N8N_WEBHOOK_TIMEOUT_SECONDS) as client:
                response = await client.post(settings.N8N_WEBHOOK_URL, json=body)
                if response.status_code >= 400:
                    logger.warning(
                        "n8n webhook responded with status %s for event %s",
                        response.status_code,
                        event_type,
                    )
        except Exception as exc:
            logger.warning("Failed to send n8n webhook for event %s: %s", event_type, exc)
