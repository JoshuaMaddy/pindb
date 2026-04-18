from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from pindb.audit_events import register_audit_events
from pindb.auth import attach_user_middleware
from pindb.config import CONFIGURATION
from pindb.lifespan import lifespan
from pindb.routes import admin, approve, create, delete, edit, get, list, search
from pindb.routes.auth import router as auth_router
from pindb.routes.auth._test_oauth import router as test_oauth_router
from pindb.routes.bulk import router as bulk_router
from pindb.routes.user import router as user_router
from pindb.routes.user.collection import router as collection_router
from pindb.routes.user.security import router as security_router
from pindb.templates.homepage import homepage

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
