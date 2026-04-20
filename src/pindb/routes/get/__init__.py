"""
FastAPI routes: `routes/get/__init__.py`.
"""

from fastapi.routing import APIRouter

from pindb.routes.get import artist, image, options, pin, pin_set, shop, tag

router = APIRouter(prefix="/get")

router.include_router(image.router)
router.include_router(options.router)
router.include_router(pin.router)
router.include_router(shop.router)
router.include_router(tag.router)
router.include_router(pin_set.router)
router.include_router(artist.router)
