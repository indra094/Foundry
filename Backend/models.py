from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, Date
from database import Base
from sqlalchemy import ForeignKey
from datetime import date
import datetime
from sqlalchemy.orm import relationship
import uuid

def gen_id():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    avatar_url = Column(String, nullable=True)

    current_org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    status = Column(String, default="Active")

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
    bonus = Column(String, default="None")
    equity = Column(Float, default=0.0)
    vesting = Column(String, default="4 yrs, 1 yr cliff")
    expectations = Column(Text, default="[]") # JSON string of accountability items
    last_updated = Column(Date, nullable=True)
    status = Column(String, default="Active")
    
    cash_contribution = Column(Float, default=0.0)
    risk_tolerance = Column(String, default="Medium")
    vesting_cliff = Column(Integer, default=4)

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
