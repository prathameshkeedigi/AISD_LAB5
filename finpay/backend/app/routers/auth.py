from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from finpay.backend.app.core.database import get_db
from finpay.backend.app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    oauth2_scheme
)
from finpay.backend.app.models.models import User, Wallet, Merchant
from finpay.backend.app.schemas.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenData
)

router = APIRouter(prefix="/auth", tags=["Authentication (TalentHub JWT)"])

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    hashed_pw = get_password_hash(user_in.password)
    user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed_pw,
        role=user_in.role.upper()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # If student, create wallet
    if user.role == "STUDENT":
        initial_paise = int(round((user_in.initial_balance_rupees or 1000.0) * 100))
        wallet = Wallet(
            user_id=user.id,
            balance_paise=initial_paise,
            tier=(user_in.tier or "BASIC").upper(),
            status="ACTIVE"
        )
        db.add(wallet)
        db.commit()

    return user

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue TalentHub-compatible JWT Token
    tier = user.wallet.tier if user.wallet else "BASIC"
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": user.role,
            "name": user.name,
            "tier": tier
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resp = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
    }
    if current_user.wallet:
        w = current_user.wallet
        resp["wallet"] = {
            "id": w.id,
            "balance_paise": w.balance_paise,
            "balance_rupees": w.balance_paise / 100.0,
            "tier": w.tier,
            "status": w.status
        }
    if current_user.merchant:
        m = current_user.merchant
        resp["merchant"] = {
            "id": m.id,
            "name": m.name,
            "code": m.code,
            "category": m.category,
            "balance_paise": m.balance_paise,
            "balance_rupees": m.balance_paise / 100.0
        }
    return resp

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    """List all registered users/students for quick persona switching."""
    users = db.query(User).all()
    result = []
    for u in users:
        tier = u.wallet.tier if u.wallet else "BASIC"
        balance_rupees = (u.wallet.balance_paise / 100.0) if u.wallet else 0.0
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "tier": tier,
            "balance_rupees": balance_rupees
        })
    return result
