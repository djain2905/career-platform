from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import HTMLResponse

from app.config import APP_NAME
from app.repository import load_profile

# No auto-generated /docs, /redoc or /openapi.json: every HTML page this app
# serves comes from a template built on base.html, which carries the Google tag.
app = FastAPI(title=APP_NAME, docs_url=None, redoc_url=None, openapi_url=None)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    data, source = load_profile()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": APP_NAME, "data": data, "source": source},
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    data, source = load_profile()
    return templates.TemplateResponse(
        "privacy.html",
        {"request": request, "app_name": APP_NAME, "data": data, "source": source},
    )
