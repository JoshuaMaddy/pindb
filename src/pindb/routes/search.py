"""
FastAPI routes: `routes/search.py`.
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import async_session_maker
from pindb.database.landing_samples import sample_random_pins
from pindb.database.pin import Pin
from pindb.search.search import search_pin
from pindb.templates.search.pin import search_pin_page, search_results

router = APIRouter(prefix="/search")

DISCOVER_PINS: int = 24
"""Random pins shown under an empty search box."""


@router.get(path="/pin")
async def get_search_pin(
    request: Request,
    q: str | None = None,
) -> HTMLResponse:
    query: str = (q or "").strip()
    pins: list[Pin] | None = None
    discover_pins: list[Pin] | None = None

    async with async_session_maker() as session:
        if query:
            pins = await search_pin(query=query, session=session)
        else:
            # No query — fill the page with a random sample instead of blank space.
            discover_pins = await sample_random_pins(session, limit=DISCOVER_PINS)

        # Live-search typing (HTMX) swaps just the results container; a full page
        # load — including a bookmarked/shared ?q= URL — renders results inline.
        # Rendered inside the session (and to a string) so the preview cards can
        # read each pin's shops/artists; see CLAUDE.md on HtpyResponse's lazy render.
        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=str(
                    search_results(
                        request=request,
                        pins=pins,
                        query=query,
                        discover_pins=discover_pins,
                    )
                )
            )

        return HTMLResponse(
            content=str(
                search_pin_page(
                    request=request,
                    initial_query=query or None,
                    pins=pins,
                    discover_pins=discover_pins,
                )
            )
        )
