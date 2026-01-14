from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import get_db
from models import OrgMember as FounderModel, Organization, User
import time

router = APIRouter(prefix="/founders", tags=["Founders"])

class Founder(BaseModel):
    id: str
    name: str
    role: str
    hoursPerWeek: int
    equity: float
    cashContribution: float
    riskTolerance: str
    vestingCliff: int
    status: str
    class Config:
        from_attributes = True

class FounderCreate(BaseModel):
    name: str
    role: str
    hoursPerWeek: int
    equity: float
    cashContribution: float
    riskTolerance: str
    vestingCliff: int

# GET /founders/
@router.get("/", response_model=List[Founder])
async def get_founders(email: str, db: Session = Depends(get_db)):
    org = db.query(Organization).join(FounderModel).join(User).filter(User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    founders = db.query(FounderModel).filter(
        FounderModel.org_id == org.id,
        FounderModel.member_type == "Founder"
    ).all()
    
    return [
        Founder(
            id=f.id,
            name=db.query(User).filter(User.id == f.user_id).first().full_name if f.user_id else "Unassigned",
            role=f.role,
            hoursPerWeek=f.hours_per_week,
            equity=f.equity,
            cashContribution=f.cash_contribution,
            riskTolerance=f.risk_tolerance,
            vestingCliff=f.vesting_cliff,
            status=f.status
        ) for f in founders
    ]

# GET /founders/{founder_id}
@router.get("/{founder_id}", response_model=Founder)
async def get_founder(founder_id: str, db: Session = Depends(get_db)):
    f = db.query(FounderModel).filter(FounderModel.id == founder_id, FounderModel.member_type == "Founder").first()
    if not f:
        raise HTTPException(status_code=404, detail="Founder not found")
    
    u = db.query(User).filter(User.id == f.user_id).first()
    
    return Founder(
        id=f.id,
        name=u.full_name if u else "Unassigned",
        role=f.role,
        hoursPerWeek=f.hours_per_week,
        equity=f.equity,
        cashContribution=f.cash_contribution,
        riskTolerance=f.risk_tolerance,
        vestingCliff=f.vesting_cliff,
        status=f.status
    )

# POST /founders/
@router.post("/", response_model=Founder)
async def add_founder(email: str, founder: FounderCreate, db: Session = Depends(get_db)):
    org = db.query(Organization).join(FounderModel).join(User).filter(User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    new_id = f"f_{int(time.time())}"
    new_founder = FounderModel(
        id=new_id,
        org_id=org.id,
        role=founder.role,
        hours_per_week=founder.hoursPerWeek,
        equity=founder.equity,
        cash_contribution=founder.cashContribution,
        risk_tolerance=founder.riskTolerance,
        vesting_cliff=founder.vestingCliff,
        status="Incomplete",
        member_type="Founder"
    )
    db.add(new_founder)
    db.commit()
    db.refresh(new_founder)
    return Founder(
        id=new_founder.id,
        name=founder.name, # No user linked yet for new founder added this way
        role=new_founder.role,
        hoursPerWeek=new_founder.hours_per_week,
        equity=new_founder.equity,
        cashContribution=new_founder.cash_contribution,
        riskTolerance=new_founder.risk_tolerance,
        vestingCliff=new_founder.vesting_cliff,
        status=new_founder.status
    )

# PUT /founders/{founder_id}
@router.put("/{founder_id}", response_model=Founder)
async def update_founder(founder_id: str, updates: dict, db: Session = Depends(get_db)):
    f = db.query(FounderModel).filter(FounderModel.id == founder_id, FounderModel.member_type == "Founder").first()
    if not f:
        raise HTTPException(status_code=404, detail="Founder not found")
    
    if 'hoursPerWeek' in updates: f.hours_per_week = updates['hoursPerWeek']
    if 'cashContribution' in updates: f.cash_contribution = updates['cashContribution']
    if 'vestingCliff' in updates: f.vesting_cliff = updates['vestingCliff']
    if 'riskTolerance' in updates: f.risk_tolerance = updates['riskTolerance']
    if 'role' in updates: f.role = updates['role']
    if 'equity' in updates: f.equity = updates['equity']
    if 'status' in updates: f.status = updates['status']

    db.commit()
    db.refresh(f)
    
    u = db.query(User).filter(User.id == f.user_id).first() if f.user_id else None
    
    return Founder(
        id=f.id,
        name=u.full_name if u else "Unassigned",
        role=f.role,
        hoursPerWeek=f.hours_per_week,
        equity=f.equity,
        cashContribution=f.cash_contribution,
        riskTolerance=f.risk_tolerance,
        vestingCliff=f.vesting_cliff,
        status=f.status
    )
