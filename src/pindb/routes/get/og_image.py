"""
FastAPI routes: `routes/get/og_image.py`.

Generates a 1200x630 Open Graph card for ``tag`` / ``shop`` / ``artist`` /
``pin_set`` pages. The card is composed at request time on top of the prebuilt
``opengraph-image-blank.webp`` base, with the entity name and up to four
randomly-sampled pin thumbnails. Pin pages don't use this route — they expose
the pin's own front image directly via ``/get/image/{guid}``.

Cached for one hour: the random pin sample is allowed to drift over time, but
short-lived caching keeps social-media scrapers from hammering the renderer
between previews.
"""

from typing import Sequence
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import Response
from fastapi.routing import APIRouter
from sqlalchemy import Row, Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database import (
    Artist,
    Pin,
    PinSet,
    Shop,
    Tag,
    async_session_maker,
)
from pindb.database.joins import (
    pin_set_memberships,
    pins_artists,
    pins_shops,
    pins_tags,
)
from pindb.file_handler import (
    THUMBNAIL_SIZES,
    ensure_sized_thumbnail_on_disk,
    image_file_path,
    load_image,
    thumbnail_storage_key,
)
from pindb.og_image import build_entity_og_image

router = APIRouter()

# Width whose stored thumbnail best matches the 252-px square stamped onto
# the OG card. Must be one of THUMBNAIL_SIZES.
_PIN_THUMB_WIDTH: int = 400
assert _PIN_THUMB_WIDTH in THUMBNAIL_SIZES

_OG_CACHE_CONTROL: str = "public, max-age=3600"
_PIN_SAMPLE_SIZE: int = 4


async def _entity_lookup(
    session: AsyncSession, entity_type: str, entity_id: int
) -> tuple[str, Table, str] | None:
    """Resolve ``entity_type`` to ``(name, join_table, pin_id_col)`` or ``None``.

    Returns ``None`` when the entity doesn't exist or is hidden by the audit
    filter (soft-deleted, unapproved-for-guests, etc.).
    """
    if entity_type == "tag":
        tag = await session.get(Tag, entity_id)
        return (tag.display_name, pins_tags, "tag_id") if tag else None
    if entity_type == "shop":
        shop = await session.get(Shop, entity_id)
        return (shop.name, pins_shops, "shop_id") if shop else None
    if entity_type == "artist":
        artist = await session.get(Artist, entity_id)
        return (artist.name, pins_artists, "artists_id") if artist else None
    if entity_type == "pin_set":
        pin_set = await session.get(PinSet, entity_id)
        return (pin_set.name, pin_set_memberships, "set_id") if pin_set else None
    return None


async def _sample_pin_thumbnails(
    session: AsyncSession, join_table: Table, pin_id_col: str, entity_id: int
) -> list[bytes]:
    """Pick up to four random visible pins and load their 400-px thumbnails."""
    fk_col = join_table.c[pin_id_col]
    rows: Sequence[Row[tuple[UUID]]] = (
        await session.execute(
            select(Pin.front_image_guid)
            .join(join_table, Pin.id == join_table.c.pin_id)
            .where(fk_col == entity_id)
            .order_by(func.random())
            .limit(_PIN_SAMPLE_SIZE)
        )
    ).all()

    images: list[bytes] = []
    for (guid,) in rows:
        guid_str = str(guid)
        ensure_sized_thumbnail_on_disk(guid_str, _PIN_THUMB_WIDTH)
        key = thumbnail_storage_key(guid_str, _PIN_THUMB_WIDTH)
        path = image_file_path(key)
        if path is not None:
            images.append(path.read_bytes())
            continue
        data = load_image(key)
        if data is None:
            # Fall back to the original if no thumbnail is reachable.
            data = load_image(guid_str)
        if data is not None:
            images.append(data)
    return images


@router.get(
    path="/og-image/{entity_type}/{id}",
    response_model=None,
    name="get_og_image",
)
async def get_og_image(entity_type: str, id: int) -> Response:
    """Return a 1200x630 WebP OG card for the requested entity."""
    if entity_type not in ("tag", "shop", "artist", "pin_set"):
        raise HTTPException(status_code=404, detail="Unsupported entity type")

    async with async_session_maker() as session:
        resolved = await _entity_lookup(session, entity_type, id)
        if resolved is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        name, join_table, pin_id_col = resolved
        pin_images = await _sample_pin_thumbnails(session, join_table, pin_id_col, id)

    webp_bytes = build_entity_og_image(name=name, pin_image_bytes=pin_images)
    return Response(
        content=webp_bytes,
        media_type="image/webp",
        headers={"Cache-Control": _OG_CACHE_CONTROL},
    )
