"""Iterations 8–9 – coordinator functions (FR-2.3, FR-3.x, FR-9.x) and privacy (FR-10.x, NFR-4.x)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.enums import ApplicationStatus as St
from app.domain.enums import Branch, ConsentPurpose
from app.domain.exceptions import ConsentMissing, CriteriaLocked, DomainError, NoSeasonForDate, PermissionDenied
from app.models.models import Application, Student, User
from app.services import admin_service as adm
from app.services import placement_service as ps
from tests.factories import (
    TODAY, make_company, make_coordinator, make_job, make_rep, make_season, make_student,
)


async def test_FR2_3_coordinator_creates_and_updates_student(db):
    coord = await make_coordinator(db)
    s = await adm.create_student(db, coord, email="new@test.edu", full_name="New Student", password="pw12345678",
                                 usn="01FE24BCI999", branch=Branch.ISE, cgpa=Decimal("7.25"), active_backlogs=1)
    s = await adm.update_student_academics(db, coord, s.id, cgpa=Decimal("7.50"), active_backlogs=0, cleared_backlogs=1)
    assert (s.cgpa, s.active_backlogs, s.cleared_backlogs) == (Decimal("7.50"), 0, 1)


async def test_FR3_2_job_drive_date_must_fall_in_a_season(db):
    coord = await make_coordinator(db)
    await make_season(db)
    c = await adm.create_company(db, coord, "Acme")
    with pytest.raises(NoSeasonForDate):
        await adm.create_job(db, coord, company_id=c.id, role_title="Dev", min_cgpa=Decimal("6.5"),
                             max_backlogs=0, drive_date=date(2030, 1, 1), allowed_branches=[])


async def test_FR3_2_company_rep_can_publish_only_for_own_company(db):
    await make_season(db)
    mine, theirs = await make_company(db), await make_company(db)
    rep = await make_rep(db, mine)
    job = await adm.create_job(db, rep, company_id=theirs.id, role_title="Dev", min_cgpa=Decimal("6.5"),
                               max_backlogs=0, drive_date=TODAY + timedelta(days=5), allowed_branches=[Branch.CSE])
    assert job.company_id == mine.id  # the token decides the company, never the request body
    assert [b.branch for b in job.allowed_branches] == [Branch.CSE]


async def test_FR3_4_coordinator_closes_listing(db):
    await make_season(db)
    coord = await make_coordinator(db)
    job = await make_job(db, await make_company(db))
    assert (await adm.close_job(db, coord, job.id)).is_open is False


async def test_FR3_5_criteria_editable_only_before_drive_date(db):
    await make_season(db)
    coord = await make_coordinator(db)
    job = await make_job(db, await make_company(db), drive_date=TODAY + timedelta(days=2))
    j = await adm.update_criteria(db, coord, job.id, min_cgpa=Decimal("7.0"), max_backlogs=1, today=TODAY)
    assert j.min_cgpa == Decimal("7.0")
    with pytest.raises(CriteriaLocked):
        await adm.update_criteria(db, coord, job.id, min_cgpa=Decimal("5"), max_backlogs=1, today=job.drive_date)


async def test_FR9_2_status_counts_per_drive_and_season(db):
    await make_season(db)
    coord = await make_coordinator(db)
    job = await make_job(db, await make_company(db))
    for _ in range(2):
        await ps.apply_for_job(db, (await make_student(db)).id, job.id, today=TODAY)
    counts = await adm.status_counts(db, coord, job_id=job.id)
    assert counts[St.APPLIED.value] == 2 and counts[St.SHORTLISTED.value] == 0
    assert (await adm.status_counts(db, coord, today=TODAY))[St.APPLIED.value] == 2


async def test_FR9_3_shortlist_csv_export(db):
    await make_season(db)
    coord = await make_coordinator(db)
    job = await make_job(db, await make_company(db))
    s = await make_student(db, usn="01FE24BCI006")
    await ps.apply_for_job(db, s.id, job.id, today=TODAY)
    await ps.shortlist_application(db, (await db.get(Application, 1)).id, coord, today=TODAY)
    csv_text = await adm.shortlist_csv(db, coord, job.id)
    lines = csv_text.strip().splitlines()
    assert lines[0] == "usn,full_name,branch,cgpa,status"
    assert lines[1].startswith("01FE24BCI006,")


async def test_FR1_4_rep_cannot_export_other_company_csv(db):
    await make_season(db)
    job = await make_job(db, await make_company(db))
    stranger = await make_rep(db, await make_company(db))
    with pytest.raises(PermissionDenied):
        await adm.shortlist_csv(db, stranger, job.id)


async def test_FR10_1_withdrawn_consent_blocks_shortlisting(db):
    await make_season(db)
    coord = await make_coordinator(db)
    job = await make_job(db, await make_company(db))
    s = await make_student(db)
    app = await ps.apply_for_job(db, s.id, job.id, today=TODAY)
    await adm.withdraw_consent(db, s.id, ConsentPurpose.PLACEMENT)
    with pytest.raises(ConsentMissing):
        await ps.shortlist_application(db, app.id, coord, today=TODAY)


async def test_consent_grant_is_idempotent_one_active_per_purpose(db):
    s = await make_student(db, consent=False)
    await adm.grant_consent(db, s.id, ConsentPurpose.PLACEMENT)
    await adm.grant_consent(db, s.id, ConsentPurpose.PLACEMENT)
    assert await adm.has_consent(db, s.id, ConsentPurpose.PLACEMENT)


async def test_FR10_2_anonymise_after_season_keeps_references(db):
    await make_season(db)
    coord = await make_coordinator(db)
    job = await make_job(db, await make_company(db))
    s = await make_student(db)
    app = await ps.apply_for_job(db, s.id, job.id, today=TODAY)
    await adm.anonymise_student(db, coord, s.id, today=date(2027, 7, 15))
    student = await db.get(Student, s.id)
    user = await db.get(User, s.user_id)
    assert student.is_anonymised and student.usn != "" and "01FE" not in student.usn
    assert user.full_name == "Anonymised" and not user.is_active and "@test.edu" not in user.email
    assert (await db.get(Application, app.id)).student_id == s.id


async def test_FR10_2_anonymise_refused_during_season_with_applications(db):
    await make_season(db)
    coord = await make_coordinator(db)
    job = await make_job(db, await make_company(db))
    s = await make_student(db)
    await ps.apply_for_job(db, s.id, job.id, today=TODAY)
    with pytest.raises(DomainError):
        await adm.anonymise_student(db, coord, s.id, today=TODAY)
