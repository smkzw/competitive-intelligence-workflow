"""Task 6.10：B 类 PNH 纵切与 D70 三案例当前运行验收。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from ci_workflow.application.fixture_runner import run_fixture_case
from ci_workflow.application.run_service import validate_run_manifest
from ci_workflow.renderers.portal.report_b import _page_records, load_report_b_data
from ci_workflow.reports.b.efficacy import EfficacyFactRow
from ci_workflow.reports.b.pages import build_matrix_view_state
from ci_workflow.reports.b.safety import SafetyFactRow
from ci_workflow.storage.manifest_store import ArtifactManifest

ROOT = Path(__file__).resolve().parents[2]
PNH_DATA = ROOT / "fixtures/positive/b-pnh/inputs/report-data.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_pnh_fixture_keeps_source_backed_efficacy_safety_and_baseline_sentinels() -> None:
    payload = _load(PNH_DATA)
    efficacy = {
        row["row_id"]: row
        for row in payload["efficacy"]  # type: ignore[index]
    }
    assert (
        efficacy["eff-apply-treatment"]["value"],
        efficacy["eff-apply-treatment"]["denominator"],
    ) == (82.3, 60)
    assert (
        efficacy["eff-apply-control"]["value"],
        efficacy["eff-apply-control"]["denominator"],
    ) == (1.8, 35)
    assert (
        efficacy["eff-appoint-treatment"]["value"],
        efficacy["eff-appoint-treatment"]["denominator"],
    ) == (92.2, 33)
    assert {row["endpoint"] for row in efficacy.values()} == {
        "血红蛋白较基线持续升高≥2 g/dL且无需输血"
    }

    safety = {
        row["row_id"]: (row["value"], row["numerator"], row["denominator"])
        for row in payload["safety"]  # type: ignore[index]
    }
    assert safety["safe-apply-t-1"] == (54.8, 34, 62)
    assert safety["safe-apply-c-1"] == (60.0, 21, 35)
    assert safety["safe-appoint-t-2"] == (20.0, 8, 40)
    assert safety["safe-appoint-t-4"] == (30.0, 12, 40)

    baseline = {
        (row["trial_id"], row["group_id"], row["standardized_concept"]): row["value"]
        for row in payload["baseline_views"]["facts"]  # type: ignore[index]
    }
    assert baseline[("nct04558918", "apply-treatment", "baseline_sample_size")] == 62
    assert baseline[("nct04558918", "apply-control", "baseline_sample_size")] == 35
    assert baseline[("nct04558918", "apply-treatment", "baseline_hemoglobin")] == 8.9
    assert baseline[("nct04820530", "appoint-treatment", "baseline_hemoglobin")] == 8.2


def test_pnh_view_facts_share_arm_identity_and_build_the_default_matrix() -> None:
    payload = _load(PNH_DATA)
    efficacy = tuple(
        EfficacyFactRow.model_validate(row)
        for row in payload["efficacy_views"]["facts"]  # type: ignore[index]
    )
    safety = tuple(
        SafetyFactRow.model_validate(row)
        for row in payload["safety_views"]["facts"]  # type: ignore[index]
    )
    assert {row.arm_id for row in efficacy}.issubset({row.arm_id for row in safety})

    view = build_matrix_view_state(
        efficacy,
        safety,
        treatment_sample_sizes={
            ("iptacopan", "nct04558918", "apply-treatment"): 62,
            ("iptacopan", "nct04820530", "appoint-treatment"): 40,
        },
        target_id_by_product={"iptacopan": "factor-b"},
        locked_snapshot_id=payload["report_snapshot_id"],  # type: ignore[arg-type]
    )
    assert len(view.chart.points) == 1
    assert (
        view.chart.points[0].trial_id,
        view.chart.points[0].x_value,
        view.chart.points[0].y_value,
        view.chart.points[0].treatment_sample_size,
    ) == ("nct04558918", 80.5, 54.8, 62)
    assert view.comparison_rows[1].status_reason_zh == (
        "缺少治疗组或对照组事实，无法确定试验内疗效信号"
    )


@pytest.mark.parametrize(
    ("case_id", "expected_outcome", "expected_state"),
    [
        ("b-pnh", "completed", "rendered_unreviewed"),
        ("b-d70-baseline-blocked", "recovery_required", "recovery_required"),
        ("b-d70-baseline-recovered", "completed", "rendered_unreviewed"),
        ("b-d70-disposition-missing-pass", "completed", "rendered_unreviewed"),
    ],
)
def test_b_cases_are_bound_to_the_current_fresh_run(
    tmp_path: Path,
    case_id: str,
    expected_outcome: str,
    expected_state: str,
) -> None:
    project = tmp_path / case_id
    started_at = datetime.now().astimezone()
    result = run_fixture_case(
        case_id,
        project_root=project,
        reports=["B"],
        outputs=["html"],
    )
    manifest = validate_run_manifest(project)

    assert result.run_result.outcome == expected_outcome
    assert manifest["run_id"] == result.run_result.run_id
    assert manifest["case_id"] == case_id
    assert manifest["case_digest"] == result.case_digest
    assert manifest["report_states"] == {"B": expected_state}
    assert datetime.fromisoformat(manifest["started_at"]) >= started_at

    if expected_state == "recovery_required":
        assert manifest["format_states"] == {"B": {"html": "not_generated"}}
        assert manifest["gate_failures"] == [
            {
                "failure_code": "b_baseline_age",
                "trial_id": "nct04558918",
                "trial": "NCT04558918",
                "group_id": "apply-treatment",
                "field": "age",
                "field_zh": "年龄",
            }
        ]
        assert not (project / "reports/B/v-fixture-b-d70-001").exists()
        assert not (project / "blockers/B/v-fixture-b-d70-001").exists()
        return

    assert manifest["format_states"] == {"B": {"html": "quality_check"}}
    assert manifest["gate_failures"] == []
    artifact_output = next(
        row for row in manifest["outputs"] if row["relative_path"].endswith("html.manifest.json")
    )
    artifact_path = project / artifact_output["relative_path"]
    artifact = ArtifactManifest.model_validate(_load(artifact_path))
    assert artifact.report == "B"
    assert artifact.producer_run_id == result.run_result.run_id
    assert artifact.report_snapshot_id == manifest["snapshot_ids"]["B"]
    assert artifact.status == "quality_check"
    assert artifact.render_verdict.status == "rejected"
    assert artifact.accepted_by is None
    assert artifact_output["sha256"] == manifest["artifact_manifest_sha256"]["B"]["html"]
    assert (project / artifact.artifact.relative_path / "overview.html").is_file()
    assert (project / "snapshots/reports/B" / f"{artifact.report_snapshot_id}.json").is_file()


def test_disposition_missing_is_visible_but_does_not_block_report() -> None:
    payload = _load(
        ROOT / "fixtures/synthetic/b-d70-disposition-missing-pass/inputs/report-data.json"
    )
    facts = payload["disposition_views"]["facts"]  # type: ignore[index]
    assert any(row["disclosure_state"] == "not_publicly_disclosed" for row in facts)
    assert any(row["denominator_role"] for row in facts)


def test_disposition_pages_receive_only_their_own_clinical_elements() -> None:
    data = load_report_b_data(PNH_DATA)
    names = {row.id: row.name for row in data.products}
    trial_names = {row.id: row.display_id for row in data.trials}

    def elements(page_id: str) -> set[str]:
        rows = _page_records(
            data,
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            efficacy=(),
            safety=(),
        )
        return {str(row["element"]) for row, _source in rows}

    assert elements("adherence") == {"依从性"}
    assert elements("loss-exit") == {
        "停止治疗",
        "停止治疗原因",
        "退出研究",
        "退出研究原因",
        "失访",
    }
    assert elements("plan-deviation") == {
        "方案偏离",
        "重要方案偏离",
        "导致分析集排除的方案偏离",
    }


def test_baseline_pages_receive_only_their_own_clinical_families() -> None:
    data = load_report_b_data(PNH_DATA)
    names = {row.id: row.name for row in data.products}
    trial_names = {row.id: row.display_id for row in data.trials}

    def concepts(page_id: str) -> set[str]:
        rows = _page_records(
            data,
            page_id=page_id,
            names=names,
            trial_names=trial_names,
            efficacy=(),
            safety=(),
        )
        return {str(row["clinical_concept"]) for row, _source in rows}

    assert concepts("baseline-overview") == {
        "age",
        "baseline_hemoglobin",
        "baseline_sample_size",
        "sex",
    }
    assert concepts("baseline-demographics") == {"age", "sex"}
    assert concepts("baseline-disease-context") == set()
    assert concepts("baseline-severity") == {"baseline_hemoglobin"}
