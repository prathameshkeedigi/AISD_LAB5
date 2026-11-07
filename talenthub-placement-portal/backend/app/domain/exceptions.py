"""Domain exceptions (FR-5.2, ADR-004). Services raise these; only the router layer turns them into HTTP responses."""


class DomainError(Exception):
    """Base class for every business-rule failure. `kind` lets the router choose a status code."""

    kind = "invalid"

    def __init__(self, message: str = ""):
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__


class NotFound(DomainError):
    kind = "not_found"


class JobNotFound(NotFound):
    pass


class ApplicationNotFound(NotFound):
    pass


class StudentNotFound(NotFound):
    pass


class PermissionDenied(DomainError):
    kind = "forbidden"


class Conflict(DomainError):
    kind = "conflict"


class AlreadyApplied(Conflict):
    pass


class SameCompanyThisSeason(Conflict):
    pass


class OfferAlreadyIssued(Conflict):
    pass


class DuplicateRound(Conflict):
    pass


class NotEligible(DomainError):
    def __init__(self, reason: str, failed_rule: str | None = None):
        super().__init__(f"Not eligible: {reason}")
        self.reason = reason
        self.failed_rule = failed_rule


class JobClosed(DomainError):
    pass


class NoSeasonForDate(DomainError):
    pass


class CriteriaLocked(DomainError):
    pass


class ConsentMissing(DomainError):
    pass


class InvalidTransition(DomainError):
    pass
