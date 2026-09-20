"""特应性皮炎锁定来源包的确定性结果重建回归。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from tools.rebuild_atopic_dermatitis_package import rebuild_atopic_dermatitis_package

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "fixtures/positive/a-atopic-dermatitis/research-package.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, Any], value)


def test_rebuild_projects_locked_outcomes_and_adverse_events_without_teae_alias(
    tmp_path: Path,
) -> None:
    result = rebuild_atopic_dermatitis_package(PACKAGE, tmp_path / "rebuilt")
    content = _load(result.content_path)
    manifest = _load(result.manifest_path)
    original = _load(PACKAGE)

    original_report = original["report_data"]
    rebuilt_report = content["report_data"]
    assert isinstance(original_report, dict)
    assert isinstance(rebuilt_report, dict)
    assert len(rebuilt_report["products"]) == len(original_report["products"])
    assert len(rebuilt_report["trials"]) == len(original_report["trials"])
    assert len(rebuilt_report["efficacy"]) == len(original_report["efficacy"]) == 6_780
    assert len(rebuilt_report["safety"]) == len(original_report["safety"]) == 10_228

    facts = {fact["row_ref"]: fact for fact in content["facts"]}
    safety_rows = rebuilt_report["safety"]
    assert isinstance(safety_rows, list)
    teae_rows = [row for row in safety_rows if row["term"] == "任何TEAE"]
    assert teae_rows
    for row in teae_rows:
        fact = facts[f"safety:{row['row_id']}"]
        assert "otherNumAffected" not in fact["locator"]["field_path"]

    issue_rows = manifest["issues"]
    assert isinstance(issue_rows, list)
    assert any(item["kind"] == "not_reported" for item in issue_rows)
    assert not any(item["kind"] == "parse_failure" for item in issue_rows)
    assert all(item["source_id"].startswith("ctgov-") for item in issue_rows)
    assert manifest["output"]["content_digest"] == result.content_digest
    assert manifest["output"]["content_sha256"]


def test_rebuild_manifest_records_product_and_trial_coverage_states(tmp_path: Path) -> None:
    result = rebuild_atopic_dermatitis_package(PACKAGE, tmp_path / "rebuilt")
    manifest = _load(result.manifest_path)
    coverage = manifest["coverage"]

    assert isinstance(coverage, dict)
    assert len(coverage["audited_trial_ids"]) == 44
    assert coverage["trial_status_counts"] == {
        "registry_results_not_posted": 18,
        "registry_results_projected": 17,
        "reported_by_secondary_source": 14,
    }
    assert len(coverage["trials"]) == 49
    assert len(coverage["products"]) == 38
    assert not [
        product
        for product in coverage["products"]
        if product["result_status"] == "有公开关键结果"
        and not product["comparable_result_trial_ids"]
    ]


def test_rebuild_output_is_byte_stable_for_same_locked_package(tmp_path: Path) -> None:
    first = rebuild_atopic_dermatitis_package(PACKAGE, tmp_path / "first")
    second = rebuild_atopic_dermatitis_package(PACKAGE, tmp_path / "second")

    assert first.content_path.read_bytes() == second.content_path.read_bytes()
    assert first.manifest_path.read_bytes() == second.manifest_path.read_bytes()
    assert first.content_digest == second.content_digest
    assert first.input_digest == second.input_digest
    assert dict(first.counts) == dict(second.counts)


def test_rebuild_never_displays_participant_counts_as_percentages(tmp_path: Path) -> None:
    result = rebuild_atopic_dermatitis_package(PACKAGE, tmp_path / "rebuilt")
    report = _load(result.content_path)["report_data"]
    efficacy = report["efficacy"]

    assert not [row for row in efficacy if row["unit"] == "%" and row["value"] > 100]
    easi75 = next(
        row
        for row in efficacy
        if row["trial_id"] == "nct05651711"
        and row["arm"] == "治疗组"
        and row["numerator"] == 178
        and row["denominator"] == 543
    )
    assert (easi75["value"], easi75["unit"]) == (32.8, "%")


def test_mixed_ae_sae_classes_and_teae_subsets_keep_their_meaning(tmp_path: Path) -> None:
    result = rebuild_atopic_dermatitis_package(PACKAGE, tmp_path / "rebuilt")
    safety = _load(result.content_path)["report_data"]["safety"]
    tralokinumab = [row for row in safety if row["trial_id"] == "nct03131648"]

    any_ae = [row for row in tralokinumab if row["term"] == "任何AE"]
    any_sae = [row for row in tralokinumab if row["term"] == "任何SAE"]
    assert {(row["numerator"], row["denominator"], row["value"]) for row in any_ae} >= {
        (411, 602, 68.3),
        (133, 196, 67.9),
    }
    assert {(row["numerator"], row["denominator"], row["value"]) for row in any_sae} >= {
        (23, 602, 3.8),
        (8, 196, 4.1),
    }
    assert not [
        row
        for row in safety
        if row["trial_id"] == "nct02277743"
        and row["term"] == "任何TEAE"
        and row["value"] in {0.0, 0.9, 1.7, 1.8}
    ]


def test_fact_zero_state_and_switch_arm_role_are_semantically_exact(tmp_path: Path) -> None:
    result = rebuild_atopic_dermatitis_package(PACKAGE, tmp_path / "rebuilt")
    content = _load(result.content_path)
    false_zero = [
        fact
        for fact in content["facts"]
        if fact["disclosure_state"] == "reported_zero"
        and float(str(fact["raw_value"]).removesuffix("%")) != 0.0
    ]
    assert not false_zero
    switched = [
        row
        for section in ("efficacy", "safety")
        for row in content["report_data"][section]
        if row.get("arm_detail")
        and any(
            token in row["arm_detail"]
            for token in (
                "Vehicle Cream to Ruxolitinib",
                "Placebo Non-Responder/Lebrikizumab",
                "Placebo Then Bermekimab",
                "Placebo- Tezepelumab",
            )
        )
    ]
    assert switched
    assert all(row["arm"] == "治疗组" for row in switched)
