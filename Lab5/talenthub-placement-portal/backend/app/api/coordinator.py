from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import application_out
from app.core.database import get_db
from app.core.deps import get_current_coordinator
from app.domain.actors import Actor
from app.schemas.schemas import ApplicationOut, CoordinatorStats
from app.services import admin_service, placement_service

router = APIRouter(prefix="/coordinator", tags=["coordinator"])


@router.get("/stats", response_model=CoordinatorStats)
async def stats(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_coordinator)):
    return await admin_service.overview(db, actor)


@router.get("/applications", response_model=list[ApplicationOut])
async def all_applications(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_coordinator)):
    return [application_out(a) for a in await placement_service.all_applications(db, actor)]
