from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from htpy import div

from pindb.routes import create

app = FastAPI()


@app.get("/")
def root():
    return HTMLResponse(div["home"])


app.include_router(create.router)
