from __future__ import annotations

from types import SimpleNamespace

import pytest

from ci_workflow.application.terminal_recovery import (
    TerminalRecoveryError,
    exhaustion_path,
    failed_gate_units,
    load_double_exhaustion,
    validate_exhaustion_scope,
)
from ci_workflow.domain.enums import FactDisclosureState, ReportKind
from ci_workflow.gates.models import GateUnitOutcome


def _gap(unit: str = "b_core_efficacy_endpoint", object_id: str = "trial-1"):
    return SimpleNamespace(
        gate_unit_id=unit,
        object_id=object_id,
        object_type="trial",
        current_state="not_reported",
        evidence_gap=SimpleNamespace(field_id="efficacy.primary"),
    )


def _record(*gaps: object):
    return SimpleNamespace(project_id="project-1", report_kind=ReportKind.B, gaps=gaps)


def _gate(*results: object):
    return SimpleNamespace(unit_results=results)


def _blocked(unit: str = "b_core_efficacy_endpoint", object_id: str = "trial-1"):
    return SimpleNamespace(
        unit_id=unit,
        object_id=object_id,
        outcome=GateUnitOutcome.BLOCKED,
        disclosure_state=FactDisclosureState.NOT_REPORTED,
        user_note_zh="主要疗效终点尚未报告。",
    )


def test_exhaustion_scope_must_equal_current_blocked_pairs() -> None:
    record = _record(_gap())
    validate_exhaustion_scope(
        record, project_id="project-1", report_kind=ReportKind.B, gate_result=_gate(_blocked())
    )
    with pytest.raises(TerminalRecoveryError, match="完全一致"):
        validate_exhaustion_scope(
            record,
            project_id="project-1",
            report_kind=ReportKind.B,
            gate_result=_gate(_blocked(object_id="trial-2")),
        )


def test_exhaustion_scope_rejects_wrong_project_or_report() -> None:
    record = _record(_gap())
    with pytest.raises(TerminalRecoveryError, match="项目"):
        validate_exhaustion_scope(
            record, project_id="other", report_kind=ReportKind.B, gate_result=_gate(_blocked())
        )
    with pytest.raises(TerminalRecoveryError, match="报告"):
        validate_exhaustion_scope(
            record, project_id="project-1", report_kind=ReportKind.C, gate_result=_gate(_blocked())
        )


def test_failed_units_are_derived_from_gate_and_exhaustion() -> None:
    units = failed_gate_units(_gate(_blocked()), _record(_gap()))
    assert len(units) == 1
    assert units[0].field_ids == ("efficacy.primary",)
    assert units[0].current_state == "not_reported"
    assert units[0].object_name_zh == "对象 trial-1"
    assert units[0].missing_or_conflict_summary_zh == "主要疗效终点尚未报告。"


def test_failed_units_keep_exhaustion_gap_state_when_evidence_is_reported_but_inadequate() -> None:
    blocked = _blocked()
    blocked.disclosure_state = FactDisclosureState.REPORTED_VALUE
    units = failed_gate_units(_gate(blocked), _record(_gap()))
    assert units[0].current_state == "not_reported"
    assert units[0].missing_or_conflict_summary_zh == "主要疗效终点尚未报告。"


def test_exhaustion_file_is_optional_until_recovery_finishes(tmp_path) -> None:
    assert exhaustion_path(tmp_path, ReportKind.C) == (
        tmp_path / "evidence/library/c-double-exhaustion.json"
    )
    assert load_double_exhaustion(tmp_path, ReportKind.C) is None
