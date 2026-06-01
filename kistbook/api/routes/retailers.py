from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kistbook.api.deps import get_current_user, get_db_session
from kistbook.db.models import CsvCustomer, ReminderConfig, Retailer

router = APIRouter(prefix="/retailers", tags=["retailers"])

E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")
CNIC_RE = re.compile(r"^\d{13}$")


def _validate_e164(phone: str, field: str) -> str:
    if not E164_RE.match(phone):
        raise ValueError(f"{field} must be E.164 format")
    return phone


# ── Request / Response schemas ──────────────────────────────────────────────


class CreateRetailerRequest(BaseModel):
    name: str
    whatsapp_number: str
    manager_phone: str

    @field_validator("whatsapp_number", "manager_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not E164_RE.match(v):
            raise ValueError("Must be E.164 format (e.g. +923001234567)")
        return v


class RetailerResponse(BaseModel):
    id: uuid.UUID
    name: str
    whatsapp_number: str
    manager_phone: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportSummary(BaseModel):
    imported: int
    skipped: int
    errors: list[dict]


class CsvRowError(BaseModel):
    row: int
    field: str
    message: str


class ConfigResponse(BaseModel):
    id: uuid.UUID
    retailer_id: uuid.UUID
    branch_a_enabled: bool
    branch_b_enabled: bool
    branch_c_enabled: bool
    tone: str
    vip_cnic_list: list[str]
    scan_time_utc: str
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class UpdateConfigRequest(BaseModel):
    branch_a_enabled: Optional[bool] = None
    branch_b_enabled: Optional[bool] = None
    branch_c_enabled: Optional[bool] = None
    tone: Optional[str] = None
    vip_cnic_list: Optional[list[str]] = None
    scan_time_utc: Optional[str] = None

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("formal", "standard", "light"):
            raise ValueError("tone must be one of: formal, standard, light")
        return v


# ── CSV row validation ───────────────────────────────────────────────────────

REQUIRED_HEADERS = {
    "customer_name", "cnic", "phone", "guarantor_name", "guarantor_phone",
    "installment_amount", "due_day_of_month", "total_installments",
    "installments_paid", "last_payment_date",
}


def _parse_csv_row(row_num: int, row: dict) -> tuple[dict | None, list[CsvRowError]]:
    errors: list[CsvRowError] = []

    def err(field: str, msg: str) -> None:
        errors.append(CsvRowError(row=row_num, field=field, message=msg))

    phone = row.get("phone", "").strip()
    if not phone:
        err("phone", "Required")
    elif not E164_RE.match(phone):
        err("phone", "Invalid E.164 format")

    cnic = row.get("cnic", "").strip()
    if not cnic:
        err("cnic", "Required")
    elif not CNIC_RE.match(cnic):
        err("cnic", "Must be 13 digits, no dashes")

    customer_name = row.get("customer_name", "").strip()
    if not customer_name:
        err("customer_name", "Required")

    try:
        amount = Decimal(row.get("installment_amount", "").strip())
        if amount <= 0:
            err("installment_amount", "Must be > 0")
    except Exception:
        err("installment_amount", "Must be a number > 0")
        amount = None

    try:
        due_day = int(row.get("due_day_of_month", "").strip())
        if not (1 <= due_day <= 28):
            err("due_day_of_month", "Must be between 1 and 28")
    except Exception:
        err("due_day_of_month", "Must be an integer between 1 and 28")
        due_day = None

    try:
        total = int(row.get("total_installments", "").strip())
        if total <= 0:
            err("total_installments", "Must be > 0")
    except Exception:
        err("total_installments", "Must be a positive integer")
        total = None

    try:
        paid = int(row.get("installments_paid", "").strip() or "0")
        if paid < 0:
            err("installments_paid", "Must be >= 0")
        if total is not None and paid > total:
            err("installments_paid", "Cannot exceed total_installments")
    except Exception:
        err("installments_paid", "Must be an integer >= 0")
        paid = None

    last_payment_raw = row.get("last_payment_date", "").strip()
    last_payment: Optional[date] = None
    if last_payment_raw:
        try:
            last_payment = date.fromisoformat(last_payment_raw)
        except ValueError:
            err("last_payment_date", "Must be ISO date format YYYY-MM-DD")

    guarantor_phone = row.get("guarantor_phone", "").strip() or None
    if guarantor_phone and not E164_RE.match(guarantor_phone):
        err("guarantor_phone", "Invalid E.164 format")

    if errors:
        return None, errors

    return {
        "customer_name": customer_name,
        "cnic": cnic,
        "phone": phone,
        "guarantor_name": row.get("guarantor_name", "").strip() or None,
        "guarantor_phone": guarantor_phone,
        "installment_amount": amount,
        "due_day_of_month": due_day,
        "total_installments": total,
        "installments_paid": paid,
        "last_payment_date": last_payment,
    }, []


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RetailerResponse)
async def create_retailer(
    body: CreateRetailerRequest,
    db: AsyncSession = Depends(get_db_session),
    _user: dict = Depends(get_current_user),
) -> RetailerResponse:
    existing = await db.scalar(select(Retailer).where(Retailer.name == body.name))
    if existing:
        raise HTTPException(status_code=409, detail="Retailer already exists")

    retailer = Retailer(
        name=body.name,
        whatsapp_number=body.whatsapp_number,
        manager_phone=body.manager_phone,
    )
    db.add(retailer)
    await db.flush()

    config = ReminderConfig(retailer_id=retailer.id)
    db.add(config)
    await db.commit()
    await db.refresh(retailer)
    return RetailerResponse.model_validate(retailer)


@router.post("/{retailer_id}/import-csv", response_model=ImportSummary)
async def import_csv(
    retailer_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db_session),
    _user: dict = Depends(get_current_user),
) -> ImportSummary:
    retailer = await db.get(Retailer, retailer_id)
    if not retailer:
        raise HTTPException(status_code=404, detail="Retailer not found")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    headers = set(reader.fieldnames or [])
    missing = REQUIRED_HEADERS - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}",
        )

    all_errors: list[dict] = []
    parsed_rows: list[dict] = []

    for row_num, row in enumerate(reader, start=2):
        data, errors = _parse_csv_row(row_num, row)
        if errors:
            all_errors.extend([e.model_dump() for e in errors])
        else:
            parsed_rows.append(data)

    if all_errors:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "csv_validation_failed",
                "detail": f"{len(all_errors)} rows failed validation",
                "errors": all_errors,
            },
        )

    from sqlalchemy.dialects.postgresql import insert as pg_insert

    for row_data in parsed_rows:
        stmt = (
            pg_insert(CsvCustomer)
            .values(
                retailer_id=retailer_id,
                is_completed=False,
                **row_data,
            )
            .on_conflict_do_update(
                constraint="uq_csv_customers_retailer_cnic",
                set_={
                    "customer_name": row_data["customer_name"],
                    "phone": row_data["phone"],
                    "guarantor_name": row_data["guarantor_name"],
                    "guarantor_phone": row_data["guarantor_phone"],
                    "installment_amount": row_data["installment_amount"],
                    "due_day_of_month": row_data["due_day_of_month"],
                    "total_installments": row_data["total_installments"],
                    "installments_paid": row_data["installments_paid"],
                    "last_payment_date": row_data["last_payment_date"],
                    "is_completed": False,
                    "imported_at": datetime.now(timezone.utc),
                },
            )
        )
        await db.execute(stmt)

    await db.commit()
    return ImportSummary(imported=len(parsed_rows), skipped=0, errors=[])


@router.get("/{retailer_id}/config", response_model=ConfigResponse)
async def get_config(
    retailer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: dict = Depends(get_current_user),
) -> ConfigResponse:
    config = await db.scalar(
        select(ReminderConfig).where(ReminderConfig.retailer_id == retailer_id)
    )
    if not config:
        raise HTTPException(status_code=404, detail="Retailer not found")
    return ConfigResponse.model_validate(config)


@router.patch("/{retailer_id}/config", response_model=ConfigResponse)
async def update_config(
    retailer_id: uuid.UUID,
    body: UpdateConfigRequest,
    db: AsyncSession = Depends(get_db_session),
    _user: dict = Depends(get_current_user),
) -> ConfigResponse:
    config = await db.scalar(
        select(ReminderConfig).where(ReminderConfig.retailer_id == retailer_id)
    )
    if not config:
        raise HTTPException(status_code=404, detail="Retailer not found")

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(config, field, value)
    config.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(config)
    return ConfigResponse.model_validate(config)
