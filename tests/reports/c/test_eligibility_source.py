from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    _chart_groups,
    _criterion_parts,
    _table_rows,
)
from ci_workflow.reports.c.eligibility_source import (
    EligibilitySourceError,
    extract_eligibility_sections,
    hydrate_report_eligibility,
)

ROOT = Path(__file__).resolve().parents[3]
REAL_INPUT = (
    ROOT
    / "runs/acceptance/task-10.2-20260901-123524/inputs/c-real/recovery/report-c-data.json"
)
REAL_SOURCES = (
    ROOT
    / "runs/acceptance/task-10.2-20260901-123524/inputs/c-real/sources/clinicaltrials"
)


def test_plain_text_registry_sections_keep_every_item() -> None:
    record = json.loads((REAL_SOURCES / "NCT02260986.json").read_text(encoding="utf-8"))
    inclusion, exclusion = extract_eligibility_sections(record)

    assert "Chronic AD" in inclusion
    assert "Documented recent history" in inclusion
    assert "Participation in a prior Dupilumab clinical trial" in exclusion
    assert "Immunosuppressive/immunomodulating drugs" in exclusion


def test_html_registry_sections_keep_every_list_item() -> None:
    record = json.loads((REAL_SOURCES / "NCT06241118.json").read_text(encoding="utf-8"))
    inclusion, exclusion = extract_eligibility_sections(record)

    assert inclusion.count("<li>") >= 4
    assert exclusion.count("<li>") >= 8
    assert "Diagnosis of AD for at least 1 year" in inclusion
    assert "Skin co-morbidity" in exclusion


def test_real_c_payload_is_hydrated_for_all_twenty_trials() -> None:
    payload = json.loads(REAL_INPUT.read_text(encoding="utf-8"))
    hydrated = hydrate_report_eligibility(payload, REAL_SOURCES)
    rows = [
        item
        for item in hydrated["observations"]
        if item["field"] in {"inclusion_criterion", "exclusion_criterion"}
    ]

    assert len(rows) == 40
    assert all(len(item["source_text"]) >= 60 for item in rows)
    assert sum(item["source_text"].count("<li>") for item in rows) >= 12
    assert any("Documented recent history" in item["source_text"] for item in rows)


def test_missing_source_fails_closed(tmp_path: Path) -> None:
    payload = json.loads(REAL_INPUT.read_text(encoding="utf-8"))

    with pytest.raises(EligibilitySourceError, match="无法读取 NCT02260986"):
        hydrate_report_eligibility(payload, tmp_path)


def test_portal_splits_plain_and_html_criteria_without_losing_items() -> None:
    plain_record = json.loads(
        (REAL_SOURCES / "NCT02260986.json").read_text(encoding="utf-8")
    )
    html_record = json.loads(
        (REAL_SOURCES / "NCT06241118.json").read_text(encoding="utf-8")
    )
    plain_inclusion, plain_exclusion = extract_eligibility_sections(plain_record)
    html_inclusion, html_exclusion = extract_eligibility_sections(html_record)

    assert len(_criterion_parts(plain_inclusion)) >= 2
    assert len(_criterion_parts(plain_exclusion)) >= 5
    assert len(_criterion_parts(html_inclusion)) >= 4
    assert len(_criterion_parts(html_exclusion)) >= 8


def test_complete_tables_expand_every_registry_criterion() -> None:
    payload = json.loads(REAL_INPUT.read_text(encoding="utf-8"))
    data = ReportCPortalData.model_validate(
        hydrate_report_eligibility(payload, REAL_SOURCES)
    )
    observations = tuple(
        item
        for item in data.observations
        if item.field in {"inclusion_criterion", "exclusion_criterion"}
    )
    rows = _table_rows(data, observations, page_id="trial-detail")

    assert len(rows) > 100
    assert len({item["table_item_id"] for item in rows}) == len(rows)
    assert any("Documented recent history" in item["value"] for item in rows)


def test_eligibility_comparison_keeps_source_text_without_synthetic_counts() -> None:
    payload = json.loads(REAL_INPUT.read_text(encoding="utf-8"))
    data = ReportCPortalData.model_validate(
        hydrate_report_eligibility(payload, REAL_SOURCES)
    )
    observations = tuple(
        item for item in data.observations if item.field == "inclusion_criterion"
    )
    groups = _chart_groups(
        data,
        observations,
        page_id="inclusion-criteria",
        title="入选标准",
    )

    assert groups[0]["_chart_type"] == "status_matrix"
    assert len(groups[0]["rows"]) == 20
    assert all(item["source_text"] for item in groups[0]["rows"])
    assert all(item.get("numeric_value") is None for item in groups[0]["rows"])
    assert all(item["unit"] != "条" for item in groups[0]["rows"])
