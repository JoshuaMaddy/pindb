"""
FastAPI routes: `routes/robots.py`.

A deny-all ``robots.txt``. Crawlers cannot reach anything behind the auth gate
anyway; this exists so the login page itself — the one public URL — does not
get indexed, and so the site's intent is unambiguous to anything that asks.
"""

from fastapi.responses import PlainTextResponse
from fastapi.routing import APIRouter

router = APIRouter()

_ROBOTS = "User-agent: *\nDisallow: /\n"


@router.get("/robots.txt", response_class=PlainTextResponse)
async def get_robots() -> PlainTextResponse:
    return PlainTextResponse(content=_ROBOTS, media_type="text/plain")
