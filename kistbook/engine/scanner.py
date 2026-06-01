from __future__ import annotations

import calendar
import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.db.models import CsvCustomer, Retailer, ReminderConfig, ReminderLog
from kistbook.engine.branch import BRANCH_STEPS, STEP_TRIGGERS, classify

logger = logging.getLogger(__name__)


def _effective_due_date(year: int, month: int, due_day: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(due_day, last_day))


def _days_since_due(today: date, due_day: int) -> int:
    due = _effective_due_date(today.year, today.month, due_day)
    return (today - due).days


async def scan_all_retailers(db: AsyncSession) -> dict:
    retailers = (await db.scalars(select(Retailer))).all()
    total_tasks = 0
    total_customers = 0

    for retailer in retailers:
        try:
            result = await scan_retailer(db, retailer.id)
            total_tasks += result["tasks_enqueued"]
            total_customers += result["customers_scanned"]
        except Exception as exc:
            logger.error(
                "scanner: per-retailer scan failed",
                extra={"retailer_id": str(retailer.id), "error": str(exc)},
                exc_info=True,
            )
            await _alert_manager_scan_failure(db, retailer, exc)

    return {"tasks_enqueued": total_tasks, "customers_scanned": total_customers}


async def scan_retailer(db: AsyncSession, retailer_id: uuid.UUID) -> dict:
    retailer = await db.get(Retailer, retailer_id)
    if not retailer:
        raise ValueError(f"Retailer {retailer_id} not found")

    config = await db.scalar(
        select(ReminderConfig).where(ReminderConfig.retailer_id == retailer_id)
    )

    today = date.today()
    customers = (
        await db.scalars(
            select(CsvCustomer).where(
                CsvCustomer.retailer_id == retailer_id,
                CsvCustomer.sequence_paused.is_(False),
                CsvCustomer.is_completed.is_(False),
            )
        )
    ).all()

    tasks_enqueued = 0
    task_index = 0

    for customer in customers:
        if config and customer.cnic in (config.vip_cnic_list or []):
            continue

        if customer.installments_paid >= customer.total_installments:
            customer.is_completed = True
            await db.commit()
            continue

        days = _days_since_due(today, customer.due_day_of_month)
        branch = classify(customer.installments_paid, days)

        if config:
            branch_enabled = getattr(config, f"branch_{branch.lower()}_enabled", True)
            if not branch_enabled:
                continue

        for step in BRANCH_STEPS[branch]:
            trigger_days, channel = STEP_TRIGGERS[step]
            if days != trigger_days:
                continue

            existing = await db.scalar(
                select(ReminderLog).where(
                    ReminderLog.customer_id == customer.id,
                    ReminderLog.step == step,
                    ReminderLog.channel == channel,
                )
            )
            if existing:
                continue

            if step == "branch_c_t+5" and not customer.guarantor_phone:
                skip_log = ReminderLog(
                    retailer_id=retailer_id,
                    customer_id=customer.id,
                    customer_cnic=customer.cnic,
                    step=step,
                    channel=channel,
                    direction="outbound",
                    status="skipped_no_guarantor",
                    sent_at=datetime.now(timezone.utc),
                )
                db.add(skip_log)
                await db.commit()
                continue

            from kistbook.engine.tasks import send_reminder

            send_reminder.apply_async(
                args=[str(customer.id), step, channel, str(retailer_id)],
                countdown=task_index * 1,
            )
            task_index += 1
            tasks_enqueued += 1

    return {
        "tasks_enqueued": tasks_enqueued,
        "customers_scanned": len(customers),
    }


async def _alert_manager_scan_failure(
    db: AsyncSession, retailer: Retailer, exc: Exception
) -> None:
    try:
        from kistbook.integrations import wetarseel

        body = f"KistBook scan FAILED for {retailer.name}. Error: {exc!s}. Please check logs."
        await wetarseel.send_freeform_message(retailer.manager_phone, body)
        logger.error(
            "scanner: scan failure alert sent to manager",
            extra={"retailer_id": str(retailer.id), "error": str(exc)},
        )
    except Exception as alert_exc:
        logger.error(
            "scanner: failed to send scan failure alert",
            extra={"retailer_id": str(retailer.id), "error": str(alert_exc)},
            exc_info=True,
        )
