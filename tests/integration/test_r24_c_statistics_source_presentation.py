"""Production C statistical text reachability/source roles; synthetic development inputs.

No PDF extraction, scientific acceptance, browser pixels or clinical truth is
claimed by these fixtures. Each test calls the real renderer/projection.
"""

import json
from pathlib import Path

import pytest

from ci_workflow.domain.enums import FactDisclosureState
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.gates.models import SourceRole
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    _chart_row,
    _external_source_entries,
    _page_observations,
    _table_rows,
    render_report_c_site,
)
from ci_workflow.reports.c import DesignFieldFamily

PDF_URL = "https://cdn.clinicaltrials.gov/large-docs/67/NCT04178967/SAP_001.pdf"
FIELDS = ("comparison_logic", "statistical_model", "effect_size", "multiplicity")


def _data() -> ReportCPortalData:
    data = ReportCPortalData.model_validate_json(
        Path("fixtures/positive/c-atopic-dermatitis/inputs/report-data.json").read_bytes()
    )
    seed = next(row for row in data.observations if row.field == "analysis_population")
    rows = tuple(seed.model_copy(update={
        "row_id": "development-stat-" + field,
        "source_row_id": "development-stat-" + field,
        "observation_id": "development-stat-" + field,
        "field": field,
        "field_family": DesignFieldFamily.STATISTICAL,
        "source_field_name": field,
        "source_field_definition": "Development statistical context",
        "source_text": "No imputation is planned; repeated measures remain descriptive.",
        "display_text": None,
        "source_role": SourceRole.PROTOCOL_SAP,
        "source_version_id": "development-protocol-version",
        "source_locator": EvidenceLocator(document_role="protocol_sap", page=6,
                                           paragraph="Statistical context", url=PDF_URL),
        "disclosure_state": FactDisclosureState.REPORTED_VALUE,
    }) for field in FIELDS)
    return data.model_copy(update={"observations": (*data.observations, *rows)})


@pytest.mark.parametrize("field", FIELDS)
def test_statistical_contract_fields_reach_statistics_page_and_complete_table(field: str) -> None:
    data = _data()
    observations = _page_observations(data, "sample-analysis-statistics")
    row_id = "development-stat-" + field
    assert row_id in {row.row_id for row in observations}
    rows = _table_rows(data, observations, page_id="sample-analysis-statistics")
    actual = next(row for row in rows if row["row_id"] == row_id)
    assert "No imputation is planned" in actual["value"]
    assert "numeric_projection" not in actual  # A paragraph is not a numeric axis.


def test_protocol_entries_keep_exact_url_and_do_not_collapse_into_registry() -> None:
    data = _data()
    entries = _external_source_entries(data, data.observations)
    protocol = [entry for entry in entries if entry["url"] == PDF_URL]
    assert len(protocol) == 1
    assert "研究方案与统计分析计划" in protocol[0]["label"]
    original_urls = {row.source_locator.url for row in data.observations
                     if row.source_role is SourceRole.CLINICAL_TRIAL_REGISTRY}
    assert original_urls <= {entry["url"] for entry in entries}
    row = next(row for row in data.observations if row.field == "statistical_model")
    projection = _chart_row(data, row, chart_type="status_matrix")
    assert projection["source_location_zh"].startswith("研究方案与统计分析计划")


def test_external_source_urls_do_not_expose_local_or_executable_replacements() -> None:
    data = _data()
    seed = data.observations[-1]
    rows = tuple(seed.model_copy(update={
        "source_locator": seed.source_locator.model_copy(update={"url": url}),
    }) for url in ("javascript:alert(1)", "file:///private/example.pdf", "https:///missing-host"))
    assert _external_source_entries(data, rows) == ()


def test_same_trial_distinct_documents_and_versions_are_not_first_wins() -> None:
    data = _data()
    seed = data.observations[-1]
    another_version = seed.model_copy(update={"source_version_id": "development-sap-version-2"})
    another_document = seed.model_copy(update={
        "source_version_id": "development-protocol-2",
        "source_locator": seed.source_locator.model_copy(update={
            "url": PDF_URL.replace("SAP_001.pdf", "Prot_000.pdf"),
        }),
    })
    entries = _external_source_entries(data, (seed, another_version, another_document, seed))
    assert len(entries) == 2
    assert sum(entry["url"] == PDF_URL for entry in entries) == 1
    assert {row.source_version_id for row in (seed, another_version)} == {
        "development-protocol-version", "development-sap-version-2",
    }
    assert another_document.source_locator.url != seed.source_locator.url


def test_ordinary_statistics_page_exposes_text_comparison_without_fake_axes(tmp_path: Path) -> None:
    site = tmp_path / "ordinary-c"
    render_report_c_site(_data(), site)
    html = (site / "sample-analysis-statistics.html").read_text()
    assert 'id="kz-c-design-matrix"' not in html
    for field in FIELDS:
        assert "development-stat-" + field in html
    assert PDF_URL in html
    payload, _ = json.JSONDecoder().raw_decode(html.split("window.__CHART_GROUPS__ = ", 1)[1])
    chart_ids = {row["row_id"] for group in payload for row in group["rows"]}
    assert {"development-stat-" + field for field in FIELDS} <= chart_ids
    assert all("numeric_projection" not in row for group in payload for row in group["rows"]
               if row["row_id"].startswith("development-stat-"))


def test_statistics_has_one_complete_reading_view_not_duplicate_paragraph_matrix(
    tmp_path: Path,
) -> None:
    data = _data()
    site = tmp_path / "ordinary-c"
    render_report_c_site(data, site)
    html = (site / "sample-analysis-statistics.html").read_text()
    groups, _ = json.JSONDecoder().raw_decode(html.split("window.__CHART_GROUPS__ = ", 1)[1])
    rows = [row for group in groups for row in group["rows"]]
    assert {row["row_id"] for row in rows} == {
        row.row_id for row in _page_observations(data, "sample-analysis-statistics")
    }
    assert all("numeric_projection" not in row for row in rows
               if row["row_id"].startswith("development-stat-"))
    assert 'id="kz-c-design-matrix"' not in html
    assert "kz-chart-table__row" in html and PDF_URL in html


def test_actual_source_scope_does_not_invent_china_failure_or_missing_n_exclusion(
    tmp_path: Path,
) -> None:
    site = tmp_path / "ordinary-c"
    render_report_c_site(_data(), site)
    html = (site / "evidence-limitations.html").read_text()
    assert "研究方案与统计分析计划" in html
    assert "中国境内登记路线访问受阻" not in html
    assert "样本量未披露的试验未纳入试验明细" not in html
    assert "仅来自 ClinicalTrials.gov" not in html
