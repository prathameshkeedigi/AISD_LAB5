import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from finpay.backend.app.core.database import Base
from finpay.backend.app.core.init_db import init_db
from finpay.backend.app.services.payment_service import PaymentService
from finpay.backend.app.services.reconciliation_service import ReconciliationService
from finpay.backend.app.models.models import User, Merchant
from datetime import datetime, timezone

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    init_db(db)
    yield db
    db.close()

def test_monthly_reconciliation_accuracy(test_db):
    rahul = test_db.query(User).filter(User.email == "rahul@campus.edu").first()
    canteen = test_db.query(Merchant).filter(Merchant.code == "CANTEEN_01").first()
    stationery = test_db.query(Merchant).filter(Merchant.code == "STATIONERY_01").first()

    payment_svc = PaymentService(test_db)
    
    # Process 2 payments
    payment_svc.process_payment(
        user_id=rahul.id,
        merchant_id=canteen.id,
        amount_rupees=200.0,
        idempotency_key=f"recon_1_{uuid.uuid4().hex}"
    )

    payment_svc.process_payment(
        user_id=rahul.id,
        merchant_id=stationery.id,
        amount_rupees=100.0,
        idempotency_key=f"recon_2_{uuid.uuid4().hex}"
    )

    now = datetime.now(timezone.utc)
    recon_svc = ReconciliationService(test_db)
    report = recon_svc.generate_monthly_reconciliation(now.year, now.month)

    assert report.total_transactions == 2
    assert report.total_volume_paise == 30000  # ₹300 = 30000 paise
    assert report.total_volume_rupees == 300.0
    # Canteen: 200 * 2% = ₹4 = 400 paise
    # Stationery: 100 * 1% = ₹1 = 100 paise
    # Total cashback = 500 paise = ₹5.00
    assert report.total_cashback_disbursed_paise == 500
    assert report.total_cashback_disbursed_rupees == 5.0
    assert report.is_balanced is True
