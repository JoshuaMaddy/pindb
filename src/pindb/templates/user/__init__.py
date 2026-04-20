"""
htpy page and fragment builders: `templates/user/__init__.py`.
"""

from fastapi import Depends
from fastapi.routing import APIRouter

from pindb.auth import require_admin
from pindb.routes.edit import artist, pin

router = APIRouter(prefix="/edit", dependencies=[Depends(require_admin)])

router.include_router(pin.router)
router.include_router(artist.router)
