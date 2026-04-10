from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import session_maker
from pindb.database.material import Material
from pindb.models.list_view import EntityListView
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.materials import materials_list, materials_list_section

router = APIRouter()


@router.get(path="/materials")
def get_list_materials(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
) -> HTMLResponse:
    with session_maker.begin() as session:
        total_count: int = session.scalar(select(func.count(Material.id))) or 0
        materials: Sequence[Material] = session.scalars(
            select(Material)
            .options(selectinload(Material.pins))
            .order_by(Material.name.asc())
            .limit(DEFAULT_PER_PAGE)
            .offset((page - 1) * DEFAULT_PER_PAGE)
        ).all()

        base_url: str = str(request.url_for("get_list_materials"))

        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=materials_list_section(
                    request=request,
                    materials=materials,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                )
            )
        return HTMLResponse(
            content=materials_list(
                request=request,
                materials=materials,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
            )
        )
