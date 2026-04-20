"""
FastAPI routes: `routes/edit/__init__.py`.
"""

from fastapi import Depends
from fastapi.routing import APIRouter

from pindb.auth import require_editor
from pindb.routes.edit import artist, pin, shop, tag

router = APIRouter(prefix="/edit", dependencies=[Depends(require_editor)])

router.include_router(pin.router)
router.include_router(artist.router)
router.include_router(tag.router)
router.include_router(shop.router)
