from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import get_db
from models import Employee as EmployeeModel, AIHistory as AIHistoryModel, Organization, OrgMember, User
import time

router = APIRouter(prefix="/team", tags=["Team"])

class Employee(BaseModel):
    id: str
    name: str
    type: str # Human, AI
    role: str
    status: str

    class Config:
        from_attributes = True

class EmployeeCreate(BaseModel):
    name: str
    type: str
    role: str
    status: str

# GET /team/employees
@router.get("/employees", response_model=List[Employee])
async def get_employees(email: str, db: Session = Depends(get_db)):
    org = db.query(Organization).join(OrgMember).join(User).filter(User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return db.query(EmployeeModel).filter(EmployeeModel.org_id == org.id).all()

# POST /team/employees
@router.post("/employees", response_model=Employee)
async def add_employee(email: str, employee: EmployeeCreate, db: Session = Depends(get_db)):
    org = db.query(Organization).join(OrgMember).join(User).filter(User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    new_id = f"e_{int(time.time())}"
    db_employee = EmployeeModel(
        id=new_id,
        org_id=org.id,
        name=employee.name,
        type=employee.type,
        role=employee.role,
        status=employee.status
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

# GET /team/ai-history/{ai_id}
@router.get("/ai-history/{ai_id}")
async def get_ai_history(ai_id: str, db: Session = Depends(get_db)):
    history = db.query(AIHistoryModel).filter(AIHistoryModel.employee_id == ai_id).all()
    if not history:
        raise HTTPException(status_code=404, detail="No activity history found for this AI agent")
    return history
