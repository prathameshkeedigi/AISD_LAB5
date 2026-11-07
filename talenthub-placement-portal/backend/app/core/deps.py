"""The only place tokens are turned into users (FR-1.2, ADR-003)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import InvalidToken, decode_access_token
from app.domain.actors import Actor
from app.domain.enums import UserRole
from app.repositories import repository as repo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
_401 = HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", {"WWW-Authenticate": "Bearer"})


async def get_current_actor(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Actor:
    try:
        payload = decode_access_token(token)
        user = await repo.get_user(db, int(payload["sub"]))
    except (InvalidToken, KeyError, ValueError):
        raise _401
    if not user or not user.is_active:
        raise _401
    student = await repo.student_by_user(db, user.id) if user.role == UserRole.STUDENT else None
    return Actor(user_id=user.id, role=user.role, student_id=student.id if student else None,
                 company_id=user.company_id)


def _role(*roles):
    async def checker(actor: Actor = Depends(get_current_actor)) -> Actor:
        if actor.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this action")
        return actor
    return checker


get_current_student = _role(UserRole.STUDENT)
get_current_company = _role(UserRole.COMPANY_REP)
get_current_coordinator = _role(UserRole.COORDINATOR)
get_company_or_coordinator = _role(UserRole.COMPANY_REP, UserRole.COORDINATOR)
