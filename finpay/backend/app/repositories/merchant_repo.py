from typing import List, Optional
from sqlalchemy.orm import Session
from finpay.backend.app.models.models import Merchant

class MerchantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, merchant_id: int) -> Optional[Merchant]:
        return self.db.query(Merchant).filter(Merchant.id == merchant_id).first()

    def get_by_code(self, code: str) -> Optional[Merchant]:
        return self.db.query(Merchant).filter(Merchant.code == code).first()

    def get_by_user_id(self, user_id: int) -> Optional[Merchant]:
        return self.db.query(Merchant).filter(Merchant.user_id == user_id).first()

    def list_all(self, active_only: bool = True) -> List[Merchant]:
        query = self.db.query(Merchant)
        if active_only:
            query = query.filter(Merchant.is_active.is_(True))
        return query.all()

    def create(self, name: str, code: str, category: str, description: Optional[str] = None, user_id: Optional[int] = None) -> Merchant:
        merchant = Merchant(
            name=name,
            code=code,
            category=category,
            description=description,
            user_id=user_id,
            balance_paise=0,
            is_active=True
        )
        self.db.add(merchant)
        self.db.commit()
        self.db.refresh(merchant)
        return merchant

    def credit_balance(self, merchant: Merchant, amount_paise: int) -> Merchant:
        merchant.balance_paise += amount_paise
        self.db.commit()
        self.db.refresh(merchant)
        return merchant
