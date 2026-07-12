"""The four display-page layouts, plus the shared photo figure.

The ``feature`` size hint means "span two columns and two rows". That constraint
is what forced ``collage`` to be a CSS **grid** rather than true columns-masonry:
CSS multi-column has no way to span an item across columns (``column-span`` only
accepts ``all``, which breaks the flow into a full-width band). Grid with
``grid-flow-dense`` backfills the holes a feature tile leaves, which is what makes
it read as an intentional collage instead of a grid with gaps.

The tradeoff that buys: fixed row heights mean ``object-cover``, so photos are
cropped to their tile. ``vertical`` is the uncropped layout.
"""

from __future__ import annotations

from fastapi import Request
from htpy import Element, div, figcaption, figure

from pindb.database.user_display import (
    DisplayImageSize,
    DisplayLayout,
    UserDisplayImage,
)
from pindb.templates.components.pins.pin_thumbnail import (
    full_image_url,
    pin_thumbnail_img,
)

# Feature tiles span two columns, so a photo can be at most half the grid width.
_GRID_SIZES: str = "(min-width: 64rem) 50vw, (min-width: 48rem) 66vw, 100vw"
_VERTICAL_SIZES: str = "(min-width: 48rem) 48rem, 100vw"

# `row-span-2` is meaningless without an explicit row height — with implicit
# `auto` rows a feature tile just gets a taller content box and the collage
# collapses back into a plain grid. This is the load-bearing class.
_COLLAGE_CONTAINER: str = (
    "grid grid-cols-2 lg:grid-cols-4 auto-rows-[9rem] sm:auto-rows-[11rem]"
    " grid-flow-dense gap-3"
)
_GRID_CONTAINER: str = "grid grid-cols-2 md:grid-cols-3 grid-flow-dense gap-3"
_VERTICAL_CONTAINER: str = "flex flex-col gap-8 max-w-3xl mx-auto w-full"

_IMG_COVER: str = "w-full h-full object-cover rounded-lg pin-zoomable cursor-zoom-in"
_IMG_CONTAIN: str = (
    "w-full h-auto object-contain rounded-lg pin-zoomable cursor-zoom-in"
)

# In the cover layouts the tile is a fixed-height grid cell, so a caption in
# normal flow has nowhere to go — it spills out of its cell and collides with
# whatever is below the grid. Overlay it on the photo instead, on a scrim, for
# the same reason the share card carries one: the text sits on an arbitrary
# photograph and has to stay readable.
_CAPTION_OVERLAY: str = (
    "absolute inset-x-0 bottom-0 rounded-b-lg px-2 py-1.5 text-sm text-base-text"
    " wrap-break-word bg-gradient-to-t from-darker/90 to-transparent"
)
# `vertical` has no fixed height, so the caption reads better below the photo.
_CAPTION_BELOW: str = "text-sm text-lightest-hover mt-1 wrap-break-word"


def _alt_text(image: UserDisplayImage, username: str) -> str:
    return image.caption or f"A photo of {username}'s pin display"


def _photo_figure(
    *,
    request: Request,
    image: UserDisplayImage,
    username: str,
    sizes: str,
    img_class: str,
    figure_class: str | None = None,
    caption_overlay: bool = True,
) -> Element:
    """One photo. ``pin-zoomable`` + ``data-full`` is all the existing lightbox needs."""
    classes = "relative " + (figure_class or "") if caption_overlay else figure_class
    return figure(class_=classes)[
        pin_thumbnail_img(
            request,
            image.image_guid,
            sizes=sizes,
            alt=_alt_text(image, username),
            class_=img_class,
            data_full=full_image_url(request, image.image_guid),
        ),
        image.caption
        and figcaption(class_=_CAPTION_OVERLAY if caption_overlay else _CAPTION_BELOW)[
            image.caption
        ],
    ]


def _span_class(image: UserDisplayImage, *, rows: bool) -> str:
    if image.size_hint is not DisplayImageSize.feature:
        return "col-span-1"
    return "col-span-2 row-span-2" if rows else "col-span-2"


def _collage(
    request: Request, images: list[UserDisplayImage], username: str
) -> Element:
    return div(class_=_COLLAGE_CONTAINER)[
        [
            _photo_figure(
                request=request,
                image=image,
                username=username,
                sizes=_GRID_SIZES,
                img_class=_IMG_COVER,
                figure_class=f"{_span_class(image, rows=True)} min-h-0",
            )
            for image in images
        ]
    ]


def _grid(request: Request, images: list[UserDisplayImage], username: str) -> Element:
    return div(class_=_GRID_CONTAINER)[
        [
            _photo_figure(
                request=request,
                image=image,
                username=username,
                sizes=_GRID_SIZES,
                img_class=f"{_IMG_COVER} aspect-square",
                figure_class=_span_class(image, rows=False),
            )
            for image in images
        ]
    ]


def _vertical(
    request: Request, images: list[UserDisplayImage], username: str
) -> Element:
    # `feature` is deliberately a no-op here: every photo is already full width
    # and uncropped, so there is nothing for the hint to buy. Not a missing case.
    return div(class_=_VERTICAL_CONTAINER)[
        [
            _photo_figure(
                request=request,
                image=image,
                username=username,
                sizes=_VERTICAL_SIZES,
                img_class=_IMG_CONTAIN,
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
        div(class_="swiper display-swiper-main rounded-lg overflow-hidden")[
            div(class_="swiper-wrapper")[
                [
                    div(class_="swiper-slide")[
                        _photo_figure(
                            request=request,
                            image=image,
                            username=username,
                            sizes=_VERTICAL_SIZES,
                            img_class=(
                                "w-full h-[24rem] sm:h-[32rem] object-contain"
                                " rounded-lg pin-zoomable cursor-zoom-in"
                            ),
                            figure_class="flex flex-col items-center",
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
    DisplayLayout.collage: _collage,
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
