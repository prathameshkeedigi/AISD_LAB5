"""Iteration 2 – status state machine (ADR-002, FR-5.6, NFR-1.2) with ADR-005 end states (decision D1)."""
from itertools import product

import pytest

from app.domain.enums import ApplicationStatus as St
from app.domain.exceptions import DomainError, InvalidTransition
from app.domain.transitions import ALLOWED, assert_transition

# Written from the requirements' transition table plus ADR-005, independent of the implementation.
EXPECTED_ALLOWED = {
    (St.APPLIED, St.SHORTLISTED),
    (St.SHORTLISTED, St.INTERVIEW_SCHEDULED),
    (St.INTERVIEW_SCHEDULED, St.INTERVIEWED),
    (St.INTERVIEWED, St.OFFERED),
    (St.OFFERED, St.ACCEPTED),
    # ADR-005: rejection before an offer, decline of an offer
    (St.APPLIED, St.REJECTED),
    (St.SHORTLISTED, St.REJECTED),
    (St.INTERVIEW_SCHEDULED, St.REJECTED),
    (St.INTERVIEWED, St.REJECTED),
    (St.OFFERED, St.DECLINED),
}
DISALLOWED = [p for p in product(St, St) if p not in EXPECTED_ALLOWED]


def test_table_matches_specification():
    assert ALLOWED == EXPECTED_ALLOWED


def test_every_disallowed_pair_is_counted():
    assert len(DISALLOWED) == 64 - 10


@pytest.mark.parametrize("current, new", sorted(EXPECTED_ALLOWED))
def test_allowed_transition_passes(current, new):
    assert_transition(current, new)


@pytest.mark.parametrize("current, new", DISALLOWED)
def test_NFR1_2_disallowed_transition_is_rejected(current, new):
    with pytest.raises(InvalidTransition):
        assert_transition(current, new)


def test_examples_from_spec_are_rejected():
    for current, new in [(St.APPLIED, St.OFFERED), (St.APPLIED, St.ACCEPTED), (St.OFFERED, St.APPLIED)]:
        with pytest.raises(InvalidTransition):
            assert_transition(current, new)


def test_ADR004_invalid_transition_is_a_domain_error_not_http():
    assert issubclass(InvalidTransition, DomainError)
    assert "fastapi" not in InvalidTransition.__module__
