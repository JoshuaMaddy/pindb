"""
FastAPI routes: `routes/bulk/__init__.py`.
"""

from fastapi import Depends
from fastapi.routing import APIRouter

from pindb.auth import require_editor
from pindb.routes.bulk import edit, pin, tag

# Tag bulk create and bulk pin edit flows are editor-allowed. Bulk pin import
# (`pin.router`) adds admin-only dependencies on its pin endpoints while
# `/bulk/options/*` stays editor-accessible for tag and pin forms. Admin-only
# operations (e.g. bulk-editing search results) check `current_user.is_admin`
# inside `bulk/edit.py`.
_editor = [Depends(require_editor)]
router = APIRouter()

router.include_router(pin.router, prefix="/bulk", dependencies=_editor)
router.include_router(tag.router, prefix="/bulk", dependencies=_editor)
router.include_router(edit.router, dependencies=_editor)
