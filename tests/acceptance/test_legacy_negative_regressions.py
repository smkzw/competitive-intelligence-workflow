"""旧版六类负向样本必须由当前产品合同确定性拒绝。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.application.fixture_runner import run_fixture_case
from ci_workflow.graph.visual_finalization import (
    VisualFinalizationError,
    validate_visual_render_evidence,
)
from ci_workflow.qc.report_a_acceptance import inspect_legacy_report_a_sample

ROOT = Path(__file__).resolve().parents[2]
NEGATIVE_ROOT = ROOT / "fixtures" / "negative"
SCENARIO_PATH = (
    ROOT
    / "fixtures"
    / "acceptance"
    / "required-v12"
    / "legacy-negative-regressions"
    / "inputs"
    / "scenario.json"
)


def _legacy_issue(directory: str, expected_code: str) -> None:
    issues = inspect_legacy_report_a_sample(NEGATIVE_ROOT / directory)
    assert expected_code in {issue.code for issue in issues}


def test_all_six_negative_subclasses_are_rejected(tmp_path: Path) -> None:
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    declared = {row["id"] for row in scenario["subscenarios"]}
    assert declared == {
        "old-csu-a",
        "pnh-b",
        "ad-a",
        "style-collapse",
        "fake-screenshot",
        "false-green-qc",
    }

    _legacy_issue("legacy-a-five-products-zero-trials", "products_without_trials")
    _legacy_issue("legacy-a-ad-shell", "unanchored_report_shell")
    _legacy_issue("legacy-a-style-break", "malformed_stylesheet")
    _legacy_issue("legacy-a-false-green", "zero_card_false_green")

    pnh = run_fixture_case(
        "b-d70-baseline-blocked",
        project_root=tmp_path / "pnh-b",
        reports=["B"],
        outputs=["html"],
    )
    assert pnh.run_result.outcome == "evidence_blocked"
    assert not (
        tmp_path / "pnh-b" / "reports" / "B" / "v-fixture-b-d70-001"
    ).exists()

    fake_screenshot_only = {
        "$schema": "schemas/visual-render-evidence.schema.json",
        "schema_version": "1.0",
        "render_targets": [
            {
                "screenshot_path": "reviews/screenshots/unbound.png",
                "screenshot_sha256": "0" * 64,
            }
        ],
    }
    with pytest.raises(VisualFinalizationError):
        validate_visual_render_evidence(fake_screenshot_only)
