"""
Serve the dashboard HTML from FastAPI.
Mount this router in main.py to add /dashboard route.
"""
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()
DASHBOARD_PATH = Path(__file__).parent / "index.html"


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_PATH.read_text(encoding="utf-8"))
