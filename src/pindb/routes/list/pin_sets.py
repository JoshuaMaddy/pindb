from typing import Sequence

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import session_maker
from pindb.database.pin_set import PinSet
from pindb.templates.list.pin_sets import pin_sets_list

router = APIRouter()


@router.get(path="/pin_sets")
def get_list_pin_sets(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        pin_sets: Sequence[PinSet] = session.scalars(
            statement=select(PinSet).order_by(PinSet.name.asc())
        ).all()

        return HTMLResponse(content=pin_sets_list(request=request, pin_sets=pin_sets))
