import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from finpay.backend.app.models.models import Wallet, Transaction, User
from finpay.backend.app.repositories.wallet_repo import WalletRepository
from finpay.backend.app.repositories.merchant_repo import MerchantRepository
from finpay.backend.app.repositories.transaction_repo import TransactionRepository
from finpay.backend.app.services.cashback_service import (
    BASIC_CATEGORY_RULES,
    get_tier_rate_multiplier,
    get_tier_cap_multiplier,
    get_tier_monthly_cap_paise
)

class WalletService:
    def __init__(self, db: Session):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.merchant_repo = MerchantRepository(db)
        self.transaction_repo = TransactionRepository(db)

    def get_wallet_by_user_id(self, user_id: int) -> Wallet:
        wallet = self.wallet_repo.get_by_user_id(user_id)
        if not wallet:
            # Auto-create if not present
            wallet = self.wallet_repo.create(user_id=user_id, initial_balance_paise=100000, tier="BASIC")
        return wallet

    def update_tier(self, user_id: int, new_tier: str) -> Wallet:
        tier_upper = new_tier.upper()
        if tier_upper not in ["BASIC", "PRIME", "PREMIUM"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier '{new_tier}'. Must be BASIC, PRIME, or PREMIUM."
            )
        wallet = self.get_wallet_by_user_id(user_id)
        return self.wallet_repo.update_tier(wallet, tier_upper)

    def topup_wallet(self, user_id: int, amount_paise: int, description: str = "Student Wallet Top-up") -> Dict[str, Any]:
        if amount_paise <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Top-up amount must be positive.")
        
        wallet = self.get_wallet_by_user_id(user_id)
        
        # Find or create Top-up system merchant
        topup_merchant = self.merchant_repo.get_by_code("TOPUP_SYSTEM")
        if not topup_merchant:
            topup_merchant = self.merchant_repo.create(
                name="FinPay Top-Up Gateway",
                code="TOPUP_SYSTEM",
                category="Top-up",
                description="System top-up provider"
            )
        
        balance_before = wallet.balance_paise
        balance_after = balance_before + amount_paise
        self.wallet_repo.update_balance(wallet, balance_after)
        
        # Credit topup merchant as well
        self.merchant_repo.credit_balance(topup_merchant, amount_paise)
        
        # Record top-up transaction
        ref_id = f"TOPUP_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        txn = self.transaction_repo.create(
            reference_id=ref_id,
            idempotency_key=f"topup_{uuid.uuid4().hex}",
            wallet_id=wallet.id,
            merchant_id=topup_merchant.id,
            amount_paise=amount_paise,
            cashback_raw_paise=0,
            cashback_awarded_paise=0,
            effective_rate_percent=0.0,
            merchant_category="Top-up",
            student_tier=wallet.tier,
            status="SUCCESS",
            type="TOPUP",
            balance_before_paise=balance_before,
            balance_after_paise=balance_after,
            description=description
        )

        return {
            "transaction_id": txn.id,
            "reference_id": ref_id,
            "wallet_id": wallet.id,
            "amount_paise": amount_paise,
            "amount_rupees": amount_paise / 100.0,
            "balance_before_paise": balance_before,
            "balance_after_paise": balance_after,
            "balance_after_rupees": balance_after / 100.0,
            "message": f"Successfully topped up ₹{amount_paise / 100.0:.2f}"
        }

    def get_monthly_category_progress(self, user_id: int, year: int, month: int) -> List[Dict[str, Any]]:
        wallet = self.get_wallet_by_user_id(user_id)
        progress_list = []

        for category, rule in BASIC_CATEGORY_RULES.items():
            if category == "Top-up":
                continue

            base_cap_paise = rule["base_monthly_cap_paise"]
            tier_cap_paise = get_tier_monthly_cap_paise(category, wallet.tier)
            earned_cashback_paise = self.transaction_repo.get_monthly_accumulated_cashback(
                wallet_id=wallet.id,
                category=category,
                year=year,
                month=month
            )
            remaining_cap_paise = max(0, tier_cap_paise - earned_cashback_paise)
            usage_pct = min(100.0, (earned_cashback_paise / tier_cap_paise * 100.0) if tier_cap_paise > 0 else 0.0)

            progress_list.append({
                "category": category,
                "base_cap_rupees": base_cap_paise / 100.0,
                "tier_cap_rupees": tier_cap_paise / 100.0,
                "tier_cap_paise": tier_cap_paise,
                "earned_cashback_paise": earned_cashback_paise,
                "earned_cashback_rupees": earned_cashback_paise / 100.0,
                "remaining_cap_paise": remaining_cap_paise,
                "remaining_cap_rupees": remaining_cap_paise / 100.0,
                "usage_percentage": round(usage_pct, 1)
            })

        return progress_list
