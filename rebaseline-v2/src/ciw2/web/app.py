"""单用户 Web 平台（FastAPI）。默认只监听 127.0.0.1；对外部署时设置 CIW_ACCESS_TOKEN。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ciw2.config import Settings, get_settings
from ciw2.domain.availability import HistoricalReportUnavailable
from ciw2.export import encode_export, fact_export
from ciw2.pipeline.runner import stage_table
from ciw2.render.portal import STATIC, render_report
from ciw2.service import LLMFactory, RunRequestError, Service, default_llms

HERE = Path(__file__).resolve().parent


class NewProject(BaseModel):
    indication: str
    reports: list[str] = ["A"]
    request_text: str = ""
    focus: str = ""
    cutoff_date: str | None = None
    start: bool = True


def create_app(settings: Settings | None = None, llm_factory: LLMFactory = default_llms,
               background: bool = True) -> FastAPI:
    svc = Service(settings or get_settings(), llm_factory)
    app = FastAPI(title="临床竞品调研平台", docs_url="/api/docs")
    app.state.svc = svc
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
    tpl = Jinja2Templates(directory=str(HERE / "templates"))
    token = os.environ.get("CIW_ACCESS_TOKEN", "").strip()

    @app.exception_handler(HistoricalReportUnavailable)
    @app.exception_handler(RunRequestError)
    async def _unavailable(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({'detail': str(exc)}, status_code=409)

    @app.middleware("http")
    async def _auth(request: Request, call_next: Any) -> Any:
        if token and not request.url.path.startswith("/static"):
            given = request.query_params.get("token") or request.cookies.get("ciw_token") \
                or request.headers.get("x-ciw-token")
            if given != token:
                return JSONResponse({"error": "需要访问令牌"}, status_code=401)
            resp = await call_next(request)
            if request.query_params.get("token"):
                resp.set_cookie("ciw_token", token, httponly=True, samesite="strict")
            return resp
        return await call_next(request)

    def _project(pid: str) -> dict[str, Any]:
        p = svc.db.project(pid)
        if p is None:
            raise HTTPException(404, "项目不存在")
        return p

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Any:
        projects = svc.db.query("SELECT * FROM projects ORDER BY created_at DESC")
        for p in projects:
            p["run"] = svc.latest_run(p["id"])
        return tpl.TemplateResponse(request, "index.html", {"projects": projects})

    @app.post("/projects")
    def create_form(indication: str = Form(...), reports: Annotated[list[str] | None, Form()] = None, request_text: str = Form(""),
                    focus: str = Form(""), cutoff_date: str = Form("")) -> Any:
        pid = svc.create_project(indication, reports or ['A'], request_text, focus, cutoff_date or None)
        svc.start_run(pid, background=background)
        return RedirectResponse(f"/projects/{pid}", status_code=303)

    @app.post("/api/projects")
    def create_api(body: NewProject) -> Any:
        pid = svc.create_project(body.indication, body.reports, body.request_text, body.focus, body.cutoff_date)
        run_id = svc.start_run(pid, background=background) if body.start else None
        return {"project_id": pid, "run_id": run_id}

    @app.post("/api/projects/{pid}/runs")
    def new_run(pid: str, resume_run: str | None = None) -> Any:
        _project(pid)
        return {"run_id": svc.start_run(pid, resume_run=resume_run, background=background)}

    @app.post("/projects/{pid}/runs")
    def new_run_form(pid: str, resume_run: str = Form("")) -> Any:
        _project(pid)
        svc.start_run(pid, resume_run=resume_run or None, background=background)
        return RedirectResponse(f"/projects/{pid}", status_code=303)

    @app.get("/api/runs/{rid}")
    def run_status(rid: str) -> Any:
        run = svc.db.one("SELECT * FROM runs WHERE id=?", (rid,))
        if not run:
            raise HTTPException(404, "运行不存在")
        return {**run, "stages": stage_table(svc.db, rid, _project(run["project_id"])["reports"])}

    @app.get("/api/runs/{rid}/steps")
    def run_steps(rid: str, stage: str | None = None, limit: int = 500) -> Any:
        sql, params = "SELECT * FROM agent_steps WHERE run_id=?", [rid]
        if stage:
            sql += " AND stage=?"
            params.append(stage)
        return svc.db.query(sql + " ORDER BY id LIMIT ?", [*params, limit])

    @app.get("/api/projects/{pid}/facts")
    def facts(pid: str, field_prefix: str = "", status: str = "") -> Any:
        _project(pid)
        rows = svc.db.current_facts(pid)
        return [f for f in rows if f["field"].startswith(field_prefix) and (not status or f["status"] == status)]

    @app.get('/api/projects/{pid}/facts/export')
    def export_facts(pid: str, format: Literal['json', 'csv'] = 'json',
                     field_prefix: str = '', status: str = '') -> Response:
        _project(pid)
        payload = fact_export(svc.db, pid, field_prefix, status)
        try:
            content = encode_export(payload, format)
        except ValueError as exc:
            raise HTTPException(409, '当前资料含不可导出值，请核对原始记录') from exc
        return Response(content, media_type='application/json' if format == 'json' else 'text/csv',
                        headers={'Content-Disposition': f'attachment; filename="ciw2-facts.{format}"',
                                 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})

    @app.get("/api/projects/{pid}/coverage")
    def coverage(pid: str) -> Any:
        run = svc.latest_run(pid)
        return svc.db.query("SELECT * FROM coverage WHERE run_id=? ORDER BY id", (run["id"],)) if run else []

    @app.get("/projects/{pid}", response_class=HTMLResponse)
    def project_page(request: Request, pid: str) -> Any:
        p = _project(pid)
        runs = svc.db.query("SELECT * FROM runs WHERE project_id=? ORDER BY created_at DESC", (pid,))
        latest = runs[0] if runs else None
        stages = stage_table(svc.db, latest["id"], p["reports"]) if latest else []
        cov = svc.db.query("SELECT route_id, region, status, COUNT(*) n, SUM(hits) hits FROM coverage WHERE run_id=? "
                           "GROUP BY route_id, region, status", (latest["id"],)) if latest else []
        counts = {t: len(svc.db.entities(pid, t)) for t in ("drug", "trial", "company", "target")}
        return tpl.TemplateResponse(request, "project.html", {
            "p": p, "runs": runs, "latest": latest, "stages": stages, "coverage": cov, "counts": counts,
            "n_facts": len(svc.db.current_facts(pid))})

    @app.get("/projects/{pid}/portal/{report}", response_class=HTMLResponse)
    def portal(pid: str, report: str) -> Any:
        p = _project(pid)
        report = report.upper()
        if report not in p["reports"]:
            raise HTTPException(404, "该项目未包含此报告")
        return render_report(svc.db, pid, report, findings=svc.latest_findings(pid, report))

    return app


def app_from_env() -> FastAPI:  # uvicorn ciw2.web.app:app_from_env --factory
    return create_app()
