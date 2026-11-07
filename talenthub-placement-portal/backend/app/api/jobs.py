from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import job_out
from app.core.database import get_db
from app.core.deps import (
    get_company_or_coordinator, get_current_actor, get_current_company, get_current_coordinator, get_current_student,
)
from app.domain.actors import Actor
from app.domain.enums import UserRole
from app.notifications import get_notifier
from app.schemas.schemas import CriteriaUpdate, JobCreate, JobOut, ShortlistOut
from app.services import admin_service, placement_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
async def list_jobs(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_actor)):
    if actor.role == UserRole.STUDENT:
        return [job_out(j, r, a) for j, r, a in await placement_service.jobs_with_eligibility(db, actor.student_id)]
    return [job_out(j) for j in await admin_service.list_jobs(db, actor)]


@router.get("/available", response_model=list[JobOut])
async def available_jobs(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_student)):
    return [job_out(j) for j in await placement_service.list_available_jobs(db, actor.student_id)]


@router.get("/mine", response_model=list[JobOut])
async def my_jobs(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_company)):
    return [job_out(j) for j in await admin_service.list_jobs(db, actor)]


@router.post("", response_model=JobOut)
async def create_job(body: JobCreate, db: AsyncSession = Depends(get_db),
                     actor: Actor = Depends(get_company_or_coordinator)):
    return job_out(await admin_service.create_job(db, actor, **body.model_dump()))


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db), _: Actor = Depends(get_current_actor)):
    return job_out(await admin_service.get_job(db, job_id))


@router.patch("/{job_id}/close", response_model=JobOut)
async def close_job(job_id: int, db: AsyncSession = Depends(get_db),
                    actor: Actor = Depends(get_company_or_coordinator)):
    return job_out(await admin_service.close_job(db, actor, job_id))


@router.patch("/{job_id}/criteria", response_model=JobOut)
async def update_criteria(job_id: int, body: CriteriaUpdate, db: AsyncSession = Depends(get_db),
                          actor: Actor = Depends(get_company_or_coordinator)):
    return job_out(await admin_service.update_criteria(db, actor, job_id, **body.model_dump()))


@router.post("/{job_id}/shortlist", response_model=ShortlistOut)
async def run_shortlist(job_id: int, db: AsyncSession = Depends(get_db),
                        actor: Actor = Depends(get_current_coordinator)):
    report = await placement_service.shortlist_students(db, job_id, actor, get_notifier())
    return {"shortlisted": len(report.shortlisted), "ineligible": report.ineligible}


@router.get("/{job_id}/status-counts")
async def job_status_counts(job_id: int, db: AsyncSession = Depends(get_db),
                            actor: Actor = Depends(get_company_or_coordinator)):
    return await admin_service.status_counts(db, actor, job_id=job_id)


@router.get("/{job_id}/shortlist.csv", response_class=PlainTextResponse)
async def shortlist_csv(job_id: int, db: AsyncSession = Depends(get_db),
                        actor: Actor = Depends(get_company_or_coordinator)):
    text = await admin_service.shortlist_csv(db, actor, job_id)
    return PlainTextResponse(text, media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="shortlist_{job_id}.csv"'})
