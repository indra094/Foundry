from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import OrgMember, Organization, Connection

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

# GET /intelligence/dashboard
@router.get("/dashboard")
async def get_dashboard_stats(email: str, db: Session = Depends(get_db)):
    # Find organization for this user
    org = db.query(Organization).join(OrgMember).join(models.User).filter(models.User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found for this user")
        
    founder_count = db.query(OrgMember).filter(OrgMember.org_id == org.id, OrgMember.member_type == "Founder").count()
    employee_count = db.query(OrgMember).filter(OrgMember.org_id == org.id, OrgMember.member_type == "Employee").count()
    customer_count = db.query(OrgMember).filter(OrgMember.org_id == org.id, OrgMember.member_type == "Customer").count()
    
    return {
        "risk": org.risk_level,
        "burnRate": org.burn_rate,
        "runway": org.runway,
        "teamSize": f"{founder_count} Founders, {employee_count} Team",
        "customerCount": customer_count
    }

# GET /intelligence/connections
@router.get("/connections")
async def get_relevant_connections(email: str, db: Session = Depends(get_db)):
    org = db.query(Organization).join(OrgMember).join(models.User).filter(models.User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    connections = db.query(Connection).filter(Connection.org_id == org.id).all()
    return connections
