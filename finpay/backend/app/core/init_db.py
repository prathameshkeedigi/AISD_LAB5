from sqlalchemy.orm import Session
from finpay.backend.app.core.database import engine, Base, SessionLocal
from finpay.backend.app.core.security import get_password_hash
from finpay.backend.app.models.models import User, Wallet, Merchant, CashbackRule
from finpay.backend.app.services.cashback_service import BASIC_CATEGORY_RULES

def init_db(db: Session = None):
    # Create all tables
    Base.metadata.create_all(bind=engine)

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        # Seed Cashback Rules
        for category, rule_info in BASIC_CATEGORY_RULES.items():
            rule = db.query(CashbackRule).filter(CashbackRule.category == category).first()
            if not rule:
                rule = CashbackRule(
                    category=category,
                    base_rate_bps=rule_info["base_rate_bps"],
                    base_monthly_cap_paise=rule_info["base_monthly_cap_paise"],
                    description=f"Standard rule for {category}"
                )
                db.add(rule)
        db.commit()

        # Seed Users
        # 1. Rahul (BASIC student from PDF)
        rahul = db.query(User).filter(User.email == "rahul@campus.edu").first()
        if not rahul:
            rahul = User(
                name="Rahul Sharma",
                email="rahul@campus.edu",
                password_hash=get_password_hash("password123"),
                role="STUDENT"
            )
            db.add(rahul)
            db.commit()
            db.refresh(rahul)

            wallet = Wallet(
                user_id=rahul.id,
                balance_paise=100000,  # ₹1,000.00
                tier="BASIC",
                status="ACTIVE"
            )
            db.add(wallet)
            db.commit()

        # 2. Priya (PRIME student)
        priya = db.query(User).filter(User.email == "priya@campus.edu").first()
        if not priya:
            priya = User(
                name="Priya Patel",
                email="priya@campus.edu",
                password_hash=get_password_hash("password123"),
                role="STUDENT"
            )
            db.add(priya)
            db.commit()
            db.refresh(priya)

            wallet = Wallet(
                user_id=priya.id,
                balance_paise=250000,  # ₹2,500.00
                tier="PRIME",
                status="ACTIVE"
            )
            db.add(wallet)
            db.commit()

        # 3. Amit (PREMIUM student)
        amit = db.query(User).filter(User.email == "amit@campus.edu").first()
        if not amit:
            amit = User(
                name="Amit Verma",
                email="amit@campus.edu",
                password_hash=get_password_hash("password123"),
                role="STUDENT"
            )
            db.add(amit)
            db.commit()
            db.refresh(amit)

            wallet = Wallet(
                user_id=amit.id,
                balance_paise=500000,  # ₹5,000.00
                tier="PREMIUM",
                status="ACTIVE"
            )
            db.add(wallet)
            db.commit()

        # 4. Admin
        admin = db.query(User).filter(User.email == "admin@campus.edu").first()
        if not admin:
            admin = User(
                name="FinPay Auditor (Admin)",
                email="admin@campus.edu",
                password_hash=get_password_hash("adminpassword"),
                role="ADMIN"
            )
            db.add(admin)
            db.commit()

        # Seed Merchants
        merchants_data = [
            {
                "name": "Campus Canteen (Food Court)",
                "code": "CANTEEN_01",
                "category": "Canteen",
                "description": "Hot meals, snacks, beverages and cafeteria food (2.0% base cashback)"
            },
            {
                "name": "Campus Books & Stationery",
                "code": "STATIONERY_01",
                "category": "Stationery",
                "description": "Notebooks, pens, textbooks and lab supplies (1.0% base cashback)"
            },
            {
                "name": "Campus Transit & Shuttle",
                "code": "TRANS_01",
                "category": "Transport",
                "description": "Campus buses, city transit tokens and e-bike rentals (3.0% base cashback)"
            },
            {
                "name": "Main Hostel Office",
                "code": "HOSTEL_01",
                "category": "Hostel",
                "description": "Hostel amenities, laundry tokens and mess extras (0.5% base cashback)"
            },
            {
                "name": "Campus Online Portal",
                "code": "ONLINE_01",
                "category": "Online",
                "description": "Online student portal, events tickets and print orders (1.0% base cashback)"
            },
            {
                "name": "FinPay Top-Up Gateway",
                "code": "TOPUP_SYSTEM",
                "category": "Top-up",
                "description": "Official campus wallet balance reload kiosk (0% cashback)"
            }
        ]

        for m_data in merchants_data:
            existing_m = db.query(Merchant).filter(Merchant.code == m_data["code"]).first()
            if not existing_m:
                m = Merchant(
                    name=m_data["name"],
                    code=m_data["code"],
                    category=m_data["category"],
                    description=m_data["description"],
                    balance_paise=0,
                    is_active=True
                )
                db.add(m)
        db.commit()
        print("FinPay Database Initialized and Seeded Successfully.")

    finally:
        if close_session:
            db.close()

if __name__ == "__main__":
    init_db()
