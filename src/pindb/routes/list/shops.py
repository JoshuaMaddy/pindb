"""
FastAPI routes: `routes/list/shops.py`.
"""

from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import Shop, session_maker
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.search.search import search_shops
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.shops import shops_list, shops_list_section

router = APIRouter()


@router.get(path="/shops")
def get_list_shops(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
    q: str = Query(default=""),
    sort: SortOrder = Query(default=SortOrder.name),
) -> HtpyResponse:
    offset: int = (page - 1) * DEFAULT_PER_PAGE
    base_url: str = str(request.url_for("get_list_shops"))

    order_by = (
        Shop.created_at.desc()
        if sort == SortOrder.newest
        else Shop.created_at.asc()
        if sort == SortOrder.oldest
        else Shop.name.asc()
    )

    with session_maker() as session:
        if q:
            shops_result, total_count = search_shops(
                query=q,
                session=session,
                offset=offset,
                limit=DEFAULT_PER_PAGE,
            )
            shops: Sequence[Shop] = shops_result
        else:
            total_count = session.scalar(select(func.count(Shop.id))) or 0
            shops = session.scalars(
                select(Shop)
                .options(selectinload(Shop.pins))
                .order_by(order_by)
                .limit(DEFAULT_PER_PAGE)
                .offset(offset)
            ).all()

        if request.headers.get("HX-Request"):
            return HtpyResponse(
                shops_list_section(
                    request=request,
                    shops=shops,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                    q=q,
                    sort=sort,
                )
            )
        return HtpyResponse(
            shops_list(
                request=request,
                shops=shops,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
                q=q,
                sort=sort,
            )
        )
