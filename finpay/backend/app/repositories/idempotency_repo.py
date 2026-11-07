from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from finpay.backend.app.models.models import IdempotencyRecord

class IdempotencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_record(self, idempotency_key: str) -> Optional[IdempotencyRecord]:
        return (
            self.db.query(IdempotencyRecord)
            .filter(IdempotencyRecord.idempotency_key == idempotency_key)
            .first()
        )

    def save_record(
        self,
        idempotency_key: str,
        user_id: int,
        endpoint: str,
        response_payload: str,
        status_code: int = 200
    ) -> IdempotencyRecord:
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            user_id=user_id,
            endpoint=endpoint,
            response_payload=response_payload,
            status_code=status_code,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
