"""
FastAPI routes: `routes/admin/stats.py`.
"""

from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.achievements import refresh_all_user_stats

router = APIRouter()


@router.post("/stats/refresh")
async def post_refresh_user_stats() -> HTMLResponse:
    await refresh_all_user_stats()
    return HTMLResponse(content="User stats and achievements refresh triggered.")
