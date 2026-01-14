from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from database import get_db
from models import Organization, OrgMember, ReadinessGate, Notification, User

router = APIRouter(prefix="/gates", tags=["Gates"])

# GET /gates/incorporation
@router.get("/incorporation")
async def get_incorporation_readiness(email: str, db: Session = Depends(get_db)):
    org = db.query(Organization).join(OrgMember).join(User).filter(User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    gate = db.query(ReadinessGate).filter(ReadinessGate.org_id == org.id, ReadinessGate.gate_id == "incorporation").first()
    if not gate:
        raise HTTPException(status_code=404, detail="Incorporation Readiness record not found in database")
        
    return {
        "score": gate.score,
        "issues": json.loads(gate.issues)
    }

# GET /gates/notifications
@router.get("/notifications")
async def get_notifications(email: str, db: Session = Depends(get_db)):
    org = db.query(Organization).join(OrgMember).join(User).filter(User.email == email).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    notifications = db.query(Notification).filter(Notification.org_id == org.id).all()
    return notifications
