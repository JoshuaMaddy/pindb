"""
FastAPI routes: `routes/create/shop.py`.
"""

from typing import Annotated

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from pydantic import BeforeValidator
from sqlalchemy.exc import IntegrityError

from pindb.database import Shop, ShopAlias, session_maker
from pindb.database.link import Link
from pindb.htmx_toast import (
    hx_redirect_with_toast_headers,
    is_unique_violation,
    unique_constraint_response,
)
from pindb.log import user_logger
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.search.update import update_shop
from pindb.templates.create_and_edit.shop import shop_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.create.shop")


@router.get(path="/shop")
def get_create_shop(request: Request) -> HtpyResponse:
    return HtpyResponse(
        shop_form(
            post_url=request.url_for("post_create_shop"),
            request=request,
        )
    )


@router.post(path="/shop")
def post_create_shop(
    request: Request,
    name: str = Form(),
    description: Annotated[
        str | None,
        Form(),
        BeforeValidator(func=empty_str_to_none),
    ] = None,
    links: Annotated[
        list[str] | None,
        Form(),
        BeforeValidator(func=empty_str_list_to_none),
    ] = None,
    aliases: list[str] = Form(default_factory=list),
) -> HTMLResponse:
    LOGGER.info("Creating shop name=%r aliases=%s", name, aliases)
    try:
        with session_maker.begin() as session:
            new_links: set[Link] = (
                {Link(path=link) for link in links} if links else set[Link]()
            )

            shop = Shop(
                name=name,
                description=description,
                links=new_links,
            )

            session.add(instance=shop)
            session.flush()

            shop.aliases = [ShopAlias(alias=a) for a in aliases if a.strip()]
            session.flush()
            shop_id: int = shop.id
    except IntegrityError as exc:
        if not is_unique_violation(exc):
            raise
        return unique_constraint_response(request=request)

    update_shop(shop=shop)

    LOGGER.info("Created shop id=%d name=%r", shop_id, name)

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=str(request.url_for("get_shop", id=shop_id)),
            message="Shop created.",
        )
    )
