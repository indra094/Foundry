from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Build database URL from env vars or default
# Format: postgresql://user:password@postgresserver/db
# DB_USER = os.getenv("POSTGRES_USER", "postgres")
# DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
# DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
# DB_NAME = os.getenv("POSTGRES_DB", "foundry")

# Fallback to SQLite correctly to avoid Windows install issues
SQLALCHEMY_DATABASE_URL = "sqlite:///./foundry_v2.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
