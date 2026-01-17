from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from database import get_db
from models import User as UserModel, OrganizationModel, OrgMember as OrgMemberModel
import time
import json

router = APIRouter(prefix="/auth", tags=["Auth"])

class UserSchema(BaseModel):
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
    geography: Optional[str] = None
    type: Optional[str] = None
    stage: Optional[str] = None

    # 🔥 ADD
    problem: Optional[str] = None
    solution: Optional[str] = None
    customer: Optional[str] = None

    onboardingStep: Optional[int] = None


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
    name: str
    geography: Optional[str] = None

# POST /auth/login
@router.post("/login", response_model=UserSchema)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url
    )

# POST /auth/signup
@router.post("/signup", response_model=UserSchema)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    timestamp = int(time.time())
    print(f"Signup request received for email: {request.email}")

    # 1. Check if user already exists
    existing_user = db.query(UserModel).filter(
        UserModel.email == request.email
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # 2. Create Organization
    org_id = f"org_{timestamp}"
    new_org = OrganizationModel(
        id=org_id,
        name=request.name,
        slug=f"foundry-{timestamp}",
        onboarding_step=1,
        industry=None,
        type=None,
        stage=None,
        geography=request.geography
    )
    db.add(new_org)

    # 3. Create User
    user_id = f"u_{timestamp}"
    new_user = UserModel(
        id=user_id,
        full_name=request.fullName,
        email=request.email,
        avatar_url=None,
        current_org_id=org_id   # 🔑 CRITICAL
    )
    db.add(new_user)

    # 4. Create Org Membership (Founder)
    member_id = f"mem_{timestamp}"
    new_member = OrgMemberModel(
        id=member_id,
        user_id=user_id,
        org_id=org_id,
        member_type="Founder",
        role="CEO",
        hours_per_week=40,
        equity=100.0,
        salary=0.0,
        bonus="",
        vesting="4y, 1y cliff",
        responsibility="Overall company leadership",
        authority=json.dumps([
            "company_direction",
            "hiring",
            "fundraising",
            "equity_decisions"
        ]),
        expectations=json.dumps([
            "full_time_commitment",
            "long_term_involvement"
        ]),
        status="Active",
        start_date=time.strftime("%Y-%m-%d"),
        planned_change="",
        last_updated=time.strftime("%Y-%m-%d")
    )
    db.add(new_member)

    # 5. Commit everything atomically
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create account"
        )

    # 6. Return user
    return UserSchema(
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
    if not user or not user.current_org_id:
        raise HTTPException(status_code=404, detail="Active workspace not found")

    org = db.query(OrganizationModel).filter(
        OrganizationModel.id == user.current_org_id
    ).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return Workspace(
        id=org.id,
        name=org.name,
        industry=org.industry,
        geography=org.geography,
        type=org.type,
        stage=org.stage,
        problem=org.problem,
        solution=org.solution,
        customer=org.customer,
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
    if not user or not user.current_org_id:
        raise HTTPException(status_code=404, detail="Active workspace not found")

    org = db.query(OrganizationModel).filter(
        OrganizationModel.id == user.current_org_id
    ).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # ✅ Existing
    if "name" in data: org.name = data["name"]
    if "industry" in data: org.industry = data["industry"]
    if "geography" in data: org.geography = data["geography"]
    if "type" in data: org.type = data["type"]
    if "stage" in data: org.stage = data["stage"]
    if "onboardingStep" in data: org.onboarding_step = data["onboardingStep"]

    # 🔥 NEW
    if "problem" in data: org.problem = data["problem"]
    if "solution" in data: org.solution = data["solution"]
    if "customer" in data: org.customer = data["customer"]

    db.commit()
    db.refresh(org)

    return Workspace(
        id=org.id,
        name=org.name,
        industry=org.industry,
        geography=org.geography,
        type=org.type,
        stage=org.stage,
        problem=org.problem,
        solution=org.solution,
        customer=org.customer,
        onboardingStep=org.onboarding_step
    )

# GET /auth/myrole
@router.get("/auth/myrole", response_model=MyRole)
async def get_my_role(email: str, db: Session = Depends(get_db)):
    return MyRole(
        title=member.role or "Founder",
        responsibility=member.responsibility or "",
        authority=json.loads(member.authority or "[]"),
        commitment=member.hours_per_week,
        startDate=member.start_date or "",
        plannedChange=member.planned_change or "",
        salary=member.salary or 0.0,
        bonus=member.bonus or "",
        equity=member.equity or 0.0,
        vesting=member.vesting or "",
        expectations=json.loads(member.expectations or "[]"),
        lastUpdated=member.last_updated or "",
        status=member.status
    )
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user or not user.current_org_id:
        raise HTTPException(status_code=404, detail="Active org not set")

    member = db.query(OrgMemberModel).filter(
        OrgMemberModel.user_id == user.id,
        OrgMemberModel.org_id == user.current_org_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Membership not found")

    return MyRole(
        title=member.role or "Founder",
        responsibility=member.responsibility or "",
        authority=json.loads(member.authority or "[]"),
        commitment=member.hours_per_week,
        startDate=member.start_date or "",
        plannedChange=member.planned_change or "",
        salary=member.salary or 0.0,
        bonus=member.bonus or "",
        equity=member.equity or 0.0,
        vesting=member.vesting or "",
        expectations=json.loads(member.expectations or "[]"),
        lastUpdated=member.last_updated or "",
        status=member.status
    )

# PATCH /auth/myrole
@router.patch("/auth/myrole", response_model=MyRole)
async def update_my_role(email: str, data: dict, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user or not user.current_org_id:
        raise HTTPException(status_code=404, detail="Active org not set")

    member = db.query(OrgMemberModel).filter(
        OrgMemberModel.user_id == user.id,
        OrgMemberModel.org_id == user.current_org_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Membership not found")

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
@router.patch("/user", response_model=UserSchema)
async def update_user(email: str, data: dict, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "fullName" in data: user.full_name = data["fullName"]
    if "avatarUrl" in data: user.avatar_url = data["avatarUrl"]
    
    db.commit()
    db.refresh(user)
    
    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        role="Founder"
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
        role="Founder"
    )
