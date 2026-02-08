from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User as UserModel, OrganizationModel, OrgMember as OrgMemberModel, upsert_job
from pydantic_types import Workspace, SetOnboardingRequest
from typing import List
import time
import json
from datetime import date

router = APIRouter(prefix="/api/v1", tags=["Workspaces"])

# POST /api/v1/workspace
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


# GET /api/v1/{org_id}/set-onboarding
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

# GET /api/v1/workspace/{org_id}
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


# GET /api/v1/workspace
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

# GET /api/v1/workspaces
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

# PATCH /api/v1/{org_id}/workspace-and-insights
@router.patch("/{org_id}/workspace-and-insights", response_model=Workspace)
async def update_workspace_and_insights(org_id: str, data: dict, db: Session = Depends(get_db)):
    await update_workspace_service(org_id, data, db)

    upsert_job(db, org_id, "idea_analysis")

    return await get_workspace_by_id(org_id, db)


# PATCH /api/v1/{org_id}/workspace
@router.patch("/{org_id}/workspace", response_model=Workspace)
async def update_workspace(org_id: str, data: dict, db: Session = Depends(get_db)):
    org = await update_workspace_service(org_id, data, db)
    upsert_job(db, org_id, "idea_analysis")
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
