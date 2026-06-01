from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.api.deps import get_current_user, get_db_session
from kistbook.db.models import Retailer, ReminderLog

router = APIRouter(prefix="/retailers", tags=["logs"])


class LogResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_cnic: str
    step: str
    channel: str
    direction: str
    template_id: Optional[str]
    status: str
    provider_msg_id: Optional[str]
    sent_at: Optional[datetime]
    status_updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    logs: list[LogResponse]


@router.get("/{retailer_id}/reminder-logs", response_model=LogListResponse)
async def list_logs(
    retailer_id: uuid.UUID,
    customer_id: Optional[uuid.UUID] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db_session),
    _user: dict = Depends(get_current_user),
) -> LogListResponse:
    retailer = await db.get(Retailer, retailer_id)
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found")

    q = select(ReminderLog).where(ReminderLog.retailer_id == retailer_id)
    count_q = select(func.count()).select_from(ReminderLog).where(
        ReminderLog.retailer_id == retailer_id
    )

    if customer_id:
        q = q.where(ReminderLog.customer_id == customer_id)
        count_q = count_q.where(ReminderLog.customer_id == customer_id)
    if direction:
        q = q.where(ReminderLog.direction == direction)
        count_q = count_q.where(ReminderLog.direction == direction)
    if status:
        q = q.where(ReminderLog.status == status)
        count_q = count_q.where(ReminderLog.status == status)
    if from_date:
        q = q.where(ReminderLog.sent_at >= from_date)
        count_q = count_q.where(ReminderLog.sent_at >= from_date)
    if to_date:
        q = q.where(ReminderLog.sent_at <= to_date)
        count_q = count_q.where(ReminderLog.sent_at <= to_date)

    q = q.order_by(ReminderLog.sent_at.desc())

    total = await db.scalar(count_q) or 0
    logs = (await db.scalars(q.offset((page - 1) * page_size).limit(page_size))).all()

    return LogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        logs=[LogResponse.model_validate(log) for log in logs],
    )
