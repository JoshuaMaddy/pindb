"""
FastAPI routes: `routes/list/shops.py`.
"""

from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select

from pindb.database import Shop, async_session_maker
from pindb.database.joins import pins_shops
from pindb.database.pin_previews import PinPreviews, load_pin_previews
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.routes.list._render import list_response
from pindb.search.search import search_shops
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.shops import shops_list, shops_list_section

router = APIRouter()


@router.get(path="/shops")
async def get_list_shops(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
    q: str = Query(default=""),
    sort: SortOrder = Query(default=SortOrder.name),
) -> HTMLResponse:
    offset: int = (page - 1) * DEFAULT_PER_PAGE
    base_url: str = str(request.url_for("get_list_shops"))

    order_by = (
        Shop.created_at.desc()
        if sort == SortOrder.newest
        else Shop.created_at.asc()
        if sort == SortOrder.oldest
        else Shop.name.asc()
    )

    async with async_session_maker() as session:
        if q:
            shops_result, total_count = await search_shops(
                query=q,
                session=session,
                offset=offset,
                limit=DEFAULT_PER_PAGE,
            )
            shops: Sequence[Shop] = shops_result
        else:
            total_count = await session.scalar(select(func.count(Shop.id))) or 0
            shops = (
                await session.scalars(
                    select(Shop)
                    .order_by(order_by)
                    .limit(DEFAULT_PER_PAGE)
                    .offset(offset)
                )
            ).all()

        previews: PinPreviews = await load_pin_previews(
            session,
            join_table=pins_shops,
            entity_column=pins_shops.c.shop_id,
            entity_ids=[shop.id for shop in shops],
        )

        return list_response(
            request,
            full=shops_list,
            section=shops_list_section,
            shops=shops,
            previews=previews,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            q=q,
            sort=sort,
        )
