"""The display editor at ``/user/me/display/edit``.

Split deliberately: **title and blurb stay a plain server form** (HTMX + the
existing submit guard already handle two text fields), while everything that is
cross-tile state — layout preview, upload queue, ordering, per-photo caption /
size / pins — lives in the one ``display-editor`` island. Splitting the island up
would force a shared store plus a coordinating parent, i.e. all of the coupling
and none of the simplicity.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from htpy import Element, button, div, form, hr, input, label, script, textarea

from pindb.asset_cache_buster import STATIC_CACHE_BUSTER
from pindb.database.user import User
from pindb.database.user_display import (
    MAX_BLURB_LENGTH,
    MAX_DISPLAY_IMAGES,
    MAX_TITLE_LENGTH,
    UserDisplay,
)
from pindb.templates.base import html_base
from pindb.templates.components.islands import island
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.pins.pin_thumbnail import image_url_prefix

_INPUT_CLASS: str = (
    "w-full rounded border border-lightest bg-main px-3 py-2 text-base-text"
    " focus:border-accent focus:outline-none"
)
_LABEL_CLASS: str = "text-sm text-lightest-hover"


def _settings_form(*, request: Request, display: UserDisplay, username: str) -> Element:
    return form(
        method="post",
        action=str(request.url_for("post_update_user_display")),
        hx_post=str(request.url_for("post_update_user_display")),
        class_="flex flex-col gap-3 max-w-2xl",
        **{
            "data-htmx-submit-guard": "",
            "data-testid": "display-settings-form",
        },
    )[
        label(class_="flex flex-col gap-1")[
            div(class_=_LABEL_CLASS)["Title"],
            input(
                type="text",
                name="title",
                value=display.title or "",
                maxlength=str(MAX_TITLE_LENGTH),
                placeholder=f"{username}'s Display",
                class_=_INPUT_CLASS,
            ),
        ],
        label(class_="flex flex-col gap-1")[
            div(class_=_LABEL_CLASS)[
                "Blurb — shown on the page and in the link preview"
            ],
            textarea(
                name="blurb",
                rows="3",
                maxlength=str(MAX_BLURB_LENGTH),
                placeholder="A few words about your setup…",
                class_=_INPUT_CLASS,
            )[display.blurb or ""],
        ],
        button(type="submit", class_="btn btn-primary w-fit")["Save"],
    ]


def display_edit_page(
    *,
    request: Request,
    display: UserDisplay,
    images: list[dict[str, Any]],
    current_user: User,
) -> Element:
    return html_base(
        title="Edit Display",
        request=request,
        # The WebP encoder is a vendored classic script, deliberately not bundled
        # into the island (see CLAUDE.md); lib/webp.ts falls back to the raw file
        # when it is absent.
        head_content=script(
            **{"type": "module"},
            src=f"/static/vendor/pindb-webp/pindb-webp-encode.js?v={STATIC_CACHE_BUSTER}",
        ),
        template_js_extra=("shared/webp_transcode.js",),
        body_content=centered_div(
            content=[
                page_heading(
                    icon="frame",
                    text="Edit Display",
                    heading_id="edit-display-heading",
                ),
                _settings_form(
                    request=request,
                    display=display,
                    username=current_user.username,
                ),
                hr,
                island(
                    "display-editor",
                    props={
                        "layout": display.layout.value,
                        "maxImages": MAX_DISPLAY_IMAGES,
                        "images": images,
                        "uploadUrl": str(request.url_for("post_user_display_image")),
                        "reorderUrl": str(
                            request.url_for("post_reorder_user_display_images")
                        ),
                        "updateDisplayUrl": str(
                            request.url_for("post_update_user_display")
                        ),
                        # Per-image URLs are built client-side: an image has no id
                        # until it has been uploaded, so url_for cannot pre-resolve
                        # them. Same trick ImageCell.svelte uses for /get/image.
                        "imageBaseUrl": str(
                            request.url_for(
                                "post_update_user_display_image", image_id=0
                            )
                        ).removesuffix("/0"),
                        "pinOptionsUrl": str(
                            request.url_for("get_display_pin_options")
                        ),
                        "viewUrl": str(
                            request.url_for(
                                "get_user_display",
                                username=current_user.username,
                            )
                        ),
                        # Resolved once via the cached route parts, so the island
                        # can build `${prefix}${guid}?w=200` per tile.
                        "thumbUrlPrefix": image_url_prefix(request),
                    },
                ),
            ],
            flex=True,
            col=True,
        ),
    )
