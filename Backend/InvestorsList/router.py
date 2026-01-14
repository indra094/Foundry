from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import get_db
from models import Investor as InvestorModel
import time

router = APIRouter(prefix="/investors", tags=["Investors"])

class Investor(BaseModel):
    id: str
    name: str
    type: str
    stage: str
    status: str
    notes: Optional[str] = ""

    class Config:
        from_attributes = True

class InvestorCreate(BaseModel):
    name: str
    type: str
    stage: str
    status: str
    notes: Optional[str] = ""

# GET /investors/
@router.get("/", response_model=List[Investor])
async def get_investors(db: Session = Depends(get_db)):
    return db.query(InvestorModel).all()

# GET /investors/{id}
@router.get("/{id}", response_model=Investor)
async def get_investor(id: str, db: Session = Depends(get_db)):
    investor = db.query(InvestorModel).filter(InvestorModel.id == id).first()
    if not investor:
        raise HTTPException(status_code=404, detail="Investor not found")
    return investor

# POST /investors/
@router.post("/", response_model=Investor)
async def add_investor(investor: InvestorCreate, db: Session = Depends(get_db)):
    new_id = f"inv_{int(time.time())}"
    db_investor = InvestorModel(
        id=new_id,
        name=investor.name,
        type=investor.type,
        stage=investor.stage,
        status=investor.status,
        notes=investor.notes
    )
    db.add(db_investor)
    db.commit()
    db.refresh(db_investor)
    return db_investor

# PUT /investors/{id}
@router.put("/{id}", response_model=Investor)
async def update_investor(id: str, updates: dict, db: Session = Depends(get_db)):
    db_investor = db.query(InvestorModel).filter(InvestorModel.id == id).first()
    if not db_investor:
        raise HTTPException(status_code=404, detail="Investor not found")
    
    for key, value in updates.items():
        if hasattr(db_investor, key):
            setattr(db_investor, key, value)
            
    db.commit()
    db.refresh(db_investor)
    return db_investor
