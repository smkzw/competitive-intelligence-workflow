"""应用服务：把配置、存储、LLM、Skill、工具组装成一次运行。Web 与 CLI 共用。"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import ciw2.sources  # noqa: F401  注册全部工具
from ciw2.config import Settings
from ciw2.domain.availability import HistoricalReportUnavailable, require_supported_cutoff
from ciw2.harness.fallback import FallbackLLM
from ciw2.harness.llm import LLM, LLMError, OpenAICompatLLM
from ciw2.harness.skills import load_skills
from ciw2.pipeline.context import RunContext
from ciw2.pipeline.runner import execute, execute_in_background
from ciw2.store.cas import CAS
from ciw2.store.db import DB

LLMFactory = Callable[[Settings], tuple[LLM, LLM | None]]


class RunRequestError(ValueError):
    pass


def default_llms(s: Settings) -> tuple[LLM, LLM | None]:
    import json
    import os

    main = OpenAICompatLLM(s.llm_base_url, s.llm_api_key, s.llm_model)
    routes: list[LLM] = [main]
    try:
        fallbacks = json.loads(s.llm_fallbacks)
        if not isinstance(fallbacks, list):
            raise TypeError('备用路由必须是数组')
        for route in fallbacks:
            routes.append(OpenAICompatLLM(os.environ[route['base_url_env']],
                os.environ[route['api_key_env']], route['model'],
                timeout_s=float(route.get('timeout_s', 120))))
    except (ValueError, KeyError, TypeError) as exc:
        raise LLMError('备用模型配置不完整或格式不正确') from exc
    check = OpenAICompatLLM(s.llm_base_url, s.llm_api_key, s.llm_check_model) if s.llm_check_model else None
    return FallbackLLM(routes) if len(routes) > 1 else main, check


class Service:
    def __init__(self, settings: Settings, llm_factory: LLMFactory = default_llms) -> None:
        settings.ensure_dirs()
        self.settings = settings
        self.db = DB(settings.db_path)
        self.cas = CAS(settings.cas_dir)
        self.llm_factory = llm_factory
        self.skills = load_skills(settings.skills_dir)

    def create_project(self, indication: str, reports: list[str], request_text: str = "", focus: str = "",
                       cutoff_date: str | None = None) -> str:
        reports = [r for r in ("A", "B", "C") if r in reports] or ["A"]
        return self.db.create_project(indication.strip(), reports, request_text, focus, cutoff_date or None)

    def context(self, project_id: str, run_id: str, **cache: Any) -> RunContext:
        llm, check = self.llm_factory(self.settings)
        return RunContext(db=self.db, cas=self.cas, settings=self.settings, llm=llm, skills=self.skills,
                          project_id=project_id, run_id=run_id, check_llm=check, cache=dict(cache))

    def start_run(self, project_id: str, *, resume_run: str | None = None, background: bool = True,
                  **cache: Any) -> str:
        project = self.db.project(project_id)
        if project is None:
            raise RunRequestError('项目不存在')
        if resume_run:
            previous = self.db.one('SELECT project_id FROM runs WHERE id=?', (resume_run,))
            if previous is None:
                raise RunRequestError('运行不存在')
            if previous['project_id'] != project_id:
                raise RunRequestError('该运行不属于当前项目')
        run_id = resume_run or self.db.create_run(project_id)
        try:
            require_supported_cutoff(project['cutoff_date'])
        except HistoricalReportUnavailable as exc:
            self.db.set_run(run_id, 'failed', error=str(exc))
            return run_id
        try:
            rc = self.context(project_id, run_id, **cache)
        except LLMError as exc:   # 配置缺失：运行直接失败并给出原因，而不是 500
            self.db.set_run(run_id, "failed", error=f"配置错误：{exc}")
            return run_id
        if background:
            execute_in_background(rc)
        else:
            execute(rc)
        return run_id

    def latest_run(self, project_id: str) -> dict[str, Any] | None:
        return self.db.one("SELECT * FROM runs WHERE project_id=? ORDER BY created_at DESC LIMIT 1", (project_id,))

    def latest_findings(self, project_id: str, report: str) -> dict[str, Any] | None:
        row = self.db.one(
            "SELECT s.output_json FROM stages s JOIN runs r ON r.id=s.run_id WHERE r.project_id=? AND s.name=? "
            "AND s.status='succeeded' ORDER BY r.created_at DESC LIMIT 1", (project_id, f"analysis_{report}"))
        import json
        return json.loads(row["output_json"]) if row and row["output_json"] else None
