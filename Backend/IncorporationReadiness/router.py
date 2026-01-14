from fastapi import APIRouter

router = APIRouter(prefix="/gates", tags=["Gates"])

# GET /gates/incorporation
@router.get("/incorporation")
async def get_incorporation_readiness():
    return {
        "score": 63,
        "issues": ["No signed agreement", "Zero customer validation"]
    }

# GET /gates/notifications
@router.get("/notifications")
async def get_notifications():
    return [
        {"id": 1, "title": "Alignment Score Dropped", "type": "Warning"}
    ]
