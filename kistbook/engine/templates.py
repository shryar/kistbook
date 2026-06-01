from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kistbook.db.models import CsvCustomer, ReminderConfig

TEMPLATE_MAP: dict[str, str] = {
    "branch_a_t-3": "kisht_reminder_friendly",
    "branch_a_t0": "kisht_reminder_due",
    "branch_a_t+1": "kisht_reminder_gentle",
    "branch_a_t+3": "kisht_reminder_firm",
    "branch_b_t+7": "kisht_soft_warm",
    "branch_b_t+10": "kisht_soft_partial_offer",
    "branch_c_t+3": "kisht_hard_firm",
    "branch_c_t+5": "kisht_guarantor_notice",
}

_STEP_VARIABLES: dict[str, list[str]] = {
    "branch_a_t-3": ["name", "amount", "due_date"],
    "branch_a_t0": ["name", "amount"],
    "branch_a_t+1": ["name", "amount"],
    "branch_a_t+3": ["name", "amount"],
    "branch_b_t+7": ["name", "amount", "installments_paid"],
    "branch_b_t+10": ["name", "amount"],
    "branch_c_t+3": ["name", "amount"],
    "branch_c_t+5": ["guarantor_name", "customer_name", "amount"],
}


def render_variables(
    step: str,
    customer: CsvCustomer,
    due_date_str: str = "",
) -> dict[str, str]:
    var_keys = _STEP_VARIABLES.get(step, [])
    result: dict[str, str] = {}
    for key in var_keys:
        match key:
            case "name":
                result[key] = customer.customer_name
            case "amount":
                result[key] = str(customer.installment_amount)
            case "due_date":
                result[key] = due_date_str
            case "installments_paid":
                result[key] = str(customer.installments_paid)
            case "guarantor_name":
                result[key] = customer.guarantor_name or ""
            case "customer_name":
                result[key] = customer.customer_name
    return result
