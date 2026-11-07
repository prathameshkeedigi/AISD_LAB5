from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_coordinator
from app.domain.actors import Actor
from app.schemas.schemas import CompanyCreate, CompanyOut, SeasonCreate, SeasonOut
from app.services import admin_service

router = APIRouter(tags=["companies"])


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(db: AsyncSession = Depends(get_db), actor: Actor = Depends(get_current_coordinator)):
    return await admin_service.list_companies(db, actor)


@router.post("/companies", response_model=CompanyOut)
async def create_company(body: CompanyCreate, db: AsyncSession = Depends(get_db),
                         actor: Actor = Depends(get_current_coordinator)):
    return await admin_service.create_company(db, actor, body.name, body.description)


@router.get("/seasons", response_model=list[SeasonOut])
async def list_seasons(db: AsyncSession = Depends(get_db), _: Actor = Depends(get_current_coordinator)):
    return await admin_service.list_seasons(db)


@router.post("/seasons", response_model=SeasonOut)
async def create_season(body: SeasonCreate, db: AsyncSession = Depends(get_db),
                        actor: Actor = Depends(get_current_coordinator)):
    return await admin_service.create_season(db, actor, body.name, body.start_date, body.end_date)
