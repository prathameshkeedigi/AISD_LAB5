"""Iteration 5 – shortlisting run (FR-6.1 to FR-6.6, NFR-1.3, NFR-6.3)."""
import pytest
from sqlalchemy import func, select

from app.domain.enums import ApplicationStatus as St
from app.models.models import Application, EligibilityDecision, Student
from app.services import placement_service as ps
from tests.factories import TODAY, make_company, make_coordinator, make_job, make_season, make_student


class FakeNotifier:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send(self, to, subject, body):
        if self.fail:
            raise ConnectionError("SMTP down")
        self.sent.append((to, subject, body))


@pytest.fixture
async def drive(db):
    await make_season(db)
    company = await make_company(db)
    job = await make_job(db, company, min_cgpa="6.50")
    good = await make_student(db, cgpa="6.50")
    bad = await make_student(db, cgpa="7.50")
    for s in (good, bad):
        await ps.apply_for_job(db, s.id, job.id, today=TODAY)
    # bad's record is corrected downwards after applying, so the run must catch it
    bad_row = await db.get(Student, bad.id)
    bad_row.cgpa = bad_row.cgpa.__class__("6.00")
    await db.commit()
    return job, good, bad, await make_coordinator(db)


async def _statuses(db, job):
    job_id = job if isinstance(job, int) else job.id
    rows = (await db.execute(select(Application).where(Application.job_id == job_id))).scalars().all()
    return {a.student_id: a.status for a in rows}


async def test_FR6_1_eligible_shortlisted_ineligible_stay_applied(db, drive):
    job, good, bad, coord = drive
    report = await ps.shortlist_students(db, job.id, coord, FakeNotifier(), today=TODAY)
    assert await _statuses(db, job) == {good.id: St.SHORTLISTED, bad.id: St.APPLIED}
    assert report.shortlisted == [good.id]
    assert report.ineligible == {bad.id: "CGPA 6 below minimum 6.5"}


async def test_FR6_3_reason_recorded_for_every_ineligible_student(db, drive):
    job, _, bad, coord = drive
    await ps.shortlist_students(db, job.id, coord, FakeNotifier(), today=TODAY)
    d = (await db.execute(select(EligibilityDecision).where(EligibilityDecision.context == "SHORTLIST",
                                                         EligibilityDecision.student_id == bad.id))).scalars().one()
    assert d.failed_rule == "R1"


async def test_FR6_2_run_creates_no_applications(db, drive):
    job, *_, coord = drive
    before = await db.scalar(select(func.count(Application.id)))
    await ps.shortlist_students(db, job.id, coord, FakeNotifier(), today=TODAY)
    assert await db.scalar(select(func.count(Application.id))) == before


async def test_FR6_5_running_twice_gives_same_state(db, drive):
    job, *_, coord = drive
    await ps.shortlist_students(db, job.id, coord, FakeNotifier(), today=TODAY)
    first = await _statuses(db, job)
    await ps.shortlist_students(db, job.id, coord, FakeNotifier(), today=TODAY)
    assert await _statuses(db, job) == first


async def test_FR6_4_NFR1_3_failure_mid_run_leaves_no_change(db, drive, monkeypatch):
    job, good, bad, coord = drive
    job_id = job.id
    second = await make_student(db, cgpa="9.00")
    await ps.apply_for_job(db, second.id, job.id, today=TODAY)
    calls = {"n": 0}
    original = ps._change_status

    async def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("crash in the middle")
        return await original(*args, **kwargs)

    monkeypatch.setattr(ps, "_change_status", flaky)
    with pytest.raises(RuntimeError):
        await ps.shortlist_students(db, job_id, coord, FakeNotifier(), today=TODAY)
    assert set((await _statuses(db, job_id)).values()) == {St.APPLIED}


async def test_FR6_6_notifies_shortlisted_and_ineligible_with_reason(db, drive):
    job, *_, coord = drive
    n = FakeNotifier()
    await ps.shortlist_students(db, job.id, coord, n, today=TODAY)
    bodies = [body for _, _, body in n.sent]
    assert len(n.sent) == 2
    assert any("CGPA 6 below minimum 6.5" in b for b in bodies)


async def test_NFR6_3_mail_failure_does_not_undo_shortlist(db, drive):
    job, good, *_, coord = drive
    await ps.shortlist_students(db, job.id, coord, FakeNotifier(fail=True), today=TODAY)
    assert (await _statuses(db, job))[good.id] == St.SHORTLISTED
