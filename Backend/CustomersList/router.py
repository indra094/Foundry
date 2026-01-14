from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from database import get_db
from models import Customer as CustomerModel, Organization, OrgMember, User
import time

router = APIRouter(prefix="/customers", tags=["Customers"])

class Customer(BaseModel):
    id: str
    company: str
    role: str
    status: str
    signal: int
    notes: Optional[str] = ""

    class Config:
        from_attributes = True

class CustomerCreate(BaseModel):
    company: str
    role: str
    status: str
    signal: int
    notes: Optional[str] = ""

# GET /customers/
@router.get("/", response_model=List[Customer])
async def get_customers(email: str, db: Session = Depends(get_db)):
    org = db.query(Organization).join(OrgMember).join(User).filter(User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return db.query(CustomerModel).filter(CustomerModel.org_id == org.id).all()

# GET /customers/{id}
@router.get("/{id}", response_model=Customer)
async def get_customer(id: str, db: Session = Depends(get_db)):
    customer = db.query(CustomerModel).filter(CustomerModel.id == id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

# POST /customers/
@router.post("/", response_model=Customer)
async def add_customer(email: str, customer: CustomerCreate, db: Session = Depends(get_db)):
    org = db.query(Organization).join(OrgMember).join(User).filter(User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    new_id = f"cust_{int(time.time())}"
    db_customer = CustomerModel(
        id=new_id,
        org_id=org.id,
        company=customer.company,
        role=customer.role,
        status=customer.status,
        signal=customer.signal,
        notes=customer.notes
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

# PUT /customers/{id}
@router.put("/{id}", response_model=Customer)
async def update_customer(id: str, updates: dict, db: Session = Depends(get_db)):
    db_customer = db.query(CustomerModel).filter(CustomerModel.id == id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    for key, value in updates.items():
        if hasattr(db_customer, key):
            setattr(db_customer, key, value)
            
    db.commit()
    db.refresh(db_customer)
    return db_customer
