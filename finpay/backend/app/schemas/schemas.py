from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Auth Schemas ---
class UserBase(BaseModel):
    name: str
    email: str = Field(..., description="User email address")
    role: str = "STUDENT"

class UserCreate(UserBase):
    password: str
    tier: Optional[str] = "BASIC"
    initial_balance_rupees: Optional[float] = 1000.0  # Seed balance in ₹ for demo convenience

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None

# --- Wallet Schemas ---
class WalletResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    tier: str
    balance_paise: int
    balance_rupees: float
    status: str
    cashback_rate_multiplier: float
    monthly_cap_multiplier: float
    created_at: datetime
    updated_at: datetime

class WalletTierUpdate(BaseModel):
    tier: str = Field(..., description="BASIC, PRIME, or PREMIUM")

class WalletTopupRequest(BaseModel):
    amount_rupees: float = Field(..., gt=0, description="Amount to top up in Rupees")
    description: Optional[str] = "Student Wallet Top-up"

# --- Merchant Schemas ---
class MerchantBase(BaseModel):
    name: str
    code: str
    category: str
    description: Optional[str] = None

class MerchantCreate(MerchantBase):
    pass

class MerchantResponse(MerchantBase):
    id: int
    balance_paise: int
    balance_rupees: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Cashback Rules & Calculation Schemas ---
class CashbackRuleResponse(BaseModel):
    id: int
    category: str
    base_rate_percent: float
    base_monthly_cap_rupees: float
    base_monthly_cap_paise: int
    description: Optional[str] = None

class CashbackPreviewRequest(BaseModel):
    merchant_id: int
    amount_rupees: float

class CashbackPreviewResponse(BaseModel):
    merchant_id: int
    merchant_name: str
    merchant_category: str
    student_tier: str
    amount_paise: int
    amount_rupees: float
    base_rate_percent: float
    tier_rate_multiplier: float
    effective_rate_percent: float
    raw_cashback_paise: int
    raw_cashback_rupees: float
    base_monthly_cap_paise: int
    tier_monthly_cap_paise: int
    tier_monthly_cap_rupees: float
    accumulated_monthly_cashback_paise: int
    accumulated_monthly_cashback_rupees: float
    remaining_monthly_cap_paise: int
    remaining_monthly_cap_rupees: float
    cashback_to_be_awarded_paise: int
    cashback_to_be_awarded_rupees: float
    cap_reached: bool

class MonthlyCategoryProgress(BaseModel):
    category: str
    base_cap_rupees: float
    tier_cap_rupees: float
    tier_cap_paise: int
    earned_cashback_paise: int
    earned_cashback_rupees: float
    remaining_cap_paise: int
    remaining_cap_rupees: float
    usage_percentage: float

# --- Payment Schemas ---
class PaymentRequest(BaseModel):
    merchant_id: int
    amount_rupees: float = Field(..., gt=0, description="Payment amount in Rupees")
    idempotency_key: str = Field(..., description="Unique client-generated idempotency key")
    description: Optional[str] = None

class PaymentResponse(BaseModel):
    transaction_id: int
    reference_id: str
    idempotency_key: str
    status: str
    wallet_id: int
    merchant_id: int
    merchant_name: str
    merchant_category: str
    student_tier: str
    amount_paise: int
    amount_rupees: float
    cashback_raw_paise: int
    cashback_raw_rupees: float
    cashback_awarded_paise: int
    cashback_awarded_rupees: float
    effective_rate_percent: float
    student_balance_before_paise: int
    student_balance_after_paise: int
    student_balance_after_rupees: float
    is_idempotent_replay: bool = False
    message: str
    created_at: datetime

# --- Transaction Schemas ---
class TransactionResponse(BaseModel):
    id: int
    reference_id: str
    idempotency_key: str
    type: str
    status: str
    merchant_name: Optional[str] = None
    merchant_category: str
    student_tier: str
    amount_paise: int
    amount_rupees: float
    cashback_raw_paise: int
    cashback_awarded_paise: int
    cashback_awarded_rupees: float
    effective_rate_percent: float
    balance_before_paise: int
    balance_after_paise: int
    description: Optional[str] = None
    created_at: datetime

# --- Reconciliation Schemas ---
class CategorySummary(BaseModel):
    category: str
    transaction_count: int
    total_amount_paise: int
    total_amount_rupees: float
    total_cashback_paise: int
    total_cashback_rupees: float

class TierSummary(BaseModel):
    tier: str
    transaction_count: int
    total_amount_paise: int
    total_amount_rupees: float
    total_cashback_paise: int
    total_cashback_rupees: float

class ReconciliationReport(BaseModel):
    month_name: str
    year: int
    start_date: datetime
    end_date: datetime
    total_transactions: int
    total_volume_paise: int
    total_volume_rupees: float
    total_cashback_disbursed_paise: int
    total_cashback_disbursed_rupees: float
    total_topup_volume_paise: int
    total_topup_volume_rupees: float
    category_breakdown: List[CategorySummary]
    tier_breakdown: List[TierSummary]
    student_total_balance_paise: int
    merchant_total_balance_paise: int
    is_balanced: bool
    audit_notes: str
