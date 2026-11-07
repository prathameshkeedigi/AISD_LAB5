"""Login use case. Raises a domain error; the router turns it into 401."""
from app.core.security import create_access_token, verify_password
from app.domain.exceptions import DomainError
from app.repositories import repository as repo


class InvalidCredentials(DomainError):
    kind = "unauthorized"


async def login(db, email: str, password: str) -> dict:
    user = await repo.user_by_email(db, email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise InvalidCredentials("Invalid email or password")
    role = user.role.value
    student = await repo.student_by_user(db, user.id) if role == "STUDENT" else None
    linked_id = student.id if student else user.company_id
    token = create_access_token({"sub": str(user.id), "role": role})
    return {"access_token": token, "token_type": "bearer", "role": role, "user_id": user.id,
            "name": user.full_name, "linked_id": linked_id}
