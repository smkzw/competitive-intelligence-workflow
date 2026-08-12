"""Task 3.2 独立科学质控否决无草稿集成测试。

GateSpec 通过后独立科学质控否决：可修复否决返回 recovering，已穷尽否决返回
evidence_blocked；两者均复用全部无草稿/无下游产物断言。否决必须绑定真实
ReportDecision.PASSED 的 gate result key、候选快照与项目宇宙。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ci_workflow.gates.blocker_audit import (
    ScientificQcRejection,
    apply_scientific_qc_rejection,
)
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.exhaustion import DoubleExhaustionRecord
from ci_workflow.gates.models import ReportDecision, ReportKind
from tests.integration.test_no_draft_when_blocked import (
    assert_no_downstream_artifacts,
    gap_exhaustion,
    now,
    prepare_workspace,
    satisfying_bindings_for,
    snapshot_for,
    spec_yaml,
)

REPORT_KINDS = (ReportKind.A, ReportKind.B, ReportKind.C)


def _passed_gate_result(report_kind: ReportKind):
    spec = spec_yaml(report_kind.value)
    snapshot = snapshot_for(report_kind)
    result = evaluate_report(
        spec,
        snapshot,
        satisfying_bindings_for(spec, snapshot),
        contract_version="1",
    )
    assert result.decision is ReportDecision.PASSED
    return result


def _rejection(
    report_kind: ReportKind,
    gate_result: object,
    *,
    recoverable: bool,
    exhausted: bool,
) -> ScientificQcRejection:
    return ScientificQcRejection(
        rejection_id=f"qc-reject-{report_kind.value}",
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        report_version="v1",
        candidate_snapshot_id=gate_result.evidence_snapshot_id,
        gate_result_key=gate_result.result_key,
        verdict="rejected",
        recoverable=recoverable,
        exhausted=exhausted,
        reviewer_id="qc-reviewer-1",
        reason_zh="独立复核发现结果解读存在可修正偏差。",
    )


@pytest.mark.parametrize(
    ("report_kind", "recoverable", "exhausted", "expected"),
    (
        (ReportKind.A, True, False, "recovering"),
        (ReportKind.B, True, False, "recovering"),
        (ReportKind.C, False, True, "evidence_blocked"),
    ),
    ids=("A-recoverable", "B-recoverable", "C-exhausted"),
)
def test_scientific_qc_rejection_requires_passed_gate_result(
    report_kind: ReportKind,
    recoverable: bool,
    exhausted: bool,
    expected: str,
    tmp_path: Path,
) -> None:
    """GateSpec 通过后质控否决：可修复回 recovering，已穷尽进 evidence_blocked。"""
    workspace_root = prepare_workspace(tmp_path)
    gate_result = _passed_gate_result(report_kind)
    snapshot = snapshot_for(report_kind)
    rejection = _rejection(
        report_kind, gate_result, recoverable=recoverable, exhausted=exhausted
    )

    next_state = apply_scientific_qc_rejection(
        rejection,
        gate_result=gate_result,
        snapshot=snapshot,
        workspace_root=workspace_root,
        database_path=workspace_root / "project.sqlite",
        exhaustion=None if recoverable else _exhausted_record(report_kind),
    )
    assert next_state == expected

    assert_no_downstream_artifacts(
        workspace_root,
        project_id=rejection.project_id,
        report_kind=report_kind,
        report_version=rejection.report_version,
    )
    assert (workspace_root / "blockers" / report_kind.value / "v1").exists() is False
    assert (workspace_root / "reports" / report_kind.value / "v1").exists() is False


def _exhausted_record(report_kind: ReportKind) -> DoubleExhaustionRecord:
    return DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=(gap_exhaustion(gap_id="gap-1"),),
        created_at=now(),
    )


def test_scientific_qc_rejection_binds_project_and_universe(
    tmp_path: Path,
) -> None:
    """跨项目、跨宇宙、错快照的否决全部失败关闭。"""
    from tests.integration.test_no_draft_when_blocked import _snapshot

    workspace_root = prepare_workspace(tmp_path)
    gate_result = _passed_gate_result(ReportKind.A)
    snapshot = snapshot_for(ReportKind.A)
    rejection = _rejection(ReportKind.A, gate_result, recoverable=True, exhausted=False)

    # 跨项目快照 → 拒绝
    other_snapshot = _snapshot(project_id="project-other")
    with pytest.raises(ValueError, match="同一项目"):
        apply_scientific_qc_rejection(
            rejection,
            gate_result=gate_result,
            snapshot=other_snapshot,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )

    # 跨宇宙（证据快照不同）→ 拒绝
    wrong_snapshot = _snapshot(evidence_snapshot_id="snapshot-999")
    with pytest.raises(ValueError, match="候选快照|证据快照"):
        apply_scientific_qc_rejection(
            rejection,
            gate_result=gate_result,
            snapshot=wrong_snapshot,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )

    # BLOCKED 结果 → 拒绝
    blocked = evaluate_report(
        spec_yaml("A"),
        snapshot_for(ReportKind.A),
        satisfying_bindings_for(
            spec_yaml("A"),
            snapshot_for(ReportKind.A),
            blocked_unit_id="a_product_identity",
        ),
        contract_version="1",
    )
    assert blocked.decision is ReportDecision.BLOCKED
    with pytest.raises(ValueError, match="已通过"):
        apply_scientific_qc_rejection(
            rejection,
            gate_result=blocked,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )

    # 结果键不符 → 拒绝
    forged = ScientificQcRejection(
        rejection_id="qc-forged",
        project_id="project_000000000000000000000001",
        report_kind=ReportKind.A,
        report_version="v1",
        candidate_snapshot_id=gate_result.evidence_snapshot_id,
        gate_result_key="gate-result_forged",
        verdict="rejected",
        recoverable=True,
        exhausted=False,
        reviewer_id="qc-reviewer-1",
        reason_zh="结果键不匹配。",
    )
    with pytest.raises(ValueError, match="结果键"):
        apply_scientific_qc_rejection(
            forged,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
        )
    assert (workspace_root / "blockers").exists() is False


def test_scientific_qc_rejection_rejects_both_recoverable_and_exhausted(
    tmp_path: Path,
) -> None:
    """否决输入必须且只能二选一：可修复或已穷尽。"""
    from pydantic import ValidationError

    workspace_root = prepare_workspace(tmp_path)
    gate_result = _passed_gate_result(ReportKind.A)
    with pytest.raises(ValidationError):
        _rejection(ReportKind.A, gate_result, recoverable=True, exhausted=True)
    with pytest.raises(ValidationError):
        _rejection(ReportKind.A, gate_result, recoverable=False, exhausted=False)
    assert (workspace_root / "blockers").exists() is False


def test_exhausted_qc_rejection_requires_matching_exhaustion_record(
    tmp_path: Path,
) -> None:
    """已穷尽否决必须绑定同项目同报告类型的双重穷尽记录。"""
    workspace_root = prepare_workspace(tmp_path)
    gate_result = _passed_gate_result(ReportKind.A)
    snapshot = snapshot_for(ReportKind.A)
    rejection = _rejection(
        ReportKind.A, gate_result, recoverable=False, exhausted=True
    )
    wrong_record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=ReportKind.B,  # 报告类型不匹配
        gaps=(gap_exhaustion(gap_id="gap-1"),),
        created_at=now(),
    )
    with pytest.raises(ValueError, match="报告类型"):
        apply_scientific_qc_rejection(
            rejection,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=workspace_root / "project.sqlite",
            exhaustion=wrong_record,
        )
    assert (workspace_root / "blockers").exists() is False


def test_qc_public_entry_revalidates_forged_inputs(tmp_path: Path) -> None:
    """QC 公共入口从原始内容完整重验证：model_copy 伪造项目/快照/宇宙/结果键/
    穷尽角色全部失败关闭，且无下游产物。"""
    report_kind = ReportKind.A
    gate_result = _passed_gate_result(report_kind)
    snapshot = snapshot_for(report_kind)
    rejection = _rejection(report_kind, gate_result, recoverable=True, exhausted=False)
    workspace_root = prepare_workspace(tmp_path)
    database_path = workspace_root / "project.sqlite"

    # 伪造结果键 → 拒绝
    forged_result = gate_result.model_copy(update={"result_key": "forged-key"})
    with pytest.raises(ValueError):
        apply_scientific_qc_rejection(
            rejection,
            gate_result=forged_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )

    # 伪造宇宙摘要 → 拒绝
    forged_snapshot = snapshot.model_copy(
        update={"universe_summary": "forged-summary"}
    )
    with pytest.raises(ValueError):
        apply_scientific_qc_rejection(
            rejection,
            gate_result=gate_result,
            snapshot=forged_snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )

    # 伪造项目（rejection 调包）→ 拒绝
    forged_rejection = ScientificQcRejection.model_validate(
        {
            **rejection.model_dump(mode="json"),
            "project_id": "project-other",
        }
    )
    with pytest.raises(ValueError):
        apply_scientific_qc_rejection(
            forged_rejection,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )

    # 已穷尽否决 + 伪造穷尽角色 → 拒绝
    exhausted_rejection = _rejection(
        report_kind, gate_result, recoverable=False, exhausted=True
    )
    from ci_workflow.gates.exhaustion import ExhaustionRole
    from tests.integration.test_no_draft_when_blocked import gap_exhaustion

    good_gap = gap_exhaustion(
        gap_id="gap-qc-forged",
        gate_spec_id=spec_yaml("A").spec_id,
        field_id=spec_yaml("A").units[0].user_label_zh,
    )
    valid_record = DoubleExhaustionRecord(
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        gaps=(good_gap,),
        created_at=now(),
    )
    # model_copy 伪造执行者角色（跳过模型校验）→ QC 入口重验证拒绝
    forged_record = valid_record.model_copy(
        update={
            "gaps": (
                good_gap.model_copy(
                    update={"executor_role": ExhaustionRole.REVIEWER}
                ),
            )
        }
    )
    with pytest.raises(ValueError):
        apply_scientific_qc_rejection(
            exhausted_rejection,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            exhaustion=forged_record,
        )

    # 正常路径仍返回原状态且零下游
    next_state = apply_scientific_qc_rejection(
        rejection,
        gate_result=gate_result,
        snapshot=snapshot,
        workspace_root=workspace_root,
        database_path=database_path,
    )
    assert next_state == "recovering"
    assert_no_downstream_artifacts(
        workspace_root,
        project_id="project_000000000000000000000001",
        report_kind=report_kind,
        report_version=rejection.report_version,
    )
