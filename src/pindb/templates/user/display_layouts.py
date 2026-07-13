"""The three display-page layouts, plus the shared photo figure.

``size_hint`` spans up to 2x2 grid tiles (``grid`` layout only — see
``_SPAN_CLASSES``). That constraint is what makes ``grid`` a CSS **grid** rather
than true columns-masonry: CSS multi-column has no way to span an item across
columns (``column-span`` only accepts ``all``, which breaks the flow into a
full-width band). Grid with ``grid-flow-dense`` backfills the holes a spanning
tile leaves.

``object_fit`` (cover/contain/fill) is a separate, per-photo, all-layout choice
— it does not interact with ``size_hint`` at all, just how the image fills
whatever box its layout gives it.
"""

from __future__ import annotations

from fastapi import Request
from htpy import Element, div, figcaption, figure, img

from pindb.database.user_display import (
    DisplayImageSize,
    DisplayLayout,
    ObjectFit,
    UserDisplayImage,
)
from pindb.templates.components.pins.pin_thumbnail import full_image_url

# Row height is pinned to the column track width via a container-query calc,
# not left to `auto`/aspect-ratio-on-the-image like a plain 1-col-per-row grid
# would allow. A `row-span-2` tile needs *both* rows it touches to already be
# exactly one column-width tall — `auto` only guarantees that when a neighboring
# 1x1 tile happens to share the row; an explicit `grid-auto-rows` guarantees it
# unconditionally, which is what makes `wide`/`tall`/`large` size hints render as
# true squares-and-rectangles instead of however tall their content pushed them.
_GRID_CONTAINER: str = (
    "grid grid-cols-2 md:grid-cols-3 grid-flow-dense gap-3"
    " [container-type:inline-size]"
    " [grid-auto-rows:calc((100cqw-0.75rem)/2)]"
    " md:[grid-auto-rows:calc((100cqw-1.5rem)/3)]"
)
_VERTICAL_CONTAINER: str = "flex flex-col gap-8 max-w-3xl mx-auto w-full"

# `object-fit` is per-image (``UserDisplayImage.object_fit``), not baked into
# these — they're just the sizing half of the `<img>` class, which does still
# vary by layout (a grid cell is a fixed box; `vertical`'s image is natural flow).
_IMG_SIZE_GRID: str = "w-full h-full rounded-lg pin-zoomable cursor-zoom-in"
_IMG_SIZE_VERTICAL: str = "w-full h-auto rounded-lg pin-zoomable cursor-zoom-in"
_IMG_SIZE_CAROUSEL: str = "w-full h-full rounded-lg pin-zoomable cursor-zoom-in"

_FIT_CLASSES: dict[ObjectFit, str] = {
    ObjectFit.cover: "object-cover",
    ObjectFit.contain: "object-contain",
    ObjectFit.fill: "object-fill",
}

# In the grid layout the tile is a fixed-height cell, so a caption in normal
# flow has nowhere to go — it spills out of its cell and collides with whatever
# is below the grid. Overlay it on the photo instead, on a scrim, for the same
# reason the share card carries one: the text sits on an arbitrary photograph
# and has to stay readable.
_CAPTION_OVERLAY: str = (
    "absolute inset-x-0 bottom-0 rounded-b-lg px-2 py-1.5 text-base text-base-text"
    " wrap-break-word bg-gradient-to-t from-darker/90 to-transparent"
)
# `vertical` has no fixed height, so the caption reads better below the photo.
_CAPTION_BELOW: str = "text-base text-lightest-hover mt-1 wrap-break-word"


def _alt_text(image: UserDisplayImage, username: str) -> str:
    return image.caption or f"A photo of {username}'s pin display"


def _photo_figure(
    *,
    request: Request,
    image: UserDisplayImage,
    username: str,
    img_size_class: str,
    figure_class: str | None = None,
    caption_overlay: bool = True,
) -> Element:
    """One photo. ``pin-zoomable`` + ``data-full`` is all the existing lightbox needs.

    Displays render the stored original, not a thumbnail — a photo of someone's
    shelf is the point of the page, so it deserves full quality even before the
    lightbox click, unlike pin catalog art which is fine downsized.
    """
    classes = "relative " + (figure_class or "") if caption_overlay else figure_class
    full_url = full_image_url(request, image.image_guid)
    img_class = f"{img_size_class} {_FIT_CLASSES[image.object_fit]}"
    return figure(class_=classes)[
        img(
            src=full_url,
            alt=_alt_text(image, username),
            class_=img_class,
            loading="lazy",
            decoding="async",
            data_full=full_url,
        ),
        image.caption
        and figcaption(class_=_CAPTION_OVERLAY if caption_overlay else _CAPTION_BELOW)[
            image.caption
        ],
    ]


# Every shape is a rectangle a CSS grid item can actually cover; there is no
# 3-tile entry because no rectangle spans exactly 3 cells.
_SPAN_CLASSES: dict[DisplayImageSize, str] = {
    DisplayImageSize.normal: "col-span-1 row-span-1",
    DisplayImageSize.wide: "col-span-2 row-span-1",
    DisplayImageSize.tall: "col-span-1 row-span-2",
    DisplayImageSize.large: "col-span-2 row-span-2",
}


def _span_class(image: UserDisplayImage) -> str:
    return _SPAN_CLASSES[image.size_hint]


def _grid(request: Request, images: list[UserDisplayImage], username: str) -> Element:
    return div(class_=_GRID_CONTAINER)[
        [
            _photo_figure(
                request=request,
                image=image,
                username=username,
                img_size_class=_IMG_SIZE_GRID,
                figure_class=_span_class(image),
            )
            for image in images
        ]
    ]


def _vertical(
    request: Request, images: list[UserDisplayImage], username: str
) -> Element:
    # `size_hint` is deliberately a no-op here: every photo is already full
    # width, so there is nothing for the span hint to buy. Not a missing case.
    return div(class_=_VERTICAL_CONTAINER)[
        [
            _photo_figure(
                request=request,
                image=image,
                username=username,
                img_size_class=_IMG_SIZE_VERTICAL,
                caption_overlay=False,
            )
            for image in images
        ]
    ]


def _carousel(
    request: Request, images: list[UserDisplayImage], username: str
) -> Element:
    """Swiper carousel.

    The ids and classes below are the hooks ``templates/js/displays/display_swiper.js``
    binds to; renaming them silently disables the carousel.
    """
    return div(id="display-carousel", class_="w-full max-w-4xl mx-auto")[
        div(
            class_=(
                # Fallback height for no-JS/pre-boot; display_swiper.js overwrites
                # this via inline style with the actual remaining viewport space.
                "swiper display-swiper-main rounded-lg overflow-hidden"
                " h-[24rem] sm:h-[32rem]"
            )
        )[
            div(class_="swiper-wrapper")[
                [
                    div(class_="swiper-slide")[
                        _photo_figure(
                            request=request,
                            image=image,
                            username=username,
                            img_size_class=_IMG_SIZE_CAROUSEL,
                            figure_class="flex flex-col items-center h-full",
                            caption_overlay=False,
                        )
                    ]
                    for image in images
                ]
            ],
            div(class_="swiper-button-prev"),
            div(class_="swiper-button-next"),
            div(class_="swiper-pagination"),
        ]
    ]


_LAYOUTS = {
    DisplayLayout.grid: _grid,
    DisplayLayout.vertical: _vertical,
    DisplayLayout.carousel: _carousel,
}


def display_photos(
    *,
    request: Request,
    layout: DisplayLayout,
    images: list[UserDisplayImage],
    username: str,
) -> Element:
    """Render *images* in the chosen layout."""
    return _LAYOUTS[layout](request, images, username)
