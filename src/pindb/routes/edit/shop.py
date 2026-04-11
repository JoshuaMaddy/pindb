from typing import Annotated

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Shop, session_maker
from pindb.database.link import Link
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.routes._guards import assert_editor_can_edit
from pindb.templates.create_and_edit.shop import shop_form

router = APIRouter()


@router.get(path="/shop/{id}", response_model=None)
def get_edit_shop(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse | None:
    with session_maker() as session:
        shop: Shop | None = session.scalar(
            select(Shop).where(Shop.id == id).options(selectinload(Shop.links))
        )

        if shop is None:
            return None

        assert_editor_can_edit(shop, current_user)

        return HTMLResponse(
            content=str(
                shop_form(
                    post_url=request.url_for("post_edit_shop", id=id),
                    shop=shop,
                    request=request,
                )
            )
        )


@router.post(path="/shop/{id}", response_model=None)
def post_edit_shop(
    request: Request,
    id: int,
    current_user: EditorUser,
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
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        shop: Shop | None = session.get(entity=Shop, ident=id)

        if not shop:
            return None

        assert_editor_can_edit(shop, current_user)

        shop.name = name
        shop.description = description

        for old_link in shop.links:
            session.delete(old_link)

        new_links: set[Link] = set()
        for new_link in links or []:
            new_links.add(Link(new_link))
        shop.links: set[Link] = new_links

        session.flush()
        shop_id: int = shop.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_shop", id=shop_id))}
    )
