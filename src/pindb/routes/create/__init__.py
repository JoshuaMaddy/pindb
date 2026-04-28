"""
FastAPI routes: `routes/create/__init__.py`.
"""

from fastapi import Depends, Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse

from pindb.auth import require_editor
from pindb.routes.create import artist, name_check, pin, pin_set, shop, tag
from pindb.templates.create_and_edit.index import create_index

router = APIRouter(prefix="/create", dependencies=[Depends(require_editor)])


@router.get(path="/")
def get_create_index(request: Request) -> HtpyResponse:
    return HtpyResponse(create_index(request=request))


router.include_router(pin.router)
router.include_router(shop.router)
router.include_router(tag.router)
router.include_router(pin_set.router)
router.include_router(artist.router)
router.include_router(name_check.router)
