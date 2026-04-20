"""
FastAPI routes: `routes/legal.py`.
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.templates.legal.about import about_page
from pindb.templates.legal.privacy import privacy_page
from pindb.templates.legal.terms import terms_page

router = APIRouter()


@router.get(path="/about")
def get_about(request: Request) -> HTMLResponse:
    return HTMLResponse(content=str(about_page(request=request)))


@router.get(path="/privacy")
def get_privacy(request: Request) -> HTMLResponse:
    return HTMLResponse(content=str(privacy_page(request=request)))


@router.get(path="/terms")
def get_terms(request: Request) -> HTMLResponse:
    return HTMLResponse(content=str(terms_page(request=request)))
