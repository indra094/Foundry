from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import get_db
from models import Employee as EmployeeModel
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
async def get_employees(db: Session = Depends(get_db)):
    return db.query(EmployeeModel).all()

# POST /team/employees
@router.post("/employees", response_model=Employee)
async def add_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    new_id = f"e_{int(time.time())}"
    db_employee = EmployeeModel(
        id=new_id,
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
async def get_ai_history(ai_id: str):
    # Mock history for now as it's not in DB yet
    return [
        {"id": 1, "activity": "Drafted email", "time": "2h ago"},
        {"id": 2, "activity": "Analyzed transcript", "time": "4h ago"}
    ]
