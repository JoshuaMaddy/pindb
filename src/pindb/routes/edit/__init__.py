from fastapi import Depends
from fastapi.routing import APIRouter

from pindb.auth import require_admin
from pindb.routes.edit import artist, material, pin, shop, tag

router = APIRouter(prefix="/edit", dependencies=[Depends(require_admin)])

router.include_router(pin.router)
router.include_router(artist.router)
router.include_router(tag.router)
router.include_router(material.router)
router.include_router(shop.router)
