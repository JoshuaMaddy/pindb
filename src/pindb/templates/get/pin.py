from fastapi import Request
from htpy import (
    Element,
    Fragment,
    a,
    div,
    fragment,
    h2,
    i,
    img,
    link,
    p,
    table,
    tbody,
    td,
    tr,
)

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.templates.base import html_base
from pindb.templates.components.back_link import back_link
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.description_block import description_block
from pindb.templates.components.dropdown_panel import dropdown_panel
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.icon_list_element import icon_list_item
from pindb.templates.components.linked_items_row import linked_items_row
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.pending_edit_banner import pending_edit_banner
from pindb.templates.components.pill_link import pill_link
from pindb.templates.components.tag_branding import (
    CATEGORY_COLORS,
    CATEGORY_HOVER_CLASSES,
    CATEGORY_ICONS,
)
from pindb.templates.components.toggle_button import toggle_button
from pindb.utils import domain_from_url, format_currency_code

_IMG_CAROUSEL_HEIGHT: str = (
    "w-full max-h-[30vh] sm:max-h-[60vh] object-contain bg-pin-base-500"
)

_PIN_SWIPER_INIT: str = """
(function () {
  function injectThumbStyles() {
    if (document.getElementById("pin-swiper-thumb-css")) {
      return;
    }
    var st = document.createElement("style");
    st.id = "pin-swiper-thumb-css";
    st.textContent =
      ".pin-swiper-thumbs .swiper-slide{opacity:0.55;cursor:pointer;width:4rem;height:4rem;}" +
      ".pin-swiper-thumbs .swiper-slide-thumb-active{opacity:1;}";
    document.head.appendChild(st);
  }
  function boot() {
    var root = document.getElementById("pin-image-carousel");
    if (!root || !window.Swiper) {
      return;
    }
    injectThumbStyles();
    var mainEl = root.querySelector(".pin-swiper-main");
    if (!mainEl) {
      return;
    }
    var n = parseInt(root.getAttribute("data-slide-count") || "1", 10);
    var thumbEl = root.querySelector(".pin-swiper-thumbs");
    var base = {
      spaceBetween: 0,
      loop: n > 1,
      grabCursor: true,
      keyboard: { enabled: true },
      navigation: {
        nextEl: root.querySelector(".pin-swiper-nav-next"),
        prevEl: root.querySelector(".pin-swiper-nav-prev"),
      },
    };
    if (n <= 1) {
      new window.Swiper(mainEl, base);
      return;
    }
    var thumbSwiper = new window.Swiper(thumbEl, {
      spaceBetween: 10,
      slidesPerView: "auto",
      freeMode: true,
      watchSlidesProgress: true,
    });
    base.thumbs = { swiper: thumbSwiper };
    new window.Swiper(mainEl, base);
  }
  function loadSwiper(cb) {
    if (window.Swiper) {
      cb();
      return;
    }
    var s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js";
    s.async = true;
    s.onload = cb;
    document.head.appendChild(s);
  }
  loadSwiper(boot);
})();
"""


def _pin_image_carousel(request: Request, pin: Pin) -> Fragment:
    """Front/back images as a Swiper carousel (thumbnails, drag, arrows, loop)."""
    front_full: str = str(request.url_for("get_image", guid=pin.front_image_guid))
    front_thumb: str = str(
        request.url_for("get_image", guid=pin.front_image_guid).include_query_params(
            thumbnail=True
        )
    )
    slides: list[tuple[str, str, str]] = [
        ("Front", front_full, front_thumb),
    ]
    if pin.back_image_guid:
        slides.append(
            (
                "Back",
                str(request.url_for("get_image", guid=pin.back_image_guid)),
                str(
                    request.url_for(
                        "get_image", guid=pin.back_image_guid
                    ).include_query_params(thumbnail=True)
                ),
            )
        )
    slide_count: int = len(slides)
    nav_hidden: str = " hidden" if slide_count <= 1 else ""

    main_slides: list[Element] = []
    thumb_slides: list[Element] = []
    for idx, (label, full_url, thumb_url) in enumerate(slides):
        main_slides.append(
            div(class_="swiper-slide flex items-center justify-center bg-pin-base-500")[
                img(
                    alt=f"{label} — {pin.name}",
                    class_=_IMG_CAROUSEL_HEIGHT,
                    loading="eager" if idx == 0 else "lazy",
                    src=full_url,
                )
            ]
        )
        thumb_slides.append(
            div(
                class_="swiper-slide !box-border overflow-hidden rounded border border-pin-base-400"
            )[
                img(
                    alt=f"{label} thumbnail",
                    class_="h-full w-full object-cover",
                    loading="lazy",
                    src=thumb_url,
                )
            ]
        )

    nav_btn: str = (
        "pointer-events-auto !h-10 !w-10 shrink-0 text-accent after:!text-xl "
        "after:!text-accent"
    )
    main_swiper: Element = div(class_="swiper pin-swiper-main w-full min-w-0")[
        div(class_="swiper-wrapper")[*main_slides],
    ]
    nav_prev: Element = div(
        class_="pin-swiper-nav-prev swiper-button-prev absolute !left-auto !right-full top-1/2 z-10 !m-0 !-translate-y-1/2 "
        + nav_btn
        + nav_hidden,
        **{"aria-label": "Previous image"},
    )
    nav_next: Element = div(
        class_="pin-swiper-nav-next swiper-button-next absolute !left-full !right-auto top-1/2 z-10 !m-0 !-translate-y-1/2 "
        + nav_btn
        + nav_hidden,
        **{"aria-label": "Next image"},
    )
    main_row: Element = div(class_="relative w-full overflow-visible")[
        main_swiper,
        nav_prev,
        nav_next,
    ]
    carousel_children: list[Element] = [main_row]
    if slide_count > 1:
        carousel_children.append(
            div(class_="swiper pin-swiper-thumbs w-full overflow-hidden")[
                div(
                    class_="swiper-wrapper !flex !w-full !items-center !justify-center",
                )[*thumb_slides],
            ],
        )

    return fragment[
        link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css",
        ),
        div(
            class_="relative flex w-full flex-col gap-3 min-md:gap-5 overflow-x-visible",
            id="pin-image-carousel",
            **{"data-slide-count": str(slide_count)},
        )[*carousel_children],
    ]


def pin_page(
    request: Request,
    pin: Pin,
    is_favorited: bool = False,
    user_sets: list[PinSet] | None = None,
    owned_entries: list[UserOwnedPin] | None = None,
    wanted_entries: list[UserWantedPin] | None = None,
    has_pending_chain: bool = False,
    viewing_pending: bool = False,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    canonical_url = str(request.url_for("get_pin", id=pin.id))
    pending_url = canonical_url + "?version=pending"
    return html_base(
        title=pin.name,
        request=request,
        script_content=_PIN_SWIPER_INIT,
        body_content=fragment[
            div(
                class_="mx-auto px-10 my-5 gap-2 w-full grid grid-cols-1 min-md:gap-8 min-md:grid-cols-2 min-md:max-w-[160ch]"
            )[
                div(class_="min-md:col-span-2")[
                    back_link(),
                    has_pending_chain
                    and pending_edit_banner(
                        viewing_pending=viewing_pending,
                        canonical_url=canonical_url,
                        pending_url=pending_url,
                    ),
                    page_heading(
                        icon="circle-star",
                        text=("(P) " + pin.name) if pin.is_pending else pin.name,
                        full_width=True,
                        extras=fragment[
                            user
                            and (user.is_admin or user.is_editor)
                            and icon_button(
                                icon="pen",
                                title="Edit pin",
                                href=str(request.url_for("get_edit_pin", id=pin.id)),
                            ),
                            user
                            and user.is_admin
                            and confirm_modal(
                                trigger=icon_button(
                                    icon="trash-2",
                                    title="Delete pin",
                                    variant="danger",
                                ),
                                message=f'Delete the pin "{pin.name}"? This will delete the pin!',
                                form_action=str(
                                    request.url_for(
                                        "post_delete_entity",
                                        entity_type="pin",
                                        id=pin.id,
                                    )
                                ),
                            ),
                        ],
                    ),
                ],
                div(class_="w-full overflow-x-visible")[
                    _pin_image_carousel(request=request, pin=pin),
                ],
                __pin_details(
                    request=request,
                    pin=pin,
                    user=user,
                    is_favorited=is_favorited,
                    user_sets=user_sets or [],
                    owned_entries=owned_entries or [],
                    wanted_entries=wanted_entries or [],
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
    owned_entries: list[UserOwnedPin],
    wanted_entries: list[UserWantedPin],
) -> Element:
    return div(class_="min-md:ml-2")[
        user
        and __user_actions(
            request=request,
            pin=pin,
            is_favorited=is_favorited,
            user_sets=user_sets,
            owned_entries=owned_entries,
            wanted_entries=wanted_entries,
        ),
        h2["Details"],
        div(class_="flex flex-col gap-2")[
            __description(pin=pin),
            __shops(pin=pin, request=request),
            __artists(pin=pin, request=request),
            __links(pin=pin),
            __acquisition(pin=pin),
            __grades(pin=pin),
            __pin_sets(pin=pin, request=request, user_sets=user_sets),
            __posts(pin=pin),
            __height(pin=pin),
            __width(pin=pin),
            __release_date(pin=pin),
            __end_date(pin=pin),
            __limited_edition(pin=pin),
            __number_produced(pin=pin),
            __funding(pin=pin),
            __tags(pin=pin, request=request),
        ],
    ]


def __user_actions(
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
        __add_to_set_panel(request=request, pin=pin, user_sets=user_sets),
        owned_panel(request=request, pin=pin, owned_entries=owned_entries),
        wanted_panel(request=request, pin=pin, wanted_entries=wanted_entries),
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
            class_="flex items-center gap-1 px-2 py-1 rounded-lg border border-pin-base-400 bg-pin-base-450 hover:border-accent cursor-pointer text-pin-base-text",
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


def __shops(
    pin: Pin,
    request: Request,
) -> Element:
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
            pill_link(
                href=str(request.url_for("get_artist", id=artist.id)),
                text=("(P) " + artist.name) if artist.is_pending else artist.name,
            )
            for artist in sorted(pin.artists, key=lambda artist: artist.name)
        ],
    )


def __links(pin: Pin) -> Element | None:
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
                            pin.grades, key=lambda grade: grade.price, reverse=True
                        )
                    ]
                ],
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
            pill_link(
                href=str(request.url_for("get_pin_set", id=ps.id)),
                text=("(P) " + ps.name.title()) if ps.is_pending else ps.name.title(),
            )
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


def __description(pin: Pin) -> Fragment:
    return description_block(pin.description)


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
