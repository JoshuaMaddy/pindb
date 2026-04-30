"""
FastAPI routes: `routes/list/__init__.py`.
"""

from fastapi import Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse

from pindb.routes.list import artists, pin_sets, shops, tags
from pindb.templates.list.index import list_index_page

router = APIRouter(prefix="/list")


@router.get(path="/")
async def get_list_index(request: Request) -> HtpyResponse:
    return HtpyResponse(list_index_page(request=request))


router.include_router(shops.router)
router.include_router(pin_sets.router)
router.include_router(tags.router)
router.include_router(artists.router)
