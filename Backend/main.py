from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from config import settings

# Validate settings on startup
settings.validate()

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

# You can import routers here dynamically or explicitly
# example:
# from .AccountCreation import router as account_creation_router
# app.include_router(account_creation_router.router)
