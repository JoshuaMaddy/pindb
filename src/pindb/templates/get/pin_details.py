"""
htpy page and fragment builders: `templates/get/pin_details.py`.

The right-hand details column on the pin page: user actions panel +
per-field rows (shops, artists, links, grades, sets, dimensions, tags,
variants, etc.). Returns a single ``div`` to be slotted next to the
image carousel.
"""

from fastapi import Request
from htpy import Element, Fragment, a, div, fragment, h2, i, p, table, tbody, td, tr
from titlecase import titlecase

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.templates.components.description_block import description_block
from pindb.templates.components.dropdown_panel import dropdown_panel
from pindb.templates.components.icon_list_element import icon_list_item
from pindb.templates.components.linked_items_row import linked_items_row
from pindb.templates.components.pill_link import pill_link
from pindb.templates.components.tag_branding import (
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
    return div(class_="md:ml-2")[
        user
        and _user_actions(
            request=request,
            pin=pin,
            is_favorited=is_favorited,
            user_sets=user_sets,
            owned_entries=owned_entries,
            wanted_entries=wanted_entries,
        ),
        h2["Details"],
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
        trigger=div(
            class_="flex items-center gap-1 px-2 py-1 rounded-lg border border-pin-base-400 bg-pin-base-450 hover:border-accent cursor-pointer text-pin-base-text"
        )[
            i(data_lucide="layout-grid", class_="inline-block"),
            "Add to Set",
        ],
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
            and p(class_="text-sm text-pin-base-300 px-2 py-1")["No sets yet."],
            a(
                href=str(
                    request.url_for("get_create_user_set")
                    if not user_sets
                    else request.url_for("get_me")
                ),
                class_="text-sm text-pin-base-100 no-underline mt-1 pt-1 border-t border-pin-base-400 hover:text-accent",
            )["+ Create a set" if not user_sets else "+ Manage sets"],
        ],
    )


def _shops(pin: Pin, request: Request) -> Element:
    return linked_items_row(
        icon="store",
        label="Shops",
        items=[
            pill_link(
                href=str(request.url_for("get_shop", id=shop.id)),
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
        items=[
            pill_link(
                href=str(request.url_for("get_artist", id=artist.id)),
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
        items=[
            pill_link(
                href=str(request.url_for("get_pin", id=variant.id)),
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
        items=[
            pill_link(
                href=str(request.url_for("get_pin", id=copy.id)),
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
        p(class_="text-base font-semibold sm:text-lg")[
            i(data_lucide="banknote", class_="inline-block pr-2"),
            "Grades",
        ],
        div(class_="ml-4 border border-pin-base-400 w-min")[
            table(class_="border-collapse")[
                tbody[
                    [
                        tr[
                            td(class_="px-2 border-r border-pin-base-400")[grade.name],
                            td(class_="px-2")[
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
        items=[
            pill_link(
                href=str(request.url_for("get_pin_set", id=ps.id)),
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
        items=[
            pill_link(
                href=str(request.url_for("get_tag", id=tag.id)),
                text=("(P) " + tag.display_name)
                if tag.is_pending
                else tag.display_name,
                icon=CATEGORY_ICONS.get(tag.category, "tag"),
                color_classes=CATEGORY_COLORS.get(
                    tag.category, "bg-pin-base-500 text-pin-base-text"
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
