"""Translate domain exceptions into HTTP responses: the only place a domain error becomes HTTP (ADR-004)."""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import DomainError, NotEligible

_STATUS = {"not_found": 404, "forbidden": 403, "conflict": 409, "unauthorized": 401, "invalid": 400}


async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    detail = exc.reason if isinstance(exc, NotEligible) else exc.message  # plain-language reason (NFR-7.1)
    return JSONResponse(status_code=_STATUS.get(exc.kind, 400), content={"detail": detail})
