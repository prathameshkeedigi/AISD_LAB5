from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_coordinator, get_current_student
from app.domain.actors import Actor
from app.domain.enums import ConsentPurpose
from app.schemas.schemas import AcademicsUpdate, StudentCreate, StudentOut
from app.services import admin_service, placement_service

router = APIRouter(prefix="/students", tags=["students"])


def _out(s) -> dict:
    return {"id": s.id, "usn": s.usn, "name": s.user.full_name, "email": s.user.email, "branch": s.branch,
            "cgpa": s.cgpa, "active_backlogs": s.active_backlogs, "cleared_backlogs": s.cleared_backlogs}


@router.get("", response_model=list[StudentOut])
async def list_students(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_coordinator)):
    return [_out(s) for s in await admin_service.list_students(db, actor)]


@router.post("", response_model=StudentOut)
async def create_student(body: StudentCreate, db: AsyncSession = Depends(get_db),
                         actor: Actor = Depends(get_current_coordinator)):
    return _out(await admin_service.create_student(db, actor, **body.model_dump()))


@router.patch("/{student_id}/academics", response_model=StudentOut)
async def update_academics(student_id: int, body: AcademicsUpdate, db: AsyncSession = Depends(get_db),
                           actor: Actor = Depends(get_current_coordinator)):
    return _out(await admin_service.update_student_academics(db, actor, student_id, **body.model_dump()))


@router.post("/{student_id}/anonymise", response_model=StudentOut)
async def anonymise(student_id: int, db: AsyncSession = Depends(get_db),
                    actor: Actor = Depends(get_current_coordinator)):
    return _out(await admin_service.anonymise_student(db, actor, student_id))


@router.get("/me", response_model=StudentOut)
async def my_profile(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_student)):
    return await placement_service.student_profile(db, actor)


@router.post("/me/consents/{purpose}")
async def grant_consent(purpose: ConsentPurpose, db: AsyncSession = Depends(get_db),
                        actor: Actor = Depends(get_current_student)):
    await admin_service.grant_consent(db, actor.student_id, purpose)
    return {"purpose": purpose, "active": True}


@router.delete("/me/consents/{purpose}")
async def withdraw_consent(purpose: ConsentPurpose, db: AsyncSession = Depends(get_db),
                           actor: Actor = Depends(get_current_student)):
    await admin_service.withdraw_consent(db, actor.student_id, purpose)
    return {"purpose": purpose, "active": False}
