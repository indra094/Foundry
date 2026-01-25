from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from workers import start_workers

from config import settings

# Validate settings on startup
settings.validate()

# Create database tables
from database import engine, Base
import models # Import models to register them with Base
Base.metadata.create_all(bind=engine)


start_workers()
app = FastAPI(title="Foundry Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
async def root():
    
    return {"message": "Foundry Backend API is running"}

# Include routers
from AccountCreation import router as account_router
from FoundersList import router as founders_router
from InvestorsList import router as investors_router
from CustomersList import router as customers_router
from TeamEmployees import router as team_router
from IncorporationReadiness import router as gate_router
from CompanyDashboard import router as intelligence_router

app.include_router(account_router.router)
app.include_router(founders_router.router)
app.include_router(investors_router.router)
app.include_router(customers_router.router)
app.include_router(team_router.router)
app.include_router(gate_router.router)
app.include_router(intelligence_router.router)
