from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import application_out
from app.core.database import get_db
from app.core.deps import get_company_or_coordinator, get_current_student
from app.domain.actors import Actor
from app.schemas.schemas import ApplicationOut, OfferCreate, OfferRespondRequest
from app.services import placement_service as ps

router = APIRouter(prefix="/offers", tags=["offers"])


@router.post("", response_model=ApplicationOut)
async def issue_offer(body: OfferCreate, db: AsyncSession = Depends(get_db),
                      actor: Actor = Depends(get_company_or_coordinator)):
    return application_out(await ps.issue_offer(db, body.application_id, actor, body.package_lpa))


@router.patch("/{application_id}/respond", response_model=ApplicationOut)
async def respond_to_offer(application_id: int, body: OfferRespondRequest, db: AsyncSession = Depends(get_db),
                           actor: Actor = Depends(get_current_student)):
    return application_out(await ps.respond_to_offer(db, application_id, actor, body.accept))
