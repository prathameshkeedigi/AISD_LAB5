from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from finpay.backend.app.core.database import get_db
from finpay.backend.app.schemas.schemas import MerchantResponse, MerchantCreate
from finpay.backend.app.services.merchant_service import MerchantService

router = APIRouter(prefix="/merchants", tags=["Merchants"])

@router.get("", response_model=List[MerchantResponse])
def get_merchants(db: Session = Depends(get_db)):
    merchant_svc = MerchantService(db)
    merchants = merchant_svc.list_merchants()
    return [
        {
            "id": m.id,
            "name": m.name,
            "code": m.code,
            "category": m.category,
            "description": m.description,
            "balance_paise": m.balance_paise,
            "balance_rupees": m.balance_paise / 100.0,
            "is_active": m.is_active,
            "created_at": m.created_at
        }
        for m in merchants
    ]

@router.get("/{merchant_id}", response_model=MerchantResponse)
def get_merchant(merchant_id: int, db: Session = Depends(get_db)):
    merchant_svc = MerchantService(db)
    m = merchant_svc.get_merchant_by_id(merchant_id)
    return {
        "id": m.id,
        "name": m.name,
        "code": m.code,
        "category": m.category,
        "description": m.description,
        "balance_paise": m.balance_paise,
        "balance_rupees": m.balance_paise / 100.0,
        "is_active": m.is_active,
        "created_at": m.created_at
    }

@router.get("/{merchant_id}/overview")
def get_merchant_overview(merchant_id: int, db: Session = Depends(get_db)):
    merchant_svc = MerchantService(db)
    return merchant_svc.get_merchant_overview(merchant_id)

@router.post("", response_model=MerchantResponse)
def create_merchant(merchant_in: MerchantCreate, db: Session = Depends(get_db)):
    merchant_svc = MerchantService(db)
    m = merchant_svc.create_merchant(
        name=merchant_in.name,
        code=merchant_in.code,
        category=merchant_in.category,
        description=merchant_in.description
    )
    return {
        "id": m.id,
        "name": m.name,
        "code": m.code,
        "category": m.category,
        "description": m.description,
        "balance_paise": m.balance_paise,
        "balance_rupees": m.balance_paise / 100.0,
        "is_active": m.is_active,
        "created_at": m.created_at
    }
