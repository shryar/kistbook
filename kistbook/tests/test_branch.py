from __future__ import annotations

import pytest

from kistbook.engine.branch import BRANCH_STEPS, STEP_TRIGGERS, classify


class TestClassify:
    def test_branch_c_never_paid_overdue(self):
        assert classify(0, 1) == "C"

    def test_branch_c_never_paid_many_days(self):
        assert classify(0, 30) == "C"

    def test_branch_a_never_paid_zero_days(self):
        # days_since_due == 0, not > 0 — so not C
        assert classify(0, 0) == "A"

    def test_branch_a_never_paid_upcoming(self):
        assert classify(0, -3) == "A"

    def test_branch_a_paid_within_3_days(self):
        assert classify(1, 3) == "A"

    def test_branch_a_paid_early(self):
        assert classify(5, -3) == "A"

    def test_branch_b_partial_payer_over_3_days(self):
        assert classify(1, 4) == "B"

    def test_branch_b_partial_payer_many_days(self):
        assert classify(3, 14) == "B"

    def test_branch_b_many_paid_still_overdue(self):
        assert classify(10, 7) == "B"

    def test_boundary_never_paid_exactly_zero(self):
        assert classify(0, 0) == "A"

    def test_boundary_paid_exactly_3_days(self):
        assert classify(2, 3) == "A"

    def test_boundary_paid_exactly_4_days(self):
        assert classify(2, 4) == "B"


class TestStepTriggers:
    def test_all_branch_a_steps_defined(self):
        for step in BRANCH_STEPS["A"]:
            assert step in STEP_TRIGGERS

    def test_all_branch_b_steps_defined(self):
        for step in BRANCH_STEPS["B"]:
            assert step in STEP_TRIGGERS

    def test_all_branch_c_steps_defined(self):
        for step in BRANCH_STEPS["C"]:
            assert step in STEP_TRIGGERS

    def test_branch_a_t_minus_3_trigger(self):
        days, channel = STEP_TRIGGERS["branch_a_t-3"]
        assert days == -3
        assert channel == "whatsapp"

    def test_branch_a_t0_trigger(self):
        days, channel = STEP_TRIGGERS["branch_a_t0"]
        assert days == 0
        assert channel == "whatsapp"

    def test_branch_b_t14_is_manager(self):
        days, channel = STEP_TRIGGERS["branch_b_t+14"]
        assert days == 14
        assert channel == "manager_whatsapp"

    def test_branch_c_t5_is_guarantor_step(self):
        days, channel = STEP_TRIGGERS["branch_c_t+5"]
        assert days == 5
        assert channel == "whatsapp"

    def test_branch_c_t7_is_manager(self):
        days, channel = STEP_TRIGGERS["branch_c_t+7"]
        assert days == 7
        assert channel == "manager_whatsapp"
