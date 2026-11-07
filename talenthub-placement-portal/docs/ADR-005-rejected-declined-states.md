# ADR-005: Add REJECTED and DECLINED as end states

**Status:** Accepted (team decision D1, 6 Nov 2026)
**Amends:** ADR-002 (application state machine); resolves open issue 2 of the requirements.

## Context
The requirements define six forward-only statuses, APPLIED → SHORTLISTED → INTERVIEW_SCHEDULED → INTERVIEWED → OFFERED → ACCEPTED, and leave rejection and withdrawal "to an ADR update if needed". In practice, a company must be able to reject an applicant, a failed interview must end the application, and a student must be able to decline an offer.

## Decision
Two end states are added. No transition leaves them.

| From | To | Who |
|---|---|---|
| APPLIED, SHORTLISTED, INTERVIEW_SCHEDULED, INTERVIEWED | REJECTED | Company representative (own drive) or coordinator; also set automatically when an interview round is failed |
| OFFERED | DECLINED | The student who owns the application |

All other rules of ADR-002 stay as they are: no skipping, no moving backwards. The full table is in `backend/app/domain/transitions.py`. `tests/unit/test_transitions.py` checks the 10 allowed moves and all 54 disallowed ones.

## Consequences
- 8 statuses instead of 6, still held in an enum, not a table.
- A declined offer does not count for rule R3, so the student stays eligible for other drives.
