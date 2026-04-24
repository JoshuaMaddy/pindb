"""HTTP cache headers for static deploy-busted assets and content-addressed images."""

import os
from pathlib import Path

from starlette.datastructures import Headers
from starlette.responses import FileResponse, Response
from starlette.staticfiles import NotModifiedResponse, StaticFiles
from starlette.types import Scope

# Pin images are addressed by stable UUID; originals and thumbs can be cached long-term.
# Minimum one day; immutable because the URL always refers to the same bytes.
IMAGE_CACHE_CONTROL = "public, max-age=86400, immutable"

# Vendored JS/CSS and `main.css` are loaded with `?v=<start_time>` so deploy changes the URL.
VENDORED_STATIC_CACHE_CONTROL = "public, max-age=31536000, immutable"


def is_vendored_or_built_css_path(full_path: str | os.PathLike[str]) -> bool:
    """True for files under ``vendor/`` and for ``main.css`` in the static tree."""
    p = Path(full_path)
    return "vendor" in p.parts or p.name == "main.css"


class CacheBustedStaticFiles(StaticFiles):
    """``StaticFiles`` with long cache for ``vendor/*`` and ``main.css``."""

    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        request_headers = Headers(scope=scope)
        response = FileResponse(
            full_path, status_code=status_code, stat_result=stat_result
        )
        if is_vendored_or_built_css_path(str(full_path)):
            response.headers["Cache-Control"] = VENDORED_STATIC_CACHE_CONTROL
        if self.is_not_modified(response.headers, request_headers):
            return NotModifiedResponse(response.headers)
        return response
