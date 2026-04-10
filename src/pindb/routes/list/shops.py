from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import Shop, session_maker
from pindb.models.list_view import EntityListView
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.shops import shops_list, shops_list_section

router = APIRouter()


@router.get(path="/shops")
def get_list_shops(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
) -> HTMLResponse:
    with session_maker.begin() as session:
        total_count: int = session.scalar(select(func.count(Shop.id))) or 0
        shops: Sequence[Shop] = session.scalars(
            select(Shop)
            .options(selectinload(Shop.pins))
            .order_by(Shop.name.asc())
            .limit(DEFAULT_PER_PAGE)
            .offset((page - 1) * DEFAULT_PER_PAGE)
        ).all()

        base_url: str = str(request.url_for("get_list_shops"))

        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=shops_list_section(
                    request=request,
                    shops=shops,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                )
            )
        return HTMLResponse(
            content=shops_list(
                request=request,
                shops=shops,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
            )
        )
