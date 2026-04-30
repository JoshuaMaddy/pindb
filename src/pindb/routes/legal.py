"""
FastAPI routes: `routes/legal.py`.
"""

from fastapi import Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse

from pindb.templates.legal.about import about_page
from pindb.templates.legal.privacy import privacy_page
from pindb.templates.legal.terms import terms_page

router = APIRouter()


@router.get(path="/about")
async def get_about(request: Request) -> HtpyResponse:
    return HtpyResponse(about_page(request=request))


@router.get(path="/privacy")
async def get_privacy(request: Request) -> HtpyResponse:
    return HtpyResponse(privacy_page(request=request))


@router.get(path="/terms")
async def get_terms(request: Request) -> HtpyResponse:
    return HtpyResponse(terms_page(request=request))
