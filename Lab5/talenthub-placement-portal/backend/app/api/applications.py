from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import application_out
from app.core.database import get_db
from app.core.deps import get_company_or_coordinator, get_current_company, get_current_student
from app.domain.actors import Actor
from app.schemas.schemas import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate
from app.services import placement_service as ps

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationOut)
async def apply(body: ApplicationCreate, db: AsyncSession = Depends(get_db),
                actor: Actor = Depends(get_current_student)):
    return application_out(await ps.apply_for_job(db, actor.student_id, body.job_id))


@router.get("/me", response_model=list[ApplicationOut])
async def my_applications(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_student)):
    return [application_out(a) for a in await ps.my_applications(db, actor)]


@router.get("/job/{job_id}", response_model=list[ApplicationOut])
async def applications_for_job(job_id: int, db: AsyncSession = Depends(get_db),
                               actor: Actor = Depends(get_company_or_coordinator)):
    return [application_out(a) for a in await ps.job_applications(db, actor, job_id)]


@router.get("/company/mine", response_model=list[ApplicationOut])
async def my_company_applications(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_company)):
    return [application_out(a) for a in await ps.company_applications(db, actor)]


@router.patch("/{application_id}/status", response_model=ApplicationOut)
async def update_status(application_id: int, body: ApplicationStatusUpdate, db: AsyncSession = Depends(get_db),
                        actor: Actor = Depends(get_company_or_coordinator)):
    if body.status == "SHORTLISTED":
        return application_out(await ps.shortlist_application(db, application_id, actor))
    return application_out(await ps.reject_application(db, application_id, actor))
