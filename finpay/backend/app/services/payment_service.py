import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from finpay.backend.app.models.models import Wallet, Merchant, Transaction, User
from finpay.backend.app.repositories.wallet_repo import WalletRepository
from finpay.backend.app.repositories.merchant_repo import MerchantRepository
from finpay.backend.app.repositories.transaction_repo import TransactionRepository
from finpay.backend.app.repositories.idempotency_repo import IdempotencyRepository
from finpay.backend.app.services.cashback_service import (
    calculate_cashback,
    get_tier_rate_multiplier,
    get_tier_cap_multiplier,
    get_tier_monthly_cap_paise,
    BASIC_CATEGORY_RULES
)

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.merchant_repo = MerchantRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.idempotency_repo = IdempotencyRepository(db)

    def preview_payment(self, user_id: int, merchant_id: int, amount_rupees: float) -> Dict[str, Any]:
        """
        Calculates preview values (raw cashback, remaining cap, final cashback)
        without creating a transaction or modifying balances.
        """
        wallet = self.wallet_repo.get_by_user_id(user_id)
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student wallet not found.")

        merchant = self.merchant_repo.get_by_id(merchant_id)
        if not merchant or not merchant.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found or inactive.")

        amount_paise = int(round(amount_rupees * 100))
        raw_cashback_paise, effective_rate = calculate_cashback(
            amount_paise=amount_paise,
            category=merchant.category,
            tier=wallet.tier
        )

        now = datetime.now(timezone.utc)
        accumulated_cashback_paise = self.txn_repo.get_monthly_accumulated_cashback(
            wallet_id=wallet.id,
            category=merchant.category,
            year=now.year,
            month=now.month
        )

        rule = BASIC_CATEGORY_RULES.get(merchant.category, {"base_rate_bps": 0, "base_monthly_cap_paise": 0})
        base_rate_percent = rule["base_rate_bps"] / 100.0
        base_monthly_cap_paise = rule["base_monthly_cap_paise"]
        tier_monthly_cap_paise = get_tier_monthly_cap_paise(merchant.category, wallet.tier)
        
        remaining_cap_paise = max(0, tier_monthly_cap_paise - accumulated_cashback_paise)
        cashback_to_be_awarded_paise = min(raw_cashback_paise, remaining_cap_paise)

        return {
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "merchant_category": merchant.category,
            "student_tier": wallet.tier,
            "amount_paise": amount_paise,
            "amount_rupees": amount_rupees,
            "base_rate_percent": base_rate_percent,
            "tier_rate_multiplier": get_tier_rate_multiplier(wallet.tier),
            "effective_rate_percent": effective_rate,
            "raw_cashback_paise": raw_cashback_paise,
            "raw_cashback_rupees": raw_cashback_paise / 100.0,
            "base_monthly_cap_paise": base_monthly_cap_paise,
            "tier_monthly_cap_paise": tier_monthly_cap_paise,
            "tier_monthly_cap_rupees": tier_monthly_cap_paise / 100.0,
            "accumulated_monthly_cashback_paise": accumulated_cashback_paise,
            "accumulated_monthly_cashback_rupees": accumulated_cashback_paise / 100.0,
            "remaining_monthly_cap_paise": remaining_cap_paise,
            "remaining_monthly_cap_rupees": remaining_cap_paise / 100.0,
            "cashback_to_be_awarded_paise": cashback_to_be_awarded_paise,
            "cashback_to_be_awarded_rupees": cashback_to_be_awarded_paise / 100.0,
            "cap_reached": remaining_cap_paise <= 0
        }

    def process_payment(
        self,
        user_id: int,
        merchant_id: int,
        amount_rupees: float,
        idempotency_key: str,
        description: str = None
    ) -> Dict[str, Any]:
        """
        Coordinates the payment, transaction recording, idempotency check,
        and monthly cashback limit enforcement according to FinPay rules.
        """
        if not idempotency_key or not idempotency_key.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment requires a non-empty idempotency_key for transaction safety."
            )

        # Step 4: Check payment safety (Idempotency)
        cached_record = self.idempotency_repo.get_record(idempotency_key)
        if cached_record:
            cached_data = json.loads(cached_record.response_payload)
            cached_data["is_idempotent_replay"] = True
            cached_data["message"] = "Idempotent request: Returned previous transaction result without re-processing."
            return cached_data

        # Also verify if transaction with this idempotency key exists
        existing_txn = self.txn_repo.get_by_idempotency_key(idempotency_key)
        if existing_txn:
            wallet = self.wallet_repo.get_by_id(existing_txn.wallet_id)
            merchant = self.merchant_repo.get_by_id(existing_txn.merchant_id)
            return {
                "transaction_id": existing_txn.id,
                "reference_id": existing_txn.reference_id,
                "idempotency_key": existing_txn.idempotency_key,
                "status": existing_txn.status,
                "wallet_id": existing_txn.wallet_id,
                "merchant_id": existing_txn.merchant_id,
                "merchant_name": merchant.name if merchant else "Merchant",
                "merchant_category": existing_txn.merchant_category,
                "student_tier": existing_txn.student_tier,
                "amount_paise": existing_txn.amount_paise,
                "amount_rupees": existing_txn.amount_paise / 100.0,
                "cashback_raw_paise": existing_txn.cashback_raw_paise,
                "cashback_raw_rupees": existing_txn.cashback_raw_paise / 100.0,
                "cashback_awarded_paise": existing_txn.cashback_awarded_paise,
                "cashback_awarded_rupees": existing_txn.cashback_awarded_paise / 100.0,
                "effective_rate_percent": existing_txn.effective_rate_percent,
                "student_balance_before_paise": existing_txn.balance_before_paise,
                "student_balance_after_paise": existing_txn.balance_after_paise,
                "student_balance_after_rupees": existing_txn.balance_after_paise / 100.0,
                "is_idempotent_replay": True,
                "message": "Idempotent replay of previously processed transaction.",
                "created_at": existing_txn.created_at.isoformat()
            }

        # Step 1: Student wallet
        wallet = self.wallet_repo.get_by_user_id(user_id)
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student wallet not found.")

        # Step 2: Make a payment - verify merchant
        merchant = self.merchant_repo.get_by_id(merchant_id)
        if not merchant or not merchant.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant not found or inactive.")

        amount_paise = int(round(amount_rupees * 100))
        if amount_paise <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than zero.")

        if wallet.balance_paise < amount_paise:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient wallet balance. Current balance: ₹{wallet.balance_paise / 100.0:.2f}, required: ₹{amount_rupees:.2f}"
            )

        # Step 3: Calculate cashback (Raw calculation without DB access)
        raw_cashback_paise, effective_rate = calculate_cashback(
            amount_paise=amount_paise,
            category=merchant.category,
            tier=wallet.tier
        )

        # Step 5: Apply monthly cashback limits
        now = datetime.now(timezone.utc)
        accumulated_cashback_paise = self.txn_repo.get_monthly_accumulated_cashback(
            wallet_id=wallet.id,
            category=merchant.category,
            year=now.year,
            month=now.month
        )

        tier_monthly_cap_paise = get_tier_monthly_cap_paise(merchant.category, wallet.tier)
        remaining_cap_paise = max(0, tier_monthly_cap_paise - accumulated_cashback_paise)

        # Awarded cashback is clamped to remaining monthly cap
        cashback_awarded_paise = min(raw_cashback_paise, remaining_cap_paise)

        # Step 6: Record the transaction & update relevant wallet records
        balance_before = wallet.balance_paise
        
        # Payment deduction + Cashback credited
        balance_after = balance_before - amount_paise + cashback_awarded_paise
        self.wallet_repo.update_balance(wallet, balance_after)

        # Merchant receives payment amount
        self.merchant_repo.credit_balance(merchant, amount_paise)

        # Generate unique transaction reference
        ref_id = f"FP_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6].upper()}"

        transaction = self.txn_repo.create(
            reference_id=ref_id,
            idempotency_key=idempotency_key,
            wallet_id=wallet.id,
            merchant_id=merchant.id,
            amount_paise=amount_paise,
            cashback_raw_paise=raw_cashback_paise,
            cashback_awarded_paise=cashback_awarded_paise,
            effective_rate_percent=effective_rate,
            merchant_category=merchant.category,
            student_tier=wallet.tier,
            status="SUCCESS",
            type="PAYMENT",
            balance_before_paise=balance_before,
            balance_after_paise=balance_after,
            description=description or f"Payment to {merchant.name}"
        )

        response_payload = {
            "transaction_id": transaction.id,
            "reference_id": ref_id,
            "idempotency_key": idempotency_key,
            "status": "SUCCESS",
            "wallet_id": wallet.id,
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "merchant_category": merchant.category,
            "student_tier": wallet.tier,
            "amount_paise": amount_paise,
            "amount_rupees": amount_rupees,
            "cashback_raw_paise": raw_cashback_paise,
            "cashback_raw_rupees": raw_cashback_paise / 100.0,
            "cashback_awarded_paise": cashback_awarded_paise,
            "cashback_awarded_rupees": cashback_awarded_paise / 100.0,
            "effective_rate_percent": effective_rate,
            "student_balance_before_paise": balance_before,
            "student_balance_after_paise": balance_after,
            "student_balance_after_rupees": balance_after / 100.0,
            "is_idempotent_replay": False,
            "message": (
                f"Payment of ₹{amount_rupees:.2f} successful. "
                f"Earned ₹{cashback_awarded_paise / 100.0:.2f} cashback!"
                if cashback_awarded_paise > 0 else
                f"Payment of ₹{amount_rupees:.2f} successful (Monthly cashback limit reached)."
            ),
            "created_at": transaction.created_at.isoformat()
        }

        # Save Idempotency Record
        self.idempotency_repo.save_record(
            idempotency_key=idempotency_key,
            user_id=user_id,
            endpoint="/api/payments/pay",
            response_payload=json.dumps(response_payload),
            status_code=200
        )

        return response_payload
