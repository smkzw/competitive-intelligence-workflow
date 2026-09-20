"""Task 8.7b：PPTX 确认中断、fixture/project 恢复与一次性入口。"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from ci_workflow.application.fixture_runner import (
    FixtureCaseError,
    _compute_case_digest,
    run_fixture_case,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.renderers.pptx_master.adapter import (
    PptxConfirmationAdapter,
    PptxConfirmationError,
    PptxReportInput,
)
from ci_workflow.renderers.pptx_master.confirmation import (
    build_confirmation_result,
    load_confirmation_session,
    load_recommendations,
    write_confirmation_result,
)

pytestmark = [pytest.mark.retained_legacy_format]

_NOW = datetime(2026, 8, 12, 2, 0, tzinfo=UTC)


def _report_input(
    report: str,
    *,
    snapshot_id: str = "snapshot-shared-001",
) -> PptxReportInput:
    project_id = "project-pptx-confirmation"
    claim_snapshot_id = "claim-snapshot-shared-001"
    evidence_snapshot_id = "evidence-snapshot-shared-001"
    coverage_set_id = "coverage-set-shared-001"
    report_data = {
        "schema_version": "1.0",
        "report": report,
        "report_version": "v1",
        "indication": "特应性皮炎",
        "data_cutoff": "2026-07-31T23:59:59+08:00",
        "sources": {"source-1": {"title": "锁定来源"}},
    }
    snapshot = {
        "schema_version": "1.0",
        "project_id": project_id,
        "report": report,
        "report_version": "v1",
        "snapshot_id": snapshot_id,
        "snapshot_sha256": "a" * 64,
        "claim_snapshot_id": claim_snapshot_id,
        "evidence_snapshot_id": evidence_snapshot_id,
        "coverage_set_id": coverage_set_id,
        "locked_at": _NOW.isoformat(),
    }
    coverage = {
        "schema_version": "1.0",
        "project_id": project_id,
        "report": report,
        "report_version": "v1",
        "coverage_set_id": coverage_set_id,
        "evidence_snapshot_id": evidence_snapshot_id,
        "claim_snapshot_id": claim_snapshot_id,
        "items": [
            {
                "item_id": f"{report.lower()}-page-1",
                "kind": "page",
                "page_responsibility_id": "overview",
                "label_zh": "总览",
            }
        ],
        "created_at": _NOW.isoformat(),
    }
    return PptxReportInput(
        report=report,
        report_data=report_data,
        snapshot=snapshot,
        coverage_set=coverage,
    )


def test_adapter_interrupts_once_and_replays_confirmed_batch_without_svg_or_pptx(
    tmp_path: Path,
) -> None:
    inputs = tuple(_report_input(report) for report in ("A", "B", "C"))
    adapter = PptxConfirmationAdapter(tmp_path)

    first = adapter.prepare(inputs, now=_NOW)

    assert first.state == "awaiting_confirmation"
    assert first.awaiting_reports == ("A", "B", "C")
    index = json.loads((tmp_path / "confirm_ui/index.json").read_text(encoding="utf-8"))
    assert index["state"] == "awaiting_confirmation"
    assert index["no_svg"] is True
    assert index["pptx_generated"] is False
    assert len(index["entries"]) == 3
    assert all(
        (tmp_path / entry.source_pack_path).is_file()
        and (tmp_path / entry.summary_path).is_file()
        and (tmp_path / entry.recommendations_path).is_file()
        and (tmp_path / entry.session_path).is_file()
        for entry in first.entries
    )
    recommendations_before = {
        entry.report: (tmp_path / entry.recommendations_path).read_bytes()
        for entry in first.entries
    }
    assert not list((tmp_path / "state/pptx").rglob("*.svg"))
    assert not list(tmp_path.rglob("*.pptx"))

    for entry in first.entries:
        recommendations = load_recommendations(tmp_path / entry.recommendations_path)
        result = build_confirmation_result(recommendations, confirmed_by="test")
        write_confirmation_result(result, tmp_path / entry.result_path)

    resumed = adapter.prepare(inputs, now=_NOW + timedelta(minutes=1))
    assert resumed.state == "confirmed"
    assert resumed.awaiting_reports == ()
    assert all(entry.state == "confirmed" for entry in resumed.entries)
    assert all(
        recommendations_before[entry.report]
        == (tmp_path / entry.recommendations_path).read_bytes()
        for entry in resumed.entries
    )
    assert all(
        load_confirmation_session(tmp_path / entry.session_path).state == "closed"
        for entry in resumed.entries
    )

    replayed = adapter.prepare(inputs, now=_NOW + timedelta(minutes=2))
    assert replayed.as_dict() == resumed.as_dict()
    assert not list((tmp_path / "state/pptx").rglob("*.svg"))
    assert not list(tmp_path.rglob("*.pptx"))


def test_adapter_rejects_cross_snapshot_batch_before_writing_any_confirmation_files(
    tmp_path: Path,
) -> None:
    inputs = tuple(_report_input(report) for report in ("A", "B"))
    mismatched = (*inputs, _report_input("C", snapshot_id="snapshot-other-001"))

    with pytest.raises(PptxConfirmationError, match="同一项目和锁定报告快照"):
        PptxConfirmationAdapter(tmp_path).prepare(mismatched, now=_NOW)

    assert not (tmp_path / "confirm_ui").exists()
    assert not (tmp_path / "state/pptx").exists()


def test_fixture_runner_rejects_pptx_as_release_output(
    tmp_path: Path,
) -> None:
    case_id = "pptx-confirmation-fixture"
    case_root = tmp_path / "cases" / case_id
    inputs_dir = case_root / "inputs"
    inputs_dir.mkdir(parents=True)
    source = (
        Path(__file__).resolve().parents[2]
        / "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    report_data = inputs_dir / "report-data.json"
    report_data.write_bytes(source.read_bytes())
    case = {
        "id": case_id,
        "description_zh": "PPTX 确认中断恢复案例",
        "indication": "特应性皮炎",
        "timezone": "Asia/Shanghai",
        "data_cutoff": "2026-07-31",
        "created_at": "2026-08-12T10:00:00+08:00",
        "reports": ["A"],
        "outputs": ["pptx"],
        "inputs": [
            {
                "path": "inputs/report-data.json",
                "role": "report_data",
                "sha256": hashlib.sha256(report_data.read_bytes()).hexdigest(),
            }
        ],
        "expected": {
            "report": "A",
            "report_version": "v-fixture-001",
            "outcome": "rendered",
            "state": "snapshot_locked",
        },
    }
    case["case_digest"] = _compute_case_digest(case)
    catalog_path = tmp_path / "cases" / "catalog.yaml"
    catalog_path.write_text(
        yaml.safe_dump({"schema_version": "1.0", "cases": [case]}, allow_unicode=True),
        encoding="utf-8",
    )
    project_root = tmp_path / "fixture-project"

    with pytest.raises(FixtureCaseError, match="html"):
        run_fixture_case(
            case_id,
            project_root=project_root,
            reports=["A"],
            outputs=["pptx"],
            catalog_path=catalog_path,
        )
    assert not project_root.exists()


def test_project_contract_rejects_pptx_release_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del tmp_path, capsys
    with pytest.raises(ValueError, match="html"):
        create_project_contract(
            indication="特应性皮炎",
            reports=["A"],
            outputs=["pptx"],
            timezone="Asia/Shanghai",
            cutoff="2026-07-31",
            created_at=datetime(
                2026, 8, 12, 10, tzinfo=ZoneInfo("Asia/Shanghai")
            ),
        )
