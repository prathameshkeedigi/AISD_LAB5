import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FinPay - Campus Digital Wallet & Cashback System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # JWT & TalentHub Compatibility
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "finpay-talenthub-shared-super-secret-key-2026")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./finpay.db")
    
    # Currency convention: all calculations strictly in paise (1 INR = 100 paise)
    PAISE_PER_RUPEE: int = 100

settings = Settings()
