from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from finpay.backend.app.core.database import get_db
from finpay.backend.app.routers.auth import get_current_user
from finpay.backend.app.models.models import User
from finpay.backend.app.schemas.schemas import (
    PaymentRequest,
    PaymentResponse,
    CashbackPreviewRequest,
    CashbackPreviewResponse
)
from finpay.backend.app.services.payment_service import PaymentService
from finpay.backend.app.core.websocket_manager import manager

router = APIRouter(prefix="/payments", tags=["Payments & Cashback"])

@router.post("/preview", response_model=CashbackPreviewResponse)
def preview_payment(
    req: CashbackPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment_svc = PaymentService(db)
    return payment_svc.preview_payment(
        user_id=current_user.id,
        merchant_id=req.merchant_id,
        amount_rupees=req.amount_rupees
    )

@router.post("/pay", response_model=PaymentResponse)
async def make_payment(
    payment_in: PaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment_svc = PaymentService(db)
    result = payment_svc.process_payment(
        user_id=current_user.id,
        merchant_id=payment_in.merchant_id,
        amount_rupees=payment_in.amount_rupees,
        idempotency_key=payment_in.idempotency_key,
        description=payment_in.description
    )

    # Real-time WebSocket notifications (if this was a fresh transaction)
    if not result.get("is_idempotent_replay"):
        # 1. Notify Student
        await manager.send_personal_message(
            {
                "event": "PAYMENT_COMPLETED",
                "reference_id": result["reference_id"],
                "merchant_name": result["merchant_name"],
                "amount_rupees": result["amount_rupees"],
                "cashback_awarded_rupees": result["cashback_awarded_rupees"],
                "balance_after_rupees": result["student_balance_after_rupees"],
                "message": result["message"]
            },
            client_id=str(current_user.id)
        )

        # 2. Notify Merchant
        await manager.send_personal_message(
            {
                "event": "PAYMENT_RECEIVED",
                "reference_id": result["reference_id"],
                "student_name": current_user.name,
                "student_tier": result["student_tier"],
                "amount_rupees": result["amount_rupees"],
                "created_at": result["created_at"]
            },
            client_id=f"merchant_{result['merchant_id']}"
        )

        # 3. Broadcast to Admin / Global audit log
        await manager.broadcast(
            {
                "event": "TRANSACTION_BROADCAST",
                "reference_id": result["reference_id"],
                "type": "PAYMENT",
                "category": result["merchant_category"],
                "amount_rupees": result["amount_rupees"],
                "cashback_rupees": result["cashback_awarded_rupees"],
                "tier": result["student_tier"]
            }
        )

    return result
