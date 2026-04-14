from typing import Annotated, Any

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Shop, session_maker
from pindb.database.link import Link
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    compute_patch,
    get_edit_chain,
    get_effective_snapshot,
    get_head_edit,
)
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.routes._guards import assert_editor_can_edit, needs_pending_edit
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
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        shop: Shop | None = session.scalar(
            select(Shop).where(Shop.id == id).options(selectinload(Shop.links))
        )

        if not shop:
            return None

        assert_editor_can_edit(shop, current_user)

        if needs_pending_edit(shop, current_user):
            chain = get_edit_chain(session, "shops", id)
            old_snapshot: dict[str, Any] = get_effective_snapshot(shop, chain)

            new_snapshot: dict[str, Any] = dict(old_snapshot)
            new_snapshot.update(
                {
                    "name": name,
                    "description": description,
                    "links": sorted(links or []),
                }
            )

            patch = compute_patch(old_snapshot, new_snapshot)
            if not patch:
                return HTMLResponse(
                    headers={"HX-Redirect": str(request.url_for("get_shop", id=id))}
                )

            head = get_head_edit(session, "shops", id)
            session.add(
                PendingEdit(
                    entity_type="shops",
                    entity_id=id,
                    patch=patch,
                    created_by_id=current_user.id,
                    parent_id=head.id if head else None,
                )
            )

            return HTMLResponse(
                headers={
                    "HX-Redirect": str(request.url_for("get_shop", id=id))
                    + "?version=pending"
                }
            )

        shop.name = name
        shop.description = description

        for old_link in list(shop.links):
            session.delete(old_link)

        new_links: set[Link] = set()
        for new_link in links or []:
            new_links.add(Link(new_link))
        shop.links = new_links

        session.flush()
        shop_id: int = shop.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_shop", id=shop_id))}
    )
