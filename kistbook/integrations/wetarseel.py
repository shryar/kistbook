from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone

import httpx

from kistbook.core.config import settings

logger = logging.getLogger(__name__)

WETARSEEL_BASE_URL = "https://api.wetarseel.com/v1"


async def send_message(to: str, template_name: str, variables: dict) -> str:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(v)} for v in variables.values()
                    ],
                }
            ],
        },
    }

    sent_at = datetime.now(timezone.utc).isoformat()
    logger.info(
        "wetarseel.send_message request",
        extra={"to": to, "template": template_name, "sent_at": sent_at, "payload": payload},
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WETARSEEL_BASE_URL}/messages",
            json=payload,
            headers={"Authorization": f"Bearer {settings.WETARSEEL_API_KEY}"},
            timeout=10.0,
        )

    logger.info(
        "wetarseel.send_message response",
        extra={
            "to": to,
            "template": template_name,
            "status_code": response.status_code,
            "body": response.text[:500],
        },
    )

    response.raise_for_status()
    data = response.json()
    return data.get("messages", [{}])[0].get("id", "")


async def send_freeform_message(to: str, body: str) -> str:
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }

    logger.info("wetarseel.send_freeform request", extra={"to": to})

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WETARSEEL_BASE_URL}/messages",
            json=payload,
            headers={"Authorization": f"Bearer {settings.WETARSEEL_API_KEY}"},
            timeout=10.0,
        )

    logger.info(
        "wetarseel.send_freeform response",
        extra={"to": to, "status_code": response.status_code, "body": response.text[:500]},
    )

    response.raise_for_status()
    data = response.json()
    return data.get("messages", [{}])[0].get("id", "")


def verify_webhook_sig(raw_body: bytes, signature_header: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header[len("sha256="):]
    computed = hmac.new(
        settings.WETARSEEL_WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, expected)
