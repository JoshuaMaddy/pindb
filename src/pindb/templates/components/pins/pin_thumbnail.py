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

# Stand-in guid used once per request to resolve the ``get_image`` route to a
# concrete URL, which is then split around it. Deriving the shape from the router
# rather than hard-coding "/get/image/{guid}" keeps this honest if the route moves.
_ROUTE_PROBE_GUID: UUID = UUID(int=0)
_URL_PARTS_STATE_KEY: str = "pindb_image_url_parts"


def _image_url_parts(request: Request) -> tuple[str, str]:
    """``(prefix, suffix)`` such that ``prefix + guid + suffix`` is an image URL.

    ``request.url_for`` is a reverse lookup over every route in the app, and an
    entity list page asks for one per thumbnail width per image — ~1450 lookups on
    a full page of tags, which measured ~150ms of pure routing. The shape of the
    URL is identical for all of them, so resolve it once and cache it on the
    request; callers then interpolate the guid and width as plain strings.
    """
    cached: tuple[str, str] | None = getattr(request.state, _URL_PARTS_STATE_KEY, None)
    if cached is None:
        resolved: str = str(request.url_for("get_image", guid=_ROUTE_PROBE_GUID))
        prefix, _, suffix = resolved.partition(str(_ROUTE_PROBE_GUID))
        cached = (prefix, suffix)
        setattr(request.state, _URL_PARTS_STATE_KEY, cached)
    return cached


def thumb_image_url(request: Request, guid: UUID, w: int) -> str:
    """Public URL for a sized WebP thumbnail (``?w=`` query)."""
    prefix, suffix = _image_url_parts(request)
    separator: str = "&" if "?" in suffix else "?"
    return f"{prefix}{guid}{suffix}{separator}w={w}"


def _srcset_value(request: Request, guid: UUID) -> str:
    """Comma-separated ``url 50w, url 100w, ...`` for the given pin image."""
    prefix, suffix = _image_url_parts(request)
    separator: str = "&" if "?" in suffix else "?"
    return ", ".join(
        f"{prefix}{guid}{suffix}{separator}w={tw} {tw}w" for tw in THUMBNAIL_SIZES
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
