from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models import User as UserModel, Organization as OrganizationModel, OrgMember as OrgMemberModel
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

# POST /auth/login
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
        avatarUrl=user.avatar_url
    )

# POST /auth/signup
@router.post("/signup", response_model=User)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    timestamp = time.time()
    existing = db.query(UserModel).filter(UserModel.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_user = UserModel(
        id=f"u_{int(timestamp)}",
        full_name=request.fullName,
        email=request.email,
        avatar_url=None
    )
    db.add(new_user)
    
    # Create Default Organization
    org_id = f"org_{int(timestamp)}"
    new_org = OrganizationModel(
        id=org_id,
        name=f"{request.fullName}'s Organization",
        slug=f"org-{int(timestamp)}"
    )
    db.add(new_org)
    
    # Create Org Member (Founder)
    new_member = OrgMemberModel(
        id=f"mem_{int(timestamp)}",
        user_id=new_user.id,
        org_id=new_org.id,
        member_type="Founder",
        role="CEO", # Default role
        hours_per_week=40,
        equity=100.0, # Default to 100% until split
        status="Active"
    )
    db.add(new_member)
    
    db.commit()
    db.refresh(new_user)
    
    return User(
        id=new_user.id,
        fullName=new_user.full_name,
        email=new_user.email,
        role="Founder", # Inferred from primary membership
        avatarUrl=new_user.avatar_url
    )

# POST /auth/google
@router.post("/google", response_model=User)
async def google_signup(db: Session = Depends(get_db)):
    # Mock Google Auth - check if mock email exists
    email = "alex@gmail.com"
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    if not user:
        timestamp = time.time()
        user = UserModel(
            id=f"u_g_{int(timestamp)}",
            full_name="Alex Google",
            email=email,
            avatar_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80"
        )
        db.add(user)
        
        # Default Org for Google User
        org = OrganizationModel(
            id=f"org_g_{int(timestamp)}",
            name="Alex's AI Startup",
            slug=f"org-g-{int(timestamp)}"
        )
        db.add(org)
        
        member = OrgMemberModel(
            id=f"mem_g_{int(timestamp)}",
            user_id=user.id,
            org_id=org.id,
            member_type="Founder",
            role="CTO",
            equity=100.0
        )
        db.add(member)
        
        db.commit()
        db.refresh(user)
        
    return User(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url
    )
