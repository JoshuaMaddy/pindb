"""URL helpers for ``templates/js`` assets (mounted at ``/templates-js``).

``filename`` is a path relative to ``templates/js/`` (e.g. ``shell/pindb_shell.js``).
Always use ``templates_js_url()`` so responses get ``?v=`` deploy busting and
long-lived ``Cache-Control`` (see ``CacheBustedTemplateJsFiles``).
"""

from pindb.asset_cache_buster import STATIC_CACHE_BUSTER


def templates_js_url(filename: str) -> str:
    return f"/templates-js/{filename}?v={STATIC_CACHE_BUSTER}"
