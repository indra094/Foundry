from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database import get_db
from models import AIIdeaAnalysis, Job, FounderAlignmentModel, InvestorReadiness, upsert_job
from pydantic_types import AnalysisPayload, FounderAlignmentResponseModel
from typing import Optional

router = APIRouter(prefix="/api/v1", tags=["Analysis"])

async def upsert_analysis(
    org_id: str,
    payload: AnalysisPayload | None,
    db: Session = Depends(get_db)
):
    if payload is None:
        return {"status": "ok", "org_id": org_id, "message": "No payload provided. No changes made."}

    try:
        analysis = db.query(AIIdeaAnalysis).filter_by(workspace_id=org_id).first()

        if not analysis:
            analysis = AIIdeaAnalysis(workspace_id=org_id)
            db.add(analysis)

        # Only update fields that are provided in the payload
        if payload.seed_funding_probability is not None:
            analysis.seed_funding_probability = payload.seed_funding_probability

        if payload.market is not None:
            analysis.market = payload.market.dict()

        if payload.investor is not None:
            analysis.investor = {"verdict_text": payload.investor}

        if payload.strengths is not None:
            analysis.strengths = payload.strengths

        if payload.weaknesses is not None:
            analysis.weaknesses = payload.weaknesses

        if payload.personas is not None:
            analysis.personas = [p.dict() for p in payload.personas]

        if payload.roadmap is not None:
            analysis.roadmap = payload.roadmap.dict()

        db.commit()
        return {"status": "ok", "org_id": org_id}

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while saving analysis."
        )

# GET /api/v1/{org_id}/idea-analysis
@router.get("/{org_id}/idea-analysis")
def get_analysis(
    org_id: str,
    db: Session = Depends(get_db)
):
    analysis = db.query(AIIdeaAnalysis).filter_by(workspace_id=org_id).order_by(AIIdeaAnalysis.generated_at.desc()).first()

    size = db.query(Job).filter(Job.org_id == org_id, Job.type == "idea_analysis").count()

    return {
        "analysis": analysis,
        "size": size
    }

@router.post("/{org_id}/idea-analysis", status_code=200)
async def create_or_update_analysis(org_id: str, background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
    
    upsert_job(db, org_id, "idea_analysis")
    #print("post analysis")

    return {"status": "ok"}


@router.get("/{org_id}/founder-alignment", response_model=FounderAlignmentResponseModel)
async def get_alignment(org_id: str, db: Session = Depends(get_db)):
    alignment = (
        db.query(FounderAlignmentModel)
        .filter(FounderAlignmentModel.org_id == org_id)
        .order_by(FounderAlignmentModel.generated_at.desc())
        .first()
    )

    size = db.query(Job).filter(Job.org_id == org_id, Job.type == "founder_alignment").count()

    return {
        "alignment": alignment,
        "size": size
    }


@router.post("/{org_id}/founder-alignment", status_code=200)
async def create_or_update_alignment(org_id: str, background_tasks: BackgroundTasks,db: Session = Depends(get_db)):
    
    upsert_job(db, org_id, "founder_alignment")
    #print("post alignment")

    return {"status": "ok"}


# GET /api/v1/{org_id}/investor-readiness
@router.get("/{org_id}/investor-readiness")
def get_investor_readiness(
    org_id: str,
    db: Session = Depends(get_db)
):
    investor_readiness = db.query(InvestorReadiness).filter_by(id=org_id).order_by(InvestorReadiness.last_updated.desc()).first()

    size = db.query(Job).filter(Job.org_id == org_id, Job.type == "investor_readiness").count()

    return {
        "investor_readiness": investor_readiness,
        "size": size
    }

@router.post("/{org_id}/investor-readiness", status_code=200)
async def create_or_update_investor_readiness(org_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    
    upsert_job(db, org_id, "investor_readiness")

    return {"status": "ok"}
