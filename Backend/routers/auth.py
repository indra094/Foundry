from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models import User as UserModel, OrgMember as OrgMemberModel
from pydantic_types import UserSchema, LoginRequest
from passlib.context import CryptContext
import time

router = APIRouter(prefix="/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# POST /auth/login
@router.post("/login", response_model=UserSchema)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    print(f"Login request received for email: {request.email}")
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    member = db.query(OrgMemberModel).filter(
        OrgMemberModel.user_id == user.id,
        OrgMemberModel.org_id == user.current_org_id
    ).first()

    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        current_org_id=user.current_org_id,
        role=member.role if member else None,
        permission_level=member.permission_level if member else None,
        equity=member.equity if member else None,
        vesting=member.vesting if member else None,
        commitment=member.hours_per_week if member else None,
        status=member.status if member else None
    )

# POST /auth/signup
@router.post("/signup", response_model=UserSchema)
async def signup(request: dict, db: Session = Depends(get_db)):
    timestamp = int(time.time())
    print(f"Signup request received for email: {request.get('email')}")

    existing_user = db.query(UserModel).filter(UserModel.email == request.get('email')).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    print("[signup] setting current_org_id = None")

    password_plain = request.get("password")
    if not password_plain:
        raise HTTPException(status_code=400, detail="Password is required")
    password_hash = hash_password(password_plain)

    user_id = f"u_{timestamp}"
    new_user = UserModel(
        id=user_id,
        full_name=request.get("fullName"),
        email=request.get("email"),
        avatar_url=None,
        current_org_id=None,
        status=request.get("status"),
        password_hash=password_hash,
        industry_experience=request.get("industry_experience")
    )
    db.add(new_user)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create account")

    return UserSchema(
        id=new_user.id,
        fullName=new_user.full_name,
        email=new_user.email,
        role="Founder",
        avatarUrl=new_user.avatar_url,
        current_org_id=new_user.current_org_id,
        status=new_user.status,
        industry_experience=new_user.industry_experience
    )

# POST /auth/google
@router.post("/google", response_model=UserSchema)
async def google_signup(email: str, db: Session = Depends(get_db)):
    # Enforce database check - no hardcoded fallbacks
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=404, 
            detail=f"Google Account ({email}) not found in database. Please register first or use a seeded demo account."
        )
        
    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        role="Founder",
        current_org_id=user.current_org_id,
        industry_experience=user.industry_experience
    )
