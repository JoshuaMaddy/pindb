"""
FastAPI routes: `routes/edit/shop.py`.
"""

from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.achievements import refresh_user_stats
from pindb.auth import EditorUser
from pindb.blacklist import blacklisted_exact_match_response
from pindb.database import BlacklistEntityType, Shop, async_session_maker
from pindb.database.entity_type import EntityType
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
)
from pindb.database.shop import replace_shop_aliases
from pindb.database.tag import normalize_tag_name
from pindb.htmx_toast import hx_redirect_with_toast_headers
from pindb.log import user_logger
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.routes._guards import (
    assert_editor_can_edit,
    clear_rejection_on_resubmit,
    needs_pending_edit,
)
from pindb.routes._urls import slugify_for_url
from pindb.routes.edit._pending_helpers import (
    apply_simple_aliased_direct_edit,
    submit_simple_aliased_pending_edit,
)
from pindb.search.update import sync_entity
from pindb.templates.create_and_edit.shop import shop_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.edit.shop")


@router.get(path="/shop/{id}", response_model=None)
async def get_edit_shop(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse:
    async with async_session_maker() as session:
        shop: Shop | None = await session.scalar(
            select(Shop)
            .where(Shop.id == id)
            .options(selectinload(Shop.links), selectinload(Shop.aliases))
        )

        if shop is None:
            raise HTTPException(status_code=404, detail="Shop not found")

        assert_editor_can_edit(shop, current_user)

        if needs_pending_edit(shop, current_user):
            chain = await get_edit_chain(session, "shops", id)
            if chain:
                effective = get_effective_snapshot(shop, chain)
                with session.no_autoflush:
                    await apply_snapshot_in_memory(shop, effective, session)

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
async def post_edit_shop(
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
    async with async_session_maker.begin() as session:
        shop: Shop | None = await session.scalar(
            select(Shop)
            .where(Shop.id == id)
            .options(selectinload(Shop.links), selectinload(Shop.aliases))
        )

        if not shop:
            raise HTTPException(status_code=404, detail="Shop not found")

        assert_editor_can_edit(shop, current_user)

        # Only *newly introduced* names/aliases are checked — an entity that
        # predates its blacklist entry stays editable (description tweaks etc.)
        # without being locked behind its own name.
        existing_keys: set[str] = {normalize_tag_name(name=shop.name)} | {
            normalize_tag_name(name=alias.alias) for alias in shop.aliases
        }
        new_candidates: list[str] = [
            candidate
            for candidate in [name, *aliases]
            if normalize_tag_name(name=candidate) not in existing_keys
        ]
        blocked: HTMLResponse | None = await blacklisted_exact_match_response(
            request=request,
            entity_type=BlacklistEntityType.shop,
            candidates=new_candidates,
        )
        if blocked is not None:
            return blocked

        if needs_pending_edit(shop, current_user):
            LOGGER.info("Submitting pending edit for shop id=%d name=%r", id, name)
            return await submit_simple_aliased_pending_edit(
                session=session,
                entity=shop,
                entity_table="shops",
                entity_id=id,
                name=name,
                description=description,
                links=links,
                aliases=aliases,
                current_user=current_user,
                request=request,
                redirect_route="get_shop",
            )

        LOGGER.info("Editing shop id=%d name=%r", id, name)
        clear_rejection_on_resubmit(shop, current_user)
        await apply_simple_aliased_direct_edit(
            entity=shop,
            name=name,
            description=description,
            links=links,
            aliases=aliases,
            replace_aliases_fn=replace_shop_aliases,
            session=session,
        )

        await session.flush()
        shop_id: int = shop.id

    await sync_entity(EntityType.shop, shop_id)
    await refresh_user_stats(user_id=current_user.id)

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=str(
                request.url_for(
                    "get_shop",
                    slug=slugify_for_url(name=name, fallback="shop"),
                    id=shop_id,
                )
            ),
            message="Shop updated.",
        )
    )
