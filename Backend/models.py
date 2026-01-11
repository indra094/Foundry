from sqlalchemy import Column, String, Integer, Float, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    role = Column(String, default="Founder")
    avatar_url = Column(String, nullable=True)

class Founder(Base):
    __tablename__ = "founders"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    role = Column(String)
    hours_per_week = Column(Integer)
    equity = Column(Float)
    cash_contribution = Column(Float)
    risk_tolerance = Column(String)
    vesting_cliff = Column(Integer)
    status = Column(String)
