from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import FinancialsModel, upsert_job
from pydantic_types import FinancialsSchema
import datetime

router = APIRouter(prefix="/auth", tags=["Financials"])

@router.get("/{org_id}/financials", response_model=FinancialsSchema)
def get_financials(org_id: str, db: Session = Depends(get_db)):
    fin = db.query(FinancialsModel).filter(FinancialsModel.org_id == org_id).first()
    if not fin:
        return FinancialsSchema(org_id=org_id)
    
    return FinancialsSchema(
        org_id=fin.org_id,
        monthly_revenue=fin.monthly_revenue,
        revenue_trend=fin.revenue_trend,
        revenue_stage=fin.revenue_stage,
        cash_in_bank=fin.cash_in_bank,
        monthly_burn=fin.monthly_burn,
        cost_structure=fin.cost_structure,
        pricing_model=fin.pricing_model,
        price_per_customer=fin.price_per_customer,
        customers_in_pipeline=fin.customers_in_pipeline,
        data_confidence=fin.data_confidence,
        last_updated=fin.last_updated
    )

@router.put("/{org_id}/financials", response_model=FinancialsSchema)
def update_financials(org_id: str, data: FinancialsSchema, db: Session = Depends(get_db)):
    fin = db.query(FinancialsModel).filter(FinancialsModel.org_id == org_id).first()
    if not fin:
        fin = FinancialsModel(org_id=org_id)
        db.add(fin)
    
    fin.monthly_revenue = data.monthly_revenue
    fin.revenue_trend = data.revenue_trend
    fin.revenue_stage = data.revenue_stage
    fin.cash_in_bank = data.cash_in_bank
    fin.monthly_burn = data.monthly_burn
    fin.cost_structure = data.cost_structure
    fin.pricing_model = data.pricing_model
    fin.price_per_customer = data.price_per_customer
    fin.customers_in_pipeline = data.customers_in_pipeline
    fin.data_confidence = data.data_confidence
    fin.last_updated = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(fin)
    upsert_job(db, org_id, "investor_readiness")
    
    return FinancialsSchema(
        org_id=fin.org_id,
        monthly_revenue=fin.monthly_revenue,
        revenue_trend=fin.revenue_trend,
        revenue_stage=fin.revenue_stage,
        cash_in_bank=fin.cash_in_bank,
        monthly_burn=fin.monthly_burn,
        cost_structure=fin.cost_structure,
        pricing_model=fin.pricing_model,
        price_per_customer=fin.price_per_customer,
        customers_in_pipeline=fin.customers_in_pipeline,
        data_confidence=fin.data_confidence,
        last_updated=fin.last_updated
    )
