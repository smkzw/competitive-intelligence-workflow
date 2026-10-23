"""运行器：顺序执行 DAG；同一 run 重跑时跳过已成功阶段（可恢复）。"""
from __future__ import annotations

import traceback
from typing import Any

from ciw2.harness.agent import AgentBudgetExceeded
from ciw2.harness.cancellation import RunCancelled
from ciw2.pipeline.context import IncompleteWork, RunContext
from ciw2.pipeline.stages import STAGES, Stage


def stages_for(reports: list[str]) -> list[Stage]:
    return [s for s in STAGES if s.reports & set(reports)]


def _mark_cancelled(rc: RunContext, message: str) -> str:
    rc.db.set_run(rc.run_id, "cancelled", error=message)
    return "cancelled"


def execute(rc: RunContext) -> str:
    """返回最终运行状态 succeeded|failed|cancelled。

    取消是合作式的：在阶段边界检查停止意图，不杀线程；当前阶段的已完成单元和同 run
    缓存保留，恢复时从该阶段继续。
    """
    rc.db.set_run(rc.run_id, "running")
    try:
        rc.check_cancelled()
    except RunCancelled as exc:
        return _mark_cancelled(rc, f"运行开始前停止：{exc}")
    plan = stages_for(rc.project["reports"])
    done = {r["name"] for r in rc.db.query("SELECT name FROM stages WHERE run_id=? AND status='succeeded'",
                                           (rc.run_id,))}
    stopped = {r['name'] for r in rc.db.query(
        "SELECT name FROM stages WHERE run_id=? AND status IN ('failed','cancelled')", (rc.run_id,))}
    restart = next((i for i, stage in enumerate(plan) if stage.name in stopped), len(plan))
    # A recovered upstream changes downstream inputs, including an earlier empty
    # "success". Keep completed stages only before the first failed/cancelled dependency.
    done &= {stage.name for stage in plan[:restart]}
    for stage in plan[restart:]:
        rc.db.set_stage(rc.run_id, stage.name, 'pending')
    soft_failures: list[str] = []
    unfinished_work = False
    for st in plan:
        if st.name in done:
            continue
        try:
            rc.check_cancelled()
        except RunCancelled as exc:
            return _mark_cancelled(rc, f"阶段 {st.name} 开始前停止：{exc}")
        rc.stage = st.name
        rc.db.set_stage(rc.run_id, st.name, "running")
        try:
            out = st.fn(rc)
            rc.db.set_stage(rc.run_id, st.name, "succeeded", output=out)
        except RunCancelled as exc:
            rc.db.set_stage(rc.run_id, st.name, "cancelled", error=str(exc))
            return _mark_cancelled(rc, f"阶段 {st.name} 已停止：{exc}")
        except Exception as exc:  # noqa: BLE001 - 阶段边界统一记录
            if rc.control is not None and rc.control.stopping:
                rc.db.set_stage(rc.run_id, st.name, "cancelled",
                                error=f"停止请求已记录；{type(exc).__name__}: {exc}")
                return _mark_cancelled(rc, f"阶段 {st.name} 因停止请求中止")
            msg = f"{type(exc).__name__}: {exc}"
            detail = msg if isinstance(exc, AgentBudgetExceeded) else msg + "\n" + traceback.format_exc()[-3000:]
            rc.db.set_stage(rc.run_id, st.name, "failed", error=detail,
                            output=exc.output if isinstance(exc, IncompleteWork) else None)
            unfinished_work |= isinstance(exc, IncompleteWork)
            if st.blocking:
                rc.db.set_run(rc.run_id, "failed", error=f"阶段 {st.name} 失败：{msg}")
                return "failed"
            soft_failures.append(st.name)
    status = 'failed' if unfinished_work else 'succeeded'
    rc.db.set_run(rc.run_id, status, error=("非阻断阶段失败：" + ", ".join(soft_failures)) if soft_failures else None)
    return status


def stage_table(db: Any, run_id: str, reports: list[str]) -> list[dict[str, Any]]:
    rows = {r["name"]: r for r in db.query("SELECT * FROM stages WHERE run_id=?", (run_id,))}
    return [{"name": s.name, "blocking": s.blocking, **(rows.get(s.name) or {"status": "pending"})}
            for s in stages_for(reports)]
