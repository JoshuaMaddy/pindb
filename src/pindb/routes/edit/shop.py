from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Shop, ShopAlias, session_maker
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
)
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.routes._guards import assert_editor_can_edit, needs_pending_edit
from pindb.routes.edit._pending_helpers import replace_links, submit_pending_edit
from pindb.templates.create_and_edit.shop import shop_form

router = APIRouter()


@router.get(path="/shop/{id}", response_model=None)
def get_edit_shop(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse:
    with session_maker() as session:
        shop: Shop | None = session.scalar(
            select(Shop)
            .where(Shop.id == id)
            .options(selectinload(Shop.links), selectinload(Shop.aliases))
        )

        if shop is None:
            raise HTTPException(status_code=404, detail="Shop not found")

        assert_editor_can_edit(shop, current_user)

        if needs_pending_edit(shop, current_user):
            chain = get_edit_chain(session, "shops", id)
            if chain:
                effective = get_effective_snapshot(shop, chain)
                with session.no_autoflush:
                    apply_snapshot_in_memory(shop, effective, session)

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
    aliases: list[str] = Form(default_factory=list),
) -> HTMLResponse:
    with session_maker.begin() as session:
        shop: Shop | None = session.scalar(
            select(Shop)
            .where(Shop.id == id)
            .options(selectinload(Shop.links), selectinload(Shop.aliases))
        )

        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")

        assert_editor_can_edit(shop, current_user)

        if needs_pending_edit(shop, current_user):
            return submit_pending_edit(
                session=session,
                entity=shop,
                entity_table="shops",
                entity_id=id,
                field_updates={
                    "name": name,
                    "description": description,
                    "links": sorted(links or []),
                    "aliases": sorted(alias for alias in aliases if alias.strip()),
                },
                current_user=current_user,
                request=request,
                redirect_route="get_shop",
            )

        shop.name = name
        shop.description = description

        replace_links(entity=shop, urls=links, session=session)

        shop.aliases = [ShopAlias(alias=alias) for alias in aliases if alias.strip()]

        session.flush()
        shop_id: int = shop.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_shop", id=shop_id))}
    )
