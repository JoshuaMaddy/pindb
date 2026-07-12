"""
FastAPI routes: `routes/list/__init__.py`.
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import async_session_maker
from pindb.database.artist import Artist
from pindb.database.joins import (
    pin_set_memberships,
    pins_artists,
    pins_shops,
    pins_tags,
)
from pindb.database.landing_samples import sample_entities_with_pins
from pindb.database.pin_previews import PinPreviews, load_pin_previews
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.routes.list import artists, pin_sets, shops, tags
from pindb.templates.list.index import list_index_page

router = APIRouter(prefix="/list")


@router.get(path="/")
async def get_list_index(request: Request) -> HTMLResponse:
    async with async_session_maker() as session:
        shop_sample = await sample_entities_with_pins(
            session,
            model=Shop,
            join_table=pins_shops,
            entity_column=pins_shops.c.shop_id,
        )
        tag_sample = await sample_entities_with_pins(
            session,
            model=Tag,
            join_table=pins_tags,
            entity_column=pins_tags.c.tag_id,
        )
        pin_set_sample = await sample_entities_with_pins(
            session,
            model=PinSet,
            join_table=pin_set_memberships,
            entity_column=pin_set_memberships.c.set_id,
            extra_where=PinSet.owner_id.is_(None),
        )
        artist_sample = await sample_entities_with_pins(
            session,
            model=Artist,
            join_table=pins_artists,
            entity_column=pins_artists.c.artists_id,
        )

        shop_previews: PinPreviews = await load_pin_previews(
            session,
            join_table=pins_shops,
            entity_column=pins_shops.c.shop_id,
            entity_ids=[shop.id for shop in shop_sample],
        )
        tag_previews: PinPreviews = await load_pin_previews(
            session,
            join_table=pins_tags,
            entity_column=pins_tags.c.tag_id,
            entity_ids=[tag.id for tag in tag_sample],
        )
        pin_set_previews: PinPreviews = await load_pin_previews(
            session,
            join_table=pin_set_memberships,
            entity_column=pin_set_memberships.c.set_id,
            entity_ids=[pin_set.id for pin_set in pin_set_sample],
        )
        artist_previews: PinPreviews = await load_pin_previews(
            session,
            join_table=pins_artists,
            entity_column=pins_artists.c.artists_id,
            entity_ids=[artist.id for artist in artist_sample],
        )

        return HTMLResponse(
            content=str(
                list_index_page(
                    request=request,
                    shops=shop_sample,
                    shop_previews=shop_previews,
                    tags=tag_sample,
                    tag_previews=tag_previews,
                    pin_sets=pin_set_sample,
                    pin_set_previews=pin_set_previews,
                    artists=artist_sample,
                    artist_previews=artist_previews,
                )
            )
        )


router.include_router(shops.router)
router.include_router(pin_sets.router)
router.include_router(tags.router)
router.include_router(artists.router)
