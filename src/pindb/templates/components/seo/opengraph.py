"""Open Graph + Twitter Card ``<head>`` fragment used by the public entity pages.

All entity types render the same five OG properties (``title``, ``description``,
``url``, ``image``, ``type``), an optional ``site_name``, and a Twitter
``summary_large_image`` card with the same image. Pin pages pass the pin's own
front image; tag/shop/artist/pin_set pages pass the dynamically composed
``/get/og-image/{type}/{id}`` URL (``pin`` uses the pin's primary key).
"""

from __future__ import annotations

from htpy import Fragment, fragment, link, meta

# Generated cards are always 1200x630 WebP. Tag/shop/artist/pin_set/pin OG
# routes emit exactly that size for consistent scraper hints.
_OG_IMAGE_WIDTH: str = "1200"
_OG_IMAGE_HEIGHT: str = "630"


def opengraph_head(
    *,
    title: str,
    description: str,
    canonical_url: str,
    image_url: str,
    og_type: str = "website",
) -> Fragment:
    """Render OpenGraph + Twitter card meta tags plus a canonical link.

    Args:
        title: Page title for ``og:title`` / ``twitter:title``. The shared site
            suffix (" | PinDB") added by ``html_base`` is intentionally omitted
            here so social previews stay readable.
        description: Short, human-readable summary for the share preview.
        canonical_url: Absolute URL of the page (used for ``og:url`` and a
            ``<link rel="canonical">``).
        image_url: Absolute URL of the share-card image (1200x630 recommended).
        og_type: ``og:type`` value. Defaults to ``website``; pages that
            represent a richer object can pass ``article`` or similar.
    """
    return fragment[
        link(rel="canonical", href=canonical_url),
        meta(property="og:site_name", content="PinDB"),
        meta(property="og:title", content=title),
        meta(property="og:description", content=description),
        meta(property="og:type", content=og_type),
        meta(property="og:url", content=canonical_url),
        meta(property="og:image", content=image_url),
        meta(property="og:image:width", content=_OG_IMAGE_WIDTH),
        meta(property="og:image:height", content=_OG_IMAGE_HEIGHT),
        meta(name="twitter:card", content="summary_large_image"),
        meta(name="twitter:title", content=title),
        meta(name="twitter:description", content=description),
        meta(name="twitter:image", content=image_url),
        meta(name="description", content=description),
    ]
