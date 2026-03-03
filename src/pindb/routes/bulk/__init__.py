from fastapi.routing import APIRouter

from pindb.routes.bulk import pin

router = APIRouter(prefix="/bulk")

router.include_router(pin.router)
