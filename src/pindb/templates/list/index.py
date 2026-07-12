"""
htpy page and fragment builders: `templates/list/index.py`.
"""

from typing import Callable, Sequence, TypeVar

from fastapi import Request
from htpy import BaseElement, Element, a, div, h1, hr, i, nav, span

from pindb.database.artist import Artist
from pindb.database.landing_samples import NARROW_SAMPLES
from pindb.database.pin_previews import PinPreviews
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.routes._urls import artist_url, pin_set_url, shop_url, tag_url
from pindb.templates.base import html_base
from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.components.layout.card import card
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.pins.entity_grid_card import entity_grid_card
from pindb.templates.components.tags.tag_branding import category_badge
from pindb.utils import review_label

_SampleEntity = TypeVar("_SampleEntity", Shop, Tag, Artist, PinSet)


def _quick_links(request: Request) -> Element:
    """2x2 nav cards. Desktop hides this — the column headers below take over."""
    return nav(
        class_="lg:hidden grid grid-cols-2 gap-2",
        aria_label="Browse entity lists",
    )[
        card(href=request.url_for("get_list_shops"), content="Shops", icon="store"),
        card(href=request.url_for("get_list_tags"), content="Tags", icon="tag"),
        card(
            href=request.url_for("get_list_pin_sets"),
            content="Pin Sets",
            icon="layout-grid",
        ),
        card(
            href=request.url_for("get_list_artists"), content="Artists", icon="palette"
        ),
    ]


def _column_header(*, href: str, icon: str, label: str) -> Element:
    return a(
        href=href,
        class_=(
            "group flex items-center gap-2 no-underline text-base-text "
            "font-semibold text-lg px-1 pb-2 border-b border-lightest "
            "hover:text-accent hover:border-accent transition-colors "
            "duration-100 ease-linear"
        ),
    )[
        i(data_lucide=icon, class_="shrink-0", aria_hidden="true"),
        span(class_="grow")[f"All {label}"],
        i(
            data_lucide="arrow-right",
            class_=(
                "shrink-0 transition-transform duration-100 ease-linear "
                "group-hover:translate-x-0.5"
            ),
            aria_hidden="true",
        ),
    ]


def _sample_grid(items: list[Element]) -> Element:
    if not items:
        return empty_state("Nothing here yet.", small=True)
    # Four rows at every size: one card per row when a column is one card wide
    # (lg), two per row once it is two wide (2xl, where the extra four samples
    # un-hide). The subgrid is what keeps those rows aligned *across* the four
    # columns — without it a taller card (a wrapped name, a tag's category
    # badge) pushes only its own column down and the columns drift apart.
    return div(
        class_=(
            "grid grid-cols-2 gap-2 lg:grid-cols-1 2xl:grid-cols-2 "
            "lg:grid-rows-subgrid lg:row-span-4"
        )
    )[*items]


def _explore_column(
    *, href: str, icon: str, label: str, items: list[Element]
) -> Element:
    return div(
        class_="flex flex-col gap-2 min-w-0 lg:grid lg:grid-rows-subgrid lg:row-span-5"
    )[
        _column_header(href=href, icon=icon, label=label),
        _sample_grid(items),
    ]


def _entity_cards(
    *,
    request: Request,
    entities: Sequence[_SampleEntity],
    previews: PinPreviews,
    url_of: Callable[[_SampleEntity], str],
    name_of: Callable[[_SampleEntity], str] = lambda entity: entity.name,
    badge_of: Callable[[_SampleEntity], BaseElement] | None = None,
) -> list[Element]:
    """Sample cards for one column.

    Beyond ``NARROW_SAMPLES`` the cards are hidden until the column is two wide
    (``2xl``), so a column is always exactly four rows tall: four stacked cards at
    ``lg``, eight in 2x4 at ``2xl``. They are rendered rather than dropped because
    the breakpoint is a client-side fact — the server has no viewport to branch on.
    """
    return [
        entity_grid_card(
            request=request,
            href=url_of(entity),
            pins=previews.pins(entity.id),
            pin_count=previews.count(entity.id),
            name=review_label(
                name_of(entity),
                is_pending=entity.is_pending,
                is_rejected=entity.is_rejected,
            ),
            badge=badge_of(entity) if badge_of else None,
            allow_overflow=badge_of is not None,
            # Columns halve in width at 2xl (two cards wide), so the name steps
            # back down a size — at text-xl nearly every name wrapped there.
            name_text_class="text-xl 2xl:text-base",
            additional_classes="" if index < NARROW_SAMPLES else "max-2xl:hidden",
        )
        for index, entity in enumerate(entities)
    ]


def list_index_page(
    request: Request,
    shops: Sequence[Shop],
    shop_previews: PinPreviews,
    tags: Sequence[Tag],
    tag_previews: PinPreviews,
    pin_sets: Sequence[PinSet],
    pin_set_previews: PinPreviews,
    artists: Sequence[Artist],
    artist_previews: PinPreviews,
) -> Element:
    return html_base(
        title="List",
        request=request,
        body_content=centered_div(
            content=[
                div[
                    h1["List"],
                    hr,
                ],
                _quick_links(request),
                div(
                    class_=(
                        "grid grid-cols-1 gap-6 "
                        "lg:grid-cols-4 lg:grid-rows-[auto_auto_auto_auto_auto] "
                        "lg:gap-x-6 lg:gap-y-4"
                    )
                )[
                    _explore_column(
                        href=str(request.url_for("get_list_shops")),
                        icon="store",
                        label="Shops",
                        items=_entity_cards(
                            request=request,
                            entities=shops,
                            previews=shop_previews,
                            url_of=lambda shop: str(
                                shop_url(request=request, shop=shop)
                            ),
                        ),
                    ),
                    _explore_column(
                        href=str(request.url_for("get_list_tags")),
                        icon="tag",
                        label="Tags",
                        items=_entity_cards(
                            request=request,
                            entities=tags,
                            previews=tag_previews,
                            url_of=lambda tag: str(tag_url(request=request, tag=tag)),
                            name_of=lambda tag: tag.display_name,
                            badge_of=lambda tag: category_badge(
                                tag.category,
                                additional_classes=(
                                    "max-md:absolute max-md:-top-2 max-md:-right-2"
                                ),
                            ),
                        ),
                    ),
                    _explore_column(
                        href=str(request.url_for("get_list_pin_sets")),
                        icon="layout-grid",
                        label="Pin Sets",
                        items=_entity_cards(
                            request=request,
                            entities=pin_sets,
                            previews=pin_set_previews,
                            url_of=lambda pin_set: str(
                                pin_set_url(request=request, pin_set=pin_set)
                            ),
                        ),
                    ),
                    _explore_column(
                        href=str(request.url_for("get_list_artists")),
                        icon="palette",
                        label="Artists",
                        items=_entity_cards(
                            request=request,
                            entities=artists,
                            previews=artist_previews,
                            url_of=lambda artist: str(
                                artist_url(request=request, artist=artist)
                            ),
                        ),
                    ),
                ],
            ],
            flex=True,
            col=True,
            content_width="default",
        ),
    )
