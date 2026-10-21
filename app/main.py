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


# Plain `def`, not `async def`: load_profile() blocks on the database, so
# FastAPI runs it in its threadpool instead of stalling the event loop.
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    data, source = load_profile()
    # The profile still renders from saved content when the database is down,
    # but projects don't, so the response says so: 503 until the next healthy
    # read, which needs no restart because every request tries the database.
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "app_name": APP_NAME, "data": data, "source": source},
        status_code=200 if source == "live" else 503,
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    data, source = load_profile()
    return templates.TemplateResponse(
        "privacy.html",
        {"request": request, "app_name": APP_NAME, "data": data, "source": source},
    )
