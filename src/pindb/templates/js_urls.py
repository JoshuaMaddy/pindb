"""URL helpers for ``templates/js`` assets (mounted at ``/templates-js``)."""

from pindb.asset_cache_buster import STATIC_CACHE_BUSTER


def templates_js_url(filename: str) -> str:
    return f"/templates-js/{filename}?v={STATIC_CACHE_BUSTER}"
