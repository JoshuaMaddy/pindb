"""Package marker for ``pindb.search.*`` submodules (import via ``importlib`` if needed).

Note: ``pindb.routes.search`` is mounted on the app for HTML search; this file is
not the primary search entry point.
"""

from fastapi import Depends
from fastapi.routing import APIRouter

from pindb.auth import require_admin
from pindb.routes.edit import artist, pin

router = APIRouter(prefix="/edit", dependencies=[Depends(require_admin)])

router.include_router(pin.router)
router.include_router(artist.router)
