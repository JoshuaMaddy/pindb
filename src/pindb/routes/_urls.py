"""
FastAPI routes: `routes/_urls.py`.

Builds canonical, slugged URLs for shareable entity pages. The slug is
decorative filler before the authoritative ID — handlers ignore it on read
but emit a 301 to the canonical form when it does not match.
"""

import re
import unicodedata

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL

from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag

_SLUG_RE: re.Pattern[str] = re.compile(pattern=r"[^a-z0-9]+")
_MAX_SLUG_LEN: int = 60


def slugify_for_url(name: str, fallback: str) -> str:
    """Render an entity name as an ASCII-only URL path segment.

    Args:
        name (str): The entity's raw display name (may contain unicode,
            apostrophes, slashes, or arbitrary punctuation).
        fallback (str): Returned when slugification yields the empty string
            (e.g. names made entirely of non-ASCII punctuation).

    Returns:
        str: Lowercase ASCII slug of `[a-z0-9_]+` form, max 60 chars.
    """
    decomposed: str = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    collapsed: str = _SLUG_RE.sub(repl="_", string=decomposed.lower()).strip("_")
    truncated: str = collapsed[:_MAX_SLUG_LEN].strip("_")
    return truncated or fallback


def canonical_slug_redirect(
    request: Request,
    route_name: str,
    canonical_slug: str,
    id: int,
) -> RedirectResponse:
    """Build a 301 redirect to the slugged form of the current page.

    Preserves the request's query string so pagination (`?page=2`) and
    pending-view (`?version=...`) survive the redirect.
    """
    target: URL = request.url_for(route_name, slug=canonical_slug, id=id)
    if request.url.query:
        target = target.replace(query=request.url.query)
    return RedirectResponse(url=str(target), status_code=301)


def pin_url(request: Request, pin: Pin) -> URL:
    return request.url_for(
        "get_pin", slug=slugify_for_url(name=pin.name, fallback="pin"), id=pin.id
    )


def tag_url(request: Request, tag: Tag) -> URL:
    return request.url_for(
        "get_tag", slug=slugify_for_url(name=tag.name, fallback="tag"), id=tag.id
    )


def shop_url(request: Request, shop: Shop) -> URL:
    return request.url_for(
        "get_shop", slug=slugify_for_url(name=shop.name, fallback="shop"), id=shop.id
    )


def artist_url(request: Request, artist: Artist) -> URL:
    return request.url_for(
        "get_artist",
        slug=slugify_for_url(name=artist.name, fallback="artist"),
        id=artist.id,
    )


def pin_set_url(request: Request, pin_set: PinSet) -> URL:
    return request.url_for(
        "get_pin_set",
        slug=slugify_for_url(name=pin_set.name, fallback="pin_set"),
        id=pin_set.id,
    )
