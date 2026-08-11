from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parents[2]
FILTER_ROOT = ROOT / "docs/architecture/filter-contracts"
CATALOG_ROOT = ROOT / "docs/architecture/page-catalogs"
COMMON_PAGE_FILTERS = {"indication", "product", "target-mechanism", "trial"}
REQUIRED_B_BASELINE = {
    "target-mechanism",
    "region",
    "cohort-arm",
    "baseline-population",
    "variable-domain",
    "variable",
    "statistic",
    "scale-unit",
    "disclosure-status",
}
REQUIRED_B_DISPOSITION = {
    "target-mechanism",
    "period",
    "disposition-population",
    "analysis-population",
    "field-family",
    "reason",
    "denominator-role",
    "measurement-object",
    "time-window",
    "disclosure-status",
}
REQUIRED_DRAWER_FIELDS = {
    "product",
    "trial",
    "cohort-arm",
    "measure-or-design-element",
    "source-name-definition",
    "scale-version-direction",
    "timepoint-window",
    "value-threshold-unit",
    "numerator-denominator",
    "denominator-role",
    "source-version",
    "precise-locator",
    "disclosure-status",
    "compatibility-difference",
    "source-excerpt",
    "normalization-note",
    "canonical-field-family",
    "statistic-form-or-measurement-object",
    "reason-original-canonical",
    "reason-mutual-exclusivity",
}


def _load(name: str) -> dict[str, object]:
    value = yaml.safe_load((FILTER_ROOT / f"{name}.yaml").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _filters(contract: dict[str, object]) -> dict[str, dict[str, object]]:
    values = cast(list[dict[str, object]], contract["filters"])
    return {str(value["id"]): value for value in values}


def test_common_filters_freeze_page_module_url_reset_and_evidence_linkage() -> None:
    common = _load("common")
    assert common["contract_version"] == "1.0"
    filters = _filters(common)
    assert set(filters) >= COMMON_PAGE_FILTERS
    state = cast(dict[str, object], common["state_contract"])
    assert state == {
        "page_reset_separate_from_module_reset": True,
        "page_and_module_state_in_url": True,
        "named_large_views_in_local_manifest": True,
        "no_state_truncation": True,
        "no_auto_expand_on_empty": True,
        "chart_table_evidence_share_fact_set": True,
        "hover_focus_selection_linked": True,
    }
    drawer = cast(dict[str, object], common["evidence_drawer"])
    assert set(cast(list[str], drawer["fields"])) >= REQUIRED_DRAWER_FIELDS
    assert drawer["same_page_right_drawer"] is True
    assert drawer["preserve_filter_scroll_focus"] is True
    assert drawer["keyboard_and_focus_return"] is True
    assert drawer["pin_multiple_items_for_side_by_side_review"] is True
    assert drawer["reduced_motion_supported"] is True


def test_report_filters_cover_a_b_c_multiselect_dimensions_and_native_chinese_labels() -> None:
    common_ids = set(_filters(_load("common")))
    report_filters: dict[str, set[str]] = {}
    for report in ("A", "B", "C"):
        contract = _load(report)
        assert contract["extends"] == "common-v1"
        filters = _filters(contract)
        report_filters[report] = set(filters)
        for filter_contract in filters.values():
            assert filter_contract["multiselect"] is True
            assert re.search(r"[\u4e00-\u9fff]", str(filter_contract["label"]))
            assert str(filter_contract["url_key"]).strip()
            assert cast(list[str], filter_contract["domains"])
    assert {"anchor-trial", "endpoint", "timepoint", "effect-form", "safety-dimension"} <= (
        common_ids | report_filters["A"]
    )
    assert (common_ids | report_filters["B"]) >= REQUIRED_B_BASELINE
    assert (common_ids | report_filters["B"]) >= REQUIRED_B_DISPOSITION
    assert {
        "cohort-arm",
        "design-element",
        "criterion-family",
        "scale-score",
        "assessment-time",
        "operator-threshold-unit",
        "endpoint-role",
        "visit-period",
    } <= (common_ids | report_filters["C"])


def test_filter_profiles_are_explicit_and_do_not_silently_widen_scope() -> None:
    for report in ("A", "B", "C"):
        contract = _load(report)
        filters = set(_filters(contract)) | set(_filters(_load("common")))
        profiles = cast(dict[str, list[str]], contract["profiles"])
        assert profiles
        for profile_ids in profiles.values():
            assert profile_ids
            assert set(profile_ids) <= filters
        applicability = cast(dict[str, object], contract["applicability"])
        assert applicability["irrelevant_dimension"] == "隐藏或禁用，并显示简洁中文原因"
        assert applicability["empty_result"] == "保持当前范围并显示空状态，不自动扩大"


def test_every_page_uses_declared_filter_and_evidence_drawer_profiles() -> None:
    common = _load("common")
    drawer = cast(dict[str, object], common["evidence_drawer"])
    drawer_profiles = cast(dict[str, list[str]], drawer["profiles"])
    drawer_fields = set(cast(list[str], drawer["fields"]))
    assert drawer_profiles
    for fields in drawer_profiles.values():
        assert fields
        assert set(fields) <= drawer_fields

    for report in ("A", "B", "C"):
        filter_profiles = set(cast(dict[str, list[str]], _load(report)["profiles"]))
        catalog = yaml.safe_load(
            (CATALOG_ROOT / f"{report}.yaml").read_text(encoding="utf-8")
        )
        assert isinstance(catalog, dict)
        pages = cast(list[dict[str, object]], catalog["pages"])
        for page in pages:
            assert set(cast(list[str], page["filter_profiles"])) <= filter_profiles
            assert str(page["evidence_drawer_profile"]) in drawer_profiles


def test_b_baseline_matrix_and_disposition_profiles_keep_required_user_dimensions() -> None:
    contract = _load("B")
    profiles = cast(dict[str, list[str]], contract["profiles"])
    for profile_id in (
        "b-baseline",
        "b-baseline-demographics",
        "b-baseline-disease",
        "b-baseline-severity",
    ):
        assert set(profiles[profile_id]) >= REQUIRED_B_BASELINE

    assert set(profiles["b-matrix"]) >= {
        "analysis-population",
        "ae-term-grade",
        "denominator-role",
    }
    for profile_id in (
        "b-disposition",
        "b-participant-flow",
        "b-adherence",
        "b-loss-exit",
        "b-screen-failure",
        "b-rescue-treatment",
        "b-prohibited-medication",
        "b-plan-deviation",
    ):
        assert "target-mechanism" in profiles[profile_id]


def test_baseline_and_disposition_drawers_preserve_interpretation_fields() -> None:
    drawer = cast(dict[str, object], _load("common")["evidence_drawer"])
    profiles = cast(dict[str, list[str]], drawer["profiles"])
    assert set(profiles["baseline-observation"]) >= {
        "canonical-field-family",
        "statistic-form-or-measurement-object",
        "timepoint-window",
    }
    assert set(profiles["trial-disposition"]) >= {
        "canonical-field-family",
        "statistic-form-or-measurement-object",
        "reason-original-canonical",
        "reason-mutual-exclusivity",
    }


def test_each_disposition_subpage_keeps_its_load_bearing_dimensions() -> None:
    profiles = cast(dict[str, list[str]], _load("B")["profiles"])
    required_by_profile = {
        "b-participant-flow": {"analysis-population", "denominator-role"},
        "b-adherence": {"analysis-population", "measurement-object", "time-window"},
        "b-loss-exit": {"analysis-population", "reason", "denominator-role", "time-window"},
        "b-screen-failure": {"analysis-population", "reason", "denominator-role"},
        "b-rescue-treatment": {"analysis-population", "denominator-role", "time-window"},
        "b-prohibited-medication": {"analysis-population", "denominator-role", "time-window"},
        "b-plan-deviation": {
            "analysis-population",
            "denominator-role",
            "measurement-object",
            "time-window",
        },
    }
    for profile_id, required in required_by_profile.items():
        assert set(profiles[profile_id]) >= required
