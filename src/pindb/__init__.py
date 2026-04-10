from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from pindb.auth import attach_user_middleware
from pindb.config import CONFIGURATION
from pindb.lifespan import lifespan
from pindb.routes import admin, create, delete, edit, get, list, search
from pindb.routes.auth import router as auth_router
from pindb.routes.bulk import router as bulk_router
from pindb.routes.user import router as user_router
from pindb.templates.homepage import homepage

app = FastAPI(lifespan=lifespan)

# SessionMiddleware is required by authlib for OAuth state handling
app.add_middleware(SessionMiddleware, secret_key=CONFIGURATION.secret_key)

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
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(create.router)
app.include_router(get.router)
app.include_router(edit.router)
app.include_router(list.router)
app.include_router(search.router)
app.include_router(delete.router)
app.include_router(bulk_router)
