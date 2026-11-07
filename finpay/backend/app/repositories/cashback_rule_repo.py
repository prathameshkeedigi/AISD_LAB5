from typing import List, Optional
from sqlalchemy.orm import Session
from finpay.backend.app.models.models import CashbackRule

class CashbackRuleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_category(self, category: str) -> Optional[CashbackRule]:
        return self.db.query(CashbackRule).filter(CashbackRule.category == category).first()

    def list_all(self) -> List[CashbackRule]:
        return self.db.query(CashbackRule).all()

    def upsert(self, category: str, base_rate_bps: int, base_monthly_cap_paise: int, description: Optional[str] = None) -> CashbackRule:
        rule = self.get_by_category(category)
        if not rule:
            rule = CashbackRule(
                category=category,
                base_rate_bps=base_rate_bps,
                base_monthly_cap_paise=base_monthly_cap_paise,
                description=description
            )
            self.db.add(rule)
        else:
            rule.base_rate_bps = base_rate_bps
            rule.base_monthly_cap_paise = base_monthly_cap_paise
            rule.description = description
        self.db.commit()
        self.db.refresh(rule)
        return rule
