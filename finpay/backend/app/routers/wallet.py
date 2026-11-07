from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from finpay.backend.app.core.database import get_db
from finpay.backend.app.routers.auth import get_current_user
from finpay.backend.app.models.models import User
from finpay.backend.app.schemas.schemas import (
    WalletResponse,
    WalletTierUpdate,
    WalletTopupRequest,
    MonthlyCategoryProgress,
    TransactionResponse
)
from finpay.backend.app.services.wallet_service import WalletService
from finpay.backend.app.services.cashback_service import (
    get_tier_rate_multiplier,
    get_tier_cap_multiplier
)
from finpay.backend.app.repositories.transaction_repo import TransactionRepository
from finpay.backend.app.core.websocket_manager import manager

router = APIRouter(prefix="/wallet", tags=["Wallet Operations"])

@router.get("/me", response_model=WalletResponse)
def get_my_wallet(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet_svc = WalletService(db)
    wallet = wallet_svc.get_wallet_by_user_id(current_user.id)
    return {
        "id": wallet.id,
        "user_id": current_user.id,
        "user_name": current_user.name,
        "tier": wallet.tier,
        "balance_paise": wallet.balance_paise,
        "balance_rupees": wallet.balance_paise / 100.0,
        "status": wallet.status,
        "cashback_rate_multiplier": get_tier_rate_multiplier(wallet.tier),
        "monthly_cap_multiplier": get_tier_cap_multiplier(wallet.tier),
        "created_at": wallet.created_at,
        "updated_at": wallet.updated_at
    }

@router.put("/tier", response_model=WalletResponse)
async def update_wallet_tier(
    tier_in: WalletTierUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet_svc = WalletService(db)
    updated_wallet = wallet_svc.update_tier(current_user.id, tier_in.tier)
    
    # Notify user via websocket
    await manager.send_personal_message(
        {
            "event": "TIER_UPDATED",
            "tier": updated_wallet.tier,
            "rate_multiplier": get_tier_rate_multiplier(updated_wallet.tier),
            "cap_multiplier": get_tier_cap_multiplier(updated_wallet.tier)
        },
        client_id=str(current_user.id)
    )

    return {
        "id": updated_wallet.id,
        "user_id": current_user.id,
        "user_name": current_user.name,
        "tier": updated_wallet.tier,
        "balance_paise": updated_wallet.balance_paise,
        "balance_rupees": updated_wallet.balance_paise / 100.0,
        "status": updated_wallet.status,
        "cashback_rate_multiplier": get_tier_rate_multiplier(updated_wallet.tier),
        "monthly_cap_multiplier": get_tier_cap_multiplier(updated_wallet.tier),
        "created_at": updated_wallet.created_at,
        "updated_at": updated_wallet.updated_at
    }

@router.post("/topup")
async def topup_my_wallet(
    topup_in: WalletTopupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet_svc = WalletService(db)
    amount_paise = int(round(topup_in.amount_rupees * 100))
    result = wallet_svc.topup_wallet(current_user.id, amount_paise, topup_in.description)

    # Real-time WebSocket broadcast
    await manager.send_personal_message(
        {
            "event": "BALANCE_UPDATED",
            "balance_paise": result["balance_after_paise"],
            "balance_rupees": result["balance_after_rupees"],
            "message": result["message"]
        },
        client_id=str(current_user.id)
    )

    return result

@router.get("/monthly-progress", response_model=List[MonthlyCategoryProgress])
def get_monthly_progress(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    target_year = year or now.year
    target_month = month or now.month
    wallet_svc = WalletService(db)
    return wallet_svc.get_monthly_category_progress(current_user.id, target_year, target_month)

@router.get("/transactions", response_model=List[TransactionResponse])
def get_my_transactions(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet_svc = WalletService(db)
    wallet = wallet_svc.get_wallet_by_user_id(current_user.id)
    txn_repo = TransactionRepository(db)
    txns = txn_repo.list_by_wallet_id(wallet.id, limit=limit)
    
    return [
        {
            "id": t.id,
            "reference_id": t.reference_id,
            "idempotency_key": t.idempotency_key,
            "type": t.type,
            "status": t.status,
            "merchant_name": t.merchant.name if t.merchant else "Merchant",
            "merchant_category": t.merchant_category,
            "student_tier": t.student_tier,
            "amount_paise": t.amount_paise,
            "amount_rupees": t.amount_paise / 100.0,
            "cashback_raw_paise": t.cashback_raw_paise,
            "cashback_awarded_paise": t.cashback_awarded_paise,
            "cashback_awarded_rupees": t.cashback_awarded_paise / 100.0,
            "effective_rate_percent": t.effective_rate_percent,
            "balance_before_paise": t.balance_before_paise,
            "balance_after_paise": t.balance_after_paise,
            "description": t.description,
            "created_at": t.created_at
        }
        for t in txns
    ]
