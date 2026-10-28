"""对外门面（工作台或脚本调用）。工作台只需要 current_release() 读出 release.json 与门户目录。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ciw.config import load_indication
from ciw.pipeline import RunResult, run
from ciw.release import load_release
from ciw.store import Workspace
from ciw.verify.llm import CachedBackend, load_roles


def run_indication(
    config_path: str | Path,
    workspace: str | Path,
    *,
    offline: bool = False,
    with_models: bool = False,
    llm_config: str | Path | None = None,
    report: str | None = None,
    log=print,
) -> RunResult:
    cfg = load_indication(config_path)
    ws = Workspace(workspace)
    roles = None
    if with_models:
        roles = {k: CachedBackend(v, ws) for k, v in load_roles(llm_config).items()}
    selected = None
    if report is not None:
        old = current_release(workspace)
        old_reports = old[0].get("rendered_reports", []) if old and old[0]["indication"]["slug"] == cfg.slug else []
        selected = sorted({report, *old_reports})
    return run(cfg, ws, offline=offline, roles=roles, log=log, report_scope=report, render_reports=selected)


def current_release(workspace: str | Path) -> tuple[dict[str, Any], Path] | None:
    """返回 (release 文档, release 目录)；没有 current 时返回 None。"""
    d = Workspace(workspace).current_release_dir()
    if d is None or not (d / "release.json").exists():
        return None
    return load_release(d), d
