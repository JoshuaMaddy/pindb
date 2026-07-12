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
from htpy import Element, a, div, fragment, hr, p, script, section

from pindb.asset_cache_buster import STATIC_CACHE_BUSTER
from pindb.database.content_report import (
    MIN_REPORT_REASON_LENGTH,
    ReportTargetType,
)
from pindb.database.pin import Pin
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


def _tagged_pins_section(*, request: Request, pins: list[Pin]) -> Element:
    return section(
        class_="flex flex-col gap-2",
        aria_labelledby="display-pins-heading",
    )[
        page_heading(
            icon="pin",
            text=f"Pins in this display ({len(pins)})",
            level=2,
            heading_id="display-pins-heading",
        ),
        div(
            class_=(
                "grid grid-flow-col grid-rows-[1fr_max-content]"
                " [grid-auto-columns:128px] gap-2 pl-1 overflow-x-auto"
            )
        )[[pin_preview_card(request=request, pin=pin) for pin in pins]],
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
    tagged_pins: list[Pin],
    current_user: User | None,
) -> Element:
    username: str = profile_user.username
    is_own_display: bool = (
        current_user is not None and current_user.id == profile_user.id
    )
    layout: DisplayLayout = display.layout if display else DisplayLayout.collage
    heading: str = (display.title if display and display.title else None) or (
        f"{username}'s Display"
    )
    canonical_url: str = str(request.url_for("get_user_display", username=username))

    blurb: str | None = display.blurb if display else None
    is_carousel: bool = layout is DisplayLayout.carousel and bool(images)

    head: Content = [
        # Vendored Swiper must load (deferred, document order) before the boot
        # script runs — same ordering contract as the pin page.
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
        hr if tagged_pins else None,
        _tagged_pins_section(request=request, pins=tagged_pins)
        if tagged_pins
        else None,
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
