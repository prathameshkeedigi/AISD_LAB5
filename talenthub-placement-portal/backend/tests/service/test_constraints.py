"""Iteration 3 – database constraints from the Lab 4 schema (NFR-8.1 to NFR-8.3, NFR-3.3)."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from app.domain.enums import ApplicationStatus, UserRole
from app.models.models import Application, ApplicationStatusHistory, InterviewSlot, Offer, Season, Student
from tests.factories import make_company, make_job, make_season, make_student, make_user


async def _expect_integrity_error(db, *objs):
    db.add_all(objs)
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


async def test_NFR8_1_application_needs_existing_student_and_job(db):
    await _expect_integrity_error(db, Application(student_id=999, job_id=999))


async def test_NFR8_3_duplicate_student_job_application_rejected_by_db(db):
    c = await make_company(db)
    s, j = await make_student(db), await make_job(db, c)
    db.add(Application(student_id=s.id, job_id=j.id))
    await db.flush()
    await _expect_integrity_error(db, Application(student_id=s.id, job_id=j.id))


async def test_NFR8_3_duplicate_usn_rejected(db):
    await make_student(db, usn="01FE24BCI006")
    u = await make_user(db, UserRole.STUDENT)
    await _expect_integrity_error(db, Student(user_id=u.id, usn="01FE24BCI006", branch="CSE", cgpa=Decimal("7")))


async def test_NFR8_3_duplicate_email_rejected(db):
    await make_user(db, email="same@test.edu")
    with pytest.raises(IntegrityError):
        await make_user(db, email="same@test.edu")


@pytest.mark.parametrize("cgpa", ["-0.01", "10.01"])
async def test_NFR3_3_cgpa_outside_0_to_10_rejected(db, cgpa):
    u = await make_user(db, UserRole.STUDENT)
    await _expect_integrity_error(db, Student(user_id=u.id, usn="X1", branch="CSE", cgpa=Decimal(cgpa)))


async def test_NFR3_3_negative_backlogs_rejected(db):
    u = await make_user(db, UserRole.STUDENT)
    await _expect_integrity_error(db, Student(user_id=u.id, usn="X2", branch="CSE", cgpa=Decimal("7"), active_backlogs=-1))


async def test_branch_outside_enum_rejected(db):
    u = await make_user(db, UserRole.STUDENT)
    with pytest.raises((StatementError, LookupError)):
        db.add(Student(user_id=u.id, usn="X3", branch="Computer Science", cgpa=Decimal("7")))
        await db.flush()


async def test_company_rep_must_have_company_and_others_must_not(db):
    with pytest.raises(IntegrityError):
        await make_user(db, UserRole.COMPANY_REP, company_id=None)
    await db.rollback()
    c = await make_company(db)
    with pytest.raises(IntegrityError):
        await make_user(db, UserRole.STUDENT, company_id=c.id)


async def test_season_end_must_be_after_start(db):
    await _expect_integrity_error(db, Season(name="bad", start_date=date(2027, 1, 1), end_date=date(2026, 1, 1)))


async def _application(db):
    c = await make_company(db)
    s, j = await make_student(db), await make_job(db, c)
    a = Application(student_id=s.id, job_id=j.id)
    db.add(a)
    await db.flush()
    return a, s


async def test_FR7_2_round_number_unique_within_application(db):
    a, _ = await _application(db)
    when = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
    db.add(InterviewSlot(application_id=a.id, round_no=1, scheduled_at=when, venue="Hall A"))
    await db.flush()
    await _expect_integrity_error(db, InterviewSlot(application_id=a.id, round_no=1, scheduled_at=when, venue="Hall B"))


async def test_round_number_must_be_at_least_1(db):
    a, _ = await _application(db)
    when = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)
    await _expect_integrity_error(db, InterviewSlot(application_id=a.id, round_no=0, scheduled_at=when, venue="Hall"))


async def test_offer_package_must_be_positive_and_one_per_application(db):
    a, _ = await _application(db)
    await _expect_integrity_error(db, Offer(application_id=a.id, package_lpa=Decimal("0"), offer_letter_key="k0"))
    a, _ = await _application(db)
    db.add(Offer(application_id=a.id, package_lpa=Decimal("5"), offer_letter_key="k1"))
    await db.flush()
    await _expect_integrity_error(db, Offer(application_id=a.id, package_lpa=Decimal("6"), offer_letter_key="k2"))


async def test_history_cannot_record_same_status_twice(db):
    a, s = await _application(db)
    row = dict(application_id=a.id, status=ApplicationStatus.APPLIED, changed_by_user_id=s.user_id)
    db.add(ApplicationStatusHistory(**row))
    await db.flush()
    await _expect_integrity_error(db, ApplicationStatusHistory(**row))


async def test_pool_drive_has_no_branch_rows(db):
    c = await make_company(db)
    j = await make_job(db, c, branches=())
    await db.refresh(j, ["allowed_branches"])
    assert j.allowed_branches == []
    await make_season(db)  # season helper works alongside
