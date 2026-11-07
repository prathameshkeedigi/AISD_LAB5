from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from finpay.backend.app.core.database import get_db
from finpay.backend.app.schemas.schemas import ReconciliationReport, CashbackRuleResponse
from finpay.backend.app.services.reconciliation_service import ReconciliationService
from finpay.backend.app.services.cashback_service import BASIC_CATEGORY_RULES

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation & Audit"])

@router.get("/monthly", response_model=ReconciliationReport)
def get_monthly_reconciliation(
    year: Optional[int] = Query(None, description="Year to reconcile (e.g. 2026)"),
    month: Optional[int] = Query(None, description="Month to reconcile (1-12)"),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    target_year = year or now.year
    target_month = month or now.month
    
    recon_svc = ReconciliationService(db)
    return recon_svc.generate_monthly_reconciliation(target_year, target_month)

@router.get("/rules", response_model=List[CashbackRuleResponse])
def get_cashback_rules():
    rules_list = []
    idx = 1
    for cat, info in BASIC_CATEGORY_RULES.items():
        base_rate_pct = info["base_rate_bps"] / 100.0
        base_cap_paise = info["base_monthly_cap_paise"]
        rules_list.append({
            "id": idx,
            "category": cat,
            "base_rate_percent": base_rate_pct,
            "base_monthly_cap_rupees": base_cap_paise / 100.0,
            "base_monthly_cap_paise": base_cap_paise,
            "description": f"Standard BASIC rule: {base_rate_pct}% cashback, monthly cap ₹{base_cap_paise/100:.2f}"
        })
        idx += 1
    return rules_list
