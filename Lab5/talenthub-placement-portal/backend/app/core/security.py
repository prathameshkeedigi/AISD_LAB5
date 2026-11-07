"""JWT and password hashing (ADR-003). The signing secret comes from the environment, never the source (NFR-3.7)."""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

log = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("TALENTHUB_TOKEN_MINUTES", "120"))


def _load_secret() -> str:
    secret = os.getenv("TALENTHUB_SECRET_KEY")
    if secret:
        return secret
    if os.getenv("TALENTHUB_ENV") == "production":
        raise RuntimeError("TALENTHUB_SECRET_KEY must be set in production")
    log.warning("TALENTHUB_SECRET_KEY not set: using a random development key (tokens end on restart)")
    return secrets.token_urlsafe(48)


SECRET_KEY = _load_secret()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto",
                           bcrypt__rounds=int(os.getenv("TALENTHUB_BCRYPT_ROUNDS", "12")))


class InvalidToken(Exception):
    pass


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):  # e.g. the "!" hash of an anonymised account
        return False


def create_access_token(data: dict, expires_minutes: int | None = None) -> str:
    to_encode = data.copy()
    minutes = ACCESS_TOKEN_EXPIRE_MINUTES if expires_minutes is None else expires_minutes
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise InvalidToken() from e
