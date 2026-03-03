from typing import Sequence

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import Shop, session_maker
from pindb.templates.list.shops import shops_list

router = APIRouter()


@router.get(path="/shops")
def get_list_shops(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        shops: Sequence[Shop] = session.scalars(
            statement=select(Shop).order_by(Shop.name.asc())
        ).all()

        return HTMLResponse(content=shops_list(request=request, shops=shops))
