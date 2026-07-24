"""
FastAPI routes: `routes/admin/blacklist.py`.

Admin CRUD for the do-not-index name blacklist (Shops/Artists). Rows are
hard-deleted on removal — the table is operational state, not content.
"""

from typing import Sequence

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.auth import AdminUser
from pindb.database import (
    BlacklistedName,
    BlacklistEntityType,
    async_session_maker,
)
from pindb.database.tag import normalize_tag_name
from pindb.log import user_logger
from pindb.templates.admin.blacklist import admin_blacklist_page

router = APIRouter()

LOGGER = user_logger("pindb.routes.admin.blacklist")


@router.get("/blacklist")
async def get_admin_blacklist(request: Request) -> HTMLResponse:
    async with async_session_maker() as session:
        entries: Sequence[BlacklistedName] = (
            await session.scalars(
                select(BlacklistedName).order_by(
                    BlacklistedName.entity_type.asc(),
                    BlacklistedName.name.asc(),
                )
            )
        ).all()
        return HTMLResponse(
            content=str(
                admin_blacklist_page(
                    request=request,
                    entries=entries,
                )
            )
        )


@router.post("/blacklist")
async def post_admin_blacklist_add(
    current_user: AdminUser,
    name: str = Form(),
    entity_type: str = Form(),
    reason: str | None = Form(default=None),
) -> RedirectResponse:
    cleaned_name: str = name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=400, detail="Name is required")

    entity_types: list[BlacklistEntityType]
    if entity_type == "both":
        entity_types = [BlacklistEntityType.shop, BlacklistEntityType.artist]
    else:
        try:
            entity_types = [BlacklistEntityType(entity_type)]
        except ValueError as error:
            raise HTTPException(
                status_code=400, detail="Unknown entity type"
            ) from error

    cleaned_reason: str | None = reason.strip() if reason and reason.strip() else None
    normalized: str = normalize_tag_name(name=cleaned_name)

    async with async_session_maker.begin() as session:
        for one_entity_type in entity_types:
            existing_id: int | None = await session.scalar(
                select(BlacklistedName.id).where(
                    BlacklistedName.entity_type == one_entity_type,
                    BlacklistedName.normalized_name == normalized,
                )
            )
            if existing_id is not None:
                continue
            session.add(
                instance=BlacklistedName(
                    entity_type=one_entity_type,
                    name=cleaned_name,
                    reason=cleaned_reason,
                    created_by_id=current_user.id,
                )
            )
            LOGGER.info(
                "Blacklisted name=%r entity_type=%s by user_id=%d",
                cleaned_name,
                one_entity_type.value,
                current_user.id,
            )

    return RedirectResponse(url="/admin/blacklist", status_code=303)


@router.post("/blacklist/{entry_id}/delete")
async def post_admin_blacklist_delete(entry_id: int) -> RedirectResponse:
    async with async_session_maker.begin() as session:
        entry: BlacklistedName | None = await session.get(BlacklistedName, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Blacklist entry not found")
        await session.delete(instance=entry)
        LOGGER.info(
            "Removed blacklist entry id=%d name=%r entity_type=%s",
            entry_id,
            entry.name,
            entry.entity_type.value,
        )

    return RedirectResponse(url="/admin/blacklist", status_code=303)
