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
# Include routers
from routers import auth, users, workspaces, financials, analysis, dashboard

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(financials.router)
app.include_router(analysis.router)
app.include_router(dashboard.router)
