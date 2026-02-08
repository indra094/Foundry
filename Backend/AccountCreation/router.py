from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from sqlalchemy.orm import Session
from models import User as UserModel, FounderAlignmentModel, DashboardModel, InvestorReadiness, OrganizationModel, AIIdeaAnalysis, OrgMember as OrgMemberModel, FinancialsModel
from pydantic_types import UserSchema, Workspace, UserOrgInfo, LoginRequest, CreateUserRequest, SetUserOrgInfoRequest, SetOnboardingRequest, MarketSchema, PersonaSchema, MilestoneSchema, RoadmapSchema, AnalysisPayload, FounderAlignmentResponse, FounderAlignmentResponseModel, FinancialsSchema
from typing import Any, Dict
from datetime import date
from database import get_db
import time
import json
from fastapi import BackgroundTasks
from queue import Queue
from workers import founder_alignment_queue, idea_analysis_queue, dashboard_queue, investor_readiness_queue
from passlib.context import CryptContext

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

# POST /auth/user
@router.post("/user", response_model=UserSchema)
async def create_user(request: dict, db: Session = Depends(get_db)):
    # 1. Validate duplicate email
    existing_user = db.query(UserModel).filter(UserModel.email == request.get("email")).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Create user id
    timestamp = int(time.time())
    user_id = f"u_{request.get("org_id")}_{timestamp}"

    print(f"[create_user] setting current_org_id = {request.get("org_id")}")

    # 3. Create new user
    new_user = UserModel(
        id=user_id,
        full_name=request.get("fullName"),
        email=request.get("email"),
        avatar_url=None,
        current_org_id=request.get("org_id"),
        status=request.get("status"),
        industry_experience=request.get("industry_experience")
    )

    founder_alignment_queue.put({"org_id":request.get("org_id")})

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
        status=new_user.status,
        industry_experience=new_user.industry_experience
    )


# POST /auth/signup
@router.post("/signup", response_model=UserSchema)
async def signup(request: dict, db: Session = Depends(get_db)):
    timestamp = int(time.time())
    print(f"Signup request received for email: {request.get("email")}")

    existing_user = db.query(UserModel).filter(UserModel.email == request.get("email")).first()
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
        bonus=0.0,
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
    except Exception as e:
        db.rollback()
        print("Failed to commit org creation:", e)
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
        onboarding_step=new_org.onboarding_step
    )


# POST /auth/set-user-org-info
@router.post("/set-user-org-info")
async def set_user_org_info(req: dict, db: Session = Depends(get_db)):
    # Find the membership
    member = db.query(OrgMemberModel).filter(
        OrgMemberModel.user_id == req.get("user_id"),
        OrgMemberModel.org_id == req.get("org_id")
    ).first()


    if not member:
        member_id = f"mem_{req.get("org_id")}_{req.get("user_id")}"
        member = OrgMemberModel(
            id=member_id,
            user_id=req.get("user_id"),
            org_id=req.get("org_id"),
            member_type=req.get("role") or "Founder",
            role=req.get("role") or "Founder",
            hours_per_week=req.get("commitment"),
            equity=req.get("equity") or 0.0,
            salary=req.get("salary") or 0.0,
            bonus=req.get("bonus") or 0.0,
            vesting=req.get("vesting"),
            responsibility="",
            authority=json.dumps([]),
            expectations=json.dumps([]),
            status=req.get("status"),
            start_date = date.today(),
            planned_change="",
            last_updated=date.today(),
            permission_level=req.get("permission_level")
        )
        db.add(member)

    if req.get("role") is not None:
        member.role = req.get("role")
        member.member_type = req.get("role")

    if req.get("commitment") is not None:
        member.hours_per_week = req.get("commitment")

    if req.get("equity") is not None:
        member.equity = req.get("equity")

    if req.get("salary") is not None:
        member.salary = req.get("salary")

    if req.get("bonus") is not None:
        member.bonus = req.get("bonus")

    if req.get("vesting") is not None:
        member.vesting = req.get("vesting")

    if req.get("permission_level") is not None:
        member.permission_level = req.get("permission_level")

    if req.get("status") is not None:
        member.status = req.get("status")

    member.last_updated = date.today()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update org info")

    founder_alignment_queue.put({"org_id":req.get("org_id")})
    return {"status": "success", "message": "User info updated"}


@router.get("/user-org-info")
async def get_user_org_info(
    user_id: str,
    org_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
        "industry_experience": user.industry_experience,
        "org_id": member.org_id,
        "role": member.role,
        "equity": member.equity,
        "salary": member.salary,
        "bonus": member.bonus,
        "vesting": member.vesting,
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
        print(u.full_name)
        print (m.hours_per_week)
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
                salary=m.salary,
                bonus=m.bonus,
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
    print(req.step)
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
        onboarding_step=org.onboarding_step
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
        onboarding_step=org.onboarding_step
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
            onboarding_step=org.onboarding_step
        ) for org in orgs
    ]

# PATCH /auth/{org_id}/workspace-and-insights
@router.patch("/{org_id}/workspace-and-insights", response_model=Workspace)
async def update_workspace_and_insights(org_id: str, data: dict, db: Session = Depends(get_db)):
    await update_workspace_service(org_id, data, db)

    idea_analysis_queue.put({"org_id":org_id})

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
    if "onboarding_step" in data: org.onboarding_step = data["onboarding_step"]
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
    idea_analysis_queue.put({"org_id":org_id})
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
        onboarding_step=org.onboarding_step
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
        current_org_id=user.current_org_id,
        industry_experience=user.industry_experience
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
    if "industry_experience" in data: user.industry_experience = data["industry_experience"]
    
    db.commit()
    db.refresh(user)
    print(f"[update_user] setting current_org_id = {data['current_org_id']}")

    
    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        role="Founder",
        current_org_id=user.current_org_id,
        industry_experience=user.industry_experience
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
    analysis = db.query(AIIdeaAnalysis).filter_by(workspace_id=org_id).order_by(AIIdeaAnalysis.generated_at.desc()).first()

    size = idea_analysis_queue.qsize()

    return {
        "analysis": analysis,
        "size": size
    }

@router.post("/{org_id}/idea-analysis", status_code=200)
async def create_or_update_analysis(org_id: str, background_tasks: BackgroundTasks):
    
    idea_analysis_queue.put({"org_id":org_id})
    #print("post analysis")

    return {"status": "ok"}


@router.get("/{org_id}/founder-alignment", response_model=FounderAlignmentResponseModel)
async def get_alignment(org_id: str, db: Session = Depends(get_db)):
    alignment = (
        db.query(FounderAlignmentModel)
        .filter(FounderAlignmentModel.org_id == org_id)
        .order_by(FounderAlignmentModel.generated_at.desc())
        .first()
    )

    size = founder_alignment_queue.qsize()

    return {
        "alignment": alignment,
        "size": size
    }


@router.post("/{org_id}/founder-alignment", status_code=200)
async def create_or_update_alignment(org_id: str, background_tasks: BackgroundTasks):
    
    founder_alignment_queue.put({"org_id":org_id})
    #print("post alignment")

    return {"status": "ok"}


import datetime

@router.get("/{org_id}/financials", response_model=FinancialsSchema)
def get_financials(org_id: str, db: Session = Depends(get_db)):
    fin = db.query(FinancialsModel).filter(FinancialsModel.org_id == org_id).first()
    if not fin:
        return FinancialsSchema(org_id=org_id)
    
    return FinancialsSchema(
        org_id=fin.org_id,
        monthly_revenue=fin.monthly_revenue,
        revenue_trend=fin.revenue_trend,
        revenue_stage=fin.revenue_stage,
        cash_in_bank=fin.cash_in_bank,
        monthly_burn=fin.monthly_burn,
        cost_structure=fin.cost_structure,
        pricing_model=fin.pricing_model,
        price_per_customer=fin.price_per_customer,
        customers_in_pipeline=fin.customers_in_pipeline,
        data_confidence=fin.data_confidence,
        last_updated=fin.last_updated
    )

@router.put("/{org_id}/financials", response_model=FinancialsSchema)
def update_financials(org_id: str, data: FinancialsSchema, db: Session = Depends(get_db)):
    fin = db.query(FinancialsModel).filter(FinancialsModel.org_id == org_id).first()
    if not fin:
        fin = FinancialsModel(org_id=org_id)
        db.add(fin)
    
    fin.monthly_revenue = data.monthly_revenue
    fin.revenue_trend = data.revenue_trend
    fin.revenue_stage = data.revenue_stage
    fin.cash_in_bank = data.cash_in_bank
    fin.monthly_burn = data.monthly_burn
    fin.cost_structure = data.cost_structure
    fin.pricing_model = data.pricing_model
    fin.price_per_customer = data.price_per_customer
    fin.customers_in_pipeline = data.customers_in_pipeline
    fin.data_confidence = data.data_confidence
    fin.last_updated = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(fin)
    investor_readiness_queue.put({"org_id":org_id})
    
    return FinancialsSchema(
        org_id=fin.org_id,
        monthly_revenue=fin.monthly_revenue,
        revenue_trend=fin.revenue_trend,
        revenue_stage=fin.revenue_stage,
        cash_in_bank=fin.cash_in_bank,
        monthly_burn=fin.monthly_burn,
        cost_structure=fin.cost_structure,
        pricing_model=fin.pricing_model,
        price_per_customer=fin.price_per_customer,
        customers_in_pipeline=fin.customers_in_pipeline,
        data_confidence=fin.data_confidence,
        last_updated=fin.last_updated
    )

# GET /auth/{org_id}/investor-readiness
@router.get("/{org_id}/investor-readiness")
def get_investor_readiness(
    org_id: str,
    db: Session = Depends(get_db)
):
    investor_readiness = db.query(InvestorReadiness).filter_by(id=org_id).order_by(InvestorReadiness.last_updated.desc()).first()

    size = investor_readiness_queue.qsize()

    return {
        "investor_readiness": investor_readiness,
        "size": size
    }

@router.post("/{org_id}/investor-readiness", status_code=200)
async def create_or_update_investor_readiness(org_id: str, background_tasks: BackgroundTasks):
    
    investor_readiness_queue.put({"org_id":org_id})

    return {"status": "ok"}


# GET /auth/{org_id}/dashboard
@router.get("/{org_id}/dashboard")
def get_dashboard(
    org_id: str,
    db: Session = Depends(get_db)
):
    dashboard = db.query(DashboardModel).filter_by(id=org_id).order_by(DashboardModel.last_computed_at.desc()).first()

    size = dashboard_queue.qsize()
    return {
        "dashboard": dashboard,
        "size": size
    }

@router.post("/{org_id}/dashboard", status_code=200)
async def create_or_update_dashboard(org_id: str, background_tasks: BackgroundTasks):
    
    dashboard_queue.put({"org_id":org_id})

    return {"status": "ok"}

