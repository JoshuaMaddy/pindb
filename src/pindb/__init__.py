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
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

from pindb.audit_events import register_audit_events  # noqa: E402
from pindb.auth import attach_user_middleware  # noqa: E402
from pindb.config import CONFIGURATION  # noqa: E402
from pindb.lifespan import lifespan  # noqa: E402
from pindb.routes import (  # noqa: E402
    admin,
    approve,
    create,
    delete,
    edit,
    get,
    legal,
    list,
    search,
)
from pindb.routes.auth import router as auth_router  # noqa: E402
from pindb.routes.auth._test_oauth import router as test_oauth_router  # noqa: E402
from pindb.routes.bulk import router as bulk_router  # noqa: E402
from pindb.routes.user import router as user_router  # noqa: E402
from pindb.routes.user.collection import router as collection_router  # noqa: E402
from pindb.routes.user.security import router as security_router  # noqa: E402
from pindb.templates.homepage import homepage  # noqa: E402

register_audit_events()

app = FastAPI(lifespan=lifespan)

# SessionMiddleware is required by authlib for OAuth state handling.
# Must not use the default cookie name "session" — that collides with
# pindb.auth.SESSION_COOKIE; after OAuth clears Starlette's session, the
# middleware would emit Set-Cookie to expire "session" and wipe the login token.
app.add_middleware(
    SessionMiddleware,
    secret_key=CONFIGURATION.secret_key,
    session_cookie="pindb_starlette_session",
)

# Attach current user to request.state on every request
app.add_middleware(BaseHTTPMiddleware, dispatch=attach_user_middleware)

app.mount(
    path="/static",
    app=StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


@app.get(path="/")
def root(request: Request):
    return HTMLResponse(content=str(homepage(request=request)))


app.include_router(admin.router)
app.include_router(approve.router)
app.include_router(auth_router)
if CONFIGURATION.allow_test_oauth_provider:
    app.include_router(test_oauth_router)
app.include_router(security_router)
app.include_router(user_router)
app.include_router(collection_router)
app.include_router(create.router)
app.include_router(get.router)
app.include_router(edit.router)
app.include_router(list.router)
app.include_router(search.router)
app.include_router(delete.router)
app.include_router(bulk_router)
app.include_router(legal.router)
