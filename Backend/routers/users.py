from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database import get_db
from models import User as UserModel, OrgMember as OrgMemberModel, upsert_job
from pydantic_types import UserSchema, UserOrgInfo, SetUserOrgInfoRequest
from typing import List
import time
import secrets
import string
import json
from datetime import date
from passlib.context import CryptContext

router = APIRouter(prefix="/api/v1", tags=["Users"])

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# POST /api/v1/user
@router.post("/user", response_model=UserSchema)
async def create_user(request: dict, db: Session = Depends(get_db)):
    # 1. Validate duplicate email
    existing_user = db.query(UserModel).filter(UserModel.email == request.get("email")).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    print("[create_user] not existing user:", request.get("email"))
    # 2. Create user id
    timestamp = int(time.time())
    user_id = f"u_{request.get('org_id')}_{timestamp}"

    # Get password from request or generate a random one
    password_plain = request.get("password")
    if not password_plain:
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password_plain = ''.join(secrets.choice(alphabet) for _ in range(12))
    password_hash = hash_password(password_plain)

    # 3. Create new user
    new_user = UserModel(
        id=user_id,
        full_name=request.get("fullName"),
        email=request.get("email"),
        avatar_url=None,
        current_org_id=request.get("org_id"),
        status=request.get("status"),
        password_hash=password_hash,
        industry_experience=request.get("industry_experience", 0)
    )


    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)
    except SQLAlchemyError as e:
        db.rollback()
        print(f"[create_user] failed to create user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    upsert_job(db, request.get("org_id"), "founder_alignment")
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


# POST /api/v1/set-user-org-info
@router.post("/set-user-org-info")
async def set_user_org_info(req: dict, db: Session = Depends(get_db)):
    # Find the membership
    member = db.query(OrgMemberModel).filter(
        OrgMemberModel.user_id == req.get("user_id"),
        OrgMemberModel.org_id == req.get("org_id")
    ).first()


    if not member:
        member_id = f"mem_{req.get('org_id')}_{req.get('user_id')}"
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

    upsert_job(db, req.get("org_id"), "founder_alignment")
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

# GET /api/v1/{org_id}/users
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


# GET /api/v1/UserOrgInfo
@router.get("/UserOrgInfo", response_model=UserOrgInfo)
async def get_my_role(email: str, db: Session = Depends(get_db)):
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

# PATCH /api/v1/UserOrgInfo
@router.patch("/UserOrgInfo", response_model=UserOrgInfo)
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

# DELETE /api/v1/org/{org_id}/user-by-email/{email}
@router.delete("/org/{org_id}/user-by-email/{email}")
async def delete_user_from_org_by_email(org_id: str, email: str, db: Session = Depends(get_db)):
    # Find the user by email
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find the membership
    member = db.query(OrgMemberModel).filter(
        OrgMemberModel.user_id == user.id,
        OrgMemberModel.org_id == org_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="User is not a member of this organization")

    try:
        # Delete the membership
        db.delete(member)

        # Optional: clear current_org_id if it matches
        if user.current_org_id == org_id:
            user.current_org_id = None
            db.add(user)

        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user from org: {str(e)}")
    upsert_job(db, org_id, "founder_alignment")
    return {"status": "success", "message": f"User {email} removed from organization {org_id}"}



# GET /api/v1/user-by-email/{email}
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

# PATCH /api/v1/user
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
    print(f"[update_user] setting current_org_id = {data.get('current_org_id')}")

    
    return UserSchema(
        id=user.id,
        fullName=user.full_name,
        email=user.email,
        avatarUrl=user.avatar_url,
        role="Founder",
        current_org_id=user.current_org_id,
        industry_experience=user.industry_experience
    )
