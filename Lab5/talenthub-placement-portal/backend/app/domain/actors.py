"""Who is performing an action, taken from the verified token (FR-1.3: never from request parameters)."""
from dataclasses import dataclass
from typing import Optional

from app.domain.enums import UserRole


@dataclass(frozen=True)
class Actor:
    user_id: int
    role: UserRole
    student_id: Optional[int] = None
    company_id: Optional[int] = None

    @property
    def is_coordinator(self) -> bool:
        return self.role == UserRole.COORDINATOR
