"""The single implementation of the eligibility rules R1–R4 (FR-4.5, NFR-2.6). Pure: no database, no HTTP."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str
    failed_rule: Optional[str] = None


def _dec(value) -> Decimal:
    # str() first so a float 6.5 becomes exactly Decimal("6.5"), never 6.4999...
    return Decimal(str(value))


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _code(value) -> str:
    return getattr(value, "value", value)


def check_eligibility(student, job) -> EligibilityResult:
    """Evaluate R1→R4 in order and return at the first failure (FR-4.1, FR-4.2)."""
    cgpa, minimum = _dec(student.cgpa), _dec(job.min_cgpa)
    if not cgpa >= minimum:  # R1: equal passes (FR-4.3)
        return EligibilityResult(False, f"CGPA {_fmt(cgpa)} below minimum {_fmt(minimum)}", "R1")
    if student.active_backlogs > job.max_backlogs:  # R2: cleared backlogs never count (FR-4.4)
        return EligibilityResult(False, f"{student.active_backlogs} active backlogs", "R2")
    if student.has_accepted_offer:  # R3: season-wide
        return EligibilityResult(False, "Already accepted an offer this season", "R3")
    allowed = {_code(b) for b in job.allowed_branches}
    if allowed and _code(student.branch) not in allowed:  # R4: empty list = pool drive
        return EligibilityResult(False, f"Branch {_code(student.branch)} not in drive scope", "R4")
    return EligibilityResult(True, "All eligibility conditions are met")
