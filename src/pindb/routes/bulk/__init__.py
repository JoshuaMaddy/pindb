"""
FastAPI routes: `routes/bulk/__init__.py`.
"""

from fastapi import Depends
from fastapi.routing import APIRouter

from pindb.auth import require_editor
from pindb.routes.bulk import edit, pin, tag

# Every bulk flow — tag create, pin import, pin edit — is editor-allowed, and
# `/bulk/options/*` rides the same gate for the tag and pin forms. Editor
# submissions land pending; admin ones auto-approve. Admin-only operations
# (e.g. bulk-editing search results) check `current_user.is_admin` inside
# `bulk/edit.py`.
_editor = [Depends(require_editor)]
router = APIRouter()

router.include_router(pin.router, prefix="/bulk", dependencies=_editor)
router.include_router(tag.router, prefix="/bulk", dependencies=_editor)
router.include_router(edit.router, dependencies=_editor)
