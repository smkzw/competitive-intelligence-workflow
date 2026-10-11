"""Optional absent source sections never require fabricated placeholder facts."""

import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site


def _payload():
    root = Path(__file__).resolve().parents[2]
    return json.loads((root / "fixtures/synthetic/a-complete/inputs/report-data.json").read_bytes())


@pytest.mark.parametrize("section", ["regulatory", "companies", "patents", "history"])
@pytest.mark.parametrize("omitted", [False, True])
def test_absent_optional_source_section_does_not_invent_rows(section, omitted):
    raw = _payload()
    if omitted:
        raw.pop(section)
    else:
        raw[section] = []
    data = ReportAPortalData.model_validate(raw)
    assert getattr(data, section) == ()
    assert data.products and data.trials and data.efficacy and data.safety


@pytest.mark.parametrize("section", ["regulatory", "companies", "patents", "history"])
def test_populated_optional_section_still_requires_real_product_relation(section):
    raw = _payload()
    raw[section][0]["product_id"] = "foreign-product"
    with pytest.raises(ValueError, match="未知产品"):
        ReportAPortalData.model_validate(raw)


def test_ordinary_a_renderer_preserves_empty_optional_sections(tmp_path):
    raw = _payload()
    for section in ("regulatory", "companies", "patents", "history"):
        raw[section] = []
    data = ReportAPortalData.model_validate(raw)
    before = data.model_dump_json()
    pages = render_report_a_site(data, tmp_path)
    assert pages and (tmp_path / "clinical-portfolio.html").is_file()
    assert data.model_dump_json() == before
    assert data.regulatory == data.companies == data.patents == data.history == ()
