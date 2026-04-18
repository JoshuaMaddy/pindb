import logging

from fastapi import Depends
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRouter

from pindb.audit_events import get_audit_user
from pindb.auth import require_admin
from pindb.database import session_maker
from pindb.database.entity_type import EntityType
from pindb.search.update import delete_pin as delete_pin_from_index
from pindb.utils import utc_now

router = APIRouter(prefix="/delete", dependencies=[Depends(require_admin)])

LOGGER = logging.getLogger("pindb.routes.delete")


@router.post(path="/{entity_type}/{id}")
def post_delete_entity(entity_type: EntityType, id: int) -> RedirectResponse:
    now = utc_now()
    user_id = get_audit_user()
    with session_maker.begin() as session:
        entity = session.get(entity_type.model, id)
        if entity is not None:
            entity.deleted_at = now
            entity.deleted_by_id = user_id

    if entity_type is EntityType.pin:
        delete_pin_from_index(pin_id=id)

    return RedirectResponse(url="/", status_code=303)
