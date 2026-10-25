"""运行器：顺序执行 DAG；同一 run 重跑时只跳过运行版本兼容的成功阶段（可恢复）。"""
from __future__ import annotations

import traceback
from collections.abc import Sequence
from typing import Any

from ciw2.harness.agent import AgentBudgetExceeded
from ciw2.harness.cancellation import RunCancelled
from ciw2.pipeline import stage_versions
from ciw2.pipeline.context import IncompleteWork, RunContext
from ciw2.pipeline.stages import STAGES, Stage

LEGACY_VERSION_REFUSAL = (
    "旧运行的成功阶段缺少运行版本回执（{names}）；为避免把旧结果当作当前规则，"
    "本次恢复在调用任何阶段、模型或来源前停止。需要具备版本回执的合格恢复候选"
    "（qualified recovery candidate）或新建运行。"
)


def stages_for(reports: list[str]) -> list[Stage]:
    return [s for s in STAGES if s.reports & set(reports)]


def _mark_cancelled(rc: RunContext, message: str) -> str:
    rc.db.set_run(rc.run_id, "cancelled", error=message)
    return "cancelled"


def complete_stage(rc: RunContext, stage: Stage, output: Any,
                   predecessors: Sequence[str] = (), *,
                   expected_binding: dict[str, Any] | None = None) -> None:
    """Write the successful output and its runtime receipt in one existing transaction."""
    receipt = stage_versions.completion_receipt(
        rc, stage, output, predecessors, expected_binding=expected_binding)
    with rc.db.tx():
        rc.db.set_stage(rc.run_id, stage.name, 'succeeded', output=output)
        stage_versions.write_receipt(rc, receipt)

def execute(rc: RunContext) -> str:
    """返回最终运行状态 succeeded|failed|cancelled。

    取消是合作式的：在阶段边界检查停止意图，不杀线程；当前阶段的已完成单元和同 run
    缓存保留，恢复时从该阶段继续。只有带兼容运行版本回执的成功阶段才复用；版本变化
    从最早受影响阶段重跑，无回执的旧成功在调用任何阶段前失败关闭。
    """
    rc.db.set_run(rc.run_id, "running")
    try:
        rc.check_cancelled()
    except RunCancelled as exc:
        return _mark_cancelled(rc, f"运行开始前停止：{exc}")
    if not stage_versions.ensure_pipeline_scope(rc):
        rc.db.set_run(rc.run_id, "failed", error=LEGACY_VERSION_REFUSAL.format(
            names="普通流程身份未绑定；已有记录可能属于独立组件运行"))
        return "failed"
    plan = stages_for(rc.project["reports"])
    restart, legacy = stage_versions.resume_boundary(rc, plan)
    if legacy:
        rc.db.set_run(rc.run_id, "failed",
                      error=LEGACY_VERSION_REFUSAL.format(names=", ".join(legacy)))
        return "failed"
    # A recovered upstream or a changed runtime changes downstream inputs, including
    # an earlier empty "success". Descendants of the earliest boundary run again.
    for stage in plan[restart:]:
        rc.db.set_stage(rc.run_id, stage.name, 'pending')
    soft_failures: list[str] = []
    unfinished_work = False
    for index, st in enumerate(plan):
        if index < restart:
            continue
        try:
            rc.check_cancelled()
        except RunCancelled as exc:
            return _mark_cancelled(rc, f"阶段 {st.name} 开始前停止：{exc}")
        rc.stage = st.name
        try:
            # Snapshot the runtime before the callback; completion recomputes it to reject hot swaps.
            predecessors = [item.name for item in plan[:index]]
            binding = stage_versions.stage_binding(rc, st, predecessors)
            rc.check_cancelled()
            out = st.fn(rc)
            complete_stage(rc, st, out, predecessors, expected_binding=binding)
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
            unfinished_work |= isinstance(exc, IncompleteWork) or st.name in {'analysis_A', 'analysis_B', 'analysis_C'}
            if st.blocking:
                rc.db.set_run(rc.run_id, "failed", error=f"阶段 {st.name} 失败：{msg}")
                return "failed"
            soft_failures.append(st.name)
    status = 'failed' if unfinished_work else 'succeeded'
    rc.db.set_run(rc.run_id, status, error=("非阻断阶段失败：" + ", ".join(soft_failures)) if soft_failures else None)
    return status


def stage_table(db: Any, run_id: str, reports: list[str]) -> list[dict[str, Any]]:
    rows = {r["name"]: r for r in db.query(
        "SELECT * FROM stages WHERE run_id=? AND name NOT LIKE ?",
        (run_id, stage_versions.RECEIPT_PREFIX + "%"))}
    return [{"name": s.name, "blocking": s.blocking, **(rows.get(s.name) or {"status": "pending"})}
            for s in stages_for(reports)]
