"""
FastAPI routes: `routes/admin/__init__.py`.
"""

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.auth import require_admin
from pindb.database import session_maker
from pindb.routes.admin import search, tag_bulk, users
from pindb.routes.admin._pending_count import count_pending
from pindb.routes.admin.tag_bulk import (
    BulkTagUpsertBody,
    BulkTagUpsertResult,
    TagUpsertNode,
    run_bulk_tag_upsert,
)
from pindb.templates.admin.index import admin_panel_page

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.get("")
def get_admin_panel(request: Request) -> HTMLResponse:
    with session_maker() as session:
        pending_count = count_pending(session)
    return HTMLResponse(
        content=str(admin_panel_page(request=request, pending_count=pending_count))
    )


router.include_router(search.router)
router.include_router(tag_bulk.router)
router.include_router(users.router)

__all__ = [
    "BulkTagUpsertBody",
    "BulkTagUpsertResult",
    "TagUpsertNode",
    "router",
    "run_bulk_tag_upsert",
]
