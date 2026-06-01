from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.db.models import CsvCustomer, Retailer, ReminderConfig, ReminderLog
from kistbook.engine.tasks import _send_reminder_async


@pytest.fixture
async def retailer(db_session: AsyncSession) -> Retailer:
    r = Retailer(
        name="TaskTestShop",
        whatsapp_number="+923002222222",
        manager_phone="+923008888888",
    )
    db_session.add(r)
    await db_session.flush()
    config = ReminderConfig(retailer_id=r.id)
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(r)
    return r


@pytest.fixture
async def customer(db_session: AsyncSession, retailer: Retailer) -> CsvCustomer:
    c = CsvCustomer(
        retailer_id=retailer.id,
        customer_name="Ahmed Khan",
        cnic="3520212345671",
        phone="+923001234567",
        installment_amount=5000,
        due_day_of_month=15,
        total_installments=12,
        installments_paid=0,
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


class TestIdempotencyGuard:
    async def test_existing_log_prevents_wetarseel_call(
        self,
        db_session: AsyncSession,
        retailer: Retailer,
        customer: CsvCustomer,
    ):
        existing_log = ReminderLog(
            retailer_id=retailer.id,
            customer_id=customer.id,
            customer_cnic=customer.cnic,
            step="branch_a_t0",
            channel="whatsapp",
            direction="outbound",
            status="sent",
            sent_at=datetime.now(timezone.utc),
        )
        db_session.add(existing_log)
        await db_session.commit()

        with patch("kistbook.engine.tasks.wetarseel") as mock_ws:
            mock_ws.send_message = AsyncMock()
            mock_ws.send_freeform_message = AsyncMock()

            await _send_reminder_async(
                str(customer.id),
                "branch_a_t0",
                "whatsapp",
                str(retailer.id),
            )

            mock_ws.send_message.assert_not_called()
            mock_ws.send_freeform_message.assert_not_called()

    async def test_no_existing_log_calls_wetarseel(
        self,
        db_session: AsyncSession,
        retailer: Retailer,
        customer: CsvCustomer,
    ):
        with patch("kistbook.engine.tasks.wetarseel") as mock_ws:
            mock_ws.send_message = AsyncMock(return_value="wamid.new123")
            mock_ws.send_freeform_message = AsyncMock(return_value="wamid.new456")

            await _send_reminder_async(
                str(customer.id),
                "branch_a_t0",
                "whatsapp",
                str(retailer.id),
            )

            mock_ws.send_message.assert_called_once()

        log = await db_session.scalar(
            select(ReminderLog).where(
                ReminderLog.customer_id == customer.id,
                ReminderLog.step == "branch_a_t0",
            )
        )
        assert log is not None
        assert log.status == "sent"
        assert log.provider_msg_id == "wamid.new123"

    async def test_wetarseel_failure_logs_failed_status(
        self,
        db_session: AsyncSession,
        retailer: Retailer,
        customer: CsvCustomer,
    ):
        with patch("kistbook.engine.tasks.wetarseel") as mock_ws:
            mock_ws.send_message = AsyncMock(side_effect=Exception("Connection error"))

            await _send_reminder_async(
                str(customer.id),
                "branch_a_t+1",
                "whatsapp",
                str(retailer.id),
            )

        log = await db_session.scalar(
            select(ReminderLog).where(
                ReminderLog.customer_id == customer.id,
                ReminderLog.step == "branch_a_t+1",
            )
        )
        assert log is not None
        assert log.status == "failed"
