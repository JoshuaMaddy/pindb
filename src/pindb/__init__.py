from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from htpy import div

from pindb.routes import create, get, images

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


@app.get("/")
def root():
    return HTMLResponse(div["home"])


app.include_router(create.router)
app.include_router(get.router)
app.include_router(images.router)
