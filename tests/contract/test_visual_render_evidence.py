from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from ci_workflow.graph.visual_finalization import (
    VisualFinalizationError,
    validate_visual_render_evidence,
    validate_visual_verification_reference,
)

ROOT = Path(__file__).resolve().parents[2]
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
DOMAINS = (
    "copy_zh",
    "hierarchy_density",
    "typography_spacing",
    "color_legibility",
    "charts_tables",
    "interaction_consistency",
    "format_rendering",
)
TRIGGERS = (
    "page_load",
    "filter_change",
    "drill_down",
    "search",
    "keyboard",
    "reduced_motion",
)


def _target(engine: str, width: int) -> dict[str, Any]:
    return {
        "target_id": f"{engine}-{width}",
        "engine": engine,
        "page_id": "overview",
        "viewport": {"width": width, "height": 900},
        "screenshot_path": f"reviews/screenshots/{engine}-{width}.png",
        "screenshot_sha256": SHA_C,
        "metrics": {
            "horizontal_overflow_px": 0,
            "clipped_text_count": 0,
            "label_overlap_count": 0,
            "unreadable_label_count": 0,
        },
        "unavailable_required_fields": [],
        "responsive_alternatives": [],
        "interaction_checks": [
            {
                "trigger": trigger,
                "passed": True,
                "evidence": f"{trigger}状态已在真实浏览器复核",
            }
            for trigger in TRIGGERS
        ],
        "visible_text_scan": {
            "passed": True,
            "engineering_tokens_found": [],
            "untranslated_tokens_found": [],
        },
    }


def _evidence() -> dict[str, Any]:
    return {
        "$schema": "schemas/visual-render-evidence.schema.json",
        "schema_version": "1.0",
        "evidence_id": "render-evidence-A-html-v1",
        "report_kind": "A",
        "report_version": "v1",
        "format": "html",
        "run_id": "run-A-html-v1",
        "visual_plan_digest": SHA_A,
        "candidate_artifact_digest": SHA_B,
        "producer_identity": "render-deliver/run-A-html-v1",
        "render_targets": [
            _target("chromium", 768),
            _target("chromium", 1024),
            _target("chromium", 1440),
            _target("webkit", 768),
            _target("webkit", 1024),
            _target("webkit", 1440),
        ],
        "defects": [],
        "created_at": "2026-08-29T16:00:00+08:00",
    }


def _verdict() -> dict[str, Any]:
    return {
        "$schema": "schemas/visual-verification-reference.schema.json",
        "schema_version": "1.0",
        "verdict_id": "visual-verdict-A-html-v1",
        "format": "html",
        "visual_plan_digest": SHA_A,
        "candidate_artifact_digest": SHA_B,
        "render_evidence_digest": SHA_C,
        "producer_identity": "render-deliver/run-A-html-v1",
        "verifier_identity": "visual-package-qc/review-A-html-v1",
        "verdict": "accepted",
        "domains": [
            {
                "domain": domain,
                "status": "accepted",
                "criteria": [f"在截图中核对{domain}对应对象、状态和数值"],
                "evidence_refs": [f"chromium-768#{domain}"],
            }
            for domain in DOMAINS
        ],
        "created_at": "2026-08-29T16:30:00+08:00",
    }


@pytest.mark.parametrize(
    "filename",
    ["visual-render-evidence.schema.json", "visual-verification-reference.schema.json"],
)
def test_visual_release_schemas_are_valid(filename: str) -> None:
    schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_visual_render_evidence_accepts_complete_html_matrix() -> None:
    validated = validate_visual_render_evidence(
        _evidence(), expected_artifact_digest=SHA_B, expected_plan_digest=SHA_A
    )
    assert validated["evidence_id"] == "render-evidence-A-html-v1"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_webkit", "完整覆盖"),
        ("missing_1024", "完整覆盖"),
        ("failed_interaction", "六类关键交互"),
        ("label_overlap", "仍有横向溢出"),
        ("open_blocker", "未关闭的阻断缺陷"),
        ("text_scan", "工程化或未中文化"),
    ],
)
def test_visual_render_evidence_rejects_incomplete_or_unreadable_output(
    mutation: str, message: str
) -> None:
    evidence = _evidence()
    if mutation == "missing_webkit":
        evidence["render_targets"] = [
            target for target in evidence["render_targets"] if target["engine"] != "webkit"
        ]
    elif mutation == "missing_1024":
        evidence["render_targets"] = [
            target for target in evidence["render_targets"] if target["viewport"]["width"] != 1024
        ]
    elif mutation == "failed_interaction":
        evidence["render_targets"][0]["interaction_checks"][1]["passed"] = False
    elif mutation == "label_overlap":
        evidence["render_targets"][0]["metrics"]["label_overlap_count"] = 2
    elif mutation == "open_blocker":
        evidence["defects"] = [
            {
                "defect_id": "defect-1",
                "severity": "major",
                "blocking": True,
                "status": "open",
                "description": "气泡标签互相遮挡",
                "page_id": "overview",
                "component": "疗效安全性矩阵",
            }
        ]
    else:
        evidence["render_targets"][0]["visible_text_scan"] = {
            "passed": False,
            "engineering_tokens_found": ["pipeline"],
            "untranslated_tokens_found": [],
        }

    with pytest.raises(VisualFinalizationError, match=message):
        validate_visual_render_evidence(evidence)


def test_hidden_required_field_requires_a_verified_user_visible_alternative() -> None:
    evidence = _evidence()
    target = evidence["render_targets"][0]
    target["unavailable_required_fields"] = ["试验编号"]
    with pytest.raises(VisualFinalizationError, match="替代入口"):
        validate_visual_render_evidence(evidence)

    target["responsive_alternatives"] = [
        {"field": "试验编号", "access_method": "点击药物名称后在详情首行显示", "verified": True}
    ]
    validate_visual_render_evidence(evidence)


def test_visual_render_evidence_rejects_candidate_digest_drift() -> None:
    with pytest.raises(VisualFinalizationError, match="当前候选产物"):
        validate_visual_render_evidence(_evidence(), expected_artifact_digest=SHA_A)


def test_independent_visual_verdict_accepts_bound_seven_domain_review() -> None:
    validated = validate_visual_verification_reference(
        _verdict(),
        expected_artifact_digest=SHA_B,
        expected_render_digest=SHA_C,
        expected_plan_digest=SHA_A,
    )
    assert validated["verdict"] == "accepted"


def test_independent_visual_verdict_rejects_self_signing() -> None:
    verdict = _verdict()
    verdict["verifier_identity"] = verdict["producer_identity"]
    with pytest.raises(VisualFinalizationError, match="不得自签"):
        validate_visual_verification_reference(verdict)


def test_independent_visual_verdict_rejects_digest_drift() -> None:
    with pytest.raises(VisualFinalizationError, match="真实呈现证据"):
        validate_visual_verification_reference(_verdict(), expected_render_digest=SHA_A)


def test_independent_visual_verdict_rejects_accepted_summary_with_rejected_domain() -> None:
    verdict = copy.deepcopy(_verdict())
    verdict["domains"][0]["status"] = "rejected"
    with pytest.raises(VisualFinalizationError, match="逐域结论"):
        validate_visual_verification_reference(verdict)
