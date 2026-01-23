from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from sqlalchemy.orm import Session
from models import User as UserModel, OrganizationModel, AIIdeaAnalysis, OrgMember as OrgMemberModel
from datetime import date
from database import get_db
import time
import json

router = APIRouter(prefix="/auth", tags=["Auth"])

class UserSchema(BaseModel):
    id: str
    fullName: str
    email: str
    role: Optional[str] = "Founder"
    permissionLevel: Optional[str] = "ADMIN"
    avatarUrl: Optional[str] = None
    current_org_id: Optional[str] = None
    authority: Optional[str] = None
    commitment: Optional[int] = None
    startDate: Optional[str] = None
    plannedChange: Optional[str] = None
    salary: Optional[float] = None
    bonus: Optional[str] = None
    equity: Optional[float] = None
    vesting: Optional[str] = None
    lastUpdated: Optional[str] = None
    status: Optional[str] = None
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


class UserOrgInfo(BaseModel):
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

class CreateUserRequest(BaseModel):
    fullName: str
    email: str
    geography: Optional[str] = None
    org_id: Optional[str] = None
    status: str

class SetUserOrgInfoRequest(BaseModel):
    user_id: str
    org_id: str
    role: Optional[str] = None
    permission_level: Optional[str] = None
    equity: Optional[float] = None
    vesting: Optional[str] = None
    commitment: Optional[int] = None

class SetOnboardingRequest(BaseModel):
    step: int

class MarketSchema(BaseModel):
    tam_value: int
    growth_rate_percent: int
    growth_index: int
    insight: str

class PersonaSchema(BaseModel):
    name: str
    pain: str
    solution: str

class MilestoneSchema(BaseModel):
    label: str
    duration_days: int
    is_active: bool

class RoadmapSchema(BaseModel):
    recommended_stage: str
    min_capital: int
    max_capital: int
    milestones: List[MilestoneSchema]

class AnalysisPayload(BaseModel):
    seed_funding_probability: int
    market: MarketSchema
    strengths: List[str]
    weaknesses: List[str]
    investor_verdict: str
    personas: List[PersonaSchema]
    roadmap: RoadmapSchema


# POST /auth/login
@router.post("/login", response_model=UserSchema)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    print(f"Login request received for email: {request.email}")
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        current_org_id=user.current_org_id
    )

# POST /auth/user
@router.post("/user", response_model=UserSchema)
async def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    # 1. Validate duplicate email
    existing_user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Create user id
    timestamp = int(time.time())
    user_id = f"u_{request.org_id}_{timestamp}"

    print(f"[create_user] setting current_org_id = {request.org_id}")

    # 3. Create new user
    new_user = UserModel(
        id=user_id,
        full_name=request.fullName,
        email=request.email,
        avatar_url=None,
        current_org_id=request.org_id,
        status=request.status
    )

    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")

    # 4. Return response
    return UserSchema(
        id=new_user.id,
        fullName=new_user.full_name,
        email=new_user.email,
        role="Founder",
        avatarUrl=new_user.avatar_url,
        current_org_id=new_user.current_org_id,
        status=new_user.status
    )


# POST /auth/signup
@router.post("/signup", response_model=UserSchema)
async def signup(request: CreateUserRequest, db: Session = Depends(get_db)):
    timestamp = int(time.time())
    print(f"Signup request received for email: {request.email}")

    existing_user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    print("[signup] setting current_org_id = None")

    user_id = f"u_{timestamp}"
    new_user = UserModel(
        id=user_id,
        full_name=request.fullName,
        email=request.email,
        avatar_url=None,
        current_org_id=None,
        status=request.status
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
        status=new_user.status
    )

# POST /auth/workspace
@router.post("/workspace", response_model=Workspace)
async def create_org(data: dict, db: Session = Depends(get_db)):
    # 1. Find user
    user = db.query(UserModel).filter(UserModel.email == data.get("email")).first()
    if not user:

        raise HTTPException(status_code=404, detail="User not found")

    # 2. Create org
    timestamp = int(time.time())
    org_id = f"org_{user.id}_{timestamp}"

    new_org = OrganizationModel(
        id=org_id,
        name=data.get("name", f"Workspace {timestamp}"),
        slug=f"foundry-{timestamp}",
        onboarding_step=1
    )
    db.add(new_org)
    print(f"[create_org] setting current_org_id = {org_id}")

    # 3. Set user's current org
    user.current_org_id = org_id

    # 4. Create founder membership
    member_id = f"mem_{org_id}_{user.id}"
    new_member = OrgMemberModel(
        id=member_id,
        user_id=user.id,
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
        start_date = date.today(),
        planned_change="",
        permission_level="ADMIN",
        last_updated=date.today()
    )
    db.add(new_member)

    # 5. Commit everything
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create org")

    # 6. Return workspace
    return Workspace(
        id=new_org.id,
        name=new_org.name,
        industry=new_org.industry,
        geography=new_org.geography,
        type=new_org.type,
        stage=new_org.stage,
        problem=new_org.problem,
        solution=new_org.solution,
        customer=new_org.customer,
        onboardingStep=new_org.onboarding_step
    )


# POST /auth/set-user-org-info
@router.post("/set-user-org-info")
async def set_user_org_info(req: SetUserOrgInfoRequest, db: Session = Depends(get_db)):
    # Find the membership
    member = db.query(OrgMemberModel).filter(
        OrgMemberModel.user_id == req.user_id,
        OrgMemberModel.org_id == req.org_id
    ).first()

    if not member:
        member_id = f"mem_{req.org_id}_{req.user_id}"
        member = OrgMemberModel(
            id=member_id,
            user_id=req.user_id,
            org_id=req.org_id,
            member_type=req.role or "Founder",
            role=req.role or "Founder",
            hours_per_week=req.commitment,
            equity=req.equity or 0.0,
            salary=0.0,
            bonus="",
            vesting=req.vesting,
            responsibility="",
            authority=json.dumps([]),
            expectations=json.dumps([]),
            status=req.status,
            start_date = date.today(),
            planned_change="",
            last_updated=date.today(),
            permission_level=req.permission_level
        )
        db.add(member)

    if req.role is not None:
        member.role = req.role
        member.member_type = req.role # Update member_type too? Maybe keep simplified "Founder"/"Executive" logic separate? 
        # sticking to role for now as requested.
    
    if req.equity is not None:
        member.equity = req.equity

    member.last_updated = date.today()
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update org info")

    return {"status": "success", "message": "User info updated"}


@router.get("/user-org-info")
async def get_user_org_info(
    user_id: str,
    org_id: str,
    db: Session = Depends(get_db)
):
    member = db.query(OrgMemberModel).filter(
        OrgMemberModel.user_id == user_id,
        OrgMemberModel.org_id == org_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Organization membership not found"
        )

    #print(member)
    return {
        "user_id": member.user_id,
        "org_id": member.org_id,
        "role": member.role,
        "equity": member.equity,
        "member_type": member.member_type,
        "last_updated": member.last_updated.strftime("%Y-%m-%d") if member.last_updated else None,
        "start_date": member.start_date.strftime("%Y-%m-%d") if member.start_date else None,
        "permission_level": member.permission_level
    }

# GET /auth/{org_id}/users
@router.get("/{org_id}/users", response_model=List[UserSchema])
async def get_users_for_org(org_id: str, db: Session = Depends(get_db)):
    users = (
        db.query(UserModel, OrgMemberModel)
        .join(OrgMemberModel, OrgMemberModel.user_id == UserModel.id)
        .filter(OrgMemberModel.org_id == org_id)
        .all()
    )

    if not users:
        raise HTTPException(status_code=404, detail="No users found for this organization")

    result = []
    for u, m in users:
        result.append(
            UserSchema(
                id=u.id,
                fullName=u.full_name,
                email=u.email,
                avatarUrl=u.avatar_url,
                current_org_id=u.current_org_id,
                role=m.role,
                authority=m.authority,
                commitment=m.hours_per_week,
                equity=m.equity,
                vesting=m.vesting,
                status=m.status,
                permission_level=m.permission_level,
                startDate=m.start_date.strftime("%Y-%m-%d") if m.start_date else None,
                lastUpdated=m.last_updated.strftime("%Y-%m-%d") if m.last_updated else None,
            )
        )
        

    return result

# GET /auth/{org_id}/set-onboarding
@router.post("/{org_id}/set-onboarding", response_model=Workspace)
def set_onboarding(org_id: str, req: SetOnboardingRequest, db: Session = Depends(get_db)):
    org = db.query(OrganizationModel).filter(OrganizationModel.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Workspace not found")

    org.onboarding_step = max(org.onboarding_step or 1, req.step)
    db.commit()
    db.refresh(org)
    return org

# GET /auth/workspace/{org_id}
@router.get("/workspace/{org_id}", response_model=Workspace)
async def get_workspace_by_id(org_id: str, db: Session = Depends(get_db)):
    org = db.query(OrganizationModel).filter(
        OrganizationModel.id == org_id
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


# GET /auth/workspace
@router.get("/workspace", response_model=Workspace)
async def get_workspace(email: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user or not user.current_org_id:
        raise HTTPException(status_code=404, detail="Active workspace not found")

    org = db.query(OrganizationModel).filter(
        OrganizationModel.id == user.current_org_id
    ).first()
    print(f"[get_workspace] using current_org_id = {user.current_org_id}")


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

# PATCH /auth/{org_id}/workspace-and-insights
@router.patch("/{org_id}/workspace-and-insights", response_model=Workspace)
async def update_workspace_and_insights(org_id: str, data: dict, db: Session = Depends(get_db)):
    await update_workspace_service(org_id, data, db)

    if "analysis" in data:
        payload = AnalysisPayload(**data["analysis"])
        await upsert_analysis(org_id, payload, db)

    return await get_workspace_by_id(org_id, db)

async def update_workspace_service(org_id: str, data: dict, db: Session):
    org = db.query(OrganizationModel).filter(
        OrganizationModel.id == org_id
    ).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if "name" in data: org.name = data["name"]
    if "industry" in data: org.industry = data["industry"]
    if "geography" in data: org.geography = data["geography"]
    if "type" in data: org.type = data["type"]
    if "stage" in data: org.stage = data["stage"]
    if "onboardingStep" in data: org.onboarding_step = data["onboardingStep"]
    if "problem" in data: org.problem = data["problem"]
    if "solution" in data: org.solution = data["solution"]
    if "customer" in data: org.customer = data["customer"]

    db.commit()
    db.refresh(org)
    return org


# PATCH /auth/{org_id}/workspace
@router.patch("/{org_id}/workspace", response_model=Workspace)
async def update_workspace(org_id: str, data: dict, db: Session = Depends(get_db)):
    org = await update_workspace_service(org_id, data, db)
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


# GET /auth/UserOrgInfo
@router.get("/auth/UserOrgInfo", response_model=UserOrgInfo)
async def get_my_role(email: str, db: Session = Depends(get_db)):
    return UserOrgInfo(
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

    return UserOrgInfo(
        title=member.role or "Founder",
        responsibility=member.responsibility or "",
        authority=json.loads(member.authority or "[]"),
        commitment=member.hours_per_week,
        startDate=member.start_date.strftime("%Y-%m-%d") if member.start_date else None,
        plannedChange=member.planned_change or "",
        salary=member.salary or 0.0,
        bonus=member.bonus or "",
        equity=member.equity or 0.0,
        vesting=member.vesting or "",
        expectations=json.loads(member.expectations or "[]"),
        lastUpdated=member.last_updated.strftime("%Y-%m-%d") if member.last_updated else None,
        status=member.status
    )

# PATCH /auth/UserOrgInfo
@router.patch("/auth/UserOrgInfo", response_model=UserOrgInfo)
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
    if "plannedChange" in data: member.planned_change = data["plannedChange"]
    if "salary" in data: member.salary = data["salary"]
    if "bonus" in data: member.bonus = data["bonus"]
    if "equity" in data: member.equity = data["equity"]
    if "vesting" in data: member.vesting = data["vesting"]
    if "expectations" in data: member.expectations = json.dumps(data["expectations"])
    if "status" in data: member.status = data["status"]

    member.last_updated = date.today()
    db.commit()

    return UserOrgInfo(
        title=member.role,
        responsibility=member.responsibility,
        authority=json.loads(member.authority),
        commitment=member.hours_per_week,
        startDate=member.start_date.strftime("%Y-%m-%d") if member.start_date else None,
        plannedChange=member.planned_change,
        salary=member.salary,
        bonus=member.bonus,
        equity=member.equity,
        vesting=member.vesting,
        expectations=json.loads(member.expectations),
        lastUpdated=member.last_updated.strftime("%Y-%m-%d") if member.last_updated else None,
        status=member.status
    )


# GET /auth/user-by-email/{email}
@router.get("/user-by-email/{email}", response_model=UserSchema)
async def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.commit()
    db.refresh(user)
    
    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        current_org_id=user.current_org_id
    )

# PATCH /auth/user
@router.patch("/user", response_model=UserSchema)
async def update_user(email: str, data: dict, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "fullName" in data: user.full_name = data["fullName"]
    if "avatarUrl" in data: user.avatar_url = data["avatarUrl"]
    if "current_org_id" in data: user.current_org_id = data["current_org_id"]  # 🔥 Allow switching orgs
    
    db.commit()
    db.refresh(user)
    print(f"[update_user] setting current_org_id = {data['current_org_id']}")

    
    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        role="Founder",
        current_org_id=user.current_org_id
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
        current_org_id=user.current_org_id
    )

async def upsert_analysis(
    org_id: str,
    payload: AnalysisPayload | None,
    db: Session = Depends(get_db)
):
    if payload is None:
        return {"status": "ok", "org_id": org_id, "message": "No payload provided. No changes made."}

    try:
        analysis = db.query(AIIdeaAnalysis).filter_by(workspace_id=org_id).first()

        if not analysis:
            analysis = AIIdeaAnalysis(workspace_id=org_id)
            db.add(analysis)

        # Only update fields that are provided in the payload
        if payload.seed_funding_probability is not None:
            analysis.seed_funding_probability = payload.seed_funding_probability

        if payload.market is not None:
            analysis.market = payload.market.dict()

        if payload.investor_verdict is not None:
            analysis.investor = {"verdict_text": payload.investor_verdict}

        if payload.strengths is not None:
            analysis.strengths = payload.strengths

        if payload.weaknesses is not None:
            analysis.weaknesses = payload.weaknesses

        if payload.personas is not None:
            analysis.personas = [p.dict() for p in payload.personas]

        if payload.roadmap is not None:
            analysis.roadmap = payload.roadmap.dict()

        db.commit()
        return {"status": "ok", "org_id": org_id}

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while saving analysis."
        )

# GET /auth/{org_id}/idea-analysis
@router.get("/{org_id}/idea-analysis")
def get_analysis(
    org_id: str,
    db: Session = Depends(get_db)
):
    analysis = db.query(AIIdeaAnalysis).filter_by(workspace_id=org_id).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    market = analysis.market or None
    investor = analysis.investor or None
    strengths = analysis.strengths or []
    weaknesses = analysis.weaknesses or []
    personas = analysis.personas or []
    roadmap = analysis.roadmap or None

    return {
        "org_id": org_id,
        "seed_funding_probability": analysis.seed_funding_probability,

        "market": market and {
            "tam_value": market.get("tam_value"),
            "growth_rate_percent": market.get("growth_rate_percent"),
            "growth_index": market.get("growth_index"),
            "insight": market.get("insight"),
        },

        "investor_verdict": investor.get("verdict_text") if investor else None,

        "strengths": [s for s in strengths],
        "weaknesses": [w for w in weaknesses],

        "personas": [
            {
                "name": p.get("name"),
                "pain": p.get("pain"),
                "solution": p.get("solution")
            }
            for p in personas
        ],

        "roadmap": roadmap and {
            "recommended_stage": roadmap.get("recommended_stage"),
            "min_capital": roadmap.get("min_capital"),
            "max_capital": roadmap.get("max_capital"),
            "milestones": [
                {
                    "label": m.get("label"),
                    "duration_days": m.get("duration_days"),
                    "is_active": bool(m.get("is_active"))
                }
                for m in (roadmap.get("milestones") or [])
            ]
        }
    }
