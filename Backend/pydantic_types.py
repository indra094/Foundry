from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class UserSchema(BaseModel):
    id: str
    fullName: str
    email: str
    role: Optional[str] = "Founder"
    permission_level: Optional[str] = "ADMIN"
    industry_experience: Optional[int] = None
    avatarUrl: Optional[str] = None
    current_org_id: Optional[str] = None
    authority: Optional[str] = None
    commitment: Optional[int] = None
    startDate: Optional[str] = None
    plannedChange: Optional[str] = None
    salary: Optional[float] = None
    bonus: Optional[float] = None
    equity: Optional[float] = None
    vesting: Optional[str] = None
    lastUpdated: Optional[str] = None
    status: Optional[str] = None
    class Config:
        orm_mode = True

class Workspace(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    geography: Optional[str] = None
    type: Optional[str] = None
    stage: Optional[str] = None

    # 🔥 ADD
    problem: Optional[str] = None
    solution: Optional[str] = None
    customer: Optional[str] = None

    onboarding_step: Optional[int] = None


class UserOrgInfo(BaseModel):
    title: str
    responsibility: str
    authority: List[str]
    commitment: int
    startDate: str
    plannedChange: str
    salary: float
    bonus: str
    equity: float
    vesting: str
    expectations: List[str]
    lastUpdated: str
    status: str

class LoginRequest(BaseModel):
    email: str
    password: str


class CreateUserRequest(BaseModel):
    fullName: str
    email: str
    geography: Optional[str] = None
    org_id: Optional[str] = None
    status: str

class SetUserOrgInfoRequest(BaseModel):
    user_id: str
    org_id: str
    role: Optional[str] = None
    permission_level: Optional[str] = None
    equity: Optional[float] = None
    vesting: Optional[str] = None
    commitment: Optional[int] = None
    industry_experience: Optional[str] = None
    status: Optional[str] = None

class SetOnboardingRequest(BaseModel):
    step: int

class MarketSchema(BaseModel):
    tam_value: int
    growth_rate_percent: int
    growth_index: int
    insight: str

class PersonaSchema(BaseModel):
    name: str
    pain: str
    solution: str

class MilestoneSchema(BaseModel):
    label: str
    duration_days: int
    is_active: bool

class RoadmapSchema(BaseModel):
    recommended_stage: str
    min_capital: int
    max_capital: int
    milestones: List[MilestoneSchema]

class AnalysisPayload(BaseModel):
    seed_funding_probability: int
    market: MarketSchema
    strengths: List[str]
    weaknesses: List[str]
    investor_verdict: str
    personas: List[PersonaSchema]
    roadmap: RoadmapSchema


class FounderAlignmentResponse(BaseModel):
    id: str
    org_id: str
    score: int
    risk_level: str
    factors: Dict[str, Any]
    risks: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, str]]] = None
    primary_risk: Optional[str] = None
    insight: Optional[str] = None
    generated_at: datetime
    model_version: str

    class Config:
        orm_mode = True

class FounderAlignmentResponseModel(BaseModel):
    alignment: Optional[FounderAlignmentResponse] = None
    size: int


class FinancialsSchema(BaseModel):
    org_id: str
    monthly_revenue: Optional[int] = None
    revenue_trend: Optional[str] = None
    revenue_stage: Optional[str] = None
    cash_in_bank: Optional[int] = None
    monthly_burn: Optional[int] = None
    cost_structure: Optional[str] = None
    pricing_model: Optional[str] = None
    price_per_customer: Optional[float] = None
    customers_in_pipeline: Optional[int] = None
    data_confidence: Optional[str] = "Rough"
    last_updated: Optional[datetime] = None

    class Config:
        orm_mode = True

