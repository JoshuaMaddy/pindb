"""PinDB ASGI application: FastAPI ``app``, middleware stack, and routers."""

from importlib.metadata import PackageNotFoundError, version

# Resolve __version__ before any pindb.* imports so footer / legal pages
# can pull it without a circular import.
try:
    __version__ = version("pindb")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

from pathlib import Path  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

from pindb.audit_events import register_audit_events  # noqa: E402
from pindb.auth import attach_user_middleware  # noqa: E402
from pindb.config import CONFIGURATION  # noqa: E402
from pindb.csrf import csrf_origin_middleware  # noqa: E402
from pindb.http_caching import CacheBustedStaticFiles  # noqa: E402
from pindb.lifespan import lifespan  # noqa: E402
from pindb.routes import (  # noqa: E402
    admin,
    approve,
    auth,
    bulk,
    create,
    delete,
    edit,
    get,
    health,
    legal,
    list,
    search,
    user,
)
from pindb.routes.auth import _test_oauth  # noqa: E402
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

# SessionMiddleware is required by authlib for OAuth state handling.
# Must not use the default cookie name "session" — that collides with
# pindb.auth.SESSION_COOKIE; after OAuth clears Starlette's session, the
# middleware would emit Set-Cookie to expire "session" and wipe the login token.
app.add_middleware(
    SessionMiddleware,
    secret_key=CONFIGURATION.secret_key,
    session_cookie="pindb_starlette_session",
    https_only=CONFIGURATION.session_cookie_secure,
)

# Attach current user to request.state on every request
app.add_middleware(BaseHTTPMiddleware, dispatch=attach_user_middleware)

# CSRF via Origin/Referer check on unsafe methods. Exempts OAuth
# callbacks where the Origin legitimately comes from the provider.
app.add_middleware(BaseHTTPMiddleware, dispatch=csrf_origin_middleware)

# Baseline security response headers (HSTS, CSP report-only, XFO, etc).
app.add_middleware(BaseHTTPMiddleware, dispatch=security_headers_middleware)

app.mount(
    path="/static",
    app=CacheBustedStaticFiles(
        directory=Path(__file__).parent / "static",
    ),
    name="static",
)


@app.get(path="/")
def root(request: Request):
    return HTMLResponse(content=str(homepage(request=request)))


app.include_router(health.router)
app.include_router(admin.router)
app.include_router(approve.router)
app.include_router(auth.router)
if CONFIGURATION.allow_test_oauth_provider:
    app.include_router(_test_oauth.router)
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
