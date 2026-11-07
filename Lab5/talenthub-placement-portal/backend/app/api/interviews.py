from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import application_out
from app.core.database import get_db
from app.core.deps import get_company_or_coordinator
from app.domain.actors import Actor
from app.schemas.schemas import ApplicationOut, InterviewResultRequest, InterviewScheduleRequest
from app.services import placement_service as ps

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/schedule", response_model=ApplicationOut)
async def schedule_interview(body: InterviewScheduleRequest, db: AsyncSession = Depends(get_db),
                             actor: Actor = Depends(get_company_or_coordinator)):
    round_no = body.round_no or await ps.next_round_no(db, body.application_id)
    return application_out(await ps.schedule_interview(
        db, body.application_id, actor, round_no=round_no, scheduled_at=body.scheduled_at,
        venue=body.venue, notes=body.notes))


@router.patch("/{application_id}/result", response_model=ApplicationOut)
async def record_result(application_id: int, body: InterviewResultRequest, db: AsyncSession = Depends(get_db),
                        actor: Actor = Depends(get_company_or_coordinator)):
    round_no = body.round_no or await ps.latest_pending_round(db, application_id)
    return application_out(await ps.record_interview_result(
        db, application_id, actor, round_no=round_no, passed=body.result == "PASS",
        notes=body.notes, final=body.final))
