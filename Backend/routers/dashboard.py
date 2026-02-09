from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import DashboardModel, Job, upsert_job

router = APIRouter(prefix="/api/v1", tags=["Dashboard"])

# GET /api/v1/{org_id}/dashboard
@router.get("/{org_id}/dashboard")
def get_dashboard(
    org_id: str,
    db: Session = Depends(get_db)
):
    dashboard = db.query(DashboardModel).filter_by(id=org_id).order_by(DashboardModel.last_computed_at.desc()).first()

    size = db.query(Job).filter(Job.org_id == org_id, Job.type == "dashboard").count()
    
    return {
        "dashboard": dashboard,
        "size": size
    }

@router.post("/{org_id}/dashboard", status_code=200)
async def create_or_update_dashboard(org_id: str, db: Session = Depends(get_db)):
    print ("add job for dashboard")
    upsert_job(db, org_id, "dashboard")

    return {"status": "ok"}
