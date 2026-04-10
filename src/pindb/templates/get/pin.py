from fastapi import Request
from htpy import (
    Element,
    a,
    div,
    fragment,
    h1,
    h2,
    i,
    img,
    p,
    table,
    tbody,
    td,
    th,
    thead,
    tr,
)

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.back_link import back_link
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.dropdown_panel import dropdown_panel
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.icon_list_element import icon_list_item
from pindb.templates.components.linked_items_row import linked_items_row
from pindb.templates.components.toggle_button import toggle_button
from pindb.utils import domain_from_url, format_currency_code


def pin_page(
    request: Request,
    pin: Pin,
    is_favorited: bool = False,
    user_sets: list[PinSet] | None = None,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    return html_base(
        title=pin.name,
        request=request,
        body_content=fragment[
            div(
                class_="mx-auto px-10 my-5 gap-2 w-full grid grid-cols-1 min-md:gap-4 min-md:grid-cols-2 min-md:max-w-[160ch]"
            )[
                div(class_="min-md:col-span-2")[
                    back_link(),
                    div(class_="flex items-end gap-3")[
                        h1[pin.name],
                        user
                        and user.is_admin
                        and fragment[
                            icon_button(
                                icon="pen",
                                title="Edit pin",
                                href=str(request.url_for("get_edit_pin", id=pin.id)),
                            ),
                            confirm_modal(
                                trigger=icon_button(
                                    icon="trash-2",
                                    title="Delete set",
                                    variant="danger",
                                ),
                                message=f'Delete the pin "{pin.name}"? This will delete the pin!',
                                form_action=str(
                                    request.url_for("post_delete_pin", id=pin.id)
                                ),
                            ),
                        ],
                    ],
                ],
                div(class_="w-full")[
                    img(
                        src=str(
                            request.url_for("get_image", guid=pin.front_image_guid)
                        ),
                        class_="w-full object-contain h-[60vh] bg-pin-base-500",
                    ),
                    pin.back_image_guid
                    and img(
                        src=str(request.url_for("get_image", guid=pin.back_image_guid)),
                        class_="w-full object-contain h-[60vh] bg-pin-base-500",
                    ),
                ],
                __pin_details(
                    request=request,
                    pin=pin,
                    user=user,
                    is_favorited=is_favorited,
                    user_sets=user_sets or [],
                ),
            ]
        ],
    )


def __pin_details(
    request: Request,
    pin: Pin,
    user: User | None,
    is_favorited: bool,
    user_sets: list[PinSet],
) -> Element:
    return div(class_="min-md:ml-2")[
        user
        and __user_actions(
            request=request,
            pin=pin,
            is_favorited=is_favorited,
            user_sets=user_sets,
        ),
        h2["Details"],
        __shops(pin=pin, request=request),
        __artists(pin=pin, request=request),
        __links(pin=pin),
        __acquisition(pin=pin),
        __grades(pin=pin),
        __pin_sets(pin=pin, request=request, user_sets=user_sets),
        __tags(pin=pin, request=request),
        __materials(pin=pin, request=request),
        __description(pin=pin),
        __posts(pin=pin),
        __height(pin=pin),
        __width(pin=pin),
        __release_date(pin=pin),
        __end_date(pin=pin),
        __limited_edition(pin=pin),
        __number_produced(pin=pin),
        __funding(pin=pin),
    ]


def __user_actions(
    request: Request,
    pin: Pin,
    is_favorited: bool,
    user_sets: list[PinSet],
) -> Element:
    return div(class_="flex flex-wrap gap-3 mb-4")[
        favorite_button(request=request, pin_id=pin.id, is_favorited=is_favorited),
        __add_to_set_panel(request=request, pin=pin, user_sets=user_sets),
    ]


# --------------------------------------------------------------------------
# Reusable fragments returned by HTMX toggle endpoints
# --------------------------------------------------------------------------


def favorite_button(request: Request, pin_id: int, is_favorited: bool) -> Element:
    icon_fill = "fill-red-400 stroke-red-400" if is_favorited else ""
    label_text = "Unfavorite" if is_favorited else "Favorite"
    action_url = str(
        request.url_for(
            "unfavorite_pin" if is_favorited else "favorite_pin",
            pin_id=pin_id,
        )
    )
    return div(id=f"favorite-btn-{pin_id}")[
        toggle_button(
            url=action_url,
            is_active=is_favorited,
            target_id=f"favorite-btn-{pin_id}",
            children=[
                i(data_lucide="heart", class_=f"inline-block {icon_fill}".strip()),
                label_text,
            ],
            class_="flex items-center gap-1 px-3 py-1 rounded-lg border border-pin-base-400 bg-pin-base-450 hover:border-accent cursor-pointer text-pin-base-text",
        )
    ]


def set_row(
    request: Request,
    pin_id: int,
    pin_set: PinSet,
    in_set: bool,
) -> Element:
    """Single row in the add-to-set dropdown. Returned by HTMX toggle endpoints."""
    action_url = str(
        request.url_for(
            "remove_pin_from_personal_set" if in_set else "add_pin_to_personal_set",
            set_id=pin_set.id,
            pin_id=pin_id,
        )
    )
    return div(id=f"set-row-{pin_set.id}-{pin_id}")[
        toggle_button(
            url=action_url,
            is_active=in_set,
            target_id=f"set-row-{pin_set.id}-{pin_id}",
            children=[
                i(
                    data_lucide="check-square" if in_set else "square",
                    class_="inline-block shrink-0",
                ),
                pin_set.name,
            ],
            class_="w-full flex items-center gap-2 px-2 py-1 rounded hover:bg-pin-base-450 cursor-pointer text-pin-base-text bg-transparent border-0 text-left font-inherit",
        )
    ]


def __add_to_set_panel(
    request: Request,
    pin: Pin,
    user_sets: list[PinSet],
) -> Element:
    pin_set_ids: set[int] = {ps.id for ps in pin.sets}
    return dropdown_panel(
        trigger=div(
            class_="flex items-center gap-1 px-3 py-1 rounded-lg border border-pin-base-400 bg-pin-base-450 hover:border-accent cursor-pointer text-pin-base-text"
        )[
            i(data_lucide="folder-plus", class_="inline-block"),
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
                href=str(request.url_for("get_my_sets")),
                class_="text-sm text-pin-base-100 no-underline mt-1 pt-1 border-t border-pin-base-400 hover:text-accent",
            )["+ Create a set" if not user_sets else "+ Manage sets"],
        ],
    )


def __shops(
    pin: Pin,
    request: Request,
) -> Element:
    return linked_items_row(
        icon="store",
        label="Shops",
        items=[
            a(href=str(request.url_for("get_shop", id=shop.id)))[shop.name]
            for shop in sorted(pin.shops, key=lambda shop: shop.name)
        ],
    )


def __artists(
    pin: Pin,
    request: Request,
) -> Element | None:
    if not pin.artists:
        return None
    return linked_items_row(
        icon="palette",
        label="Artists",
        items=[
            a(href=str(request.url_for("get_artist", id=artist.id)))[artist.name]
            for artist in sorted(pin.artists, key=lambda artist: artist.name)
        ],
    )


def __links(pin: Pin) -> Element | None:
    if not pin.links:
        return None
    return linked_items_row(
        icon="link",
        label="Links",
        items=[a(href=link.path)[domain_from_url(url=link.path)] for link in pin.links],
    )


def __acquisition(pin: Pin) -> Element:
    return icon_list_item(
        icon="package",
        name="Acquisition Method",
        value=pin.acquisition_type.pretty_name(),
    )


def __grades(pin: Pin) -> Element | None:
    if not pin.grades:
        return None
    return div[
        p(class_="text-lg font-semibold")[
            i(data_lucide="banknote", class_="inline-block pr-2"),
            "Grades",
        ],
        table(class_="border-collapse")[
            thead[
                tr[
                    th(class_="text-left pr-4")["Grade"],
                    th(class_="text-left")["Price"],
                ]
            ],
            tbody[
                [
                    tr[
                        td(class_="pr-4")[grade.name],
                        td[
                            format_currency_code(
                                amount=grade.price, code=pin.currency.code
                            )
                        ],
                    ]
                    for grade in sorted(pin.grades, key=lambda grade: grade.name)
                ]
            ],
        ],
    ]


def __pin_sets(
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
            a(href=str(request.url_for("get_pin_set", id=ps.id)))[ps.name.title()]
            for ps in visible_pin_sets
        ],
    )


def __tags(
    pin: Pin,
    request: Request,
) -> Element:
    return linked_items_row(
        icon="tag",
        label="Tags",
        items=[
            a(href=str(request.url_for("get_tag", id=tag.id)))[tag.name]
            for tag in sorted(pin.tags, key=lambda tag: tag.name)
        ],
    )


def __materials(
    pin: Pin,
    request: Request,
) -> Element:
    return linked_items_row(
        icon="anvil",
        label="Materials",
        items=[
            a(href=str(request.url_for("get_material", id=material.id)))[
                material.name.title()
            ]
            for material in sorted(pin.materials, key=lambda material: material.name)
        ],
    )


def __description(pin: Pin) -> Element | None:
    if pin.description is None:
        return
    return div(class_="flex flex-wrap gap-2 items-baseline")[
        p(class_="text-lg font-semibold")["Description"],
        pin.description,
    ]


def __posts(pin: Pin) -> Element:
    return icon_list_item(
        icon="pin",
        name="Posts",
        value=str(pin.posts),
    )


def __height(pin: Pin) -> Element | None:
    if pin.height is None:
        return
    return icon_list_item(
        icon="move-vertical",
        name="Height",
        value=f"{pin.height:.2f}mm",
    )


def __width(pin: Pin) -> Element | None:
    if pin.width is None:
        return
    return icon_list_item(
        icon="move-horizontal",
        name="Width",
        value=f"{pin.width:.2f}mm",
    )


def __release_date(pin: Pin) -> Element | None:
    if pin.release_date is None:
        return
    return icon_list_item(
        icon="calendar-check-2",
        name="Released",
        value=str(pin.release_date),
    )


def __end_date(pin: Pin) -> Element | None:
    if pin.end_date is None:
        return
    return icon_list_item(
        icon="calendar-x-2",
        name="Ended",
        value=str(pin.end_date),
    )


def __limited_edition(pin: Pin) -> Element | None:
    if pin.limited_edition is None:
        return
    return icon_list_item(
        icon="sparkles",
        name="Limited Edition",
        value="Yes" if pin.limited_edition else "No",
    )


def __number_produced(pin: Pin) -> Element | None:
    if pin.number_produced is None:
        return
    return icon_list_item(
        icon="hash",
        name="Number Produced",
        value=str(pin.number_produced),
    )


def __funding(pin: Pin) -> Element | None:
    if pin.funding_type is None:
        return
    return icon_list_item(
        icon="hand-coins",
        name="Funding",
        value=pin.funding_type.title(),
    )
