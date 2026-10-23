"""应用服务：把配置、存储、LLM、Skill、工具组装成一次运行。Web 与 CLI 共用。

后台运行由本进程内的一个串行队列执行：同一时刻只驱动一个运行（共享浏览器/来源负载）。
队列、运行所有权和停止意图都是进程本地状态；这不是多进程调度或租约。服务启动时不修改
数据库中既有的 queued/running 行，因为它们可能仍由另一个进程持有。
"""
from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from typing import Any

import ciw2.sources  # noqa: F401  注册全部工具
from ciw2.config import Settings
from ciw2.domain.availability import HistoricalReportUnavailable, require_supported_cutoff
from ciw2.harness.cancellation import RunCancelled, RunControl
from ciw2.harness.fallback import FallbackLLM
from ciw2.harness.llm import LLM, LLMError, OpenAICompatLLM
from ciw2.harness.skills import load_skills
from ciw2.pipeline.context import RunContext
from ciw2.pipeline.runner import execute
from ciw2.store.cas import CAS
from ciw2.store.db import DB

LLMFactory = Callable[[Settings], tuple[LLM, LLM | None]]
TERMINAL_RUN_STATES = frozenset({"succeeded", "failed", "cancelled"})
QUEUED_CANCELLED = '已按用户请求取消；排队任务未开始，未调用模型或来源'
FOREIGN_PROCESS = '该运行由其他进程持有；本进程不重复启动，也不假装能跨进程停止它'


class RunRequestError(ValueError):
    pass


def default_llms(s: Settings) -> tuple[LLM, LLM | None]:
    import json
    import os

    # Observed GLM nonstreaming completion took145s;120s cancelled healthy work.
    main = OpenAICompatLLM(s.llm_base_url, s.llm_api_key, s.llm_model, timeout_s=300)
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
    if len(routes) > 1:
        main.max_retries = 1  # Use the explicitly configured backup instead of3 cancelled copies.
    check = OpenAICompatLLM(s.llm_base_url, s.llm_api_key, s.llm_check_model, timeout_s=300) if s.llm_check_model else None
    return FallbackLLM(routes) if len(routes) > 1 else main, check


class Service:
    def __init__(self, settings: Settings, llm_factory: LLMFactory = default_llms) -> None:
        settings.ensure_dirs()
        self.settings = settings
        self.db = DB(settings.db_path)
        self.cas = CAS(settings.cas_dir)
        self.llm_factory = llm_factory
        self.skills = load_skills(settings.skills_dir)
        self._cond = threading.Condition()
        self._run_lock = threading.Lock()
        self._pending: deque[tuple[RunContext, RunControl]] = deque()
        self._owned: dict[str, RunControl] = {}
        self._active: str | None = None
        self._worker: threading.Thread | None = None

    def create_project(self, indication: str, reports: list[str], request_text: str = "", focus: str = "",
                       cutoff_date: str | None = None) -> str:
        reports = [r for r in ("A", "B", "C") if r in reports] or ["A"]
        return self.db.create_project(indication.strip(), reports, request_text, focus, cutoff_date or None)

    def context(self, project_id: str, run_id: str, *, control: RunControl | None = None,
                **cache: Any) -> RunContext:
        llm, check = self.llm_factory(self.settings)
        return RunContext(db=self.db, cas=self.cas, settings=self.settings, llm=llm, skills=self.skills,
                          project_id=project_id, run_id=run_id, check_llm=check, control=control,
                          cache=dict(cache))

    def start_run(self, project_id: str, *, resume_run: str | None = None, background: bool = True,
                  **cache: Any) -> str:
        """准入一次运行。同一项目已有排队/执行中的本进程运行时直接返回该运行，不另起线程。"""
        project = self.db.project(project_id)
        if project is None:
            raise RunRequestError('项目不存在')
        target = self._resume_target(project_id, resume_run)
        control = RunControl()
        with self._cond:
            active = self.db.active_run(project_id)
            existing = self._active_or_error(active, target, background)
            if existing is not None:
                return existing
            run_id = target['id'] if target is not None else self.db.create_run(project_id)
            if target is not None and self.db.run(run_id)['status'] in TERMINAL_RUN_STATES:
                self.db.set_run(run_id, 'queued')
            try:
                require_supported_cutoff(project['cutoff_date'])
            except HistoricalReportUnavailable as exc:
                self.db.set_run(run_id, 'failed', error=str(exc))
                return run_id
            try:
                rc = self.context(project_id, run_id, control=control, **cache)
            except LLMError as exc:   # 配置缺失：运行直接失败并给出原因，而不是 500
                self.db.set_run(run_id, 'failed', error=f"配置错误：{exc}")
                return run_id
            self._owned[run_id] = control
            if background:
                self._pending.append((rc, control))
                self._ensure_worker()
                self._cond.notify()
                return run_id
        try:
            with self._run_lock:   # 同步 CLI 与后台队列共享同一执行闸门
                with self._cond:
                    if self._owned.get(run_id) is not control:
                        return run_id   # 排队期间已被取消或由新的运行控制接管
                    status = self.db.run(run_id)['status']
                    if status == 'cancelled':
                        return run_id
                    if status == 'queued' and not self.db.start_run_if_queued(run_id):
                        return run_id
                execute(rc)
        finally:
            with self._cond:
                self._release(run_id, control)
        return run_id

    def cancel_run(self, project_id: str, run_id: str) -> dict[str, Any]:
        """排队任务立即取消；执行中任务只记录停止意图，由运行器在安全边界停止。"""
        if self.db.project(project_id) is None:
            raise RunRequestError('项目不存在')
        row = self.db.run(run_id)
        if row is None:
            raise RunRequestError('运行不存在')
        if row['project_id'] != project_id:
            raise RunRequestError('该运行不属于当前项目')
        with self._cond:
            control = self._owned.get(run_id)
            row = self.db.run(run_id)
            assert row is not None
            if row['status'] in TERMINAL_RUN_STATES:
                return {'run_id': run_id, 'status': row['status'], 'cancel_requested': False}
            # A queued row is not executing anywhere; the conditional update is a safe
            # cooperative boundary even when another process queued it.
            if row['status'] == 'queued' and self.db.cancel_queued_run(run_id, QUEUED_CANCELLED):
                self._release(run_id)
                return {'run_id': run_id, 'status': 'cancelled', 'cancel_requested': True}
            row = self.db.run(run_id)
            if control is None:
                raise RunRequestError(FOREIGN_PROCESS)
            control.request_stop()
            return {'run_id': run_id, 'status': row['status'], 'cancel_requested': True}

    def stopping(self, run_id: str) -> bool:
        with self._cond:
            control = self._owned.get(run_id)
            return bool(control and control.stopping)

    def wait_idle(self, timeout: float | None = None) -> bool:
        """等待本进程队列清空；用于测试和优雅收尾，不是调度器接口。"""
        with self._cond:
            return self._cond.wait_for(lambda: not self._pending and self._active is None, timeout)

    def _resume_target(self, project_id: str, resume_run: str | None) -> dict[str, Any] | None:
        if not resume_run:
            return None
        row = self.db.run(resume_run)
        if row is None:
            raise RunRequestError('运行不存在')
        if row['project_id'] != project_id:
            raise RunRequestError('该运行不属于当前项目')
        return row

    def _active_or_error(self, active: dict[str, Any] | None, target: dict[str, Any] | None,
                         background: bool) -> str | None:
        if active is None:
            return None
        if target is not None and target['id'] != active['id']:
            raise RunRequestError('该项目已有排队或执行中的运行，不能同时恢复另一运行')
        if background:
            if active['id'] in self._owned:
                return active['id']
            raise RunRequestError(FOREIGN_PROCESS)
        if active['id'] in self._owned:
            raise RunRequestError('该运行已在本进程排队或执行，不能重复启动')
        if target is None:
            raise RunRequestError('该项目已有排队或执行中的运行；请先停止或显式恢复该运行')
        # 显式前台 resume = 操作者声明该排队/中断运行归本次 CLI 所有。
        return None

    def _ensure_worker(self) -> None:
        if self._worker is None or not self._worker.is_alive():
            self._worker = threading.Thread(target=self._work, name='ciw2-run-queue', daemon=True)
            self._worker.start()

    def _work(self) -> None:
        while True:
            with self._cond:
                while not self._pending:
                    self._cond.wait()
                rc, control = self._pending.popleft()
                if self._owned.get(rc.run_id) is not control:
                    self._cond.notify_all()
                    continue
                if not self.db.start_run_if_queued(rc.run_id):
                    self._release(rc.run_id, control)
                    continue
                self._active = rc.run_id
            try:
                with self._run_lock:
                    execute(rc)
            except RunCancelled as exc:   # execute normally records this itself
                self.db.set_run(rc.run_id, 'cancelled', error=str(exc))
            except Exception as exc:  # noqa: BLE001 - 工作线程不能静默死亡并留下假 running
                self.db.set_run(rc.run_id, 'failed', error=f'运行线程异常：{type(exc).__name__}: {exc}')
            finally:
                with self._cond:
                    self._release(rc.run_id, control)

    def _release(self, run_id: str, expected: RunControl | None = None) -> None:
        """调用方必须持有 self._cond。expected 不匹配时不得移除新的运行控制。"""
        if expected is None or self._owned.get(run_id) is expected:
            self._owned.pop(run_id, None)
            if self._active == run_id:
                self._active = None
        self._cond.notify_all()

    def latest_run(self, project_id: str) -> dict[str, Any] | None:
        return self.db.one("SELECT * FROM runs WHERE project_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                           (project_id,))

    def latest_findings(self, project_id: str, report: str) -> dict[str, Any] | None:
        row = self.db.one(
            "SELECT s.output_json FROM stages s JOIN runs r ON r.id=s.run_id WHERE r.project_id=? AND s.name=? "
            "AND s.status='succeeded' ORDER BY r.created_at DESC, r.rowid DESC LIMIT 1", (project_id, f"analysis_{report}"))
        import json
        return json.loads(row["output_json"]) if row and row["output_json"] else None
