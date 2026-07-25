"""PinDB ASGI application: FastAPI ``app``, middleware stack, and routers."""

from importlib.metadata import PackageNotFoundError, version

from fastapi.middleware.gzip import GZipMiddleware

# Resolve __version__ before any pindb.* imports so footer / legal pages
# can pull it without a circular import.
try:
    __version__ = version("pindb")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

from pathlib import Path  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exception_handlers import (  # noqa: E402
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from htpy.starlette import HtpyResponse  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402

from pindb.audit_events import register_audit_events  # noqa: E402
from pindb.auth import attach_user_middleware  # noqa: E402
from pindb.config import CONFIGURATION  # noqa: E402
from pindb.csrf import csrf_origin_middleware  # noqa: E402
from pindb.database import async_session_maker  # noqa: E402
from pindb.database.pin import Pin  # noqa: E402
from pindb.htmx_toast import htmx_error_toast  # noqa: E402
from pindb.http_caching import (  # noqa: E402
    CacheBustedStaticFiles,
    CacheBustedTemplateJsFiles,
)
from pindb.lifespan import lifespan  # noqa: E402
from pindb.require_login import require_login_middleware  # noqa: E402
from pindb.routes import (  # noqa: E402
    admin,
    approve,
    auth,
    bulk,
    create,
    delete,
    docs,
    edit,
    get,
    health,
    legal,
    list,
    messages,
    report,
    robots,
    search,
    user,
)
from pindb.routes.user import collection, security  # noqa: E402
from pindb.security_headers import security_headers_middleware  # noqa: E402
from pindb.templates.homepage import homepage  # noqa: E402

register_audit_events()

app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Default-deny auth gate. Added BEFORE attach_user so it runs AFTER it
# (Starlette nests middleware in reverse add-order) and can read the
# already-resolved request.state.user without a second DB round-trip.
app.add_middleware(BaseHTTPMiddleware, dispatch=require_login_middleware)

# Attach current user to request.state on every request
app.add_middleware(BaseHTTPMiddleware, dispatch=attach_user_middleware)

# CSRF via Origin/Referer check on unsafe methods. No exemptions — the OAuth
# callbacks that needed one are gone.
app.add_middleware(BaseHTTPMiddleware, dispatch=csrf_origin_middleware)

# Baseline security response headers (HSTS, CSP report-only, XFO, etc).
app.add_middleware(BaseHTTPMiddleware, dispatch=security_headers_middleware)

# Gzip
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=7)


app.mount(
    path="/static",
    app=CacheBustedStaticFiles(
        directory=Path(__file__).parent / "static",
    ),
    name="static",
)

app.mount(
    path="/templates-js",
    app=CacheBustedTemplateJsFiles(directory=str(CONFIGURATION.templates_js_dir)),
    name="templates_js",
)


_FIELD_LABELS: dict[str, str] = {
    "name": "Name",
    "acquisition_type": "Acquisition type",
    "grade_names": "Grade name",
    "grade_prices": "Grade price",
    "front_image": "Front image",
    "back_image": "Back image",
    "currency_id": "Currency",
    "shop_ids": "Shop",
    "tag_ids": "Tag",
    "artist_ids": "Artist",
}


def _humanize_field(raw: str) -> str:
    return _FIELD_LABELS.get(raw, raw.replace("_", " ").capitalize())


def _format_validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    missing = [
        str(err["loc"][-1])
        for err in errors
        if err.get("type") == "missing" and err.get("loc")
    ]
    if missing:
        labels = [_humanize_field(name) for name in missing]
        if len(labels) == 1:
            return f"{labels[0]} is required."
        return "Missing required fields: " + ", ".join(labels) + "."
    if errors:
        first = errors[0]
        loc = first.get("loc") or ("",)
        field = _humanize_field(str(loc[-1]))
        return f"{field}: {first.get('msg', 'invalid value')}"
    return "Invalid form submission."


@app.exception_handler(RequestValidationError)
async def _htmx_validation_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    if request.headers.get("HX-Request"):
        return htmx_error_toast(message=_format_validation_message(exc))
    return await request_validation_exception_handler(request, exc)


@app.get(path="/")
async def root(request: Request):
    async with async_session_maker() as db:
        pin_count: int = (await db.scalar(select(func.count(Pin.id)))) or 0
        r = await db.scalars(
            select(Pin)
            .where(Pin.front_image_guid.is_not(None))
            .order_by(func.random())
            .limit(60)
            .options(
                selectinload(Pin.shops),
                selectinload(Pin.artists),
            )
        )
        pins = r.all()
        return HtpyResponse(
            homepage(request=request, pins=[*pins], pin_count=pin_count)
        )


app.include_router(health.router)
app.include_router(admin.router)
app.include_router(approve.router)
app.include_router(auth.router)
app.include_router(security.router)
app.include_router(user.router)
app.include_router(collection.router)
app.include_router(create.router)
app.include_router(get.router)
app.include_router(edit.router)
app.include_router(list.router)
app.include_router(search.router)
app.include_router(delete.router)
app.include_router(bulk.router)
app.include_router(legal.router)
app.include_router(docs.router)
app.include_router(messages.router)
app.include_router(report.router)
app.include_router(robots.router)
