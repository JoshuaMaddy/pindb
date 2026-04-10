from __future__ import annotations

from itertools import groupby
from typing import Literal

from fastapi import Request
from htpy import (
    Element,
    VoidElement,
    a,
    div,
    hr,
    img,
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
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.empty_state import empty_state
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.pill_link import pill_link
from pindb.templates.components.pin_grid import pin_grid

PAGE_SIZE: int = 24

ViewMode = Literal["grid", "table"]

_TOGGLE_ACTIVE: str = "px-2 py-1 rounded border border-accent bg-pin-base-450 text-accent text-sm no-underline"
_TOGGLE_INACTIVE: str = (
    "px-2 py-1 rounded border border-pin-base-400 bg-pin-base-500"
    " text-pin-base-300 text-sm no-underline hover:border-accent hover:text-pin-base-text"
)
_TH_CLASS: str = (
    "text-left py-2 px-2 font-medium text-pin-base-300 border-b border-pin-base-400"
)
_TD_CLASS: str = "py-2 px-2 border-b border-pin-base-400 align-middle"
_TD_CLASS_NO_BORDER: str = "py-2 px-2 align-middle"


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
    total_pages: int = max(1, -(-total // PAGE_SIZE))

    grid_url: str = f"{current_url}?view=grid&page=1"
    table_url: str = f"{current_url}?view=table&page=1"

    toggle: Element = div(class_="flex gap-1")[
        a(href=grid_url, class_=_TOGGLE_ACTIVE if view == "grid" else _TOGGLE_INACTIVE)[
            "Grid"
        ],
        a(
            href=table_url,
            class_=_TOGGLE_ACTIVE if view == "table" else _TOGGLE_INACTIVE,
        )["Table"],
    ]

    prev_url: str = f"{current_url}?view={view}&page={page - 1}" if page > 1 else ""
    next_url: str = (
        f"{current_url}?view={view}&page={page + 1}" if page < total_pages else ""
    )

    pagination: Element = div(
        class_="flex gap-4 items-center justify-center py-4 text-sm"
    )[
        a(href=prev_url, class_="text-accent no-underline hover:underline")
        if prev_url
        else span(class_="text-pin-base-400")["←"],
        span(class_="text-pin-base-300")[
            f"Page {page} of {total_pages} ({total} pins)"
        ],
        a(href=next_url, class_="text-accent no-underline hover:underline")
        if next_url
        else span(class_="text-pin-base-400")["→"],
    ]

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
                div(class_="flex items-baseline justify-between gap-4")[
                    page_heading(
                        icon="user",
                        text=f"{profile_user.username} / {breadcrumb_label}",
                        level=1,
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
    return img(
        src=str(
            request.url_for(
                "get_image", guid=pin.front_image_guid
            ).include_query_params(thumbnail=True)
        ),
        class_="w-12 h-12 object-contain rounded",
    )


def _pin_button(request: Request, pin: Pin) -> Element:
    return pill_link(href=str(request.url_for("get_pin", id=pin.id)), text=pin.name)


def _shop_links(request: Request, shops: set[Shop]) -> Element:
    if not shops:
        return span(class_="text-pin-base-400")["—"]
    return div(class_="flex flex-wrap gap-x-2 gap-y-1")[
        [
            pill_link(
                href=str(request.url_for("get_shop", id=shop.id)),
                text=shop.name,
            )
            for shop in sorted(shops, key=lambda shop: shop.name)
        ]
    ]


def _artist_links(request: Request, artists: set[Artist]) -> Element:
    if not artists:
        return span(class_="text-pin-base-400")["—"]
    return div(class_="flex flex-wrap gap-x-2 gap-y-1")[
        [
            pill_link(
                href=str(request.url_for("get_artist", id=artist.id)),
                text=artist.name,
            )
            for artist in sorted(artists, key=lambda artist: artist.name)
        ]
    ]


def _unique_pins_from_owned(owned_pins: list[UserOwnedPin]) -> list[Pin]:
    seen: set[int] = set()
    pins: list[Pin] = []
    for entry in owned_pins:
        if entry.pin_id not in seen:
            seen.add(entry.pin_id)
            pins.append(entry.pin)
    return pins


def _unique_pins_from_wanted(wanted_pins: list[UserWantedPin]) -> list[Pin]:
    seen: set[int] = set()
    pins: list[Pin] = []
    for entry in wanted_pins:
        if entry.pin_id not in seen:
            seen.add(entry.pin_id)
            pins.append(entry.pin)
    return pins


def _group_by_pin(entries: list[UserOwnedPin]) -> list[list[UserOwnedPin]]:
    return [
        list(group) for _, group in groupby(entries, key=lambda entry: entry.pin_id)
    ]


def _group_wanted_by_pin(entries: list[UserWantedPin]) -> list[list[UserWantedPin]]:
    return [
        list(group) for _, group in groupby(entries, key=lambda entry: entry.pin_id)
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
    return table(class_="w-full border-collapse text-sm")[
        thead[
            tr[
                th(class_=_TH_CLASS)[""],
                th(class_=_TH_CLASS)["Name"],
                th(class_=_TH_CLASS)["Shops"],
                th(class_=_TH_CLASS)["Artists"],
            ]
        ],
        tbody[
            [
                tr[
                    td(class_=_TD_CLASS)[_thumbnail(request=request, pin=pin)],
                    td(class_=_TD_CLASS)[_pin_button(request=request, pin=pin)],
                    td(class_=_TD_CLASS)[_shop_links(request=request, shops=pin.shops)],
                    td(class_=_TD_CLASS)[
                        _artist_links(request=request, artists=pin.artists)
                    ],
                ]
                for pin in pins
            ]
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
            pins=_unique_pins_from_owned(owned_pins=owned_pins),
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
    groups: list[list[UserOwnedPin]] = _group_by_pin(entries=owned_pins)
    rows: list[Element] = []

    for group in groups:
        pin: Pin = group[0].pin
        span_count: int = len(group)

        for index, entry in enumerate(group):
            is_first: bool = index == 0
            is_last: bool = index == span_count - 1
            grade_td_class: str = _TD_CLASS if is_last else _TD_CLASS_NO_BORDER

            row_cells: list[Element] = []
            if is_first:
                row_cells.extend(
                    [
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _thumbnail(request=request, pin=pin)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _pin_button(request=request, pin=pin)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _shop_links(request=request, shops=pin.shops)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _artist_links(request=request, artists=pin.artists)
                        ],
                    ]
                )
            row_cells.extend(
                [
                    td(class_=grade_td_class)[
                        entry.grade.name if entry.grade is not None else "—"
                    ],
                    td(class_=grade_td_class)[str(entry.quantity)],
                    td(class_=grade_td_class)[
                        str(entry.tradeable_quantity)
                        if entry.tradeable_quantity > 0
                        else "—"
                    ],
                ]
            )
            rows.append(tr[row_cells])

    return table(class_="w-full border-collapse text-sm")[
        thead[
            tr[
                th(class_=_TH_CLASS)[""],
                th(class_=_TH_CLASS)["Name"],
                th(class_=_TH_CLASS)["Shops"],
                th(class_=_TH_CLASS)["Artists"],
                th(class_=_TH_CLASS)["Grade"],
                th(class_=_TH_CLASS)["Qty"],
                th(class_=_TH_CLASS)["Tradeable"],
            ]
        ],
        tbody[rows],
    ]


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
            pins=_unique_pins_from_wanted(wanted_pins=wanted_pins),
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
    groups: list[list[UserWantedPin]] = _group_wanted_by_pin(entries=wanted_pins)
    rows: list[Element] = []

    for group in groups:
        pin: Pin = group[0].pin
        span_count: int = len(group)

        for index, entry in enumerate(group):
            is_first: bool = index == 0
            is_last: bool = index == span_count - 1
            grade_td_class: str = _TD_CLASS if is_last else _TD_CLASS_NO_BORDER

            row_cells: list[Element] = []
            if is_first:
                row_cells.extend(
                    [
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _thumbnail(request=request, pin=pin)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _pin_button(request=request, pin=pin)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _shop_links(request=request, shops=pin.shops)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _artist_links(request=request, artists=pin.artists)
                        ],
                    ]
                )
            row_cells.append(
                td(class_=grade_td_class)[
                    entry.grade.name if entry.grade is not None else "—"
                ]
            )
            rows.append(tr[row_cells])

    return table(class_="w-full border-collapse text-sm")[
        thead[
            tr[
                th(class_=_TH_CLASS)[""],
                th(class_=_TH_CLASS)["Name"],
                th(class_=_TH_CLASS)["Shops"],
                th(class_=_TH_CLASS)["Artists"],
                th(class_=_TH_CLASS)["Grade"],
            ]
        ],
        tbody[rows],
    ]


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
            pins=_unique_pins_from_owned(owned_pins=tradeable_entries),
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
    groups: list[list[UserOwnedPin]] = _group_by_pin(entries=tradeable_entries)
    rows: list[Element] = []

    for group in groups:
        pin: Pin = group[0].pin
        span_count: int = len(group)

        for index, entry in enumerate(group):
            is_first: bool = index == 0
            is_last: bool = index == span_count - 1
            grade_td_class: str = _TD_CLASS if is_last else _TD_CLASS_NO_BORDER

            row_cells: list[Element] = []
            if is_first:
                row_cells.extend(
                    [
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _thumbnail(request=request, pin=pin)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _pin_button(request=request, pin=pin)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _shop_links(request=request, shops=pin.shops)
                        ],
                        td(class_=_TD_CLASS, rowspan=span_count)[
                            _artist_links(request=request, artists=pin.artists)
                        ],
                    ]
                )
            row_cells.extend(
                [
                    td(class_=grade_td_class)[
                        entry.grade.name if entry.grade is not None else "—"
                    ],
                    td(class_=grade_td_class)[str(entry.tradeable_quantity)],
                ]
            )
            rows.append(tr[row_cells])

    return table(class_="w-full border-collapse text-sm")[
        thead[
            tr[
                th(class_=_TH_CLASS)[""],
                th(class_=_TH_CLASS)["Name"],
                th(class_=_TH_CLASS)["Shops"],
                th(class_=_TH_CLASS)["Artists"],
                th(class_=_TH_CLASS)["Grade"],
                th(class_=_TH_CLASS)["Tradeable Qty"],
            ]
        ],
        tbody[rows],
    ]
