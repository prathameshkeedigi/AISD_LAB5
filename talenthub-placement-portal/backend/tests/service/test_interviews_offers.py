"""Iteration 6 – interviews and offers (FR-7.1 to FR-7.3, FR-8.1 to FR-8.6, NFR-8.4)."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.enums import ApplicationStatus as St
from app.domain.exceptions import (
    ApplicationNotFound,
    DuplicateRound,
    InvalidTransition,
    NotEligible,
    PermissionDenied,
)
from app.services import placement_service as ps
from tests.factories import (
    TODAY, make_company, make_coordinator, make_job, make_rep, make_season, make_student, student_actor,
)

WHEN = datetime(2026, 11, 20, 10, tzinfo=timezone.utc)


@pytest.fixture
async def ctx(db):
    await make_season(db)
    company = await make_company(db)
    rep = await make_rep(db, company)
    coord = await make_coordinator(db)
    student = await make_student(db)
    job = await make_job(db, company)
    app = await ps.apply_for_job(db, student.id, job.id, today=TODAY)
    return dict(company=company, rep=rep, coord=coord, student=student, job=job, app=app)


async def _to_interviewed(db, c):
    await ps.shortlist_application(db, c["app"].id, c["coord"], today=TODAY)
    await ps.schedule_interview(db, c["app"].id, c["coord"], round_no=1, scheduled_at=WHEN, venue="Hall A")
    return await ps.record_interview_result(db, c["app"].id, c["rep"], round_no=1, passed=True, final=True)


async def test_FR7_1_interview_needs_SHORTLISTED(db, ctx):
    with pytest.raises(InvalidTransition):
        await ps.schedule_interview(db, ctx["app"].id, ctx["coord"], round_no=1, scheduled_at=WHEN, venue="Hall A")


async def test_FR7_1_scheduling_sets_INTERVIEW_SCHEDULED(db, ctx):
    await ps.shortlist_application(db, ctx["app"].id, ctx["coord"], today=TODAY)
    a = await ps.schedule_interview(db, ctx["app"].id, ctx["coord"], round_no=1, scheduled_at=WHEN, venue="Hall A")
    assert a.status == St.INTERVIEW_SCHEDULED


async def test_FR7_2_several_rounds_but_round_number_unique(db, ctx):
    await ps.shortlist_application(db, ctx["app"].id, ctx["coord"], today=TODAY)
    await ps.schedule_interview(db, ctx["app"].id, ctx["coord"], round_no=1, scheduled_at=WHEN, venue="Hall A")
    await ps.schedule_interview(db, ctx["app"].id, ctx["coord"], round_no=2, scheduled_at=WHEN, venue="Hall B")
    with pytest.raises(DuplicateRound):
        await ps.schedule_interview(db, ctx["app"].id, ctx["coord"], round_no=2, scheduled_at=WHEN, venue="Hall C")


async def test_FR7_3_passing_final_round_sets_INTERVIEWED(db, ctx):
    assert (await _to_interviewed(db, ctx)).status == St.INTERVIEWED


async def test_failing_a_round_rejects_application(db, ctx):
    await ps.shortlist_application(db, ctx["app"].id, ctx["coord"], today=TODAY)
    await ps.schedule_interview(db, ctx["app"].id, ctx["coord"], round_no=1, scheduled_at=WHEN, venue="Hall A")
    a = await ps.record_interview_result(db, ctx["app"].id, ctx["rep"], round_no=1, passed=False)
    assert a.status == St.REJECTED


async def test_FR8_2_offer_refused_unless_INTERVIEWED(db, ctx):
    with pytest.raises(InvalidTransition):
        await ps.issue_offer(db, ctx["app"].id, ctx["rep"], Decimal("8.5"))


async def test_FR8_1_offer_sets_OFFERED_with_unpredictable_key(db, ctx):
    await _to_interviewed(db, ctx)
    a = await ps.issue_offer(db, ctx["app"].id, ctx["rep"], Decimal("8.5"))
    assert a.status == St.OFFERED
    key = a.offer.offer_letter_key
    assert len(key) >= 32
    for word in (ctx["company"].name, ctx["student"].usn, "2026"):
        assert word.lower() not in key.lower()


async def test_FR1_4_other_company_rep_cannot_issue_offer(db, ctx):
    await _to_interviewed(db, ctx)
    stranger = await make_rep(db, await make_company(db))
    with pytest.raises(PermissionDenied):
        await ps.issue_offer(db, ctx["app"].id, stranger, Decimal("8.5"))


async def test_FR8_4_only_owner_can_accept(db, ctx):
    await _to_interviewed(db, ctx)
    await ps.issue_offer(db, ctx["app"].id, ctx["rep"], Decimal("8.5"))
    other = await make_student(db)
    with pytest.raises(ApplicationNotFound):
        await ps.respond_to_offer(db, ctx["app"].id, student_actor(other), accept=True, today=TODAY)


async def test_FR8_4_accept_sets_ACCEPTED_and_cannot_repeat(db, ctx):
    await _to_interviewed(db, ctx)
    await ps.issue_offer(db, ctx["app"].id, ctx["rep"], Decimal("8.5"))
    me = student_actor(ctx["student"])
    a = await ps.respond_to_offer(db, ctx["app"].id, me, accept=True, today=TODAY)
    assert a.status == St.ACCEPTED
    with pytest.raises(InvalidTransition):
        await ps.respond_to_offer(db, ctx["app"].id, me, accept=False, today=TODAY)


async def test_decline_sets_DECLINED(db, ctx):
    await _to_interviewed(db, ctx)
    await ps.issue_offer(db, ctx["app"].id, ctx["rep"], Decimal("8.5"))
    a = await ps.respond_to_offer(db, ctx["app"].id, student_actor(ctx["student"]), accept=False, today=TODAY)
    assert a.status == St.DECLINED


async def test_FR8_5_after_accepting_student_fails_R3_for_other_drives(db, ctx):
    await _to_interviewed(db, ctx)
    await ps.issue_offer(db, ctx["app"].id, ctx["rep"], Decimal("8.5"))
    await ps.respond_to_offer(db, ctx["app"].id, student_actor(ctx["student"]), accept=True, today=TODAY)
    other_job = await make_job(db, await make_company(db))
    with pytest.raises(NotEligible) as e:
        await ps.apply_for_job(db, ctx["student"].id, other_job.id, today=TODAY)
    assert e.value.failed_rule == "R3"


async def test_cannot_accept_second_offer_in_same_season(db, ctx):
    me = student_actor(ctx["student"])
    other_company = await make_company(db)
    other_rep = await make_rep(db, other_company)
    other_app = await ps.apply_for_job(db, ctx["student"].id, (await make_job(db, other_company)).id, today=TODAY)
    for app, rep in ((ctx["app"], ctx["rep"]), (other_app, other_rep)):
        c = dict(ctx, app=app, rep=rep)
        await _to_interviewed(db, c)
        await ps.issue_offer(db, app.id, rep, Decimal("8"))
    await ps.respond_to_offer(db, ctx["app"].id, me, accept=True, today=TODAY)
    with pytest.raises(NotEligible):
        await ps.respond_to_offer(db, other_app.id, me, accept=True, today=TODAY)
