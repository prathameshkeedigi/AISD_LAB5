from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_actor
from app.domain.actors import Actor
from app.schemas.schemas import LoginRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(db, body.email, body.password)


@router.get("/me")
async def me(actor: Actor = Depends(get_current_actor)):
    return {"role": actor.role.value, "user_id": actor.user_id,
            "linked_id": actor.student_id if actor.student_id else actor.company_id}
