from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select

from kistbook.celery_app import celery_app
from kistbook.db.models import CsvCustomer, Retailer, ReminderLog
from kistbook.db.session import AsyncSessionLocal
from kistbook.engine.templates import TEMPLATE_MAP, render_variables
from kistbook.integrations import wetarseel

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="kistbook.engine.tasks.send_reminder", acks_late=True)
def send_reminder(
    self,
    customer_id: str,
    step: str,
    channel: str,
    retailer_id: str,
) -> None:
    asyncio.run(_send_reminder_async(customer_id, step, channel, retailer_id))


async def _send_reminder_async(
    customer_id: str,
    step: str,
    channel: str,
    retailer_id: str,
) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            select(ReminderLog).where(
                ReminderLog.customer_id == uuid.UUID(customer_id),
                ReminderLog.step == step,
                ReminderLog.channel == channel,
            )
        )
        if existing:
            logger.info(
                "send_reminder: idempotency guard hit — already sent",
                extra={"customer_id": customer_id, "step": step, "channel": channel},
            )
            return

        customer = await db.get(CsvCustomer, uuid.UUID(customer_id))
        if not customer:
            logger.error("send_reminder: customer not found", extra={"customer_id": customer_id})
            return

        retailer = await db.get(Retailer, uuid.UUID(retailer_id))
        if not retailer:
            logger.error("send_reminder: retailer not found", extra={"retailer_id": retailer_id})
            return

        template_name = TEMPLATE_MAP.get(step)
        variables = render_variables(step, customer)
        target_phone = retailer.manager_phone if channel == "manager_whatsapp" else customer.phone

        try:
            if template_name:
                provider_msg_id = await wetarseel.send_message(
                    target_phone, template_name, variables
                )
            else:
                body = _build_manager_alert(step, customer, retailer)
                provider_msg_id = await wetarseel.send_freeform_message(target_phone, body)

            log = ReminderLog(
                retailer_id=uuid.UUID(retailer_id),
                customer_id=uuid.UUID(customer_id),
                customer_cnic=customer.cnic,
                step=step,
                channel=channel,
                direction="outbound",
                template_id=template_name,
                status="sent",
                provider_msg_id=provider_msg_id,
                sent_at=datetime.now(timezone.utc),
            )
            db.add(log)
            await db.commit()

        except Exception as exc:
            logger.error(
                "send_reminder: WeTarseel call failed",
                extra={"customer_id": customer_id, "step": step, "error": str(exc)},
                exc_info=True,
            )
            log = ReminderLog(
                retailer_id=uuid.UUID(retailer_id),
                customer_id=uuid.UUID(customer_id),
                customer_cnic=customer.cnic,
                step=step,
                channel=channel,
                direction="outbound",
                template_id=template_name,
                status="failed",
                sent_at=datetime.now(timezone.utc),
            )
            db.add(log)
            await db.commit()


def _build_manager_alert(step: str, customer: CsvCustomer, retailer: Retailer) -> str:
    amount = customer.installment_amount
    name = customer.customer_name
    if step == "branch_b_t+14":
        return f"ALERT: {name} is 14 days overdue on Branch B. Amount: PKR {amount}. CNIC: {customer.cnic}"
    if step == "branch_c_t+7":
        return f"ALERT: {name} has NEVER paid and is 7 days overdue. Amount: PKR {amount}. CNIC: {customer.cnic}"
    return f"KistBook alert for customer {name} (step: {step}). Amount: PKR {amount}."


@celery_app.task(name="kistbook.engine.tasks.run_daily_scan")
def run_daily_scan(retailer_id: str | None = None) -> dict:
    return asyncio.run(_run_daily_scan_async(retailer_id))


async def _run_daily_scan_async(retailer_id: str | None) -> dict:
    from kistbook.engine.scanner import scan_all_retailers, scan_retailer

    async with AsyncSessionLocal() as db:
        if retailer_id:
            result = await scan_retailer(db, uuid.UUID(retailer_id))
        else:
            result = await scan_all_retailers(db)
    return result
