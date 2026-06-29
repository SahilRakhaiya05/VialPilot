"""FastAPI application with API routes and web UI."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.vialpilot.api.routes import router as api_router
from src.vialpilot.api.simulator_routes import router as simulator_router
from src.vialpilot.config import DOCS_SITE_URL, GITHUB_REPO_URL, UPLOAD_DIR
from src.vialpilot.db.database import init_db
from src.vialpilot.simulator.scenes import SCENES


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="VialPilot", version="2.0.0")
    app.include_router(api_router)
    app.include_router(simulator_router)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.filters["tojson"] = lambda v, indent=0: json.dumps(v, indent=indent, default=str, ensure_ascii=False)
    templates.env.globals["docs_url"] = DOCS_SITE_URL
    templates.env.globals["github_url"] = GITHUB_REPO_URL

    @app.get("/media")
    async def serve_media(path: str):
        file_path = Path(path).resolve()
        upload_root = UPLOAD_DIR.resolve()
        if not str(file_path).startswith(str(upload_root)) or not file_path.exists():
            raise HTTPException(404, "File not found")
        return FileResponse(str(file_path))

    @app.get("/", response_class=HTMLResponse)
    async def landing(request: Request):
        return templates.TemplateResponse(request, "landing.html")

    @app.get("/dashboard", response_class=HTMLResponse)
    @app.get("/dashboard/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse(
            request, "dashboard.html", {"scenes": SCENES},
        )

    @app.get("/analyzer")
    async def analyzer_redirect():
        """Pipeline Analyzer (Dash) — port 8050."""
        return RedirectResponse("http://127.0.0.1:8050", status_code=302)

    @app.get("/simulator", response_class=HTMLResponse)
    @app.get("/simulator/", response_class=HTMLResponse)
    async def simulator_page(request: Request):
        from src.vialpilot.simulator.session import get_session

        status = get_session().status()
        return templates.TemplateResponse(request, "simulator.html", {"sim": status})

    @app.get("/demo", response_class=HTMLResponse)
    @app.get("/demo/", response_class=HTMLResponse)
    async def demo_page(request: Request):
        return templates.TemplateResponse(request, "demo_compare.html")

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        from src.vialpilot.api.routes import settings

        s = settings()
        return templates.TemplateResponse(request, "settings.html", {"settings": s})

    @app.get("/runs", response_class=HTMLResponse)
    async def history(request: Request):
        from src.vialpilot.db.database import SessionLocal
        from src.vialpilot.db import repository as repo

        db = SessionLocal()
        try:
            runs = [repo.to_run_summary(r) for r in repo.list_runs(db)]
        finally:
            db.close()
        return templates.TemplateResponse(request, "history.html", {"runs": runs})

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    async def run_detail(request: Request, run_id: str):
        from src.vialpilot.db.database import SessionLocal
        from src.vialpilot.db import repository as repo

        db = SessionLocal()
        try:
            run = repo.get_run(db, run_id)
            if not run:
                return RedirectResponse("/runs", status_code=302)
        finally:
            db.close()
        return templates.TemplateResponse(
            request, "run_detail.html", {"run_id": run_id},
        )

    @app.get("/runs/{run_id}/report-view", response_class=HTMLResponse)
    async def report_view(request: Request, run_id: str):
        from src.vialpilot.db.database import SessionLocal
        from src.vialpilot.db import repository as repo
        from src.vialpilot.services.reports import report_to_markdown

        db = SessionLocal()
        try:
            run = repo.get_run(db, run_id)
            if not run:
                return RedirectResponse("/runs", status_code=302)
            md = report_to_markdown(run)
        finally:
            db.close()
        return templates.TemplateResponse(
            request, "report.html", {"run_id": run_id, "markdown": md},
        )

    return app


app = create_app()