"""Synthetic demo data (NFR-4.6). Dates are relative to today so the demo season and drives are always current."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.enums import Branch, ConsentPurpose, UserRole
from app.models.models import Company, Consent, JobAllowedBranch, JobListing, Season, Student, User

DEMO_PASSWORD = "password123"


def _current_season_bounds(today: date) -> tuple[date, date]:
    start_year = today.year if today.month >= 7 else today.year - 1
    return date(start_year, 7, 1), date(start_year + 1, 6, 30)


async def seed_if_empty(db: AsyncSession, today: date | None = None):
    if (await db.execute(select(User))).scalars().first():
        return  # already seeded
    today = today or datetime.now(timezone.utc).date()
    start, end = _current_season_bounds(today)
    db.add(Season(name=f"{start.year}-{str(end.year)[2:]}", start_date=start, end_date=end))

    abc = Company(name="ABC Technologies", description="Product-based software company")
    xyz = Company(name="XYZ Corp", description="Core engineering & infrastructure company")
    db.add_all([abc, xyz])
    await db.flush()

    drive = min(today + timedelta(days=7), end - timedelta(days=1))
    jobs = [
        (JobListing(company_id=abc.id, role_title="Software Developer", package_lpa=Decimal("8.5"),
                    description="Full-stack development role working on cloud products.",
                    min_cgpa=Decimal("7.00"), max_backlogs=2, drive_date=drive), []),  # pool drive
        (JobListing(company_id=abc.id, role_title="QA Engineer", package_lpa=Decimal("6.0"),
                    description="Manual and automated testing of web applications.",
                    min_cgpa=Decimal("6.00"), max_backlogs=3, drive_date=drive), [Branch.CSE, Branch.ISE, Branch.ECE]),
        (JobListing(company_id=xyz.id, role_title="Backend Engineer", package_lpa=Decimal("10.0"),
                    description="Build and maintain scalable backend services.",
                    min_cgpa=Decimal("8.00"), max_backlogs=0, drive_date=drive), [Branch.CSE, Branch.ISE]),
    ]
    for job, branches in jobs:
        db.add(job)
        await db.flush()
        db.add_all(JobAllowedBranch(job_id=job.id, branch=b) for b in branches)

    def user(email, name, role, company_id=None):
        return User(email=email, password_hash=hash_password(DEMO_PASSWORD), full_name=name, role=role,
                    company_id=company_id)

    people = [
        (user("rahul@student.talenthub.edu", "Rahul Sharma", UserRole.STUDENT), "01FE24BCS101", Branch.CSE, "8.20", 1, 0),
        (user("priya@student.talenthub.edu", "Priya Nair", UserRole.STUDENT), "01FE24BIS102", Branch.ISE, "9.10", 0, 1),
        (user("aman@student.talenthub.edu", "Aman Verma", UserRole.STUDENT), "01FE24BEC103", Branch.ECE, "6.40", 3, 0),
    ]
    db.add_all([
        user("hr@abctech.com", "ABC HR", UserRole.COMPANY_REP, abc.id),
        user("hr@xyzcorp.com", "XYZ HR", UserRole.COMPANY_REP, xyz.id),
        user("coordinator@talenthub.edu", "Placement Coordinator", UserRole.COORDINATOR),
    ])
    for u, usn, branch, cgpa, active, cleared in people:
        db.add(u)
        await db.flush()
        s = Student(user_id=u.id, usn=usn, branch=branch, cgpa=Decimal(cgpa), active_backlogs=active,
                    cleared_backlogs=cleared)
        db.add(s)
        await db.flush()
        db.add(Consent(student_id=s.id, purpose=ConsentPurpose.PLACEMENT))
    await db.commit()
