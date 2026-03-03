from typing import Sequence

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import session_maker
from pindb.database.material import Material
from pindb.templates.list.materials import materials_list

router = APIRouter()


@router.get(path="/materials")
def get_list_materials(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        materials: Sequence[Material] = session.scalars(
            statement=select(Material).order_by(Material.name.asc())
        ).all()

        return HTMLResponse(
            content=materials_list(request=request, materials=materials)
        )
