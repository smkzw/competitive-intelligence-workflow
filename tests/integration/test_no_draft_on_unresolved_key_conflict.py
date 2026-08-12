"""Task 3.2 未决关键冲突无草稿集成测试。

冲突不得伪装为未公开或数值零；A/B/C 各一个非空关键冲突复用全部无草稿负断言。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.exhaustion import DoubleExhaustionRecord
from ci_workflow.gates.models import (
    GateUnitOutcome,
    ReportDecision,
    ReportKind,
)
from tests.integration.test_no_draft_when_blocked import (
    assert_no_downstream_artifacts,
    failed_gate_unit,
    gap_exhaustion,
    now,
    prepare_workspace,
    routed_audit,
    satisfying_bindings_for,
    snapshot_for,
    spec_yaml,
    write_via_entry,
)

REPORT_KINDS = (ReportKind.A, ReportKind.B, ReportKind.C)


def _conflict_unit_id(report_kind: ReportKind) -> str:
    """选择存在必需上下文字段的适用关键单元作为冲突载体。"""
    from tests.integration.test_no_draft_when_blocked import applicable_critical_units

    spec = spec_yaml(report_kind.value)
    snapshot = snapshot_for(report_kind)
    for unit in spec.units:
        if unit.blocking_level.value != "critical":
            continue
        if not unit.required_context_fields:
            continue
        if unit.unit_id not in applicable_critical_units(spec, snapshot):
            continue
        return unit.unit_id
    raise AssertionError(f"报告 {report_kind.value} 无适用的带字段关键冲突载体")


@pytest.mark.parametrize("report_kind", REPORT_KINDS, ids=lambda k: k.value)
def test_unresolved_key_conflict_never_becomes_not_publicly_disclosed_or_zero(
    report_kind: ReportKind, tmp_path: Path
) -> None:
    """A/B/C 未决关键冲突：冲突值不得被写成未公开或数值零，且无任何下游产物。"""
    spec = spec_yaml(report_kind.value)
    snapshot = snapshot_for(report_kind)
    unit_id = _conflict_unit_id(report_kind)

    gate_result = evaluate_report(
        spec,
        snapshot,
        satisfying_bindings_for(spec, snapshot, blocked_unit_id=unit_id),
        contract_version="1",
    )
    assert gate_result.decision is ReportDecision.BLOCKED
    blocked_pairs = [
        (r.unit_id, r.object_id)
        for r in gate_result.unit_results
        if r.outcome is GateUnitOutcome.BLOCKED
    ]
    assert blocked_pairs, "冲突场景必须存在阻断单元"
    assert all(unit == unit_id for unit, _ in blocked_pairs)

    failed_units = tuple(
        failed_gate_unit(
            spec, unit, object_id, current_state="conflicting"
        )
        for unit, object_id in blocked_pairs
    )
    record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=tuple(
            gap_exhaustion(
                gap_id=f"gap-{index}",
                gate_unit_id=unit,
                object_id=object_id,
                object_type=next(
                    x for x in spec.units if x.unit_id == unit
                ).object_type.value,
                current_state="conflicting",
            )
            for index, (unit, object_id) in enumerate(blocked_pairs, start=1)
        ),
        created_at=now(),
    )
    audit = routed_audit(
        report_kind=report_kind,
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed_units,
        exhausted=record,
    )
    conflict_units = [u for u in audit.failed_units if u.unit_id == unit_id]
    assert conflict_units
    assert all(u.current_state == "conflicting" for u in conflict_units)
    for u in conflict_units:
        summary = u.missing_or_conflict_summary_zh
        assert "未公开" not in summary
        assert "零" not in summary
        assert "0" not in summary

    workspace_root = prepare_workspace(tmp_path)
    write_via_entry(
        audit,
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
    )

    assert_no_downstream_artifacts(
        workspace_root,
        project_id=audit.project_id,
        report_kind=report_kind,
        report_version=audit.report_version,
    )
    audit_path = workspace_root / "blockers" / report_kind.value / "v1" / "audit.json"
    assert audit_path.exists()
    assert (workspace_root / "reports" / report_kind.value / "v1").exists() is False
