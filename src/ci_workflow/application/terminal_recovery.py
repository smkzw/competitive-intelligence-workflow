"""Minimal adapter from the shared exhaustion contract to blocker publication."""

from __future__ import annotations

from pathlib import Path

from ci_workflow.domain.enums import ReportKind
from ci_workflow.gates.blocker_audit import (
    FailedGateUnit,
    build_and_write_blocker_package,
)
from ci_workflow.gates.exhaustion import GAP_STATES, DoubleExhaustionRecord
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    GateSpec,
    GateUnitOutcome,
    ReportGateResult,
)


class TerminalRecoveryError(ValueError):
    """The supplied exhaustion record does not close the current gate failure."""


def exhaustion_path(project_root: Path, report_kind: ReportKind) -> Path:
    return (
        project_root
        / "evidence"
        / "library"
        / f"{report_kind.value.lower()}-double-exhaustion.json"
    )


def load_double_exhaustion(
    project_root: Path, report_kind: ReportKind
) -> DoubleExhaustionRecord | None:
    path = exhaustion_path(project_root, report_kind)
    if not path.is_file():
        return None
    try:
        return DoubleExhaustionRecord.model_validate_json(path.read_bytes())
    except ValueError as error:
        raise TerminalRecoveryError(f"双重穷尽记录无效：{path}") from error


def _blocked_pairs(gate_result: ReportGateResult) -> set[tuple[str, str]]:
    return {
        (item.unit_id, item.object_id)
        for item in gate_result.unit_results
        if item.outcome is GateUnitOutcome.BLOCKED
    }


def validate_exhaustion_scope(
    exhaustion: DoubleExhaustionRecord,
    *,
    project_id: str,
    report_kind: ReportKind,
    gate_result: ReportGateResult,
) -> None:
    if exhaustion.project_id != project_id:
        raise TerminalRecoveryError("双重穷尽记录与当前项目不一致")
    if exhaustion.report_kind is not report_kind:
        raise TerminalRecoveryError("双重穷尽记录与当前报告类型不一致")
    exhausted_pairs = {(gap.gate_unit_id, gap.object_id) for gap in exhaustion.gaps}
    if exhausted_pairs != _blocked_pairs(gate_result):
        raise TerminalRecoveryError("双重穷尽缺口必须与当前阻断单元完全一致")


def failed_gate_units(
    gate_result: ReportGateResult,
    exhaustion: DoubleExhaustionRecord,
) -> tuple[FailedGateUnit, ...]:
    """Derive user-facing failed units; callers cannot submit a second truth set."""
    results = {
        (item.unit_id, item.object_id): item
        for item in gate_result.unit_results
        if item.outcome is GateUnitOutcome.BLOCKED
    }
    units: list[FailedGateUnit] = []
    for gap in exhaustion.gaps:
        result = results[(gap.gate_unit_id, gap.object_id)]
        observed_state = (
            result.disclosure_state.value if result.disclosure_state is not None else None
        )
        # Gate 可因来源等级/上下文不足阻断一个已有数值；reported_value/zero
        # 不是缺口状态，此时保留已由双重穷尽合同验证的 gap.current_state。
        state = observed_state if observed_state in GAP_STATES else gap.current_state
        units.append(
            FailedGateUnit(
                unit_id=gap.gate_unit_id,
                object_type=gap.object_type,
                object_id=gap.object_id,
                object_name_zh=f"对象 {gap.object_id}",
                field_ids=(gap.evidence_gap.field_id,),
                current_state=state,
                user_label_zh="关键证据单元",
                missing_or_conflict_summary_zh=(
                    result.user_note_zh or "关键证据仍未达到报告要求。"
                ),
            )
        )
    return tuple(units)


def publish_terminal_blocker(
    *,
    project_root: Path,
    project_id: str,
    contract_version: str,
    report_kind: ReportKind,
    spec: GateSpec,
    snapshot: ApplicableUniverseSnapshot,
    gate_result: ReportGateResult,
    exhaustion: DoubleExhaustionRecord,
    source_links: tuple[str, ...],
) -> tuple[Path, Path]:
    """Validate one existing exhaustion truth and publish the shared blocker package."""
    validate_exhaustion_scope(
        exhaustion,
        project_id=project_id,
        report_kind=report_kind,
        gate_result=gate_result,
    )
    return build_and_write_blocker_package(
        project_id=project_id,
        report_kind=report_kind,
        contract_version=contract_version,
        report_version="v1",
        spec=spec,
        snapshot=snapshot,
        gate_result=gate_result,
        failed_units=failed_gate_units(gate_result, exhaustion),
        exhaustion=exhaustion,
        residual_uncertainty_zh="未公开资料仍可能在后续披露中改变当前判断。",
        user_help_needed=False,
        minimal_user_action_zh="无需用户操作。",
        source_links=source_links,
        resume_instruction_zh="新增可靠证据后重新运行，系统将从当前项目继续核对。",
        workspace_root=project_root,
        database_path=project_root / "state/project.sqlite",
        created_at=exhaustion.created_at,
    )
