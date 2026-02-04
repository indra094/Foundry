from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, Date
from database import Base
from sqlalchemy import ForeignKey
from datetime import date
import datetime
from sqlalchemy.orm import relationship
import uuid

def gen_id():
    return str(uuid.uuid4())


class Investor(Base):
    __tablename__ = "investors"

    id = Column(String, primary_key=True, index=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    name = Column(String)
    type = Column(String) # VC, Angel, etc.
    stage = Column(String)
    status = Column(String)
    notes = Column(String, nullable=True)

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, index=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    company = Column(String)
    role = Column(String)
    status = Column(String)
    signal = Column(Integer, default=0) # 0-5
    notes = Column(String, nullable=True)

class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True, index=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    name = Column(String)
    type = Column(String) # Human, AI
    role = Column(String)
    status = Column(String)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    title = Column(String)
    type = Column(String) # Warning, Info, Success
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AIHistory(Base):
    __tablename__ = "ai_history"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, ForeignKey("employees.id"))
    activity = Column(String)
    timestamp = Column(String)

class ReadinessGate(Base):
    __tablename__ = "readiness_gates"
    id = Column(Integer, primary_key=True, index=True)
    gate_id = Column(String) # e.g. "incorporation", "funding"
    org_id = Column(String, ForeignKey("organizations.id"))
    score = Column(Integer)
    issues = Column(Text) # JSON string of strings

class Connection(Base):
    __tablename__ = "connections"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, ForeignKey("organizations.id"))
    name = Column(String)
    role = Column(String)
    company = Column(String)
    relevance = Column(String)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    avatar_url = Column(String, nullable=True)

    current_org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    status = Column(String, default="Active")
    industry_experience = Column(Integer, default=0)

class OrganizationModel(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True)
    name = Column(String)
    slug = Column(String)

    industry = Column(String, nullable=True)
    geography = Column(String, nullable=True)
    type = Column(String, nullable=True)
    stage = Column(String, nullable=True)

    # 🔥 ADD THESE
    problem = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)
    customer = Column(String, nullable=True)

    onboarding_step = Column(Integer, default=0)
    risk_level = Column(String, default="Low")
    burn_rate = Column(Integer, default=0)
    runway = Column(String, nullable=True)


class OrgMember(Base):
    __tablename__ = "org_members"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    org_id = Column(String, ForeignKey("organizations.id"))
    
    member_type = Column(String, default="Founder") # 'Founder' or 'Executive'
    role = Column(String) # Title e.g. CEO, CTO
    permission_level = Column(String, default="ADMIN") # 'Read', 'Write', 'Admin'

    # UserOrgInfo detailed fields
    responsibility = Column(String, nullable=True)
    authority = Column(Text, default="[]") # JSON string of authority tags
    hours_per_week = Column(Integer, default=40)
    start_date = Column(Date, nullable=True)
    planned_change = Column(String, default="none")
    salary = Column(Float, default=0.0)
    bonus = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)
    vesting = Column(String, default="4 yrs, 1 yr cliff")
    expectations = Column(Text, default="[]") # JSON string of accountability items
    last_updated = Column(Date, nullable=True)
    status = Column(String, default="Active")
    
    cash_contribution = Column(Float, default=0.0)
    risk_tolerance = Column(String, default="Medium")
    vesting_cliff = Column(Integer, default=4)

class AIIdeaAnalysis(Base):
    __tablename__ = "ai_idea_analysis"

    workspace_id = Column(String, primary_key=True, index=True)
    version = Column(Integer, default=1)
    seed_funding_probability = Column(Integer, nullable=True)

    # store everything in JSON
    market = Column(JSON, nullable=True)
    investor = Column(JSON, nullable=True)
    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)
    personas = Column(JSON, nullable=True)
    roadmap = Column(JSON, nullable=True)

    generated_at = Column(DateTime, default=datetime.datetime.utcnow)

class FounderAlignmentModel(Base):
    __tablename__ = "founder_alignment"

    id = Column(String, primary_key=True, default=gen_id, index=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)

    # Summary
    score = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)

    # JSON fields
    factors = Column(JSON, nullable=False)
    risks = Column(JSON, nullable=True)
    actions = Column(JSON, nullable=True)

    # Insight
    primary_risk = Column(String, nullable=True)
    insight = Column(Text, nullable=True)

    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    model_version = Column(String, default="v1")

class FinancialsModel(Base):
    __tablename__ = "financials"

    org_id = Column(String, ForeignKey("organizations.id"), primary_key=True)
    
    monthly_revenue = Column(Integer, nullable=True)
    revenue_trend = Column(String, nullable=True) # Growing, Flat, Declining
    revenue_stage = Column(String, nullable=True) # Pre-revenue, Early, Recurring
    
    cash_in_bank = Column(Integer, nullable=True)
    monthly_burn = Column(Integer, nullable=True)
    cost_structure = Column(String, nullable=True) # Fixed, Variable, Mix
    
    pricing_model = Column(String, nullable=True) # Subscription, Usage, One-time, Enterprise
    price_per_customer = Column(Float, nullable=True)
    customers_in_pipeline = Column(Integer, nullable=True) # or customers/month
    
    data_confidence = Column(String, default="Rough") # Rough, Precise
    
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

class InvestorReadiness(Base):
    __tablename__ = "investor_readiness"

    id = Column(Integer, primary_key=True)

    readiness_score = Column(Float, nullable=False)

    pushbacks = Column(JSON, nullable=False)
    fixes = Column(JSON, nullable=False)
    demands = Column(JSON, nullable=False)

    simulated_reaction = Column(JSON, nullable=False)
    investor_type = Column(JSON, nullable=False)
    recommendation = Column(JSON, nullable=False)

    # 🆕 ADD THIS
    summary_insight = Column(Text, nullable=True)
    # one-paragraph investor-style summary

    investor_mindset_quotes = Column(JSON, nullable=True)
    demand_warning = Column(String, nullable=True)
    next_action = Column(JSON, nullable=True)

    last_updated = Column(DateTime, default=datetime.datetime.utcnow)



class DashboardModel(Base):
    __tablename__ = "dashboard"

    id = Column(Integer, primary_key=True)

    # --- Executive Summary ---
    verdict = Column(String, nullable=True)  
    # e.g. "Execution Stable", "Execution Risk", "Capital Constrained"

    thesis = Column(Text, nullable=True)
    # 1–2 sentence high-level summary

    # --- Killer Insight ---
    killer_insight = Column(Text, nullable=True)
    killer_insight_risk = Column(String, nullable=True)
    # e.g. "Founder Risk", "Capital Risk", "Market Risk"

    killer_insight_confidence = Column(Float, nullable=True)
    # 0.0–1.0 (nice AI credibility signal)

    # --- Capital & Runway ---
    runway_months = Column(Integer, nullable=True)
    burn_rate = Column(Float, nullable=True)

    capital_recommendation = Column(String, nullable=True)
    # e.g. "Raise in 3 months", "Cut burn by 20%"

    # --- Action Items (AI-driven) ---
    top_actions = Column(JSON, nullable=True)
    """
    [
      {
        "title": "Founder equity misalignment",
        "why": "...",
        "risk": "...",
        "screenId": "ALIGNMENT_OVERVIEW"
      }
    ]
    """

    # --- Metadata ---
    data_sources = Column(JSON, nullable=True)
    # e.g. ["founders", "financials", "market_inputs"]

    last_computed_at = Column(DateTime, default=datetime.datetime.utcnow)
    model_version = Column(String, nullable=True)

