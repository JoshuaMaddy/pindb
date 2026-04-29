"""
htpy page and fragment builders: `templates/get/pin_details.py`.

The right-hand details column on the pin page: user actions panel +
per-field rows (shops, artists, links, grades, sets, dimensions, tags,
variants, etc.). Returns a single ``div`` to be slotted next to the
image carousel.
"""

from fastapi import Request
from htpy import (
    Element,
    Fragment,
    a,
    aside,
    button,
    div,
    fragment,
    h2,
    h3,
    i,
    p,
    table,
    tbody,
    td,
    th,
    thead,
    tr,
)
from titlecase import titlecase

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.routes._urls import artist_url, pin_set_url, pin_url, shop_url, tag_url
from pindb.templates.components.display.description_block import description_block
from pindb.templates.components.display.dropdown_panel import dropdown_panel
from pindb.templates.components.display.icon_list_element import icon_list_item
from pindb.templates.components.display.linked_items_row import linked_items_row
from pindb.templates.components.nav.pill_link import pill_link
from pindb.templates.components.tags.tag_branding import (
    CATEGORY_COLORS,
    CATEGORY_HOVER_CLASSES,
    CATEGORY_ICONS,
)
from pindb.templates.get.pin_fragments import favorite_button, set_row
from pindb.utils import domain_from_url, format_currency_code, format_pin_dimension_mm


def pin_details(
    request: Request,
    pin: Pin,
    user: User | None,
    is_favorited: bool,
    user_sets: list[PinSet],
    owned_entries: list[UserOwnedPin],
    wanted_entries: list[UserWantedPin],
) -> Element:
    return aside(class_="md:ml-2", aria_labelledby="pin-details-heading")[
        user
        and _user_actions(
            request=request,
            pin=pin,
            is_favorited=is_favorited,
            user_sets=user_sets,
            owned_entries=owned_entries,
            wanted_entries=wanted_entries,
        ),
        h2(id="pin-details-heading")["Details"],
        div(class_="flex flex-col gap-2")[
            _description(pin=pin),
            _shops(pin=pin, request=request),
            _artists(pin=pin, request=request),
            _links(pin=pin),
            _acquisition(pin=pin),
            _grades(pin=pin),
            _pin_sets(pin=pin, request=request, user_sets=user_sets),
            _posts(pin=pin),
            _height(request=request, pin=pin),
            _width(request=request, pin=pin),
            _release_date(pin=pin),
            _end_date(pin=pin),
            _limited_edition(pin=pin),
            _number_produced(pin=pin),
            _funding(pin=pin),
            _tags(pin=pin, request=request),
            _variants(pin=pin, request=request),
            _unauthorized_copies(pin=pin, request=request),
        ],
    ]


def _user_actions(
    request: Request,
    pin: Pin,
    is_favorited: bool,
    user_sets: list[PinSet],
    owned_entries: list[UserOwnedPin],
    wanted_entries: list[UserWantedPin],
) -> Element:
    from pindb.templates.get.pin_collection import owned_panel, wanted_panel

    return div(class_="flex flex-wrap gap-2 mb-4")[
        favorite_button(request=request, pin_id=pin.id, is_favorited=is_favorited),
        _add_to_set_panel(request=request, pin=pin, user_sets=user_sets),
        owned_panel(request=request, pin=pin, owned_entries=owned_entries),
        wanted_panel(request=request, pin=pin, wanted_entries=wanted_entries),
    ]


def _add_to_set_panel(
    request: Request,
    pin: Pin,
    user_sets: list[PinSet],
) -> Element:
    pin_set_ids: set[int] = {ps.id for ps in pin.sets}
    return dropdown_panel(
        trigger=button(
            type="button",
            class_="flex items-center gap-1 px-2 py-1 rounded-lg border border-lightest bg-lighter hover:border-accent cursor-pointer text-base-text text-left",
            **{
                ":aria-expanded": "open",
            },
            aria_haspopup="menu",
            aria_controls="pin-add-to-set-panel",
        )[
            i(data_lucide="layout-grid", class_="inline-block", aria_hidden="true"),
            "Add to Set",
        ],
        panel_id="pin-add-to-set-panel",
        content=fragment[
            [
                set_row(
                    request=request,
                    pin_id=pin.id,
                    pin_set=ps,
                    in_set=ps.id in pin_set_ids,
                )
                for ps in user_sets
            ],
            not user_sets
            and p(class_="text-sm text-lightest-hover px-2 py-1")["No sets yet."],
            a(
                href=str(
                    request.url_for("get_create_user_set")
                    if not user_sets
                    else request.url_for("get_me")
                ),
                class_="text-sm text-base-text no-underline mt-1 pt-1 border-t border-lightest hover:text-accent",
            )["+ Create a set" if not user_sets else "+ Manage sets"],
        ],
    )


def _shops(pin: Pin, request: Request) -> Element:
    return linked_items_row(
        icon="store",
        label="Shops",
        heading_level=3,
        items=[
            pill_link(
                href=str(shop_url(request=request, shop=shop)),
                text=("(P) " + shop.name) if shop.is_pending else shop.name,
            )
            for shop in sorted(pin.shops, key=lambda shop: shop.name)
        ],
    )


def _artists(pin: Pin, request: Request) -> Element | None:
    if not pin.artists:
        return None
    return linked_items_row(
        icon="palette",
        label="Artists",
        heading_level=3,
        items=[
            pill_link(
                href=str(artist_url(request=request, artist=artist)),
                text=("(P) " + artist.name) if artist.is_pending else artist.name,
            )
            for artist in sorted(pin.artists, key=lambda artist: artist.name)
        ],
    )


def _links(pin: Pin) -> Element | None:
    if not pin.links:
        return None
    return linked_items_row(
        icon="link",
        label="Links",
        heading_level=3,
        items=[
            pill_link(href=link.path, text=domain_from_url(url=link.path))
            for link in pin.links
        ],
    )


def _variants(pin: Pin, request: Request) -> Element | None:
    if not pin.variants:
        return None
    return linked_items_row(
        icon="copy",
        label="Variants",
        heading_level=3,
        items=[
            pill_link(
                href=str(pin_url(request=request, pin=variant)),
                text=("(P) " + variant.name) if variant.is_pending else variant.name,
            )
            for variant in sorted(pin.variants, key=lambda v: v.name)
        ],
    )


def _unauthorized_copies(pin: Pin, request: Request) -> Element | None:
    if not pin.unauthorized_copies:
        return None
    return linked_items_row(
        icon="triangle-alert",
        label="Unauthorized Copies",
        heading_level=3,
        items=[
            pill_link(
                href=str(pin_url(request=request, pin=copy)),
                text=("(P) " + copy.name) if copy.is_pending else copy.name,
            )
            for copy in sorted(pin.unauthorized_copies, key=lambda c: c.name)
        ],
    )


def _acquisition(pin: Pin) -> Element:
    return icon_list_item(
        icon="package",
        name="Acquisition Method",
        value=pin.acquisition_type.pretty_name(),
    )


def _grades(pin: Pin) -> Element | None:
    if not pin.grades:
        return None
    return div[
        h3(
            id="pin-details-grades-heading",
            class_="text-base font-semibold sm:text-lg m-0",
        )[
            i(
                data_lucide="banknote",
                class_="inline-block pr-2",
                aria_hidden="true",
            ),
            "Grades",
        ],
        div(class_="border border-lightest w-full rounded")[
            table(
                class_="border-collapse w-full",
                aria_labelledby="pin-details-grades-heading",
            )[
                thead(class_="border-b border-lightest bg-main")[
                    tr[
                        th(
                            scope="col",
                            class_="text-left pl-2 w-min whitespace-nowrap",
                        )["Name"],
                        th(
                            scope="col",
                            class_="text-right pr-2 pl-2 w-full",
                        )["Price"],
                    ]
                ],
                tbody[
                    [
                        tr[
                            td(
                                class_="px-2 border-r border-lightest w-min whitespace-nowrap"
                            )[grade.name],
                            td(class_="text-right px-2 w-full")[
                                format_currency_code(
                                    amount=grade.price, code=pin.currency.code
                                )
                            ],
                        ]
                        for grade in sorted(
                            pin.grades,
                            key=lambda g: (
                                g.price is None,
                                -(g.price if g.price is not None else 0.0),
                                g.name,
                            ),
                        )
                    ]
                ],
            ],
        ],
    ]


def _pin_sets(
    pin: Pin,
    request: Request,
    user_sets: list[PinSet],
) -> Element | None:
    visible_pin_sets: list[PinSet] = [
        ps for ps in pin.sets if ps.owner_id is None or ps in user_sets
    ]
    if not visible_pin_sets:
        return None

    return linked_items_row(
        icon="layout-grid",
        label="Pin Sets",
        heading_level=3,
        items=[
            pill_link(
                href=str(pin_set_url(request=request, pin_set=ps)),
                text=("(P) " + titlecase(ps.name))
                if ps.is_pending
                else titlecase(ps.name),
            )
            for ps in visible_pin_sets
        ],
    )


def _tags(pin: Pin, request: Request) -> Element:
    return linked_items_row(
        icon="tag",
        label="Tags",
        heading_level=3,
        items=[
            pill_link(
                href=str(tag_url(request=request, tag=tag)),
                text=("(P) " + tag.display_name)
                if tag.is_pending
                else tag.display_name,
                icon=CATEGORY_ICONS.get(tag.category, "tag"),
                color_classes=CATEGORY_COLORS.get(
                    tag.category, "bg-main text-base-text"
                ),
                hover_classes=CATEGORY_HOVER_CLASSES.get(
                    tag.category, "hover:border-accent hover:text-accent"
                ),
            )
            for tag in sorted(pin.tags, key=lambda tag: (tag.category, tag.name))
        ],
    )


def _description(pin: Pin) -> Fragment:
    return description_block(pin.description)


def _posts(pin: Pin) -> Element:
    return icon_list_item(
        icon="pin",
        name="Posts",
        value=str(pin.posts),
    )


def _height(request: Request, pin: Pin) -> Element | None:
    if pin.height is None:
        return None
    unit: str = getattr(request.state, "dimension_unit", "mm")
    return icon_list_item(
        icon="move-vertical",
        name="Height",
        value=format_pin_dimension_mm(pin.height, unit),
    )


def _width(request: Request, pin: Pin) -> Element | None:
    if pin.width is None:
        return None
    unit: str = getattr(request.state, "dimension_unit", "mm")
    return icon_list_item(
        icon="move-horizontal",
        name="Width",
        value=format_pin_dimension_mm(pin.width, unit),
    )


def _release_date(pin: Pin) -> Element | None:
    if pin.release_date is None:
        return None
    return icon_list_item(
        icon="calendar-check-2",
        name="Released",
        value=str(pin.release_date),
    )


def _end_date(pin: Pin) -> Element | None:
    if pin.end_date is None:
        return None
    return icon_list_item(
        icon="calendar-x-2",
        name="Ended",
        value=str(pin.end_date),
    )


def _limited_edition(pin: Pin) -> Element | None:
    if pin.limited_edition is None:
        return None
    return icon_list_item(
        icon="sparkles",
        name="Limited Edition",
        value="Yes" if pin.limited_edition else "No",
    )


def _number_produced(pin: Pin) -> Element | None:
    if pin.number_produced is None:
        return None
    return icon_list_item(
        icon="hash",
        name="Number Produced",
        value=str(pin.number_produced),
    )


def _funding(pin: Pin) -> Element | None:
    if pin.funding_type is None:
        return None
    return icon_list_item(
        icon="hand-coins",
        name="Funding",
        value=titlecase(pin.funding_type),
    )
