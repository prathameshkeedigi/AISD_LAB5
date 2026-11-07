from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from finpay.backend.app.models.models import Transaction

class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        reference_id: str,
        idempotency_key: str,
        wallet_id: int,
        merchant_id: int,
        amount_paise: int,
        cashback_raw_paise: int,
        cashback_awarded_paise: int,
        effective_rate_percent: float,
        merchant_category: str,
        student_tier: str,
        status: str,
        type: str,
        balance_before_paise: int,
        balance_after_paise: int,
        description: Optional[str] = None
    ) -> Transaction:
        txn = Transaction(
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            wallet_id=wallet_id,
            merchant_id=merchant_id,
            amount_paise=amount_paise,
            cashback_raw_paise=cashback_raw_paise,
            cashback_awarded_paise=cashback_awarded_paise,
            effective_rate_percent=effective_rate_percent,
            merchant_category=merchant_category,
            student_tier=student_tier,
            status=status,
            type=type,
            balance_before_paise=balance_before_paise,
            balance_after_paise=balance_after_paise,
            description=description,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)
        return txn

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Transaction]:
        return self.db.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).first()

    def get_by_reference_id(self, ref_id: str) -> Optional[Transaction]:
        return self.db.query(Transaction).filter(Transaction.reference_id == ref_id).first()

    def list_by_wallet_id(self, wallet_id: int, limit: int = 50) -> List[Transaction]:
        return (
            self.db.query(Transaction)
            .filter(Transaction.wallet_id == wallet_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_by_merchant_id(self, merchant_id: int, limit: int = 50) -> List[Transaction]:
        return (
            self.db.query(Transaction)
            .filter(Transaction.merchant_id == merchant_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_all(self, limit: int = 100) -> List[Transaction]:
        return (
            self.db.query(Transaction)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_monthly_accumulated_cashback(
        self, wallet_id: int, category: str, year: int, month: int
    ) -> int:
        """
        Calculates the sum of cashback_awarded_paise for a specific student wallet
        in a specific merchant category during the specified year and month.
        """
        # Determine month start and end
        start_date = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        total = (
            self.db.query(func.coalesce(func.sum(Transaction.cashback_awarded_paise), 0))
            .filter(
                Transaction.wallet_id == wallet_id,
                Transaction.merchant_category == category,
                Transaction.status == "SUCCESS",
                Transaction.type == "PAYMENT",
                Transaction.created_at >= start_date,
                Transaction.created_at < end_date,
            )
            .scalar()
        )
        return int(total or 0)
