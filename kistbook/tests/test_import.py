from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.core.config import settings
from kistbook.core.security import create_access_token
from kistbook.db.models import CsvCustomer, Retailer, ReminderConfig


def _auth_header() -> dict:
    token = create_access_token({"sub": "test_user"})
    return {"Authorization": f"Bearer {token}"}


CSV_HEADERS = "customer_name,cnic,phone,guarantor_name,guarantor_phone,installment_amount,due_day_of_month,total_installments,installments_paid,last_payment_date"


def _make_row(
    name="Ahmed Khan",
    cnic="3520212345671",
    phone="+923001234567",
    g_name="",
    g_phone="",
    amount="5000",
    due_day="15",
    total="12",
    paid="3",
    last_date="2026-05-15",
) -> str:
    return f"{name},{cnic},{phone},{g_name},{g_phone},{amount},{due_day},{total},{paid},{last_date}"


@pytest.fixture
async def retailer(db_session: AsyncSession) -> Retailer:
    r = Retailer(
        name=f"ImportShop-{uuid.uuid4().hex[:6]}",
        whatsapp_number="+923004444444",
        manager_phone="+923006666666",
    )
    db_session.add(r)
    await db_session.flush()
    config = ReminderConfig(retailer_id=r.id)
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(r)
    return r


class TestCsvImport:
    async def test_valid_5_row_import(self, client: AsyncClient, retailer: Retailer):
        rows = [
            _make_row(cnic=f"352021234567{i}", phone=f"+9230012345{i:02d}")
            for i in range(5)
        ]
        csv_content = (CSV_HEADERS + "\n" + "\n".join(rows)).encode()

        response = await client.post(
            f"/retailers/{retailer.id}/import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            headers=_auth_header(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == 5
        assert data["errors"] == []

    async def test_invalid_phone_returns_422(self, client: AsyncClient, retailer: Retailer):
        rows = [_make_row(cnic="1000000000001", phone="not-a-phone")]
        csv_content = (CSV_HEADERS + "\n" + "\n".join(rows)).encode()

        response = await client.post(
            f"/retailers/{retailer.id}/import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            headers=_auth_header(),
        )
        assert response.status_code == 422

    async def test_due_day_31_returns_422(self, client: AsyncClient, retailer: Retailer):
        rows = [_make_row(cnic="2000000000001", due_day="31")]
        csv_content = (CSV_HEADERS + "\n" + "\n".join(rows)).encode()

        response = await client.post(
            f"/retailers/{retailer.id}/import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            headers=_auth_header(),
        )
        assert response.status_code == 422

    async def test_reimport_updates_existing(
        self, client: AsyncClient, db_session: AsyncSession, retailer: Retailer
    ):
        cnic = "3000000000001"
        rows = [_make_row(cnic=cnic, phone="+923001112222", paid="1")]
        csv_content = (CSV_HEADERS + "\n" + "\n".join(rows)).encode()

        await client.post(
            f"/retailers/{retailer.id}/import-csv",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            headers=_auth_header(),
        )

        rows2 = [_make_row(cnic=cnic, phone="+923001112222", paid="3")]
        csv2 = (CSV_HEADERS + "\n" + "\n".join(rows2)).encode()

        response = await client.post(
            f"/retailers/{retailer.id}/import-csv",
            files={"file": ("test.csv", io.BytesIO(csv2), "text/csv")},
            headers=_auth_header(),
        )
        assert response.status_code == 200

        customer = await db_session.scalar(
            select(CsvCustomer).where(
                CsvCustomer.retailer_id == retailer.id,
                CsvCustomer.cnic == cnic,
            )
        )
        assert customer.installments_paid == 3

    async def test_missing_required_column_returns_400(
        self, client: AsyncClient, retailer: Retailer
    ):
        bad_csv = "customer_name,cnic\nAhmed,3520212345671".encode()
        response = await client.post(
            f"/retailers/{retailer.id}/import-csv",
            files={"file": ("test.csv", io.BytesIO(bad_csv), "text/csv")},
            headers=_auth_header(),
        )
        assert response.status_code == 400
