from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.db.models import CsvCustomer, Retailer, ReminderLog

logger = logging.getLogger(__name__)

_PAID_KEYWORDS = ("paid", "pay kar diya", "ho gaya", "payment", "kar diya")
_HELP_KEYWORDS = ("help", "problem", "masla", "issue", "nahi")
_PROMISE_KEYWORDS = ("kal", "parso", "next week", "tomorrow", "week", "agle", "monday", "tuesday",
                     "wednesday", "thursday", "friday", "saturday", "sunday")


def _classify_reply(text: str) -> str:
    lower = text.lower()
    for kw in _PAID_KEYWORDS:
        if kw in lower:
            return "PAID"
    for kw in _PROMISE_KEYWORDS:
        if kw in lower:
            return "PROMISE"
    for kw in _HELP_KEYWORDS:
        if kw in lower:
            return "HELP"
    return "HELP"


async def handle_inbound_reply(
    db: AsyncSession,
    from_phone: str,
    message_id: str,
    raw_text: str,
    retailer: Retailer,
) -> None:
    customer = await db.scalar(
        select(CsvCustomer).where(
            CsvCustomer.phone == from_phone,
            CsvCustomer.retailer_id == retailer.id,
        )
    )

    customer_id = customer.id if customer else uuid.uuid4()
    customer_cnic = customer.cnic if customer else "unknown"

    reply_class = _classify_reply(raw_text)

    log = ReminderLog(
        retailer_id=retailer.id,
        customer_id=customer_id,
        customer_cnic=customer_cnic,
        step=f"inbound_{reply_class.lower()}",
        channel="whatsapp",
        direction="inbound",
        inbound_text=raw_text,
        status="replied",
        provider_msg_id=message_id,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(log)

    if customer and reply_class in ("PAID", "HELP"):
        customer.sequence_paused = True

    await db.flush()

    manager_body = _build_manager_notification(reply_class, customer, from_phone, raw_text)

    try:
        from kistbook.integrations import wetarseel

        mgr_msg_id = await wetarseel.send_freeform_message(retailer.manager_phone, manager_body)

        mgr_log = ReminderLog(
            retailer_id=retailer.id,
            customer_id=customer_id,
            customer_cnic=customer_cnic,
            step=f"manager_alert_{reply_class.lower()}",
            channel="manager_whatsapp",
            direction="outbound",
            message_body=manager_body,
            status="sent",
            provider_msg_id=mgr_msg_id,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(mgr_log)
    except Exception as exc:
        logger.error(
            "reply_handler: manager alert failed",
            extra={"from": from_phone, "class": reply_class, "error": str(exc)},
            exc_info=True,
        )

    await db.commit()


def _build_manager_notification(
    reply_class: str,
    customer: CsvCustomer | None,
    from_phone: str,
    raw_text: str,
) -> str:
    name = customer.customer_name if customer else from_phone
    amount = customer.installment_amount if customer else "?"
    match reply_class:
        case "PAID":
            return f"PAYMENT CLAIM: {name} says they paid. Amount: PKR {amount}. Please verify in CRM. Reply: '{raw_text}'"
        case "PROMISE":
            return f"PROMISE TO PAY: {name} made a promise. Amount: PKR {amount}. Reply: '{raw_text}'"
        case _:
            return f"HELP REQUEST: {name} needs assistance. Amount: PKR {amount}. Reply: '{raw_text}'"
