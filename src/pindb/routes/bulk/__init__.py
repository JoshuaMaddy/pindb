from fastapi import Depends
from fastapi.routing import APIRouter

from pindb.auth import require_admin
from pindb.routes.bulk import pin

router = APIRouter(prefix="/bulk", dependencies=[Depends(require_admin)])

router.include_router(pin.router)
