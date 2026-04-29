"""
htpy page and fragment builders: `templates/user/pin_list_pages.py`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from itertools import groupby
from typing import Literal

from fastapi import Request
from htpy import (
    Element,
    VoidElement,
    a,
    div,
    hr,
    nav,
    span,
    table,
    tbody,
    td,
    th,
    thead,
    tr,
)

from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.shop import Shop
from pindb.database.user import User
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.routes._urls import artist_url, pin_url, shop_url
from pindb.templates.base import html_base
from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.listing.pagination_controls import pagination_controls
from pindb.templates.components.nav.bread_crumb import bread_crumb
from pindb.templates.components.nav.pill_link import pill_link
from pindb.templates.components.pins.pin_grid import pin_grid
from pindb.templates.components.pins.pin_thumbnail import pin_thumbnail_img
from pindb.templates.list.base import TABLE_LIST_SCROLL
from pindb.templates.pin_image_alt import pin_front_image_alt

PAGE_SIZE: int = 24

ViewMode = Literal["grid", "table"]

_TOGGLE_ACTIVE: str = (
    "px-2 py-1 rounded border border-accent bg-lighter text-accent text-sm no-underline"
)
_TOGGLE_INACTIVE: str = (
    "px-2 py-1 rounded border border-lightest bg-main"
    " text-lightest-hover text-sm no-underline hover:border-accent hover:text-base-text"
)
_TH_CLASS: str = (
    "text-left whitespace-nowrap py-2 px-2 font-medium text-lightest-hover "
    "border-b border-lightest"
)
_TD_CLASS: str = "py-2 px-2 border-b border-lightest align-middle"
_TD_LINK: str = (
    "py-2 px-2 border-b border-lightest align-middle max-w-none [&_a]:whitespace-nowrap"
)
_TABLE_PIN_LIST: str = "border-collapse text-sm w-max min-w-full"


# ---------------------------------------------------------------------------
# Shared shell
# ---------------------------------------------------------------------------


def _list_shell(
    request: Request,
    title: str,
    profile_user: User,
    breadcrumb_label: str,
    page: int,
    total: int,
    view: ViewMode,
    current_url: str,
    content: Element,
) -> Element:
    grid_url: str = f"{current_url}?view=grid&page=1"
    table_url: str = f"{current_url}?view=table&page=1"

    toggle: Element = nav(class_="flex gap-1", aria_label="Pin list layout")[
        a(href=grid_url, class_=_TOGGLE_ACTIVE if view == "grid" else _TOGGLE_INACTIVE)[
            "Grid"
        ],
        a(
            href=table_url,
            class_=_TOGGLE_ACTIVE if view == "table" else _TOGGLE_INACTIVE,
        )["Table"],
    ]

    pagination: Element | None = pagination_controls(
        base_url=current_url,
        page=page,
        total_count=total,
        per_page=PAGE_SIZE,
        extra_params={"view": view},
    )

    return html_base(
        title=title,
        request=request,
        body_content=centered_div(
            content=[
                bread_crumb(
                    entries=[
                        (
                            request.url_for(
                                "get_user_profile", username=profile_user.username
                            ),
                            profile_user.username,
                        ),
                        breadcrumb_label,
                    ]
                ),
                div(class_="flex w-full min-w-0 flex-col gap-2")[
                    page_heading(
                        icon="user",
                        text=f"{profile_user.username} / {breadcrumb_label}",
                        level=1,
                        heading_id="user-pin-list-heading",
                    ),
                    toggle,
                ],
                hr,
                total > 0
                and content
                or empty_state(f"No pins in {breadcrumb_label.lower()} yet."),
                total > 0 and pagination,
            ],
            flex=True,
            col=True,
        ),
    )


# ---------------------------------------------------------------------------
# Shared table helpers
# ---------------------------------------------------------------------------


def _thumbnail(request: Request, pin: Pin) -> VoidElement:
    return pin_thumbnail_img(
        request,
        pin.front_image_guid,
        sizes="(min-width: 48rem) 48px, 44px",
        alt=pin_front_image_alt(pin),
        class_="w-12 h-12 object-contain rounded",
    )


def _pin_button(request: Request, pin: Pin) -> Element:
    return pill_link(
        href=str(
            pin_url(request=request, pin=pin).include_query_params(
                back=str(request.url)
            )
        ),
        text=("(P) " + pin.name) if pin.is_pending else pin.name,
    )


def _shop_links(request: Request, shops: set[Shop]) -> Element:
    if not shops:
        return span(class_="text-lighter-hover")["—"]
    return div(
        class_="inline-flex max-w-none flex-wrap gap-x-2 gap-y-1 [&_a]:whitespace-nowrap",
    )[
        [
            pill_link(
                href=str(shop_url(request=request, shop=shop)),
                text=("(P) " + shop.name) if shop.is_pending else shop.name,
            )
            for shop in sorted(shops, key=lambda shop: shop.name)
        ]
    ]


def _artist_links(request: Request, artists: set[Artist]) -> Element:
    if not artists:
        return span(class_="text-lighter-hover")["—"]
    return div(
        class_="inline-flex max-w-none flex-wrap gap-x-2 gap-y-1 [&_a]:whitespace-nowrap",
    )[
        [
            pill_link(
                href=str(artist_url(request=request, artist=artist)),
                text=("(P) " + artist.name) if artist.is_pending else artist.name,
            )
            for artist in sorted(artists, key=lambda artist: artist.name)
        ]
    ]


_PinEntry = UserOwnedPin | UserWantedPin


def unique_pins(entries: Sequence[_PinEntry]) -> list[Pin]:
    """Deduplicate entries by pin_id, preserving order."""
    seen: set[int] = set()
    pins: list[Pin] = []
    for entry in entries:
        if entry.pin_id not in seen:
            seen.add(entry.pin_id)
            pins.append(entry.pin)
    return pins


def _group_by_pin(entries: Sequence[_PinEntry]) -> list[list[_PinEntry]]:
    return [
        list(group) for _, group in groupby(entries, key=lambda entry: entry.pin_id)
    ]


def _pin_grouped_table(
    *,
    request: Request,
    entries: Sequence[_PinEntry],
    extra_headers: list[str],
    extra_cells: Callable[[_PinEntry], list[Element]],
) -> Element:
    """Generic rowspan table for pin entries grouped by pin.

    ``extra_headers`` are the column headers after the common
    (thumbnail, name, shops, artists) columns.
    ``extra_cells`` receives a single entry row and returns
    the td elements for the extra columns.
    """
    groups = _group_by_pin(entries)
    rows: list[Element] = []

    for group in groups:
        pin: Pin = group[0].pin
        span_count: int = len(group)

        for index, entry in enumerate(group):
            is_first: bool = index == 0

            row_cells: list[Element] = []
            if is_first:
                row_cells.extend(
                    [
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _thumbnail(request=request, pin=pin)
                        ],
                        td(class_=_TD_LINK, rowspan=span_count)[
                            _pin_button(request=request, pin=pin)
                        ],
                        td(class_=_TD_LINK, rowspan=span_count)[
                            _shop_links(request=request, shops=pin.shops)
                        ],
                        td(class_=_TD_LINK, rowspan=span_count)[
                            _artist_links(request=request, artists=pin.artists)
                        ],
                    ]
                )
            row_cells.extend(extra_cells(entry))
            rows.append(tr[row_cells])

    return div(class_=TABLE_LIST_SCROLL)[
        table(class_=_TABLE_PIN_LIST)[
            thead[
                tr[
                    th(class_=_TH_CLASS, scope="col")[
                        span(class_="sr-only")["Thumbnail"],
                    ],
                    th(class_=_TH_CLASS, scope="col")["Name"],
                    th(class_=_TH_CLASS, scope="col")["Shops"],
                    th(class_=_TH_CLASS, scope="col")["Artists"],
                    [
                        th(class_=_TH_CLASS, scope="col")[header]
                        for header in extra_headers
                    ],
                ]
            ],
            tbody[rows],
        ],
    ]


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------


def favorites_list_page(
    request: Request,
    profile_user: User,
    pins: list[Pin],
    total: int,
    page: int,
    view: ViewMode,
) -> Element:
    current_url: str = str(
        request.url_for("user_favorites_list", username=profile_user.username)
    )
    content: Element = (
        pin_grid(request=request, pins=pins)
        if view == "grid"
        else _favorites_table(request=request, pins=pins)
    )
    return _list_shell(
        request=request,
        title=f"{profile_user.username}'s Favorites",
        profile_user=profile_user,
        breadcrumb_label="Favorites",
        page=page,
        total=total,
        view=view,
        current_url=current_url,
        content=content,
    )


def _favorites_table(request: Request, pins: list[Pin]) -> Element:
    return div(class_=TABLE_LIST_SCROLL)[
        table(class_=_TABLE_PIN_LIST)[
            thead[
                tr[
                    th(class_=_TH_CLASS, scope="col")[
                        span(class_="sr-only")["Thumbnail"],
                    ],
                    th(class_=_TH_CLASS, scope="col")["Name"],
                    th(class_=_TH_CLASS, scope="col")["Shops"],
                    th(class_=_TH_CLASS, scope="col")["Artists"],
                ]
            ],
            tbody[
                [
                    tr[
                        td(class_=_TD_CLASS)[_thumbnail(request=request, pin=pin)],
                        td(class_=_TD_LINK)[_pin_button(request=request, pin=pin)],
                        td(class_=_TD_LINK)[
                            _shop_links(request=request, shops=pin.shops)
                        ],
                        td(class_=_TD_LINK)[
                            _artist_links(request=request, artists=pin.artists)
                        ],
                    ]
                    for pin in pins
                ]
            ],
        ],
    ]


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def collection_list_page(
    request: Request,
    profile_user: User,
    owned_pins: list[UserOwnedPin],
    total: int,
    page: int,
    view: ViewMode,
) -> Element:
    current_url: str = str(
        request.url_for("user_collection_list", username=profile_user.username)
    )
    content: Element = (
        pin_grid(
            request=request,
            pins=unique_pins(entries=owned_pins),
        )
        if view == "grid"
        else _collection_table(request=request, owned_pins=owned_pins)
    )
    return _list_shell(
        request=request,
        title=f"{profile_user.username}'s Collection",
        profile_user=profile_user,
        breadcrumb_label="Collection",
        page=page,
        total=total,
        view=view,
        current_url=current_url,
        content=content,
    )


def _collection_table(
    request: Request,
    owned_pins: list[UserOwnedPin],
) -> Element:
    def extra_cells(entry: _PinEntry) -> list[Element]:
        assert isinstance(entry, UserOwnedPin)
        return [
            td(class_=_TD_CLASS)[entry.grade.name if entry.grade is not None else "—"],
            td(class_=_TD_CLASS)[str(entry.quantity)],
            td(class_=_TD_CLASS)[
                str(entry.tradeable_quantity) if entry.tradeable_quantity > 0 else "—"
            ],
        ]

    return _pin_grouped_table(
        request=request,
        entries=owned_pins,
        extra_headers=["Grade", "Qty", "Tradeable"],
        extra_cells=extra_cells,
    )


# ---------------------------------------------------------------------------
# Wants
# ---------------------------------------------------------------------------


def wants_list_page(
    request: Request,
    profile_user: User,
    wanted_pins: list[UserWantedPin],
    total: int,
    page: int,
    view: ViewMode,
) -> Element:
    current_url: str = str(
        request.url_for("user_wants_list", username=profile_user.username)
    )
    content: Element = (
        pin_grid(
            request=request,
            pins=unique_pins(entries=wanted_pins),
        )
        if view == "grid"
        else _wants_table(request=request, wanted_pins=wanted_pins)
    )
    return _list_shell(
        request=request,
        title=f"{profile_user.username}'s Wants",
        profile_user=profile_user,
        breadcrumb_label="Wants",
        page=page,
        total=total,
        view=view,
        current_url=current_url,
        content=content,
    )


def _wants_table(
    request: Request,
    wanted_pins: list[UserWantedPin],
) -> Element:
    def extra_cells(entry: _PinEntry) -> list[Element]:
        return [
            td(class_=_TD_CLASS)[entry.grade.name if entry.grade is not None else "—"],
        ]

    return _pin_grouped_table(
        request=request,
        entries=wanted_pins,
        extra_headers=["Grade"],
        extra_cells=extra_cells,
    )


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------


def trades_list_page(
    request: Request,
    profile_user: User,
    tradeable_entries: list[UserOwnedPin],
    total: int,
    page: int,
    view: ViewMode,
) -> Element:
    current_url: str = str(
        request.url_for("user_trades_list", username=profile_user.username)
    )
    content: Element = (
        pin_grid(
            request=request,
            pins=unique_pins(entries=tradeable_entries),
        )
        if view == "grid"
        else _trades_table(request=request, tradeable_entries=tradeable_entries)
    )
    return _list_shell(
        request=request,
        title=f"{profile_user.username}'s Trades",
        profile_user=profile_user,
        breadcrumb_label="Trades",
        page=page,
        total=total,
        view=view,
        current_url=current_url,
        content=content,
    )


def _trades_table(
    request: Request,
    tradeable_entries: list[UserOwnedPin],
) -> Element:
    def extra_cells(entry: _PinEntry) -> list[Element]:
        assert isinstance(entry, UserOwnedPin)
        return [
            td(class_=_TD_CLASS)[entry.grade.name if entry.grade is not None else "—"],
            td(class_=_TD_CLASS)[str(entry.tradeable_quantity)],
        ]

    return _pin_grouped_table(
        request=request,
        entries=tradeable_entries,
        extra_headers=["Grade", "Tradeable Qty"],
        extra_cells=extra_cells,
    )
