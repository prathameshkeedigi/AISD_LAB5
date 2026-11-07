"""Iteration 1 – eligibility rules R1–R4 (FR-4.1 to FR-4.7).
Expected values are taken from the requirements' rule and boundary tables (NFR-1.1), not from the code."""
from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from app.domain.enums import Branch
from app.services.eligibility_service import EligibilityResult, check_eligibility


@dataclass
class S:
    cgpa: Decimal = Decimal("8.00")
    active_backlogs: int = 0
    cleared_backlogs: int = 0
    branch: Branch = Branch.CSE
    has_accepted_offer: bool = False


@dataclass
class J:
    min_cgpa: Decimal = Decimal("6.50")
    max_backlogs: int = 0
    allowed_branches: set = field(default_factory=set)


def test_FR4_1_returns_eligibility_result():
    r = check_eligibility(S(), J())
    assert isinstance(r, EligibilityResult)
    assert r.eligible is True


def test_FR4_2_all_pass_reason_states_all_conditions_met():
    assert check_eligibility(S(), J()).reason == "All eligibility conditions are met"


@pytest.mark.parametrize(
    "cgpa, eligible",
    [(Decimal("6.49"), False), (Decimal("6.50"), True), (Decimal("6.51"), True)],
)
def test_FR4_3_R1_cgpa_boundary(cgpa, eligible):
    assert check_eligibility(S(cgpa=cgpa), J(min_cgpa=Decimal("6.50"))).eligible is eligible


def test_FR4_3_R1_float_input_6_5_equals_minimum():
    assert check_eligibility(S(cgpa=6.5), J(min_cgpa=6.5)).eligible is True


def test_FR4_7_R1_reason_text():
    r = check_eligibility(S(cgpa=Decimal("6.49")), J(min_cgpa=Decimal("6.50")))
    assert r.reason == "CGPA 6.49 below minimum 6.5"
    assert r.failed_rule == "R1"


def test_FR4_4_R2_cleared_backlogs_ignored():
    assert check_eligibility(S(active_backlogs=0, cleared_backlogs=3), J(max_backlogs=0)).eligible is True


def test_R2_one_active_backlog_on_no_backlog_drive_is_ineligible():
    r = check_eligibility(S(active_backlogs=1), J(max_backlogs=0))
    assert r.eligible is False
    assert r.failed_rule == "R2"
    assert r.reason == "1 active backlogs"


def test_R2_backlogs_equal_to_maximum_pass():
    assert check_eligibility(S(active_backlogs=2), J(max_backlogs=2)).eligible is True


def test_R3_already_accepted_offer_is_ineligible():
    r = check_eligibility(S(has_accepted_offer=True), J())
    assert (r.eligible, r.failed_rule, r.reason) == (False, "R3", "Already accepted an offer this season")


@pytest.mark.parametrize("branch", list(Branch))
def test_FR3_3_R4_empty_allowed_branches_is_pool_drive(branch):
    assert check_eligibility(S(branch=branch), J(allowed_branches=set())).eligible is True


def test_R4_branch_in_whitelist_passes():
    assert check_eligibility(S(branch=Branch.CSE), J(allowed_branches={Branch.CSE, Branch.ISE})).eligible is True


def test_R4_branch_outside_whitelist_fails():
    r = check_eligibility(S(branch=Branch.ECE), J(allowed_branches={Branch.CSE}))
    assert (r.eligible, r.failed_rule, r.reason) == (False, "R4", "Branch ECE not in drive scope")


def test_FR4_2_first_failing_rule_is_reported():
    r = check_eligibility(S(cgpa=Decimal("5.00"), branch=Branch.ECE), J(allowed_branches={Branch.CSE}))
    assert r.failed_rule == "R1"


def test_FR4_1_ineligibility_is_returned_not_raised():
    r = check_eligibility(S(cgpa=Decimal("0"), active_backlogs=9, has_accepted_offer=True), J())
    assert r.eligible is False
