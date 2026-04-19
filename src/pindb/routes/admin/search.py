from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.search.update import update_all

router = APIRouter()


@router.post("/search/sync")
def sync_search_index() -> HTMLResponse:
    update_all()
    return HTMLResponse(content="Search index sync triggered.")
