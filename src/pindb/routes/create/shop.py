from typing import Annotated

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator

from pindb.database import Shop, session_maker
from pindb.database.link import Link
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.search.update import update_shop
from pindb.templates.create_and_edit.shop import shop_form

router = APIRouter()


@router.get(path="/shop")
def get_create_shop(request: Request) -> HTMLResponse:
    return HTMLResponse(
        content=shop_form(
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
) -> HTMLResponse:
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
        shop_id: int = shop.id

    update_shop(shop=shop)

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_shop", id=shop_id))}
    )
