"""
Responsive pin thumbnails using ``<img src srcset sizes>`` for ``/get/image`` URLs.

Follows the usual responsive-image pattern (width descriptors + ``sizes``):

- **src** — Always set to the **smallest** cached thumbnail URL so non-srcset
  clients and the initial fetch pay minimal bandwidth; browsers with srcset
  replace it when they pick a larger candidate from ``srcset``.
- **srcset** — Comma-separated list of ``URL`` + space + width descriptor
  (``{N}w`` means intrinsic width of that asset is *N* CSS pixels).
- **sizes** — Required with ``w`` descriptors. Callers pass a comma-separated
  list: optional ``(media) length`` pairs (first matching condition wins), then
  a default length — typically using viewport media queries (``min-width`` /
  ``max-width``) so the browser can choose a file before layout paints.

See: responsive images with width descriptors (e.g. web.dev / Learn HTML).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from htpy import VoidElement, img

from pindb.file_handler import THUMBNAIL_SIZES

THUMBNAIL_SRC_FALLBACK_W = min(THUMBNAIL_SIZES)


def thumb_image_url(request: Request, guid: UUID, w: int) -> str:
    """Public URL for a sized WebP thumbnail (``?w=`` query)."""
    return str(request.url_for("get_image", guid=guid).include_query_params(w=w))


def _srcset_value(request: Request, guid: UUID) -> str:
    """Comma-separated ``url 50w, url 100w, ...`` for the given pin image."""
    return ", ".join(
        f"{thumb_image_url(request, guid, tw)} {tw}w" for tw in THUMBNAIL_SIZES
    )


def pin_thumbnail_img(
    request: Request,
    guid: UUID,
    sizes: str,
    *,
    alt: str,
    class_: str | None = None,
    loading: str | None = "lazy",
    decoding: str | None = "async",
    **extra: Any,
) -> VoidElement:
    """Lazy-loaded ``<img>`` with full ``srcset`` (all ``THUMBNAIL_SIZES`` in ``w``)."""
    src = thumb_image_url(request, guid, THUMBNAIL_SRC_FALLBACK_W)
    srcset = _srcset_value(request, guid)
    kwargs: dict[str, Any] = {
        "src": src,
        "srcset": srcset,
        "sizes": sizes,
        "alt": alt,
        **extra,
    }
    if class_ is not None:
        kwargs["class_"] = class_
    if loading is not None:
        kwargs["loading"] = loading
    if decoding is not None:
        kwargs["decoding"] = decoding
    return img(**kwargs)
