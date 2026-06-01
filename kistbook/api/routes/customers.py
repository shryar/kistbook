from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.api.deps import get_current_user, get_db_session
from kistbook.db.models import CsvCustomer, Retailer

router = APIRouter(prefix="/retailers", tags=["customers"])


class CustomerResponse(BaseModel):
    id: uuid.UUID
    customer_name: str
    cnic: str
    phone: str
    installment_amount: Decimal
    due_day_of_month: int
    total_installments: int
    installments_paid: int
    last_payment_date: Optional[date]
    sequence_paused: bool
    is_completed: bool
    imported_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    customers: list[CustomerResponse]


class PatchCustomerRequest(BaseModel):
    sequence_paused: Optional[bool] = None


@router.get("/{retailer_id}/customers", response_model=CustomerListResponse)
async def list_customers(
    retailer_id: uuid.UUID,
    paused: Optional[bool] = None,
    completed: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db_session),
    _user: dict = Depends(get_current_user),
) -> CustomerListResponse:
    retailer = await db.get(Retailer, retailer_id)
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found")

    q = select(CsvCustomer).where(CsvCustomer.retailer_id == retailer_id)
    count_q = select(func.count()).select_from(CsvCustomer).where(
        CsvCustomer.retailer_id == retailer_id
    )

    if paused is not None:
        q = q.where(CsvCustomer.sequence_paused == paused)
        count_q = count_q.where(CsvCustomer.sequence_paused == paused)
    if completed is not None:
        q = q.where(CsvCustomer.is_completed == completed)
        count_q = count_q.where(CsvCustomer.is_completed == completed)

    total = await db.scalar(count_q) or 0
    customers = (
        await db.scalars(q.offset((page - 1) * page_size).limit(page_size))
    ).all()

    return CustomerListResponse(
        total=total,
        page=page,
        page_size=page_size,
        customers=[CustomerResponse.model_validate(c) for c in customers],
    )


@router.patch("/{retailer_id}/customers/{customer_id}", response_model=CustomerResponse)
async def patch_customer(
    retailer_id: uuid.UUID,
    customer_id: uuid.UUID,
    body: PatchCustomerRequest,
    db: AsyncSession = Depends(get_db_session),
    _user: dict = Depends(get_current_user),
) -> CustomerResponse:
    retailer = await db.get(Retailer, retailer_id)
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found")

    customer = await db.scalar(
        select(CsvCustomer).where(
            CsvCustomer.id == customer_id,
            CsvCustomer.retailer_id == retailer_id,
        )
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if body.sequence_paused is not None:
        customer.sequence_paused = body.sequence_paused

    await db.commit()
    await db.refresh(customer)
    return CustomerResponse.model_validate(customer)
