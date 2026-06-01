from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.core.config import settings
from kistbook.db.models import CsvCustomer, Retailer, ReminderConfig, ReminderLog


def _sign_payload(body: bytes) -> str:
    sig = hmac.new(
        settings.WETARSEEL_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return f"sha256={sig}"


@pytest.fixture
async def retailer(db_session: AsyncSession) -> Retailer:
    r = Retailer(
        name="WebhookShop",
        whatsapp_number="+923003333333",
        manager_phone="+923007777777",
    )
    db_session.add(r)
    await db_session.flush()
    config = ReminderConfig(retailer_id=r.id)
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(r)
    return r


@pytest.fixture
async def active_customer(db_session: AsyncSession, retailer: Retailer) -> CsvCustomer:
    c = CsvCustomer(
        retailer_id=retailer.id,
        customer_name="Fatima Ali",
        cnic="3520299999991",
        phone="+923001234567",
        installment_amount=3000,
        due_day_of_month=10,
        total_installments=6,
        installments_paid=2,
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


def _inbound_payload(from_phone: str, message_id: str, body_text: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": from_phone,
                        "id": message_id,
                        "timestamp": "1748735456",
                        "text": {"body": body_text},
                        "type": "text",
                    }]
                }
            }]
        }],
    }


def _delivery_payload(msg_id: str, new_status: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{
                        "id": msg_id,
                        "status": new_status,
                        "timestamp": "1748735123",
                    }]
                }
            }]
        }],
    }


class TestWebhookSecurity:
    async def test_invalid_signature_returns_401(self, client: AsyncClient, retailer: Retailer):
        body = json.dumps(_inbound_payload("+923001234567", "wamid.x", "paid")).encode()
        response = await client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalidsig",
            },
        )
        assert response.status_code == 401

    async def test_missing_signature_returns_401(self, client: AsyncClient, retailer: Retailer):
        body = json.dumps(_inbound_payload("+923001234567", "wamid.x", "paid")).encode()
        response = await client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 401

    async def test_no_db_change_on_invalid_sig(
        self, client: AsyncClient, db_session: AsyncSession, retailer: Retailer
    ):
        body = json.dumps(_inbound_payload("+923001234567", "wamid.x", "paid")).encode()
        await client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalidsig",
            },
        )
        count = await db_session.scalar(
            select(ReminderLog).where(ReminderLog.inbound_text == "paid")
        )
        assert count is None


class TestDeliveryStatusUpdate:
    async def test_delivery_status_updates_log(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        retailer: Retailer,
        active_customer: CsvCustomer,
    ):
        log = ReminderLog(
            retailer_id=retailer.id,
            customer_id=active_customer.id,
            customer_cnic=active_customer.cnic,
            step="branch_a_t0",
            channel="whatsapp",
            direction="outbound",
            status="sent",
            provider_msg_id="wamid.deliver_test",
        )
        db_session.add(log)
        await db_session.commit()

        body = json.dumps(_delivery_payload("wamid.deliver_test", "delivered")).encode()
        response = await client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": _sign_payload(body),
            },
        )
        assert response.status_code == 200

        await db_session.refresh(log)
        assert log.status == "delivered"


class TestInboundReplyHandling:
    async def test_paid_reply_pauses_sequence(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        retailer: Retailer,
        active_customer: CsvCustomer,
    ):
        with patch("kistbook.engine.reply_handler.wetarseel") as mock_ws:
            mock_ws.send_freeform_message = AsyncMock(return_value="wamid.mgr1")

            body = json.dumps(
                _inbound_payload(active_customer.phone, "wamid.paid_reply", "paid kar diya")
            ).encode()
            response = await client.post(
                "/webhooks/whatsapp",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": _sign_payload(body),
                },
            )

        assert response.status_code == 200
        await db_session.refresh(active_customer)
        assert active_customer.sequence_paused is True

    async def test_help_reply_pauses_sequence(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        retailer: Retailer,
        active_customer: CsvCustomer,
    ):
        with patch("kistbook.engine.reply_handler.wetarseel") as mock_ws:
            mock_ws.send_freeform_message = AsyncMock(return_value="wamid.mgr2")

            active_customer.sequence_paused = False
            await db_session.commit()

            body = json.dumps(
                _inbound_payload(active_customer.phone, "wamid.help_reply", "help chahiye")
            ).encode()
            response = await client.post(
                "/webhooks/whatsapp",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": _sign_payload(body),
                },
            )

        assert response.status_code == 200
        await db_session.refresh(active_customer)
        assert active_customer.sequence_paused is True

    async def test_promise_reply_does_not_pause(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        retailer: Retailer,
        active_customer: CsvCustomer,
    ):
        with patch("kistbook.engine.reply_handler.wetarseel") as mock_ws:
            mock_ws.send_freeform_message = AsyncMock(return_value="wamid.mgr3")

            active_customer.sequence_paused = False
            await db_session.commit()

            body = json.dumps(
                _inbound_payload(active_customer.phone, "wamid.promise_reply", "kal kar dunga")
            ).encode()
            response = await client.post(
                "/webhooks/whatsapp",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": _sign_payload(body),
                },
            )

        assert response.status_code == 200
        await db_session.refresh(active_customer)
        assert active_customer.sequence_paused is False

    async def test_synchronous_processing_sc003(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        retailer: Retailer,
        active_customer: CsvCustomer,
    ):
        """SC-003: reply handled + manager alert dispatched within single synchronous request cycle."""
        with patch("kistbook.engine.reply_handler.wetarseel") as mock_ws:
            mock_ws.send_freeform_message = AsyncMock(return_value="wamid.sync_test")

            active_customer.sequence_paused = False
            await db_session.commit()

            body = json.dumps(
                _inbound_payload(active_customer.phone, "wamid.sync_reply", "masla hai")
            ).encode()
            response = await client.post(
                "/webhooks/whatsapp",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Hub-Signature-256": _sign_payload(body),
                },
            )

        assert response.status_code == 200
        mock_ws.send_freeform_message.assert_called_once()
