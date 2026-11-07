"""Synthetic test data builders (NFR-4.6). Each one adds rows and flushes, so ids are available."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from itertools import count

from app.core.security import hash_password
from app.domain.enums import Branch, ConsentPurpose, UserRole
from app.models.models import Company, Consent, JobAllowedBranch, JobListing, Season, Student, User
from app.domain.actors import Actor

TODAY = date(2026, 11, 6)
_n = count(1)


async def make_season(db, start=date(2026, 7, 1), end=date(2027, 6, 30), name=None):
    s = Season(name=name or f"{start.year}-{str(end.year)[2:]}", start_date=start, end_date=end)
    db.add(s)
    await db.flush()
    return s


async def make_company(db, name=None):
    c = Company(name=name or f"Company {next(_n)}")
    db.add(c)
    await db.flush()
    return c


async def make_user(db, role=UserRole.COORDINATOR, company_id=None, email=None, name="Test User"):
    u = User(
        email=email or f"user{next(_n)}@test.edu",
        password_hash=hash_password("password123"),
        full_name=name,
        role=role,
        company_id=company_id,
    )
    db.add(u)
    await db.flush()
    return u


async def make_rep(db, company):
    u = await make_user(db, UserRole.COMPANY_REP, company_id=company.id)
    return Actor(user_id=u.id, role=UserRole.COMPANY_REP, company_id=company.id)


async def make_coordinator(db):
    u = await make_user(db, UserRole.COORDINATOR)
    return Actor(user_id=u.id, role=UserRole.COORDINATOR)


async def make_student(db, cgpa="8.00", active=0, cleared=0, branch=Branch.CSE, consent=True, usn=None):
    u = await make_user(db, UserRole.STUDENT)
    s = Student(
        user_id=u.id,
        usn=usn or f"01FE24BCS{next(_n):03d}",
        branch=branch,
        cgpa=Decimal(cgpa),
        active_backlogs=active,
        cleared_backlogs=cleared,
    )
    db.add(s)
    await db.flush()
    if consent:
        db.add(Consent(student_id=s.id, purpose=ConsentPurpose.PLACEMENT, granted_at=datetime.now(timezone.utc)))
        await db.flush()
    return s


def student_actor(student):
    return Actor(user_id=student.user_id, role=UserRole.STUDENT, student_id=student.id)


async def make_job(db, company, min_cgpa="6.50", max_backlogs=0, branches=(), drive_date=None, is_open=True):
    j = JobListing(
        company_id=company.id,
        role_title=f"Role {next(_n)}",
        min_cgpa=Decimal(min_cgpa),
        max_backlogs=max_backlogs,
        drive_date=drive_date or TODAY + timedelta(days=7),
        is_open=is_open,
    )
    db.add(j)
    await db.flush()
    for b in branches:
        db.add(JobAllowedBranch(job_id=j.id, branch=b))
    await db.flush()
    return j
