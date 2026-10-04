"""Study inclusion does not require a guessed product or comparative result."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData, TrialRow
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site


def _payload() -> dict[str, Any]:
    path = (
        Path(__file__).resolve().parents[3]
        / "fixtures/synthetic/a-complete/inputs/report-data.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _study(payload: dict[str, Any], case: str) -> dict[str, Any]:
    study = {
        **payload["trials"][0],
        "id": "nct00001999",
        "display_id": "NCT00001999",
        "name": "未归属产品的相关研究",
        "product_id": None,
        "product_links": [],
        "role": "相关研究；产品关系待核",
        "sample_size": None,
        "planned_sample_size": None,
        "reported_sample_size": None,
        "treatment_sample_size": None,
        "enrollment_type": "UNKNOWN",
    }
    if case == "zero":
        study.update(sample_size=0, enrollment_type="ACTUAL")
    elif case == "estimated":
        study.update(planned_sample_size=21, enrollment_type="ESTIMATED")
    elif case == "linked":
        study.update(product_id=payload["products"][0]["id"])
    return study


@pytest.mark.parametrize("case", ("unknown", "zero", "estimated", "linked"))
def test_related_study_reaches_index_filters_dossier_search_and_offline_payload(
    tmp_path: Path, case: str,
) -> None:
    payload = _payload()
    study = _study(payload, case)
    payload["related_studies"] = [study]
    data = ReportBPortalData.model_validate(payload)
    expected_ids = {row["id"] for row in payload["trials"]} | {study["id"]}
    assert {row.id for row in data.all_studies} == expected_ids
    assert set(data.trial_ids) == expected_ids
    site = tmp_path / "site"
    render_report_b_site(data, site)
    profile = (site / "product-trial-profiles.html").read_text(encoding="utf-8")
    assert f'trials/{study["id"]}.html' in profile
    script = re.search(r"<script>(window\.__SNAPSHOT_ID__.*?)</script>", profile, re.S)
    assert script is not None
    result = subprocess.run(
        ["node", "-e", (
            "var window={};" + script.group(1)
            + ";console.log(JSON.stringify(window.__FILTER_ROWS__));"
        )],
        check=True, capture_output=True, text=True,
    )
    rows = json.loads(result.stdout)
    assert {row["trial"] for row in rows if row.get("trial")} == expected_ids
    related_row = next(row for row in rows if row.get("trial") == study["id"])
    assert related_row["product"] == (study["product_id"] or "")
    sitemap = json.loads((site / "data/sitemap.json").read_text(encoding="utf-8"))
    assert any(route["path"] == f'trials/{study["id"]}.html' for route in sitemap["routes"])
    assert study["name"] in (site / "data/search-index.js").read_text(encoding="utf-8")
    offline = (site / "data/report.js").read_text(encoding="utf-8")
    saved = json.loads(offline.removeprefix("window.REPORT_B=").rstrip(";\n"))
    assert saved["related_studies"] == [study]
    dossier = (site / f'trials/{study["id"]}.html').read_text(encoding="utf-8")
    assert "None" not in dossier
    assert "null.html" not in dossier
    if study["product_id"] is None:
        assert "产品关系待核" in dossier
        assert "../products/None.html" not in dossier
    if case == "zero":
        assert "实际样本量</dt><dd>0 人" in dossier
    elif case == "estimated":
        assert "计划样本量</dt><dd>21 人" in dossier
        assert "实际样本量</dt><dd>未列示" in dossier
    elif case == "unknown":
        assert "实际样本量</dt><dd>未列示" in dossier
    intro = (site / "overview.html").read_text(encoding="utf-8")
    assert f"{len(expected_ids)} 项研究" in intro
    assert "不能据此认定竞品检索已完整" in intro


@pytest.mark.parametrize("case", ("duplicate", "overlap", "unknown_product", "unknown_link"))
def test_related_study_relations_fail_closed(case: str) -> None:
    payload = _payload()
    study = _study(payload, "unknown")
    if case == "duplicate":
        payload["related_studies"] = [study, study]
        message = "相关研究标识重复"
    elif case == "overlap":
        study["id"] = payload["trials"][0]["id"]
        payload["related_studies"] = [study]
        message = "相关研究与产品关联研究重复"
    elif case == "unknown_product":
        study["product_id"] = "invented-product"
        payload["related_studies"] = [study]
        message = "相关研究引用了未知产品"
    else:
        study["product_links"] = [{
            "product_id": "invented-product", "arm_role": "unknown", "arm_labels": [],
        }]
        payload["related_studies"] = [study]
        message = "相关研究干预关系引用了未知产品"
    with pytest.raises(ValueError, match=message):
        ReportBPortalData.model_validate(payload)


def test_legacy_a_trial_remains_product_bound_and_serialization_unchanged() -> None:
    payload = _payload()
    data = ReportAPortalData.model_validate(payload)
    expected = TrialRow.model_validate(payload["trials"][0]).model_dump(mode="json")
    assert data.trials[0].model_dump(mode="json") == expected
    unassigned = {**payload["trials"][0], "product_id": None}
    with pytest.raises(ValueError):
        TrialRow.model_validate(unassigned)
