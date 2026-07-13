"""The public, shareable display page: ``/user/{username}/display``.

This is the page the whole feature exists to produce. Someone drops the link in a
Discord server, the OG card unfurls with their cover photo and the PinDB
wordmark, and the "Pins in this display" strip carries the click back into the
catalog. Guests see all of it — there is no auth dependency on the route.

A user with no display renders a 200 empty state, never a 404: a shared link must
not break, and the owner needs somewhere to land.
"""

from __future__ import annotations

from fastapi import Request
from htpy import Element, a, div, fragment, hr, link, p, script, section

from pindb.asset_cache_buster import STATIC_CACHE_BUSTER
from pindb.database.content_report import (
    MIN_REPORT_REASON_LENGTH,
    ReportTargetType,
)
from pindb.database.user import User
from pindb.database.user_display import DisplayLayout, UserDisplay, UserDisplayImage
from pindb.templates.base import html_base
from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.components.forms.icon_button import icon_button
from pindb.templates.components.islands import island
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.pins.pin_lightbox import pin_lightbox
from pindb.templates.components.pins.pin_preview_card import pin_preview_card
from pindb.templates.components.seo.opengraph import opengraph_head
from pindb.templates.types import Content
from pindb.templates.user.display_layouts import display_photos


def _share_description(display: UserDisplay | None, username: str) -> str:
    """og:description — the user's blurb when they wrote one."""
    if display and display.blurb:
        return display.blurb
    return f"See {username}'s real-life pin display on PinDB."


def _image_pin_strip(
    *, request: Request, image: UserDisplayImage, index: int
) -> Element:
    """One photo's own row of tagged pins — same pin can appear in several rows."""
    label = image.caption or f"Photo {index + 1}"
    pins = sorted(image.pins, key=lambda pin: pin.id)
    return div(class_="flex flex-col gap-1.5")[
        p(class_="text-sm text-lightest-hover wrap-break-word")[label],
        div(
            class_=(
                "grid grid-flow-col grid-rows-[1fr_max-content]"
                # `overflow-x: auto` forces `overflow-y` to compute as `auto` too
                # (CSS coerces a `visible` axis to `auto` whenever its sibling
                # axis isn't `visible`) — with no vertical room, the pin card's
                # hover tilt/scale (`.pin-3d-card`, `input.css`) then gets
                # clipped and can spawn a page-level vertical scrollbar. `py-3`
                # gives the hover transform room to bleed into padding instead
                # of hitting that clip edge, so nothing needs clipping or
                # scrolling in the first place.
                " [grid-auto-columns:192px] gap-2 px-1 py-3 overflow-x-auto"
            )
        )[[pin_preview_card(request=request, pin=pin) for pin in pins]],
    ]


def _tagged_pins_section(
    *, request: Request, images: list[UserDisplayImage]
) -> Element | None:
    """One strip per photo, instead of one deduped strip for the whole display.

    The same pin can legitimately appear under more than one photo — it's the
    photo that's the context for "why is this pin here", so collapsing repeats
    across photos would throw that context away.
    """
    tagged = [(index, image) for index, image in enumerate(images) if image.pins]
    if not tagged:
        return None
    total = sum(len(image.pins) for _, image in tagged)
    return section(
        class_="flex flex-col gap-4",
        aria_labelledby="display-pins-heading",
    )[
        page_heading(
            icon="pin",
            text=f"Pins in this display ({total})",
            level=2,
            heading_id="display-pins-heading",
        ),
        [
            _image_pin_strip(request=request, image=image, index=index)
            for index, image in tagged
        ],
    ]


def _report_bar(*, request: Request, images: list[UserDisplayImage]) -> Element:
    """Report the cover photo — the entry point into the moderation queue.

    Scoped to one photo rather than the page: a report names a concrete target,
    and the cover is the one every visitor has definitely seen. An admin who acts
    on it lands on the whole display anyway.
    """
    return div(class_="flex justify-end pt-4")[
        island(
            "report-modal",
            props={
                "postUrl": str(request.url_for("post_content_report")),
                "targetType": ReportTargetType.display_image.value,
                "targetId": images[0].id,
                "minLength": MIN_REPORT_REASON_LENGTH,
            },
        )
    ]


def user_display_page(
    *,
    request: Request,
    profile_user: User,
    display: UserDisplay | None,
    images: list[UserDisplayImage],
    current_user: User | None,
) -> Element:
    username: str = profile_user.username
    is_own_display: bool = (
        current_user is not None and current_user.id == profile_user.id
    )
    layout: DisplayLayout = display.layout if display else DisplayLayout.grid
    heading: str = (display.title if display and display.title else None) or (
        f"{username}'s Display"
    )
    canonical_url: str = str(request.url_for("get_user_display", username=username))

    blurb: str | None = display.blurb if display else None
    is_carousel: bool = layout is DisplayLayout.carousel and bool(images)

    head: Content = [
        # Vendored Swiper must load (deferred, document order) before the boot
        # script runs — same ordering contract as the pin page. The stylesheet is
        # load-bearing too: without it `.swiper-wrapper`/`.swiper-slide` have no
        # flex layout or overflow clipping, so slides stack instead of sliding.
        link(
            rel="stylesheet",
            href=f"/static/vendor/swiper.min.css?v={STATIC_CACHE_BUSTER}",
        )
        if is_carousel
        else None,
        script(
            src=f"/static/vendor/swiper.min.js?v={STATIC_CACHE_BUSTER}",
            defer=True,
        )
        if is_carousel
        else None,
        opengraph_head(
            title=heading,
            description=_share_description(display, username),
            canonical_url=canonical_url,
            image_url=str(
                request.url_for(
                    "get_og_image",
                    entity_type="user_display",
                    id=profile_user.id,
                )
            ),
        ),
    ]
    js_extra: tuple[str, ...] = (
        ("displays/display_swiper.js", "pins/pin_lightbox.js")
        if is_carousel
        else ("pins/pin_lightbox.js",)
    )
    pins_section: Element | None = _tagged_pins_section(request=request, images=images)

    body: Content = [
        page_heading(
            icon="frame",
            text=heading,
            extras=[
                is_own_display
                and icon_button(
                    icon="pencil",
                    title="Edit display",
                    href=str(request.url_for("get_edit_user_display")),
                ),
            ],
            heading_id="user-display-heading",
        ),
        a(
            href=str(request.url_for("get_user_profile", username=username)),
            class_="text-sm text-lightest-hover w-fit",
        )[f"by {username}"],
        p(class_="text-lightest-hover max-w-3xl wrap-break-word")[blurb]
        if blurb
        else None,
        hr,
        display_photos(
            request=request,
            layout=layout,
            images=images,
            username=username,
        )
        if images
        else empty_state(
            "No display photos yet — add some to build your page."
            if is_own_display
            else "No display photos yet."
        ),
        hr if pins_section else None,
        pins_section,
        _report_bar(request=request, images=images)
        if (current_user is not None and not is_own_display and images)
        else None,
    ]

    return html_base(
        title=heading,
        request=request,
        template_js_extra=js_extra,
        head_content=head,
        body_content=fragment[
            centered_div(content=body, flex=True, col=True),
            pin_lightbox(),
        ],
    )
