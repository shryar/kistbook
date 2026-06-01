"""Initial schema: all four tables with idempotency constraint

Revision ID: 001
Revises:
Create Date: 2026-06-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "retailers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("whatsapp_number", sa.Text, nullable=False),
        sa.Column("manager_phone", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "reminder_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "retailer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("retailers.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("branch_a_enabled", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("branch_b_enabled", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("branch_c_enabled", sa.Boolean, nullable=False, server_default="TRUE"),
        sa.Column("tone", sa.String(20), nullable=False, server_default="standard"),
        sa.Column(
            "vip_cnic_list",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("scan_time_utc", sa.String(5), nullable=False, server_default="01:00"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("tone IN ('formal', 'standard', 'light')", name="ck_reminder_config_tone"),
    )

    op.create_table(
        "csv_customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "retailer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("retailers.id"),
            nullable=False,
        ),
        sa.Column("customer_name", sa.Text, nullable=False),
        sa.Column("cnic", sa.Text, nullable=False),
        sa.Column("phone", sa.Text, nullable=False),
        sa.Column("guarantor_name", sa.Text, nullable=True),
        sa.Column("guarantor_phone", sa.Text, nullable=True),
        sa.Column("installment_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_day_of_month", sa.SmallInteger, nullable=False),
        sa.Column("total_installments", sa.SmallInteger, nullable=False),
        sa.Column("installments_paid", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("last_payment_date", sa.Date, nullable=True),
        sa.Column("sequence_paused", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column(
            "imported_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("installment_amount > 0", name="ck_csv_customers_installment_amount"),
        sa.CheckConstraint(
            "due_day_of_month BETWEEN 1 AND 28", name="ck_csv_customers_due_day"
        ),
        sa.CheckConstraint(
            "total_installments > 0", name="ck_csv_customers_total_installments"
        ),
        sa.CheckConstraint(
            "installments_paid >= 0", name="ck_csv_customers_installments_paid_min"
        ),
        sa.CheckConstraint(
            "installments_paid <= total_installments",
            name="ck_csv_customers_installments_paid_max",
        ),
        sa.UniqueConstraint("retailer_id", "cnic", name="uq_csv_customers_retailer_cnic"),
    )

    op.create_index(
        "ix_csv_customers_active",
        "csv_customers",
        ["retailer_id"],
        postgresql_where=sa.text("is_completed = FALSE AND sequence_paused = FALSE"),
    )

    op.create_table(
        "reminder_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "retailer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("retailers.id"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("csv_customers.id"),
            nullable=False,
        ),
        sa.Column("customer_cnic", sa.Text, nullable=False),
        sa.Column("step", sa.Text, nullable=False),
        sa.Column("channel", sa.Text, nullable=False),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("template_id", sa.Text, nullable=True),
        sa.Column("message_body", sa.Text, nullable=True),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("provider_msg_id", sa.Text, nullable=True),
        sa.Column("inbound_text", sa.Text, nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status_updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "customer_id", "step", "channel", name="uq_reminder_logs_idempotency"
        ),
    )

    op.create_index(
        "ix_reminder_logs_retailer_sent_at",
        "reminder_logs",
        ["retailer_id", sa.text("sent_at DESC")],
    )
    op.create_index(
        "ix_reminder_logs_provider_msg_id",
        "reminder_logs",
        ["provider_msg_id"],
    )


def downgrade() -> None:
    op.drop_table("reminder_logs")
    op.drop_index("ix_csv_customers_active", table_name="csv_customers")
    op.drop_table("csv_customers")
    op.drop_table("reminder_config")
    op.drop_table("retailers")
