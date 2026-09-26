"""Old A display rows must not be treated as accepted source atoms."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.audit_a_payload_drift import (
    audit_payloads,
    audit_row_source_maps,
    load_payload,
)


def test_drift_audit_matches_source_title_not_display_row_id() -> None:
    old = {
        "efficacy": [{
            "row_id": "eff-1", "trial_id": "nct1", "product_id": "drug-a",
            "endpoint": "中文展示名", "endpoint_source": "Original endpoint",
            "value": 0, "denominator": 20,
        }],
        "safety": [],
    }
    new = {
        "efficacy": [], "safety": [],
        "additional_observations": [{
            "row_id": "other-hash", "trial_id": "NCT1", "product_id": "drug-b",
            "endpoint": "Original endpoint", "raw_value": "0.00",
            "group_assignment_state": "unknown",
        }],
    }
    report = audit_payloads(old, new)
    assert report["counts"]["matched_unique"] == 1
    assert report["counts"]["reclassified"] == 1
    assert report["counts"]["old_only"] == 0
    assert report["counts"]["new_only"] == 0
    pair = report["matched_unique"][0]
    assert pair["old_row_id"] == "eff-1"
    assert pair["new_row_id"] == "other-hash"
    assert pair["changes"]["domain"] == ["efficacy", "additional_observations"]
    assert pair["changes"]["product_id"] == ["drug-a", "drug-b"]
    assert pair["changes"]["denominator"] == [20, None]


def test_duplicate_source_keys_remain_ambiguous_and_row_id_reuse_is_visible() -> None:
    old = {"efficacy": [
        {"row_id": "eff-1", "trial_id": "nct1", "endpoint_source": "E", "value": 0},
        {"row_id": "eff-2", "trial_id": "nct1", "endpoint_source": "E", "value": 0},
    ], "safety": []}
    new = {"efficacy": [
        {"row_id": "eff-1", "trial_id": "nct1", "endpoint": "E", "value": 1},
        {"row_id": "eff-2", "trial_id": "nct1", "endpoint": "E", "value": 0},
    ], "safety": []}
    report = audit_payloads(old, new)
    assert report["counts"]["matched_unique"] == 0
    assert report["counts"]["ambiguous_or_count_drift"] == 1
    assert report["counts"]["row_id_reused_for_different_source_key"] == 1
    assert report["ambiguous_or_count_drift"][0]["old_row_ids"] == ["eff-1", "eff-2"]


def test_safety_true_zero_matches_and_file_loader_accepts_only_report_assignment(
    tmp_path: Path,
) -> None:
    old = {"efficacy": [], "safety": [{
        "row_id": "safe-1", "trial_id": "nct2", "term_key": "death", "value": 0,
    }]}
    new = {"efficacy": [], "safety": [{
        "row_id": "safe-9", "trial_id": "NCT2", "term_key": "death", "value": 0,
    }]}
    assert audit_payloads(old, new)["counts"]["matched_unique"] == 1
    path = tmp_path / "report.js"
    path.write_text("window.REPORT_A=" + json.dumps(old) + ";\n", encoding="utf-8")
    assert load_payload(path) == old
    path.write_text("window.UNRELATED=" + json.dumps(old) + ";", encoding="utf-8")
    with pytest.raises(ValueError, match="REPORT_A"):
        load_payload(path)


def test_exact_source_delta_separates_page_noise_from_value_and_context() -> None:
    base = {"trial_id": "nct1", "value_path": "$.resultsSection.outcome[0].value",
            "domain": "efficacy", "raw_value": "7", "outcome_title": "Response",
            "group_id": "OG1", "source_page_sha256": "old", "row_id": "eff-1"}
    unchanged = {**base, "source_page_sha256": "new", "row_id": "eff-hash"}
    first = audit_row_source_maps({"row_source_map": [base]},
                                  {"row_source_map": [unchanged]})
    assert first["counts"] == {
        "old_atoms": 1, "new_atoms": 1, "unchanged": 1, "modified": 0,
        "withdrawn": 0, "added": 0, "source_page_changed": 1,
    }
    assert first["pairs"][0]["old_row_id"] == "eff-1"
    assert first["pairs"][0]["new_row_id"] == "eff-hash"
    changed = {**unchanged, "raw_value": "8", "group_id": "OG2"}
    second = audit_row_source_maps({"row_source_map": [base]},
                                   {"row_source_map": [changed]})
    assert second["counts"]["modified"] == 1
    assert second["pairs"][0]["changed_fields"] == ["raw_value", "group_id"]
    with pytest.raises(ValueError, match="duplicate exact source atom"):
        audit_row_source_maps({"row_source_map": [base, base]},
                              {"row_source_map": [changed]})
