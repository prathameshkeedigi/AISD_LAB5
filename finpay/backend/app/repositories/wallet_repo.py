from typing import Optional
from sqlalchemy.orm import Session
from finpay.backend.app.models.models import Wallet

class WalletRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: int) -> Optional[Wallet]:
        return self.db.query(Wallet).filter(Wallet.user_id == user_id).first()

    def get_by_id(self, wallet_id: int) -> Optional[Wallet]:
        return self.db.query(Wallet).filter(Wallet.id == wallet_id).first()

    def create(self, user_id: int, initial_balance_paise: int = 0, tier: str = "BASIC") -> Wallet:
        wallet = Wallet(
            user_id=user_id,
            balance_paise=initial_balance_paise,
            tier=tier.upper(),
            status="ACTIVE"
        )
        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)
        return wallet

    def update_balance(self, wallet: Wallet, new_balance_paise: int) -> Wallet:
        wallet.balance_paise = new_balance_paise
        self.db.commit()
        self.db.refresh(wallet)
        return wallet

    def update_tier(self, wallet: Wallet, new_tier: str) -> Wallet:
        wallet.tier = new_tier.upper()
        self.db.commit()
        self.db.refresh(wallet)
        return wallet
