from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from starlette.responses import HTMLResponse

from app import repository
from app.main import app, templates

MEASUREMENT_ID = "G-V64QT2T9EG"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "app" / "templates"
PAGES = sorted(p.name for p in TEMPLATES_DIR.glob("*.html") if p.name != "base.html")


@pytest.mark.parametrize("name", PAGES)
def test_every_page_template_extends_base(name):
    first_line = (TEMPLATES_DIR / name).read_text().splitlines()[0]
    assert first_line == '{% extends "base.html" %}'


@pytest.mark.parametrize("name", PAGES)
def test_every_page_renders_the_tag_exactly_once(name):
    html = templates.get_template(name).render(data=repository.MINIMAL, source="live")
    assert html.count("googletagmanager.com/gtag/js") == 1
    assert html.count(f"gtag/js?id={MEASUREMENT_ID}") == 1
    assert html.count(f"gtag('config', '{MEASUREMENT_ID}')") == 1
    assert html.index("googletagmanager.com/gtag/js") < html.index("<meta charset")


def test_only_template_pages_serve_html():
    # A page route added outside the templates (or FastAPI's /docs) would skip the tag.
    html_routes = {
        r.path for r in app.routes
        if isinstance(r, APIRoute) and r.response_class is HTMLResponse
    }
    other_routes = {
        r.path for r in app.routes
        if isinstance(r, APIRoute) and r.response_class is not HTMLResponse
    }
    assert html_routes == {"/", "/privacy"}
    assert other_routes == {"/health"}
    assert app.docs_url is None and app.redoc_url is None and app.openapi_url is None
