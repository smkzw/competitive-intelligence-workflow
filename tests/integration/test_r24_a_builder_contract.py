"""R24 generic A entry: source enrollment and explicit arm relationships."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    TrialRow,
    _display_efficacy_rows,
    render_report_a_site,
)


def _study(
    nct: str, count: int | None, enrollment_type: str | None,
    interventions: list[dict[str, Any]],
) -> dict[str, Any]:
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": nct},
        "designModule": {"enrollmentInfo": {
            **({"count": count} if count is not None else {}),
            **({"type": enrollment_type} if enrollment_type is not None else {}),
        }},
        "armsInterventionsModule": {
            "interventions": interventions,
            "armGroups": [
                {"label": "Drug arm", "type": "EXPERIMENTAL"},
                {"label": "Comparator arm", "type": "ACTIVE_COMPARATOR"},
            ],
        },
    }}


def _build(tmp_path: Path, studies: list[dict[str, Any]]) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    cas = tmp_path / "cas" / "evidence" / "raw" / "sha256" / "aa"
    cas.mkdir(parents=True)
    (cas / "page.bin").write_text(json.dumps({"studies": studies}), encoding="utf-8")
    alias = tmp_path / "alias.json"
    alias.write_text(json.dumps({
        "map_id": "r24-synthetic", "canonical_by_alias": {
            "Studydrug": "studydrug", "Activedrug": "activedrug",
        },
    }), encoding="utf-8")
    output = tmp_path / "report.json"
    subprocess.run([
        sys.executable, str(root / "tools/build_a_payload.py"),
        "--cas-dir", str(tmp_path / "cas"), "--alias-map", str(alias),
        "--indication", "合成适应症", "--indication-id", "synthetic",
        "--output", str(output), "--cutoff", "2026-09-24",
    ], cwd=root, check=True, capture_output=True, text=True)
    payload: dict[str, Any] = json.loads(output.read_text(encoding="utf-8"))
    ReportAPortalData.model_validate(payload)
    for trial in payload["trials"]:
        TrialRow.model_validate(trial)
    return payload


def test_unknown_zero_planned_and_actual_n_remain_distinct(tmp_path: Path) -> None:
    drug = [{"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]}]
    studies = [
        _study("NCT00000001", None, None, drug),
        _study("NCT00000002", 0, "ACTUAL", drug),
        _study("NCT00000003", 50, "ESTIMATED", drug),
        _study("NCT00000004", 40, "ACTUAL", drug),
    ]
    rows = {row["display_id"]: row for row in _build(tmp_path, studies)["trials"]}
    assert set(rows) == {study["protocolSection"]["identificationModule"]["nctId"]
                         for study in studies}
    assert rows["NCT00000001"]["sample_size"] is None
    assert rows["NCT00000002"]["sample_size"] == 0
    assert rows["NCT00000002"]["enrollment_type"] == "ACTUAL"
    assert rows["NCT00000003"]["sample_size"] is None
    assert rows["NCT00000003"]["planned_sample_size"] == 50
    assert rows["NCT00000004"]["sample_size"] == 40


def test_intervention_order_does_not_reassign_the_trial_or_hide_comparator(
    tmp_path: Path,
) -> None:
    comparator = {
        "name": "Activedrug", "type": "DRUG",
        "armGroupLabels": ["Comparator arm"],
    }
    study_drug = {
        "name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"],
    }
    for index, ordered in enumerate(((comparator, study_drug),
                                     (study_drug, comparator))):
        payload = _build(
            tmp_path / str(index),
            [_study("NCT00000005", 60, "ACTUAL", deepcopy(list(ordered)))],
        )
        assert len(payload["trials"]) == 1
        trial = payload["trials"][0]
        assert trial["product_id"] == "studydrug"
        assert {(link["product_id"], link["arm_role"])
                for link in trial["product_links"]} == {
                    ("studydrug", "experimental"),
                    ("activedrug", "active_comparator"),
                }
        site = tmp_path / str(index) / "site"
        render_report_a_site(ReportAPortalData.model_validate(payload), site)
        assert "NCT00000005" in (site / "products" / "studydrug.html").read_text()
        assert "NCT00000005" in (site / "products" / "activedrug.html").read_text()


def test_outcome_group_is_not_inferred_from_unrelated_array_positions(
    tmp_path: Path,
) -> None:
    study = _study("NCT00000006", 40, "ACTUAL", [
        {"name": "Activedrug", "type": "DRUG", "armGroupLabels": ["Comparator arm"]},
        {"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]},
    ])
    study["resultsSection"] = {
        "participantFlowModule": {"groups": [
            {"title": "Comparator arm"}, {"title": "Drug arm"},
        ]},
        "outcomeMeasuresModule": {"outcomeMeasures": [{
            "title": "Participants With Response", "timeFrame": "Week 24",
            "unitOfMeasure": "Participants", "groups": [{"id": "OG1", "title": "OG1"}],
            "classes": [{"categories": [{"measurements": [
                {"groupId": "OG1", "value": "4"},
            ]}]}],
        }]},
    }
    payload = _build(tmp_path, [study])
    row = payload["efficacy"][0]
    assert row["arm"] == "OG1"
    assert row["group_assignment_state"] == "unknown"
    display_row = _display_efficacy_rows(ReportAPortalData.model_validate(payload))[0]
    assert display_row["numeric_projection"]["renderable"] is False
    assert display_row["unrendered_reason"] == "group_product_relationship_unresolved"
    site = tmp_path / "site"
    render_report_a_site(ReportAPortalData.model_validate(payload), site)
    html = (site / "efficacy.html").read_text(encoding="utf-8")
    assert "产品归属待核" in html
    assert "1 条疗效观察的组别—产品关系待核" in html
    search = (site / "data" / "search-index.js").read_text(encoding="utf-8")
    assert "Participants With Response · studydrug" not in search


def test_ada_is_not_delivered_as_a_clinical_efficacy_row(tmp_path: Path) -> None:
    study = _study("NCT00000007", 40, "ACTUAL", [
        {"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]},
    ])
    study["resultsSection"] = {"outcomeMeasuresModule": {"outcomeMeasures": [{
        "title": "Participants With Anti-drug Antibodies (ADA)",
        "timeFrame": "Week 24", "unitOfMeasure": "Participants",
        "groups": [{"id": "OG1", "title": "Drug arm"}],
        "classes": [{"categories": [{"measurements": [
            {"groupId": "OG1", "value": "2"},
        ]}]}],
    }]}}
    payload = _build(tmp_path, [study])
    assert payload["efficacy"] == []
    assert payload["safety"] == []
    assert len(payload["additional_observations"]) == 1
    assert payload["additional_observations"][0]["domain"] == "immunogenicity"
    sidecar = json.loads((tmp_path / "report.derivation.json").read_text())
    assert len(sidecar["non_efficacy_observations"]) == 1
    assert sidecar["non_efficacy_observations"][0]["domain"] == "immunogenicity"
    assert sidecar["non_efficacy_observations"][0]["raw_value"] == "2"


def test_ae_event_group_uses_declared_arm_relationship_not_focus_product(
    tmp_path: Path,
) -> None:
    study = _study("NCT00000008", 40, "ACTUAL", [
        {"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]},
        {"name": "Activedrug", "type": "DRUG", "armGroupLabels": ["Comparator arm"]},
    ])
    long_window = (
        "Adverse events were reported from first dose until the end of study "
        "treatment plus 30 days, up to a maximum duration of 48 weeks"
    )
    study["resultsSection"] = {"adverseEventsModule": {"timeFrame": long_window,
        "eventGroups": [
        {"title": "Comparator arm", "seriousNumAffected": 2,
         "seriousNumAtRisk": 20},
        {"title": "Unmapped arm", "seriousNumAffected": 1,
         "seriousNumAtRisk": 20},
    ]}}
    payload = _build(tmp_path, [study])
    rows = payload["safety"]
    assert [(row["product_id"], row["group_assignment_state"])
            for row in rows] == [
                ("activedrug", "declared"),
                ("studydrug", "unknown"),
            ]
    site = tmp_path / "site"
    render_report_a_site(ReportAPortalData.model_validate(payload), site)
    html = (site / "safety.html").read_text(encoding="utf-8")
    assert "查看完整观察窗" in html
    assert long_window in html
    assert "1 条安全性观察的组别—产品关系待核" in html
