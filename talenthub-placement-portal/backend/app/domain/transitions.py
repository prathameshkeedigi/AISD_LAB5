"""Application state machine: ADR-002 forward chain plus the ADR-005 end states REJECTED and DECLINED."""
from app.domain.enums import ApplicationStatus as St
from app.domain.exceptions import InvalidTransition

ALLOWED = {
    (St.APPLIED, St.SHORTLISTED),
    (St.SHORTLISTED, St.INTERVIEW_SCHEDULED),
    (St.INTERVIEW_SCHEDULED, St.INTERVIEWED),
    (St.INTERVIEWED, St.OFFERED),
    (St.OFFERED, St.ACCEPTED),
    (St.APPLIED, St.REJECTED),
    (St.SHORTLISTED, St.REJECTED),
    (St.INTERVIEW_SCHEDULED, St.REJECTED),
    (St.INTERVIEWED, St.REJECTED),
    (St.OFFERED, St.DECLINED),
}


def assert_transition(current, new) -> None:
    current, new = St(current), St(new)
    if (current, new) not in ALLOWED:
        raise InvalidTransition(f"Cannot move an application from {current.value} to {new.value}")
