"""Data access only. Repositories add and flush but never commit: the service owns the transaction (FR-6.4)."""
from datetime import date

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import ApplicationStatus, ConsentPurpose
from app.models.models import (
    Application, Company, Consent, InterviewSlot, JobListing, Season, Student, User,
)

_APP_LOAD = (
    selectinload(Application.student).selectinload(Student.user),
    selectinload(Application.job).selectinload(JobListing.company),
    selectinload(Application.interviews),
    selectinload(Application.offer),
    selectinload(Application.history),
)


async def add(db: AsyncSession, obj):
    db.add(obj)
    await db.flush()
    return obj


# ---------- users / students / companies ----------
async def user_by_email(db, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


async def get_user(db, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def get_student(db, student_id: int) -> Student | None:
    return await db.scalar(select(Student).options(selectinload(Student.user)).where(Student.id == student_id)
                           .execution_options(populate_existing=True))


async def student_by_user(db, user_id: int) -> Student | None:
    return await db.scalar(select(Student).options(selectinload(Student.user)).where(Student.user_id == user_id))


async def list_students(db) -> list[Student]:
    return list((await db.scalars(select(Student).options(selectinload(Student.user)).order_by(Student.id))).all())


async def get_company(db, company_id: int) -> Company | None:
    return await db.get(Company, company_id)


async def list_companies(db) -> list[Company]:
    return list((await db.scalars(select(Company).order_by(Company.id))).all())


# ---------- seasons (replace v_current_season / v_job_season) ----------
async def season_for_date(db, d: date) -> Season | None:
    return await db.scalar(select(Season).where(Season.start_date <= d, Season.end_date >= d))


async def list_seasons(db) -> list[Season]:
    return list((await db.scalars(select(Season).order_by(Season.start_date))).all())


def _in_season(season: Season):
    return and_(JobListing.drive_date >= season.start_date, JobListing.drive_date <= season.end_date)


# ---------- jobs ----------
async def get_job(db, job_id: int) -> JobListing | None:
    return await db.scalar(
        select(JobListing).options(selectinload(JobListing.company)).where(JobListing.id == job_id)
        .execution_options(populate_existing=True)
    )


async def list_jobs(db, company_id: int | None = None) -> list[JobListing]:
    q = select(JobListing).options(selectinload(JobListing.company)).order_by(JobListing.drive_date, JobListing.id)
    if company_id is not None:
        q = q.where(JobListing.company_id == company_id)
    return list((await db.scalars(q.execution_options(populate_existing=True))).all())


# ---------- applications ----------
async def get_application(db, application_id: int) -> Application | None:
    return await db.scalar(
        select(Application).options(*_APP_LOAD).where(Application.id == application_id).execution_options(populate_existing=True)
    )


async def find_application(db, student_id: int, job_id: int) -> Application | None:
    return await db.scalar(select(Application).where(Application.student_id == student_id, Application.job_id == job_id))


async def list_applications(db, *, job_id=None, student_id=None, company_id=None, status=None) -> list[Application]:
    q = select(Application).join(JobListing, Application.job_id == JobListing.id).options(*_APP_LOAD)
    if job_id is not None:
        q = q.where(Application.job_id == job_id)
    if student_id is not None:
        q = q.where(Application.student_id == student_id)
    if company_id is not None:
        q = q.where(JobListing.company_id == company_id)
    if status is not None:
        q = q.where(Application.status == status)
    return list((await db.scalars(q.order_by(Application.id).execution_options(populate_existing=True))).all())


async def applied_job_ids(db, student_id: int) -> set[int]:
    return set((await db.scalars(select(Application.job_id).where(Application.student_id == student_id))).all())


async def has_accepted_offer_in_season(db, student_id: int, season: Season | None) -> bool:
    """Replaces v_student_season_acceptance: R3 is derived, never stored."""
    if season is None:
        return False
    q = select(exists().where(
        Application.student_id == student_id,
        Application.status == ApplicationStatus.ACCEPTED,
        Application.job_id == JobListing.id,
        _in_season(season),
    ))
    return bool(await db.scalar(q))


async def applied_to_company_in_season(db, student_id: int, company_id: int, season: Season) -> bool:
    q = select(exists().where(
        Application.student_id == student_id,
        Application.job_id == JobListing.id,
        JobListing.company_id == company_id,
        _in_season(season),
    ))
    return bool(await db.scalar(q))


async def status_counts(db, *, job_id=None, season: Season | None = None) -> dict[str, int]:
    q = select(Application.status, func.count(Application.id)).join(JobListing, Application.job_id == JobListing.id)
    if job_id is not None:
        q = q.where(Application.job_id == job_id)
    if season is not None:
        q = q.where(_in_season(season))
    rows = (await db.execute(q.group_by(Application.status))).all()
    counts = {s.value: 0 for s in ApplicationStatus}
    for status, n in rows:
        counts[ApplicationStatus(status).value] = n
    return counts


# ---------- interviews ----------
async def get_slot(db, application_id: int, round_no: int) -> InterviewSlot | None:
    return await db.scalar(
        select(InterviewSlot).where(InterviewSlot.application_id == application_id, InterviewSlot.round_no == round_no)
    )


# ---------- consents ----------
async def active_consent(db, student_id: int, purpose: ConsentPurpose) -> Consent | None:
    return await db.scalar(select(Consent).where(
        Consent.student_id == student_id, Consent.purpose == purpose, Consent.withdrawn_at.is_(None)
    ))
