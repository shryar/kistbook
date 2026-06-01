from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.api.deps import get_db_session
from kistbook.db.models import Retailer, ReminderLog
from kistbook.integrations.wetarseel import verify_webhook_sig
from kistbook.integrations.whatsapp_types import WhatsAppWebhookPayload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


class WebhookResponse(BaseModel):
    status: str


@router.post("/whatsapp", response_model=WebhookResponse)
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> WebhookResponse:
    raw_body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_sig(raw_body, sig):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = WhatsAppWebhookPayload.model_validate_json(raw_body)
    except Exception as exc:
        logger.error("webhooks: failed to parse payload", extra={"error": str(exc)})
        return WebhookResponse(status="ok")

    for entry in payload.entry:
        for change in entry.changes:
            value = change.value

            if value.statuses:
                for status_event in value.statuses:
                    await _handle_delivery_status(db, status_event.id, status_event.status)

            if value.messages:
                for message in value.messages:
                    if message.type != "text" or not message.text:
                        continue
                    await _handle_inbound_message(
                        db,
                        from_phone=message.from_,
                        message_id=message.id,
                        raw_text=message.text.body,
                    )

    return WebhookResponse(status="ok")


async def _handle_delivery_status(db: AsyncSession, provider_msg_id: str, new_status: str) -> None:
    from datetime import datetime, timezone

    log = await db.scalar(
        select(ReminderLog).where(ReminderLog.provider_msg_id == provider_msg_id)
    )
    if not log:
        logger.warning("webhooks: delivery status for unknown msg_id", extra={"id": provider_msg_id})
        return

    log.status = new_status
    log.status_updated_at = datetime.now(timezone.utc)
    await db.commit()


async def _handle_inbound_message(
    db: AsyncSession,
    from_phone: str,
    message_id: str,
    raw_text: str,
) -> None:
    from kistbook.engine.reply_handler import handle_inbound_reply

    retailer = await db.scalar(select(Retailer))
    if not retailer:
        logger.error("webhooks: no retailer found for inbound message")
        return

    await handle_inbound_reply(db, from_phone, message_id, raw_text, retailer)
