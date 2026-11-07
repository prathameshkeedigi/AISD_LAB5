"""Placement workflow: apply, shortlist, interview, offer, accept (FR-5 to FR-8).

Raises only domain exceptions (ADR-004). Owns the transaction: one commit per use case."""
import logging
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

from app.domain.actors import Actor
from app.domain.enums import ApplicationStatus as St
from app.domain.enums import ConsentPurpose, UserRole
from app.domain.exceptions import (
    AlreadyApplied, ApplicationNotFound, ConsentMissing, DuplicateRound, InvalidTransition, JobClosed, JobNotFound,
    NoSeasonForDate, NotEligible, NotFound, OfferAlreadyIssued, PermissionDenied, SameCompanyThisSeason,
    StudentNotFound,
)
from app.domain.transitions import assert_transition
from app.models.models import Application, ApplicationStatusHistory, EligibilityDecision, InterviewSlot, Offer
from app.repositories import repository as repo
from app.services.eligibility_service import EligibilityResult, check_eligibility

log = logging.getLogger(__name__)


def _today() -> date:
    return datetime.now(timezone.utc).date()


@dataclass(frozen=True)
class _StudentFacts:
    cgpa: Decimal
    active_backlogs: int
    branch: str
    has_accepted_offer: bool


@dataclass(frozen=True)
class _JobFacts:
    min_cgpa: Decimal
    max_backlogs: int
    allowed_branches: tuple


@dataclass
class ShortlistReport:
    shortlisted: list[int] = field(default_factory=list)
    ineligible: dict[int, str] = field(default_factory=dict)


# ---------- shared helpers ----------
async def evaluate(db, student, job) -> EligibilityResult:
    """Gather the facts (R3 is derived from the job's season) and call the single rule function (FR-4.5)."""
    season = await repo.season_for_date(db, job.drive_date)
    facts = _StudentFacts(
        student.cgpa, student.active_backlogs, student.branch,
        await repo.has_accepted_offer_in_season(db, student.id, season),
    )
    return check_eligibility(facts, _JobFacts(job.min_cgpa, job.max_backlogs, tuple(b.branch for b in job.allowed_branches)))


async def _record_decision(db, student_id, job_id, result: EligibilityResult, context: str):
    await repo.add(db, EligibilityDecision(
        student_id=student_id, job_id=job_id, failed_rule=result.failed_rule, reason=result.reason, context=context,
    ))


async def _change_status(db, application: Application, new_status: St, by_user_id: int):
    """The only place an application's status changes (FR-5.6), always with a history row (NFR-9.1)."""
    assert_transition(application.status, new_status)
    application.status = new_status
    await repo.add(db, ApplicationStatusHistory(
        application_id=application.id, status=new_status, changed_by_user_id=by_user_id,
    ))


async def _require_consent(db, student_id: int):
    if not await repo.active_consent(db, student_id, ConsentPurpose.PLACEMENT):
        raise ConsentMissing("The student has not consented to placement data processing")


def _require_company_access(actor: Actor, job):
    if actor.is_coordinator:
        return
    if actor.role == UserRole.COMPANY_REP and actor.company_id == job.company_id:
        return
    raise PermissionDenied("Not your company's drive")


async def _load_for_company(db, application_id: int, actor: Actor) -> Application:
    app = await repo.get_application(db, application_id)
    if not app:
        raise ApplicationNotFound("Application not found")
    _require_company_access(actor, app.job)
    return app


async def _commit(db):
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


# ---------- FR-5: applying ----------
async def apply_for_job(db, student_id: int, job_id: int, today: date | None = None) -> Application:
    today = today or _today()
    job = await repo.get_job(db, job_id)
    if not job:
        raise JobNotFound("Job listing not found")
    student = await repo.get_student(db, student_id)
    if not student:
        raise StudentNotFound("Student not found")
    if not job.is_open or job.drive_date <= today:
        raise JobClosed("This drive is closed for applications")
    if await repo.find_application(db, student_id, job_id):
        raise AlreadyApplied("You have already applied to this job")
    await _require_consent(db, student_id)

    season = await repo.season_for_date(db, job.drive_date)
    if season is None or season.id != getattr(await repo.season_for_date(db, today), "id", None):
        raise JobClosed("This drive is not in the current placement season")  # FR-5.4
    if await repo.applied_to_company_in_season(db, student_id, job.company_id, season):
        raise SameCompanyThisSeason("You have already applied to this company this season")  # FR-5.3

    result = await evaluate(db, student, job)
    await _record_decision(db, student_id, job_id, result, "APPLY")
    if not result.eligible:
        await _commit(db)  # keep the decision record (NFR-9.3) even though the apply fails
        raise NotEligible(result.reason, result.failed_rule)

    app = await repo.add(db, Application(student_id=student_id, job_id=job_id, status=St.APPLIED))
    await repo.add(db, ApplicationStatusHistory(application_id=app.id, status=St.APPLIED, changed_by_user_id=student.user_id))
    await _commit(db)
    return await repo.get_application(db, app.id)


async def jobs_with_eligibility(db, student_id: int, today: date | None = None):
    """Open, future drives with the student's eligibility and whether they already applied."""
    today = today or _today()
    student = await repo.get_student(db, student_id)
    if not student:
        raise StudentNotFound("Student not found")
    applied = await repo.applied_job_ids(db, student_id)
    out = []
    for job in await repo.list_jobs(db):
        if job.is_open and job.drive_date > today:
            out.append((job, await evaluate(db, student, job), job.id in applied))
    return out


async def list_available_jobs(db, student_id: int, today: date | None = None):
    """FR-4.6: open, future, eligible and not yet applied."""
    return [job for job, result, applied in await jobs_with_eligibility(db, student_id, today) if result.eligible and not applied]


# ---------- FR-6: shortlisting ----------
async def shortlist_students(db, job_id: int, actor: Actor, notifier, today: date | None = None) -> ShortlistReport:
    if not actor.is_coordinator:
        raise PermissionDenied("Only the placement coordinator runs shortlisting")
    job = await repo.get_job(db, job_id)
    if not job:
        raise JobNotFound("Job listing not found")
    report, mails = ShortlistReport(), []
    try:
        for app in await repo.list_applications(db, job_id=job_id, status=St.APPLIED):
            student = app.student
            if not await repo.active_consent(db, student.id, ConsentPurpose.PLACEMENT):
                report.ineligible[student.id] = "No placement consent on record"
                continue
            result = await evaluate(db, student, job)
            await _record_decision(db, student.id, job_id, result, "SHORTLIST")
            if result.eligible:
                await _change_status(db, app, St.SHORTLISTED, actor.user_id)
                report.shortlisted.append(student.id)
                mails.append((student.user.email, f"Shortlisted: {job.role_title}", "You have been shortlisted."))
            else:
                report.ineligible[student.id] = result.reason
                mails.append((student.user.email, f"Not shortlisted: {job.role_title}", f"Reason: {result.reason}"))
        await db.commit()  # one transaction for the whole run (FR-6.4)
    except Exception:
        await db.rollback()
        raise
    for to, subject, body in mails:  # after commit: a mail failure never undoes the run (NFR-6.3)
        try:
            notifier.send(to, subject, body)
        except Exception:
            log.warning("Could not send notification to student", exc_info=True)
    return report


async def shortlist_application(db, application_id: int, actor: Actor, today: date | None = None) -> Application:
    app = await _load_for_company(db, application_id, actor)
    assert_transition(app.status, St.SHORTLISTED)
    await _require_consent(db, app.student_id)
    result = await evaluate(db, app.student, app.job)
    await _record_decision(db, app.student_id, app.job_id, result, "SHORTLIST")
    if not result.eligible:
        await _commit(db)
        raise NotEligible(result.reason, result.failed_rule)
    await _change_status(db, app, St.SHORTLISTED, actor.user_id)
    await _commit(db)
    return await repo.get_application(db, app.id)


async def reject_application(db, application_id: int, actor: Actor) -> Application:
    app = await _load_for_company(db, application_id, actor)
    await _change_status(db, app, St.REJECTED, actor.user_id)
    await _commit(db)
    return await repo.get_application(db, app.id)


# ---------- FR-7: interviews ----------
async def schedule_interview(db, application_id: int, actor: Actor, *, round_no: int, scheduled_at: datetime,
                             venue: str, notes: str = "") -> Application:
    app = await _load_for_company(db, application_id, actor)
    if app.status == St.SHORTLISTED:
        if await repo.get_slot(db, app.id, round_no):
            raise DuplicateRound(f"Round {round_no} is already scheduled")
        await _change_status(db, app, St.INTERVIEW_SCHEDULED, actor.user_id)
    elif app.status == St.INTERVIEW_SCHEDULED:  # a further round; no status change
        if await repo.get_slot(db, app.id, round_no):
            raise DuplicateRound(f"Round {round_no} is already scheduled")
    else:
        raise InvalidTransition(f"Cannot schedule an interview for an application in {St(app.status).value}")
    await repo.add(db, InterviewSlot(application_id=app.id, round_no=round_no, scheduled_at=scheduled_at,
                                     venue=venue, notes=notes))
    await _commit(db)
    return await repo.get_application(db, app.id)


async def record_interview_result(db, application_id: int, actor: Actor, *, round_no: int, passed: bool,
                                  notes: str = "", final: bool = True) -> Application:
    app = await _load_for_company(db, application_id, actor)
    if app.status != St.INTERVIEW_SCHEDULED:
        raise InvalidTransition("Results can be recorded only while interviews are scheduled")
    slot = await repo.get_slot(db, app.id, round_no)
    if not slot:
        raise NotFound(f"Round {round_no} has not been scheduled")
    slot.passed = passed
    if notes:
        slot.notes = notes
    if not passed:
        await _change_status(db, app, St.REJECTED, actor.user_id)
    elif final:
        await _change_status(db, app, St.INTERVIEWED, actor.user_id)
    await _commit(db)
    return await repo.get_application(db, app.id)


# ---------- FR-8: offers ----------
async def issue_offer(db, application_id: int, actor: Actor, package_lpa: Decimal) -> Application:
    app = await _load_for_company(db, application_id, actor)
    if app.offer is not None:
        raise OfferAlreadyIssued("An offer was already issued for this application")
    await _change_status(db, app, St.OFFERED, actor.user_id)  # refuses unless INTERVIEWED (FR-8.2)
    await repo.add(db, Offer(application_id=app.id, package_lpa=package_lpa,
                             offer_letter_key=secrets.token_hex(32)))  # unpredictable (FR-8.3, NFR-3.5)
    await _commit(db)
    return await repo.get_application(db, app.id)


async def respond_to_offer(db, application_id: int, actor: Actor, accept: bool, today: date | None = None) -> Application:
    app = await repo.get_application(db, application_id)
    if not app or app.student_id != actor.student_id:
        raise ApplicationNotFound("Application not found")  # same answer as "missing": reveals nothing (NFR-3.4)
    target = St.ACCEPTED if accept else St.DECLINED
    assert_transition(app.status, target)
    if accept:
        season = await repo.season_for_date(db, app.job.drive_date)
        if await repo.has_accepted_offer_in_season(db, app.student_id, season):
            raise NotEligible("Already accepted an offer this season", "R3")
    await _change_status(db, app, target, actor.user_id)  # derived R3 flag changes in this same commit (NFR-8.4)
    await _commit(db)
    return await repo.get_application(db, app.id)


# ---------- read use cases (ownership checked here, NFR-3.2) ----------
async def my_applications(db, actor: Actor) -> list[Application]:
    return await repo.list_applications(db, student_id=actor.student_id)


async def company_applications(db, actor: Actor) -> list[Application]:
    if actor.role != UserRole.COMPANY_REP:
        raise PermissionDenied("Company representatives only")
    return await repo.list_applications(db, company_id=actor.company_id)


async def job_applications(db, actor: Actor, job_id: int) -> list[Application]:
    job = await repo.get_job(db, job_id)
    if not job:
        raise JobNotFound("Job listing not found")
    _require_company_access(actor, job)
    return await repo.list_applications(db, job_id=job_id)


async def all_applications(db, actor: Actor) -> list[Application]:
    if not actor.is_coordinator:
        raise PermissionDenied("Only the placement coordinator can do this")
    return await repo.list_applications(db)


async def student_profile(db, actor: Actor, today: date | None = None) -> dict:
    student = await repo.get_student(db, actor.student_id)
    if not student:
        raise StudentNotFound("Student profile not found")
    season = await repo.season_for_date(db, today or _today())
    return {
        "id": student.id, "usn": student.usn, "name": student.user.full_name, "email": student.user.email,
        "branch": student.branch, "cgpa": student.cgpa, "active_backlogs": student.active_backlogs,
        "cleared_backlogs": student.cleared_backlogs,
        "has_accepted_offer": await repo.has_accepted_offer_in_season(db, student.id, season),
    }


async def next_round_no(db, application_id: int) -> int:
    app = await repo.get_application(db, application_id)
    return (max((s.round_no for s in app.interviews), default=0) + 1) if app else 1


async def latest_pending_round(db, application_id: int) -> int:
    app = await repo.get_application(db, application_id)
    pending = [s.round_no for s in (app.interviews if app else []) if s.passed is None]
    return max(pending) if pending else 1
