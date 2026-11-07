"""Coordinator functions (FR-2.3, FR-3, FR-9) and privacy functions (FR-10, NFR-4). Domain exceptions only."""
import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal

from app.core.security import hash_password
from app.domain.actors import Actor
from app.domain.enums import ApplicationStatus as St
from app.domain.enums import Branch, ConsentPurpose, UserRole
from app.domain.exceptions import (
    Conflict, CriteriaLocked, DomainError, JobNotFound, NoSeasonForDate, NotFound, PermissionDenied, StudentNotFound,
)
from app.models.models import Company, Consent, JobAllowedBranch, JobListing, Season, Student, User
from app.repositories import repository as repo

_SHORTLIST_STATUSES = {St.SHORTLISTED, St.INTERVIEW_SCHEDULED, St.INTERVIEWED, St.OFFERED, St.ACCEPTED, St.DECLINED}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _require_coordinator(actor: Actor):
    if not actor.is_coordinator:
        raise PermissionDenied("Only the placement coordinator can do this")


def _require_job_access(actor: Actor, job):
    if actor.is_coordinator or (actor.role == UserRole.COMPANY_REP and actor.company_id == job.company_id):
        return
    raise PermissionDenied("Not your company's drive")


async def _job(db, job_id):
    job = await repo.get_job(db, job_id)
    if not job:
        raise JobNotFound("Job listing not found")
    return job


# ---------- FR-3.1 companies, seasons ----------
async def create_company(db, actor: Actor, name: str, description: str = "") -> Company:
    _require_coordinator(actor)
    company = await repo.add(db, Company(name=name, description=description))
    await db.commit()
    return company


async def create_season(db, actor: Actor, name: str, start_date: date, end_date: date) -> Season:
    _require_coordinator(actor)
    for s in await repo.list_seasons(db):
        if start_date <= s.end_date and end_date >= s.start_date:
            raise Conflict(f"Overlaps season {s.name}")  # seasons must not overlap (Lab 4 rule)
    season = await repo.add(db, Season(name=name, start_date=start_date, end_date=end_date))
    await db.commit()
    return season


# ---------- FR-2.3 students ----------
async def create_student(db, actor: Actor, *, email: str, full_name: str, password: str, usn: str, branch: Branch,
                         cgpa: Decimal, active_backlogs: int = 0, cleared_backlogs: int = 0) -> Student:
    _require_coordinator(actor)
    user = await repo.add(db, User(email=email, password_hash=hash_password(password), full_name=full_name,
                                   role=UserRole.STUDENT))
    student = await repo.add(db, Student(user_id=user.id, usn=usn, branch=branch, cgpa=cgpa,
                                         active_backlogs=active_backlogs, cleared_backlogs=cleared_backlogs))
    await db.commit()
    return await repo.get_student(db, student.id)


async def update_student_academics(db, actor: Actor, student_id: int, *, cgpa: Decimal, active_backlogs: int,
                                   cleared_backlogs: int | None = None) -> Student:
    _require_coordinator(actor)
    student = await repo.get_student(db, student_id)
    if not student:
        raise StudentNotFound("Student not found")
    student.cgpa, student.active_backlogs = cgpa, active_backlogs
    if cleared_backlogs is not None:
        student.cleared_backlogs = cleared_backlogs
    await db.commit()
    return await repo.get_student(db, student_id)


# ---------- FR-3.2 to FR-3.5 job listings ----------
async def create_job(db, actor: Actor, *, company_id: int | None, role_title: str, min_cgpa: Decimal, max_backlogs: int,
                     drive_date: date, allowed_branches: list, description: str = "",
                     package_lpa: Decimal = Decimal("0")) -> JobListing:
    if actor.role == UserRole.COMPANY_REP:
        company_id = actor.company_id  # the token decides the company (FR-1.4)
    else:
        _require_coordinator(actor)
        if company_id is None or not await repo.get_company(db, company_id):
            raise NotFound("Company not found")
    if not await repo.season_for_date(db, drive_date):
        raise NoSeasonForDate("The drive date is not inside any placement season")
    job = await repo.add(db, JobListing(company_id=company_id, role_title=role_title, description=description,
                                        package_lpa=package_lpa, min_cgpa=min_cgpa, max_backlogs=max_backlogs,
                                        drive_date=drive_date, is_open=True))
    for b in dict.fromkeys(allowed_branches):
        await repo.add(db, JobAllowedBranch(job_id=job.id, branch=b))
    await db.commit()
    return await repo.get_job(db, job.id)


async def close_job(db, actor: Actor, job_id: int) -> JobListing:
    job = await _job(db, job_id)
    _require_job_access(actor, job)
    job.is_open = False
    await db.commit()
    return await repo.get_job(db, job_id)


async def update_criteria(db, actor: Actor, job_id: int, *, min_cgpa: Decimal, max_backlogs: int,
                          allowed_branches: list | None = None, today: date | None = None) -> JobListing:
    today = today or _today()
    job = await _job(db, job_id)
    _require_job_access(actor, job)
    if today >= job.drive_date:
        raise CriteriaLocked("Criteria can be changed only before the drive date")
    job.min_cgpa, job.max_backlogs = min_cgpa, max_backlogs
    if allowed_branches is not None:
        job.allowed_branches = [JobAllowedBranch(job_id=job.id, branch=b) for b in dict.fromkeys(allowed_branches)]
    await db.commit()
    return await repo.get_job(db, job_id)


# ---------- FR-9 reporting ----------
async def status_counts(db, actor: Actor, *, job_id: int | None = None, today: date | None = None) -> dict[str, int]:
    if job_id is not None:
        _require_job_access(actor, await _job(db, job_id))
        return await repo.status_counts(db, job_id=job_id)
    _require_coordinator(actor)
    season = await repo.season_for_date(db, today or _today())
    return await repo.status_counts(db, season=season) if season else {s.value: 0 for s in St}


async def overview(db, actor: Actor, today: date | None = None) -> dict:
    _require_coordinator(actor)
    students = await repo.list_students(db)
    apps = await repo.list_applications(db)
    placed = {a.student_id for a in apps if a.status == St.ACCEPTED}
    return {
        "total_students": len(students),
        "total_companies": len(await repo.list_companies(db)),
        "total_jobs": len(await repo.list_jobs(db)),
        "total_applications": len(apps),
        "total_offers": sum(1 for a in apps if a.offer is not None),
        "total_accepted": len(placed),
        "placement_percentage": round(len(placed) / len(students) * 100, 1) if students else 0.0,
        "status_counts": await status_counts(db, actor, today=today),
    }


async def shortlist_csv(db, actor: Actor, job_id: int) -> str:
    _require_job_access(actor, await _job(db, job_id))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["usn", "full_name", "branch", "cgpa", "status"])
    for a in await repo.list_applications(db, job_id=job_id):
        if a.status in _SHORTLIST_STATUSES:
            s = a.student
            w.writerow([s.usn, s.user.full_name, s.branch.value, s.cgpa, St(a.status).value])
    return buf.getvalue()


# ---------- FR-10 privacy ----------
async def has_consent(db, student_id: int, purpose: ConsentPurpose) -> bool:
    return await repo.active_consent(db, student_id, purpose) is not None


async def grant_consent(db, student_id: int, purpose: ConsentPurpose) -> Consent:
    existing = await repo.active_consent(db, student_id, purpose)
    if existing:
        return existing
    consent = await repo.add(db, Consent(student_id=student_id, purpose=purpose))
    await db.commit()
    return consent


async def withdraw_consent(db, student_id: int, purpose: ConsentPurpose) -> None:
    existing = await repo.active_consent(db, student_id, purpose)
    if existing:
        existing.withdrawn_at = datetime.now(timezone.utc)  # kept, never deleted
        await db.commit()


async def anonymise_student(db, actor: Actor, student_id: int, today: date | None = None) -> Student:
    """FR-10.2: blank personal data but keep the rows, so every foreign key stays valid (NFR-4.4)."""
    _require_coordinator(actor)
    today = today or _today()
    student = await repo.get_student(db, student_id)
    if not student:
        raise StudentNotFound("Student not found")
    season = await repo.season_for_date(db, today)
    if season and any(season.start_date <= a.job.drive_date <= season.end_date
                      for a in await repo.list_applications(db, student_id=student_id)):
        raise DomainError("Personal data can be erased only after the season ends")
    user = student.user
    user.full_name, user.email, user.password_hash, user.is_active = (
        "Anonymised", f"anonymised-{user.id}@invalid", "!", False)
    student.usn, student.is_anonymised = f"ANON-{student.id}", True
    for purpose in ConsentPurpose:
        c = await repo.active_consent(db, student_id, purpose)
        if c:
            c.withdrawn_at = datetime.now(timezone.utc)
    await db.commit()
    return await repo.get_student(db, student_id)


# ---------- read use cases ----------
async def list_students(db, actor: Actor) -> list[Student]:
    _require_coordinator(actor)  # companies never get the full student list (NFR-3.4)
    return await repo.list_students(db)


async def list_companies(db, actor: Actor) -> list[Company]:
    _require_coordinator(actor)
    return await repo.list_companies(db)


async def list_seasons(db) -> list[Season]:
    return await repo.list_seasons(db)


async def list_jobs(db, actor: Actor) -> list[JobListing]:
    if actor.role == UserRole.COMPANY_REP:
        return await repo.list_jobs(db, company_id=actor.company_id)
    return await repo.list_jobs(db)


async def get_job(db, job_id: int) -> JobListing:
    return await _job(db, job_id)
