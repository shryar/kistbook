from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_number: Mapped[str] = mapped_column(Text, nullable=False)
    manager_phone: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    config: Mapped[Optional[ReminderConfig]] = relationship(back_populates="retailer", uselist=False)
    customers: Mapped[list[CsvCustomer]] = relationship(back_populates="retailer")
    reminder_logs: Mapped[list[ReminderLog]] = relationship(back_populates="retailer")


class ReminderConfig(Base):
    __tablename__ = "reminder_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id"), nullable=False, unique=True
    )
    branch_a_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="TRUE")
    branch_b_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="TRUE")
    branch_c_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="TRUE")
    tone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="standard",
    )
    vip_cnic_list: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    scan_time_utc: Mapped[str] = mapped_column(String(5), nullable=False, server_default="01:00")
    updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    __table_args__ = (
        CheckConstraint("tone IN ('formal', 'standard', 'light')", name="ck_reminder_config_tone"),
    )

    retailer: Mapped[Retailer] = relationship(back_populates="config")


class CsvCustomer(Base):
    __tablename__ = "csv_customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id"), nullable=False
    )
    customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    cnic: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)
    guarantor_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    guarantor_phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    installment_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_day_of_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_installments: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    installments_paid: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    last_payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sequence_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="FALSE")
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="FALSE")
    imported_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("installment_amount > 0", name="ck_csv_customers_installment_amount"),
        CheckConstraint("due_day_of_month BETWEEN 1 AND 28", name="ck_csv_customers_due_day"),
        CheckConstraint("total_installments > 0", name="ck_csv_customers_total_installments"),
        CheckConstraint("installments_paid >= 0", name="ck_csv_customers_installments_paid_min"),
        CheckConstraint(
            "installments_paid <= total_installments",
            name="ck_csv_customers_installments_paid_max",
        ),
        UniqueConstraint("retailer_id", "cnic", name="uq_csv_customers_retailer_cnic"),
    )

    retailer: Mapped[Retailer] = relationship(back_populates="customers")
    reminder_logs: Mapped[list[ReminderLog]] = relationship(back_populates="customer")


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retailers.id"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("csv_customers.id"), nullable=False
    )
    customer_cnic: Mapped[str] = mapped_column(Text, nullable=False)
    step: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    provider_msg_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inbound_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    status_updated_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("customer_id", "step", "channel", name="uq_reminder_logs_idempotency"),
    )

    retailer: Mapped[Retailer] = relationship(back_populates="reminder_logs")
    customer: Mapped[CsvCustomer] = relationship(back_populates="reminder_logs")
