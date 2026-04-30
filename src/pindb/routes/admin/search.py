"""
FastAPI routes: `routes/admin/search.py`.
"""

from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.search.update import update_all

router = APIRouter()


@router.post("/search/sync")
async def sync_search_index() -> HTMLResponse:
    await update_all()
    return HTMLResponse(content="Search index sync triggered.")
