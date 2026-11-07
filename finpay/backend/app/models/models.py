from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from finpay.backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="STUDENT")  # STUDENT, MERCHANT, ADMIN
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    wallet = relationship("Wallet", back_populates="user", uselist=False)
    merchant = relationship("Merchant", back_populates="user", uselist=False)

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    # Stored strictly in integer paise (1 INR = 100 paise) to prevent floating point errors
    balance_paise = Column(BigInteger, default=0, nullable=False)
    tier = Column(String(20), default="BASIC", nullable=False)  # BASIC, PRIME, PREMIUM
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, FROZEN
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet")

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    # Categories: Canteen, Stationery, Transport, Hostel, Online, Top-up
    category = Column(String(50), index=True, nullable=False)
    balance_paise = Column(BigInteger, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="merchant")
    transactions = relationship("Transaction", back_populates="merchant")

class CashbackRule(Base):
    __tablename__ = "cashback_rules"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), unique=True, index=True, nullable=False)
    # Stored as basis points (e.g. 2.0% = 200 bps, 0.5% = 50 bps)
    base_rate_bps = Column(Integer, nullable=False)
    # Stored in integer paise (e.g. ₹50 = 5000 paise)
    base_monthly_cap_paise = Column(BigInteger, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    reference_id = Column(String(64), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(128), index=True, nullable=False)
    wallet_id = Column(Integer, ForeignKey("wallets.id"), index=True, nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), index=True, nullable=False)
    
    # Financial fields strictly in integer paise
    amount_paise = Column(BigInteger, nullable=False)
    cashback_raw_paise = Column(BigInteger, default=0, nullable=False)
    cashback_awarded_paise = Column(BigInteger, default=0, nullable=False)
    effective_rate_percent = Column(Float, default=0.0, nullable=False)
    
    merchant_category = Column(String(50), index=True, nullable=False)
    student_tier = Column(String(20), nullable=False)
    status = Column(String(20), default="SUCCESS", nullable=False)  # SUCCESS, FAILED
    type = Column(String(20), default="PAYMENT", nullable=False)   # PAYMENT, TOPUP, REFUND
    description = Column(String(255), nullable=True)
    
    balance_before_paise = Column(BigInteger, nullable=False)
    balance_after_paise = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    wallet = relationship("Wallet", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    endpoint = Column(String(100), nullable=False)
    response_payload = Column(Text, nullable=False)
    status_code = Column(Integer, default=200, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
