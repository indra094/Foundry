from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from database import get_db
from models import User as UserModel, Organization as OrganizationModel, OrgMember as OrgMemberModel
import time
import json

router = APIRouter(prefix="/auth", tags=["Auth"])

class User(BaseModel):
    id: str
    fullName: str
    email: str
    role: Optional[str] = "Founder"
    avatarUrl: Optional[str] = None
    class Config:
        orm_mode = True

class Workspace(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    type: Optional[str] = None
    stage: Optional[str] = None
    onboardingStep: int

class MyRole(BaseModel):
    title: str
    responsibility: str
    authority: List[str]
    commitment: int
    startDate: str
    plannedChange: str
    salary: float
    bonus: str
    equity: float
    vesting: str
    expectations: List[str]
    lastUpdated: str
    status: str

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
        name=f"Foundry",
        slug=f"org-{int(timestamp)}",
        onboarding_step=6 # Default to completed for demo feel as per request
    )
    db.add(new_org)
    
    # Create Org Member (Founder)
    new_member = OrgMemberModel(
        id=f"mem_{int(timestamp)}",
        user_id=new_user.id,
        org_id=new_org.id,
        member_type="Founder",
        role="CEO",
        hours_per_week=40,
        equity=50.0,
        status="Active"
    )
    db.add(new_member)
    
    db.commit()
    db.refresh(new_user)
    
    return User(
        id=new_user.id,
        fullName=new_user.full_name,
        email=new_user.email,
        role="Founder",
        avatarUrl=new_user.avatar_url
    )

# GET /auth/workspace
@router.get("/workspace", response_model=Workspace)
async def get_workspace(email: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    member = db.query(OrgMemberModel).filter(OrgMemberModel.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Membership not found")
    
    org = db.query(OrganizationModel).filter(OrganizationModel.id == member.org_id).first()
    return Workspace(
        id=org.id,
        name=org.name,
        industry=org.industry,
        type=org.type,
        stage=org.stage,
        onboardingStep=org.onboarding_step
    )

# GET /auth/workspaces
@router.get("/workspaces", response_model=List[Workspace])
async def get_workspaces(email: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    memberships = db.query(OrgMemberModel).filter(OrgMemberModel.user_id == user.id).all()
    org_ids = [m.org_id for m in memberships]
    
    orgs = db.query(OrganizationModel).filter(OrganizationModel.id.in_(org_ids)).all()
    
    return [
        Workspace(
            id=org.id,
            name=org.name,
            industry=org.industry,
            type=org.type,
            stage=org.stage,
            onboardingStep=org.onboarding_step
        ) for org in orgs
    ]

# PATCH /auth/workspace
@router.patch("/workspace", response_model=Workspace)
async def update_workspace(email: str, data: dict, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    member = db.query(OrgMemberModel).filter(OrgMemberModel.user_id == user.id).first()
    org = db.query(OrganizationModel).filter(OrganizationModel.id == member.org_id).first()
    
    if "name" in data: org.name = data["name"]
    if "onboardingStep" in data: org.onboarding_step = data["onboardingStep"]
    if "industry" in data: org.industry = data["industry"]
    if "type" in data: org.type = data["type"]
    if "stage" in data: org.stage = data["stage"]
    
    db.commit()
    return Workspace(
        id=org.id,
        name=org.name,
        onboardingStep=org.onboarding_step,
        industry=org.industry,
        type=org.type,
        stage=org.stage
    )

# GET /auth/myrole
@router.get("/myrole", response_model=MyRole)
async def get_my_role(email: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    member = db.query(OrgMemberModel).filter(OrgMemberModel.user_id == user.id).first()
    
    return MyRole(
        title=member.role or "Founder",
        responsibility=member.responsibility or "",
        authority=json.loads(member.authority),
        commitment=member.hours_per_week,
        startDate=member.start_date or "",
        plannedChange=member.planned_change,
        salary=member.salary,
        bonus=member.bonus,
        equity=member.equity,
        vesting=member.vesting,
        expectations=json.loads(member.expectations),
        lastUpdated=member.last_updated or "",
        status=member.status
    )

# PATCH /auth/myrole
@router.patch("/myrole", response_model=MyRole)
async def update_my_role(email: str, data: dict, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    member = db.query(OrgMemberModel).filter(OrgMemberModel.user_id == user.id).first()
    
    if "title" in data: member.role = data["title"]
    if "responsibility" in data: member.responsibility = data["responsibility"]
    if "authority" in data: member.authority = json.dumps(data["authority"])
    if "commitment" in data: member.hours_per_week = data["commitment"]
    if "startDate" in data: member.start_date = data["startDate"]
    if "plannedChange" in data: member.planned_change = data["plannedChange"]
    if "salary" in data: member.salary = data["salary"]
    if "bonus" in data: member.bonus = data["bonus"]
    if "equity" in data: member.equity = data["equity"]
    if "vesting" in data: member.vesting = data["vesting"]
    if "expectations" in data: member.expectations = json.dumps(data["expectations"])
    if "status" in data: member.status = data["status"]
    
    member.last_updated = time.strftime("%Y-%m-%d")
    db.commit()
    
    return MyRole(
        title=member.role,
        responsibility=member.responsibility,
        authority=json.loads(member.authority),
        commitment=member.hours_per_week,
        startDate=member.start_date,
        plannedChange=member.planned_change,
        salary=member.salary,
        bonus=member.bonus,
        equity=member.equity,
        vesting=member.vesting,
        expectations=json.loads(member.expectations),
        lastUpdated=member.last_updated,
        status=member.status
    )

# PATCH /auth/user
@router.patch("/user", response_model=User)
async def update_user(email: str, data: dict, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "fullName" in data: user.full_name = data["fullName"]
    if "avatarUrl" in data: user.avatar_url = data["avatarUrl"]
    
    db.commit()
    db.refresh(user)
    
    return User(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        role="Founder"
    )

# POST /auth/google
@router.post("/google", response_model=User)
async def google_signup(email: str, db: Session = Depends(get_db)):
    # Enforce database check - no hardcoded fallbacks
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=404, 
            detail=f"Google Account ({email}) not found in database. Please register first or use a seeded demo account."
        )
        
    return User(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        role="Founder"
    )
