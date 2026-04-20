"""
FastAPI routes: `routes/bulk/__init__.py`.
"""

from fastapi import Depends
from fastapi.routing import APIRouter

from pindb.auth import require_editor
from pindb.routes.bulk import edit, pin

# Bulk creation and bulk editing are editor-allowed; admin-only operations
# (such as bulk-editing search results) check `current_user.is_admin` at the
# specific endpoint.
router = APIRouter(dependencies=[Depends(require_editor)])

router.include_router(pin.router, prefix="/bulk")
router.include_router(edit.router)
