"""Root-family membership: source Age/Sex reach demographics without science remaps."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_b import (
    _baseline_navigational_family,
    _baseline_subpage_empty_copy,
    _page_records,
    load_report_b_data,
)

ROOT = Path(__file__).resolve().parents[2]
FROZEN_B = (
    ROOT
    / ".artifacts/1007-abc-current-integration-v1/working/project/evidence/library"
    / "b-candidate-v5.json"
)
PNH_DATA = ROOT / "fixtures/positive/b-pnh/inputs/report-data.json"


def _names(data):
    return {row.id: row.name for row in data.products}, {
        row.id: row.display_id for row in data.trials
    }


@pytest.mark.skipif(not FROZEN_B.is_file(), reason="frozen current21 B payload absent")
def test_source_age_continuous_and_sex_reach_demographics_without_science_rewrite() -> None:
    before = sha256(FROZEN_B.read_bytes()).hexdigest()
    payload = json.loads(FROZEN_B.read_bytes())
    source_facts = payload["baseline_views"]["facts"]
    assert len(source_facts) == 183
    source_by_id = {row["row_id"]: row for row in source_facts}
    age_ids = {
        row_id
        for row_id, row in source_by_id.items()
        if str(row.get("clinical_concept", "")).startswith("Age, Continuous")
    }
    sex_ids = {
        row_id
        for row_id, row in source_by_id.items()
        if str(row.get("clinical_concept", "")).startswith("Sex: Female, Male")
    }
    assert len(age_ids) == 24
    assert len(sex_ids) == 24

    data = load_report_b_data(FROZEN_B)
    names, trial_names = _names(data)
    demo = _page_records(
        data,
        page_id="baseline-demographics",
        names=names,
        trial_names=trial_names,
        efficacy=(),
        safety=(),
    )
    demo_ids = {str(row["row_id"]) for row, _source in demo}
    assert age_ids <= demo_ids
    assert sex_ids <= demo_ids
    assert demo_ids == age_ids | sex_ids

    for row, source in demo:
        raw = source_by_id[str(row["row_id"])]
        assert isinstance(source, dict)
        # Navigational membership must not rewrite source science atoms.
        for key in (
            "clinical_concept",
            "unit",
            "value",
            "statistic_form",
            "source_value_role",
            "source_domain",
            "source_fact_version_id",
            "source_version_id",
            "source_row_id",
        ):
            assert source.get(key) == raw.get(key)
        assert row.get("clinical_concept") not in {"age", "sex"}
        assert row.get("value") == raw.get("value")
        assert row.get("unit") == raw.get("unit")

    overview = _page_records(
        data,
        page_id="baseline-overview",
        names=names,
        trial_names=trial_names,
        efficacy=(),
        safety=(),
    )
    overview_ids = {str(row["row_id"]) for row, _source in overview}
    assert overview_ids == set(source_by_id)
    race_ids = {
        row_id
        for row_id, row in source_by_id.items()
        if str(row.get("clinical_concept", "")).startswith(
            ("Race (", "Race/", "Ethnicity")
        )
    }
    assert race_ids
    assert race_ids.isdisjoint(demo_ids)
    assert race_ids <= overview_ids
    assert sha256(FROZEN_B.read_bytes()).hexdigest() == before


def test_legacy_canonical_age_sex_demographics_membership_preserved() -> None:
    data = load_report_b_data(PNH_DATA)
    names, trial_names = _names(data)
    concepts = {
        str(row["clinical_concept"])
        for row, _source in _page_records(
            data,
            page_id="baseline-demographics",
            names=names,
            trial_names=trial_names,
            efficacy=(),
            safety=(),
        )
    }
    assert concepts == {"age", "sex"}


def test_dosage_age_and_unknown_titles_are_not_forced_into_demographics() -> None:
    assert (
        _baseline_navigational_family(
            {"clinical_concept": "baseline:dosageage"},
            {"clinical_concept": "Dosage age", "unit": "mg", "value": 12},
        )
        is None
    )
    assert (
        _baseline_navigational_family(
            {"clinical_concept": "baseline:ageindosageschedule"},
            {"clinical_concept": "Age in dosage schedule", "unit": "years", "value": 40},
        )
        is None
    )
    assert (
        _baseline_navigational_family(
            {"clinical_concept": "baseline:raceethnicitycustomizedasian"},
            {"clinical_concept": "Race/Ethnicity, Customized｜Asian", "value": 1},
        )
        is None
    )
    assert (
        _baseline_navigational_family(
            {"clinical_concept": "baseline:agecontinuous"},
            {"clinical_concept": "Age, Continuous", "unit": "years", "value": 51.1},
        )
        == "age"
    )
    assert (
        _baseline_navigational_family(
            {"clinical_concept": "baseline:agecontinuous标准差"},
            {
                "clinical_concept": "Age, Continuous｜标准差",
                "unit": "years",
                "value": 15.8,
                "source_value_role": "dispersion",
            },
        )
        == "age"
    )
    assert (
        _baseline_navigational_family(
            {"clinical_concept": "baseline:sexfemalemalefemale"},
            {"clinical_concept": "Sex: Female, Male｜Female", "value": 48},
        )
        == "sex"
    )
    assert _baseline_navigational_family({"clinical_concept": "age"}, {}) == "age"
    assert _baseline_navigational_family({"clinical_concept": "sex"}, {}) == "sex"


def test_baseline_empty_reason_distinguishes_no_match_from_no_public_baseline() -> None:
    no_public_title, no_public_lead = _baseline_subpage_empty_copy(
        "baseline-demographics",
        has_public_baseline=False,
        has_matching_rows=False,
    )
    no_match_title, no_match_lead = _baseline_subpage_empty_copy(
        "baseline-demographics",
        has_public_baseline=True,
        has_matching_rows=False,
    )
    assert no_public_title == "暂无公开记录（基线）"
    assert "公开基线" in no_public_lead
    assert no_match_title != no_public_title
    assert "人口学" in no_match_title
    assert "无匹配" in no_match_title or "未匹配" in no_match_title
    assert "总览" in no_match_lead or "其他" in no_match_lead
    populated_title, _lead = _baseline_subpage_empty_copy(
        "baseline-demographics",
        has_public_baseline=True,
        has_matching_rows=True,
    )
    assert populated_title == no_public_title  # unused when rows exist; keep stable default


def test_populated_baseline_lead_does_not_claim_no_public_records() -> None:
    _title, lead = _baseline_subpage_empty_copy(
        "baseline-demographics", has_public_baseline=True, has_matching_rows=True,
    )
    assert "暂无公开" not in lead


def test_source_publication_name_is_not_a_baseline_measure_identity() -> None:
    assert _baseline_navigational_family(
        {"clinical_concept": "baseline:unresolved"}, {"source_name": "Age"},
    ) is None
