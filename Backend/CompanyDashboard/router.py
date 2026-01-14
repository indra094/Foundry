from fastapi import APIRouter

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

# GET /intelligence/dashboard
@router.get("/dashboard")
async def get_dashboard_stats():
    # This would ideally aggregate from other models, but keeping mock for now
    return {
        "risk": "Medium",
        "burnRate": 15000,
        "runway": "12 months",
        "teamSize": "2 + 2 AI",
        "customerCount": 2
    }

# GET /intelligence/connections
@router.get("/connections")
async def get_relevant_connections():
    return [
        {"id": 1, "name": "John VC", "role": "Investor", "company": "Sequoia", "relevance": "High"},
        {"id": 2, "name": "Sarah Angel", "role": "Angel", "company": "AngelList", "relevance": "High"}
    ]
