from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from finpay.backend.app.models.models import Merchant
from finpay.backend.app.repositories.merchant_repo import MerchantRepository
from finpay.backend.app.repositories.transaction_repo import TransactionRepository

class MerchantService:
    def __init__(self, db: Session):
        self.db = db
        self.merchant_repo = MerchantRepository(db)
        self.txn_repo = TransactionRepository(db)

    def list_merchants(self) -> List[Merchant]:
        return self.merchant_repo.list_all(active_only=True)

    def get_merchant_by_id(self, merchant_id: int) -> Merchant:
        merchant = self.merchant_repo.get_by_id(merchant_id)
        if not merchant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found.")
        return merchant

    def create_merchant(self, name: str, code: str, category: str, description: Optional[str] = None, user_id: Optional[int] = None) -> Merchant:
        existing = self.merchant_repo.get_by_code(code)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Merchant code '{code}' already exists.")
        return self.merchant_repo.create(name=name, code=code, category=category, description=description, user_id=user_id)

    def get_merchant_overview(self, merchant_id: int) -> Dict[str, Any]:
        merchant = self.get_merchant_by_id(merchant_id)
        transactions = self.txn_repo.list_by_merchant_id(merchant_id, limit=20)
        
        return {
            "merchant_id": merchant.id,
            "name": merchant.name,
            "code": merchant.code,
            "category": merchant.category,
            "balance_paise": merchant.balance_paise,
            "balance_rupees": merchant.balance_paise / 100.0,
            "recent_transactions": [
                {
                    "id": t.id,
                    "reference_id": t.reference_id,
                    "amount_paise": t.amount_paise,
                    "amount_rupees": t.amount_paise / 100.0,
                    "student_tier": t.student_tier,
                    "status": t.status,
                    "created_at": t.created_at
                }
                for t in transactions
            ]
        }
