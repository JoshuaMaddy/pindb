from fastapi.routing import APIRouter

from pindb.routes.edit import artist, pin

router = APIRouter(prefix="/edit")

router.include_router(pin.router)
router.include_router(artist.router)
