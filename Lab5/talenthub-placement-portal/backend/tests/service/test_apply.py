"""Iteration 4 – applying for a job (FR-5.1 to FR-5.5, FR-4.6, NFR-9.1, NFR-9.3)."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.domain.enums import ApplicationStatus, Branch
from app.domain.exceptions import (
    AlreadyApplied,
    ConsentMissing,
    DomainError,
    JobClosed,
    JobNotFound,
    NotEligible,
    SameCompanyThisSeason,
)
from app.models.models import ApplicationStatusHistory, EligibilityDecision
from app.services import placement_service as ps
from tests.factories import TODAY, make_company, make_job, make_season, make_student


@pytest.fixture
async def world(db):
    await make_season(db)
    company = await make_company(db)
    return company


async def test_FR5_1_successful_application_is_APPLIED_with_history(db, world):
    s, j = await make_student(db), await make_job(db, world)
    app = await ps.apply_for_job(db, s.id, j.id, today=TODAY)
    assert app.status == ApplicationStatus.APPLIED
    hist = (await db.execute(select(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == app.id))).scalars().all()
    assert [(h.status, h.changed_by_user_id) for h in hist] == [(ApplicationStatus.APPLIED, s.user_id)]
    assert hist[0].changed_at is not None


async def test_FR5_2_missing_job_raises_JobNotFound(db, world):
    s = await make_student(db)
    with pytest.raises(JobNotFound):
        await ps.apply_for_job(db, s.id, 999, today=TODAY)


async def test_FR5_2_all_domain_exceptions_share_one_base():
    for exc in (JobNotFound, NotEligible, AlreadyApplied):
        assert issubclass(exc, DomainError)


async def test_FR3_4_closed_job_refuses_applications(db, world):
    s, j = await make_student(db), await make_job(db, world, is_open=False)
    with pytest.raises(JobClosed):
        await ps.apply_for_job(db, s.id, j.id, today=TODAY)


async def test_job_whose_drive_date_has_passed_refuses_applications(db, world):
    s, j = await make_student(db), await make_job(db, world, drive_date=TODAY - timedelta(days=1))
    with pytest.raises(JobClosed):
        await ps.apply_for_job(db, s.id, j.id, today=TODAY)


async def test_FR5_2_ineligible_student_gets_NotEligible_with_reason(db, world):
    s, j = await make_student(db, cgpa="6.49"), await make_job(db, world, min_cgpa="6.50")
    with pytest.raises(NotEligible) as e:
        await ps.apply_for_job(db, s.id, j.id, today=TODAY)
    assert e.value.reason == "CGPA 6.49 below minimum 6.5"


async def test_NFR9_3_rejected_apply_decision_is_stored_with_reason(db, world):
    s, j = await make_student(db, branch=Branch.ECE), await make_job(db, world, branches=[Branch.CSE])
    with pytest.raises(NotEligible):
        await ps.apply_for_job(db, s.id, j.id, today=TODAY)
    d = (await db.execute(select(EligibilityDecision))).scalars().one()
    assert (d.student_id, d.job_id, d.failed_rule, d.reason, d.context) == (
        s.id, j.id, "R4", "Branch ECE not in drive scope", "APPLY")


async def test_FR4_3_cgpa_exactly_minimum_can_apply(db, world):
    s, j = await make_student(db, cgpa="6.50"), await make_job(db, world, min_cgpa="6.50")
    assert (await ps.apply_for_job(db, s.id, j.id, today=TODAY)).status == ApplicationStatus.APPLIED


async def test_FR5_2_applying_twice_raises_AlreadyApplied(db, world):
    s, j = await make_student(db), await make_job(db, world)
    await ps.apply_for_job(db, s.id, j.id, today=TODAY)
    with pytest.raises(AlreadyApplied):
        await ps.apply_for_job(db, s.id, j.id, today=TODAY)


async def test_FR5_3_second_drive_of_same_company_in_season_refused(db, world):
    s = await make_student(db)
    j1, j2 = await make_job(db, world), await make_job(db, world)
    await ps.apply_for_job(db, s.id, j1.id, today=TODAY)
    with pytest.raises(SameCompanyThisSeason):
        await ps.apply_for_job(db, s.id, j2.id, today=TODAY)


async def test_FR5_3_other_company_same_season_is_allowed(db, world):
    s = await make_student(db)
    other = await make_company(db)
    await ps.apply_for_job(db, s.id, (await make_job(db, world)).id, today=TODAY)
    assert await ps.apply_for_job(db, s.id, (await make_job(db, other)).id, today=TODAY)


async def test_FR10_1_student_without_consent_cannot_apply(db, world):
    s, j = await make_student(db, consent=False), await make_job(db, world)
    with pytest.raises(ConsentMissing):
        await ps.apply_for_job(db, s.id, j.id, today=TODAY)


async def test_FR4_6_available_jobs_are_open_future_eligible_and_not_applied(db, world):
    s = await make_student(db, cgpa="7.00")
    ok = await make_job(db, world, min_cgpa="6.00")
    other = await make_company(db)
    await make_job(db, other, min_cgpa="9.00")                                 # ineligible
    await make_job(db, other, is_open=False)                                  # closed
    await make_job(db, other, drive_date=TODAY - timedelta(days=1))           # past
    applied = await make_job(db, await make_company(db))
    await ps.apply_for_job(db, s.id, applied.id, today=TODAY)                 # already applied
    jobs = await ps.list_available_jobs(db, s.id, today=TODAY)
    assert [j.id for j in jobs] == [ok.id]
