from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models import User as UserModel
import time

router = APIRouter(prefix="/auth", tags=["Auth"])

class User(BaseModel):
    id: str
    fullName: str
    email: str
    role: Optional[str] = "Founder"
    avatarUrl: Optional[str] = None
    class Config:
        orm_mode = True

class LoginRequest(BaseModel):
    email: str

class SignupRequest(BaseModel):
    fullName: str
    email: str

@router.post("/login", response_model=User)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if not user:
        # For demo, auto-create if not exists or return error? 
        # Requirement says "login", so usually expect error if not found.
        # But to keep it simple as per previous mock:
        raise HTTPException(status_code=404, detail="User not found")
    
    return User(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        role=user.role,
        avatarUrl=user.avatar_url
    )

@router.post("/signup", response_model=User)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(UserModel).filter(UserModel.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_user = UserModel(
        id=f"u_{int(time.time())}",
        full_name=request.fullName,
        email=request.email,
        role="Founder"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return User(
        id=new_user.id,
        fullName=new_user.full_name,
        email=new_user.email,
        role=new_user.role,
        avatarUrl=new_user.avatar_url
    )

@router.post("/google", response_model=User)
async def google_signup(db: Session = Depends(get_db)):
    # Mock Google Auth - check if mock email exists
    email = "alex@gmail.com"
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    if not user:
        user = UserModel(
            id=f"u_g_{int(time.time())}",
            full_name="Alex Google",
            email=email,
            role="Founder",
            avatar_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return User(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        role=user.role,
        avatarUrl=user.avatar_url
    )
