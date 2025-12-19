from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from pindb.routes import create, delete, edit, get, list, search
from pindb.templates.homepage import homepage

app = FastAPI()

app.mount(
    path="/static",
    app=StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


@app.get(path="/")
def root(request: Request):
    return HTMLResponse(content=str(homepage(request=request)))


app.include_router(create.router)
app.include_router(get.router)
app.include_router(edit.router)
app.include_router(list.router)
app.include_router(search.router)
app.include_router(delete.router)
