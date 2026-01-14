from sqlalchemy import Column, String, Integer, Float, Boolean
from database import Base

from sqlalchemy import ForeignKey, DateTime
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    avatar_url = Column(String, nullable=True)
    # Removing 'role' from User as it's now organization-specific in OrgMember

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    slug = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class OrgMember(Base):
    __tablename__ = "org_members"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    org_id = Column(String, ForeignKey("organizations.id"))
    
    member_type = Column(String, default="Founder") # 'Founder' or 'Executive'
    role = Column(String) # e.g. CEO, CTO
    
    # Equity/Compensation fields
    hours_per_week = Column(Integer, default=40)
    equity = Column(Float, default=0.0)
    cash_contribution = Column(Float, default=0.0)
    risk_tolerance = Column(String, default="Medium")
    vesting_cliff = Column(Integer, default=4)
    status = Column(String, default="Active")
