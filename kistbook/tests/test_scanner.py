from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.db.models import CsvCustomer, Retailer, ReminderConfig, ReminderLog
from kistbook.engine.scanner import _days_since_due, _effective_due_date, scan_retailer


@pytest.fixture
async def retailer(db_session: AsyncSession) -> Retailer:
    r = Retailer(
        name="TestShop",
        whatsapp_number="+923001111111",
        manager_phone="+923009999999",
    )
    db_session.add(r)
    await db_session.flush()
    config = ReminderConfig(retailer_id=r.id)
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(r)
    return r


def _make_customer(retailer_id: uuid.UUID, **kwargs) -> CsvCustomer:
    defaults = dict(
        retailer_id=retailer_id,
        customer_name="Test User",
        cnic="3520212345671",
        phone="+923001234567",
        installment_amount=5000,
        due_day_of_month=1,
        total_installments=12,
        installments_paid=0,
    )
    defaults.update(kwargs)
    return CsvCustomer(**defaults)


class TestEffectiveDueDate:
    def test_normal_month(self):
        assert _effective_due_date(2026, 3, 15) == date(2026, 3, 15)

    def test_february_short_month(self):
        assert _effective_due_date(2026, 2, 30) == date(2026, 2, 28)

    def test_last_day_of_month(self):
        assert _effective_due_date(2026, 4, 31) == date(2026, 4, 30)


class TestDaysSinceDue:
    def test_overdue_by_3(self):
        today = date(2026, 6, 4)
        assert _days_since_due(today, 1) == 3

    def test_upcoming_3_days(self):
        today = date(2026, 6, 1)
        due = _effective_due_date(2026, 6, 4)
        result = (today - due).days
        assert result == -3


class TestScannerFilters:
    async def test_paused_customer_skipped(self, db_session: AsyncSession, retailer: Retailer):
        customer = _make_customer(
            retailer.id,
            cnic="1111111111111",
            sequence_paused=True,
            installments_paid=0,
        )
        db_session.add(customer)
        await db_session.commit()

        with patch("kistbook.engine.tasks.send_reminder") as mock_task:
            with patch(
                "kistbook.engine.scanner._days_since_due", return_value=0
            ):
                result = await scan_retailer(db_session, retailer.id)

        assert mock_task.apply_async.call_count == 0

    async def test_completed_customer_skipped(self, db_session: AsyncSession, retailer: Retailer):
        customer = _make_customer(
            retailer.id,
            cnic="2222222222222",
            is_completed=True,
            installments_paid=5,
            total_installments=5,
        )
        db_session.add(customer)
        await db_session.commit()

        with patch("kistbook.engine.tasks.send_reminder") as mock_task:
            result = await scan_retailer(db_session, retailer.id)

        assert mock_task.apply_async.call_count == 0

    async def test_vip_customer_skipped(self, db_session: AsyncSession, retailer: Retailer):
        config = await db_session.get(ReminderConfig, None)
        from sqlalchemy import select

        config = await db_session.scalar(
            select(ReminderConfig).where(ReminderConfig.retailer_id == retailer.id)
        )
        config.vip_cnic_list = ["9999999999999"]
        await db_session.commit()

        customer = _make_customer(retailer.id, cnic="9999999999999")
        db_session.add(customer)
        await db_session.commit()

        with patch("kistbook.engine.tasks.send_reminder") as mock_task:
            with patch("kistbook.engine.scanner._days_since_due", return_value=0):
                result = await scan_retailer(db_session, retailer.id)

        assert mock_task.apply_async.call_count == 0

    async def test_already_logged_step_skipped(self, db_session: AsyncSession, retailer: Retailer):
        customer = _make_customer(retailer.id, cnic="3333333333333")
        db_session.add(customer)
        await db_session.flush()

        log = ReminderLog(
            retailer_id=retailer.id,
            customer_id=customer.id,
            customer_cnic=customer.cnic,
            step="branch_a_t0",
            channel="whatsapp",
            direction="outbound",
            status="sent",
            sent_at=datetime.now(timezone.utc),
        )
        db_session.add(log)
        await db_session.commit()

        with patch("kistbook.engine.tasks.send_reminder") as mock_task:
            with patch("kistbook.engine.scanner._days_since_due", return_value=0):
                result = await scan_retailer(db_session, retailer.id)

        assert mock_task.apply_async.call_count == 0

    async def test_no_guarantor_step_logged_as_skipped(
        self, db_session: AsyncSession, retailer: Retailer
    ):
        customer = _make_customer(
            retailer.id,
            cnic="4444444444444",
            installments_paid=0,
            guarantor_phone=None,
        )
        db_session.add(customer)
        await db_session.commit()

        with patch("kistbook.engine.tasks.send_reminder") as mock_task:
            with patch("kistbook.engine.scanner._days_since_due", return_value=5):
                result = await scan_retailer(db_session, retailer.id)

        from sqlalchemy import select

        skip_log = await db_session.scalar(
            select(ReminderLog).where(
                ReminderLog.customer_id == customer.id,
                ReminderLog.step == "branch_c_t+5",
                ReminderLog.status == "skipped_no_guarantor",
            )
        )
        assert skip_log is not None
        assert mock_task.apply_async.call_count == 0
