import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from finpay.backend.app.core.database import Base
from finpay.backend.app.core.init_db import init_db
from finpay.backend.app.services.payment_service import PaymentService
from finpay.backend.app.services.wallet_service import WalletService
from finpay.backend.app.models.models import User, Merchant, Wallet

# Use in-memory SQLite database for test isolation
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    init_db(db)
    yield db
    db.close()

def test_rahul_payment_and_cashback(test_db):
    """
    Rahul (BASIC) pays ₹100 at Canteen.
    Initial balance: ₹1,000 (100,000 paise).
    Payment: ₹100 = 10,000 paise.
    Cashback: 2% of ₹100 = ₹2 = 200 paise.
    Net deduction: 10,000 - 200 = 9,800 paise.
    Final balance: 100,000 - 9,800 = 90,200 paise = ₹902.00.
    """
    rahul = test_db.query(User).filter(User.email == "rahul@campus.edu").first()
    canteen = test_db.query(Merchant).filter(Merchant.code == "CANTEEN_01").first()
    
    payment_svc = PaymentService(test_db)
    idempotency_key = f"test_key_{uuid.uuid4().hex}"

    result = payment_svc.process_payment(
        user_id=rahul.id,
        merchant_id=canteen.id,
        amount_rupees=100.0,
        idempotency_key=idempotency_key,
        description="Lunch at canteen"
    )

    assert result["status"] == "SUCCESS"
    assert result["amount_paise"] == 10000
    assert result["cashback_raw_paise"] == 200
    assert result["cashback_awarded_paise"] == 200
    assert result["cashback_awarded_rupees"] == 2.0
    assert result["student_balance_before_paise"] == 100000
    assert result["student_balance_after_paise"] == 90200
    assert result["student_balance_after_rupees"] == 902.0
    assert result["is_idempotent_replay"] is False

    # Check merchant balance
    test_db.refresh(canteen)
    assert canteen.balance_paise == 10000

def test_idempotency_safety(test_db):
    """
    Sending the same idempotency key twice MUST return the cached transaction
    and NOT deduct funds or award cashback twice.
    """
    rahul = test_db.query(User).filter(User.email == "rahul@campus.edu").first()
    canteen = test_db.query(Merchant).filter(Merchant.code == "CANTEEN_01").first()
    
    payment_svc = PaymentService(test_db)
    idempotency_key = "idemp_exact_same_key_999"

    # First attempt
    res1 = payment_svc.process_payment(
        user_id=rahul.id,
        merchant_id=canteen.id,
        amount_rupees=50.0,
        idempotency_key=idempotency_key
    )
    balance_after_first = res1["student_balance_after_paise"]
    assert res1["is_idempotent_replay"] is False

    # Second attempt with IDENTICAL idempotency key
    res2 = payment_svc.process_payment(
        user_id=rahul.id,
        merchant_id=canteen.id,
        amount_rupees=50.0,
        idempotency_key=idempotency_key
    )
    assert res2["is_idempotent_replay"] is True
    assert res2["reference_id"] == res1["reference_id"]
    assert res2["student_balance_after_paise"] == balance_after_first

    # Ensure wallet balance was only deducted ONCE
    wallet = test_db.query(Wallet).filter(Wallet.user_id == rahul.id).first()
    assert wallet.balance_paise == balance_after_first

def test_monthly_cap_clamping(test_db):
    """
    Test scenario:
    Stationery BASIC cap is ₹20 (2,000 paise).
    If student spends ₹2,500 at Stationery (1% rate):
    Raw cashback = ₹25 = 2,500 paise.
    Permitted monthly cap = 2,000 paise.
    Awarded cashback MUST be clamped to 2,000 paise!
    Subsequent purchases in same month must receive 0 cashback.
    """
    rahul = test_db.query(User).filter(User.email == "rahul@campus.edu").first()
    stationery = test_db.query(Merchant).filter(Merchant.code == "STATIONERY_01").first()
    
    # Give rahul plenty of funds
    wallet = test_db.query(Wallet).filter(Wallet.user_id == rahul.id).first()
    wallet.balance_paise = 500000  # ₹5,000
    test_db.commit()

    payment_svc = PaymentService(test_db)

    # First transaction: ₹2,500 at 1% -> raw cashback is 2500 paise, cap is 2000 paise
    res1 = payment_svc.process_payment(
        user_id=rahul.id,
        merchant_id=stationery.id,
        amount_rupees=2500.0,
        idempotency_key=f"cap_test_1_{uuid.uuid4().hex}"
    )
    assert res1["cashback_raw_paise"] == 2500
    assert res1["cashback_awarded_paise"] == 2000  # Clamped to cap!

    # Second transaction in same month: ₹100 at 1% -> cap is saturated, should award 0 paise
    res2 = payment_svc.process_payment(
        user_id=rahul.id,
        merchant_id=stationery.id,
        amount_rupees=100.0,
        idempotency_key=f"cap_test_2_{uuid.uuid4().hex}"
    )
    assert res2["cashback_raw_paise"] == 100
    assert res2["cashback_awarded_paise"] == 0  # 0 cashback because monthly limit reached!
