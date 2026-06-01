from __future__ import annotations

STEP_TRIGGERS: dict[str, tuple[int, str]] = {
    # step_key: (days_since_due, target_channel)
    "branch_a_t-3": (-3, "whatsapp"),
    "branch_a_t0": (0, "whatsapp"),
    "branch_a_t+1": (1, "whatsapp"),
    "branch_a_t+3": (3, "whatsapp"),
    "branch_b_t+7": (7, "whatsapp"),
    "branch_b_t+10": (10, "whatsapp"),
    "branch_b_t+14": (14, "manager_whatsapp"),
    "branch_c_t+3": (3, "whatsapp"),
    "branch_c_t+5": (5, "whatsapp"),  # guarantor step — skip if no guarantor
    "branch_c_t+7": (7, "manager_whatsapp"),
}

BRANCH_STEPS: dict[str, list[str]] = {
    "A": ["branch_a_t-3", "branch_a_t0", "branch_a_t+1", "branch_a_t+3"],
    "B": ["branch_b_t+7", "branch_b_t+10", "branch_b_t+14"],
    "C": ["branch_c_t+3", "branch_c_t+5", "branch_c_t+7"],
}


def classify(installments_paid: int, days_since_due: int) -> str:
    if installments_paid == 0 and days_since_due > 0:
        return "C"
    if installments_paid >= 1 and days_since_due > 3:
        return "B"
    return "A"
