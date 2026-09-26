"""R24 generic A entry: source enrollment and explicit arm relationships."""

from __future__ import annotations

import hashlib
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


def test_capture_receipt_selects_only_pinned_pages_from_mixed_cas(
    tmp_path: Path,
) -> None:
    """A live project also stores per-study slices and receipts in the same CAS."""
    root = Path(__file__).resolve().parents[2]
    cas = tmp_path / "cas"
    study = _study("NCT00000011", 40, "ACTUAL", [
        {"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]},
    ])
    page = json.dumps({"studies": [study]}, sort_keys=True).encode()
    digest = hashlib.sha256(page).hexdigest()
    page_relative = f"evidence/raw/sha256/{digest[:2]}/{digest}.bin"
    page_path = cas / page_relative
    page_path.parent.mkdir(parents=True)
    page_path.write_bytes(page)
    decoy = cas / "evidence/raw/sha256/ff/other.bin"
    decoy.parent.mkdir(parents=True)
    decoy.write_text(json.dumps({"record": study}), encoding="utf-8")
    receipt = cas / "capture.json"
    receipt.write_text(json.dumps({
        "schema_version": "1.0", "projection_status": "complete",
        "records": [{"nct_id": "NCT00000011"}],
        "acquisition": {
            "status": "complete", "pagination_complete": True, "total_count": 1,
            "pages": [{
                "page_number": 1, "acquired_at": "2026-09-26T10:00:00Z",
                "study_ids": ["NCT00000011"],
                "raw_asset": {"relative_path": page_relative, "sha256": digest,
                              "byte_size": len(page)},
            }],
        },
    }), encoding="utf-8")
    alias = tmp_path / "alias.json"
    alias.write_text(json.dumps({
        "map_id": "synthetic-v1", "canonical_by_alias": {"Studydrug": "studydrug"},
    }), encoding="utf-8")

    def run(output: Path, *, pinned: bool) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable, str(root / "tools/build_a_payload.py"),
            "--cas-dir", str(cas), "--alias-map", str(alias),
            "--indication", "合成适应症", "--indication-id", "synthetic",
            "--output", str(output), "--cutoff", "2026-09-26",
        ]
        if pinned:
            command.extend(["--capture-receipt", str(receipt)])
        return subprocess.run(command, cwd=root, capture_output=True, text=True)

    unpinned = tmp_path / "unpinned.json"
    assert run(unpinned, pinned=False).returncode != 0
    assert not unpinned.exists()

    pinned = tmp_path / "pinned.json"
    completed = run(pinned, pinned=True)
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(pinned.read_text(encoding="utf-8"))
    assert {row["display_id"] for row in payload["trials"]} == {"NCT00000011"}
    sidecar = json.loads((tmp_path / "pinned.derivation.json").read_text())
    assert sidecar["pages"] == [{"page": 1, "sha256": digest}]

    receipt_data = json.loads(receipt.read_text())
    receipt_data["records"][0]["nct_id"] = "NCT99999999"
    receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
    mismatched = tmp_path / "mismatched.json"
    assert run(mismatched, pinned=True).returncode != 0
    assert not mismatched.exists()

    receipt_data["records"][0]["nct_id"] = "NCT00000011"
    receipt_data["acquisition"]["pages"][0]["raw_asset"]["sha256"] = "0" * 64
    receipt.write_text(json.dumps(receipt_data), encoding="utf-8")
    tampered = tmp_path / "tampered.json"
    assert run(tampered, pinned=True).returncode != 0
    assert not tampered.exists()


def test_result_row_identity_survives_page_order_and_new_study(
    tmp_path: Path,
) -> None:
    """A refresh must not retarget a saved consumer when pagination changes."""
    drug = [{"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]}]

    def with_result(nct: str, value: str) -> dict[str, Any]:
        study = _study(nct, 40, "ACTUAL", drug)
        study["resultsSection"] = {"outcomeMeasuresModule": {"outcomeMeasures": [{
            "title": "Participants With Response", "timeFrame": "Week 24",
            "unitOfMeasure": "Participants",
            "groups": [{"id": "OG1", "title": "Drug arm"}],
            "classes": [{"categories": [{"measurements": [
                {"groupId": "OG1", "value": value},
            ]}]}],
        }]}}
        return study

    original = _build(tmp_path / "original", [
        with_result("NCT00000021", "7"), with_result("NCT00000022", "8"),
    ])
    refreshed = _build(tmp_path / "refreshed", [
        with_result("NCT00000020", "9"), with_result("NCT00000022", "8"),
        with_result("NCT00000021", "10"),
    ])
    before = {row["trial_id"]: row["row_id"] for row in original["efficacy"]}
    after = {row["trial_id"]: row["row_id"] for row in refreshed["efficacy"]}
    assert {key: after[key] for key in before} == before
    assert len(set(after.values())) == len(after)


def test_unknown_zero_planned_and_actual_n_remain_distinct(tmp_path: Path) -> None:
    drug = [{"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]}]
    studies = [
        _study("NCT00000001", None, None, drug),
        _study("NCT00000002", 0, "ACTUAL", drug),
        _study("NCT00000003", 50, "ESTIMATED", drug),
        _study("NCT00000004", 40, "ACTUAL", drug),
    ]
    payload = _build(tmp_path, studies)
    rows = {row["display_id"]: row for row in payload["trials"]}
    assert payload["regulatory"][0]["date"] == "2026-09-24"
    assert "中国来源未接入当前载荷" in payload["history"][0]["observation"]
    assert set(rows) == {study["protocolSection"]["identificationModule"]["nctId"]
                         for study in studies}
    assert rows["NCT00000001"]["sample_size"] is None
    assert rows["NCT00000002"]["sample_size"] == 0
    assert rows["NCT00000002"]["enrollment_type"] == "ACTUAL"
    assert rows["NCT00000003"]["sample_size"] is None
    assert rows["NCT00000003"]["planned_sample_size"] == 50
    assert rows["NCT00000004"]["sample_size"] == 40


def test_registration_sponsors_do_not_become_one_order_dependent_developer(
    tmp_path: Path,
) -> None:
    drug = [{"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]}]

    def sponsored(nct: str, sponsor: str) -> dict[str, Any]:
        study = _study(nct, 40, "ACTUAL", drug)
        study["protocolSection"]["sponsorCollaboratorsModule"] = {
            "leadSponsor": {"name": sponsor},
        }
        return study

    first = sponsored("NCT00000031", "Sponsor Beta")
    second = sponsored("NCT00000032", "Sponsor Alpha")
    for index, studies in enumerate(((first, second), (second, first))):
        payload = _build(tmp_path / str(index), list(studies))
        product = next(row for row in payload["products"] if row["id"] == "studydrug")
        assert product["developer_basis"] == "registration_sponsor"
        assert product["developer"] == "Sponsor Alpha、Sponsor Beta"
        assert {row["sponsor"] for row in payload["companies"]} == {
            "Sponsor Alpha", "Sponsor Beta",
        }
        assert all(row["licensor"] == "未公开披露" for row in payload["companies"])
        site = tmp_path / str(index) / "site"
        render_report_a_site(ReportAPortalData.model_validate(payload), site)
        detail = (site / "products" / "studydrug.html").read_text(encoding="utf-8")
        assert "登记申办方（不等于研发归属）" in detail
        assert "许可方：Sponsor Alpha" not in detail
        assert "登记申办方：Sponsor Alpha" in detail


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


def test_ambiguous_reported_proportion_explains_why_it_is_not_plotted(
    tmp_path: Path,
) -> None:
    study = _study("NCT00000009", 40, "ACTUAL", [
        {"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]},
    ])
    study["resultsSection"] = {"outcomeMeasuresModule": {"outcomeMeasures": [{
        "title": "Proportion of Participants With Response",
        "timeFrame": "Week 24", "unitOfMeasure": "Proportion of participants",
        "paramType": "NUMBER", "groups": [{"id": "OG1", "title": "Drug arm"}],
        "denoms": [{"units": "Participants", "counts": [
            {"groupId": "OG1", "value": "40"},
        ]}],
        "classes": [{"categories": [{"measurements": [
            {"groupId": "OG1", "value": "92.7"},
        ]}]}],
    }]}}
    data = ReportAPortalData.model_validate(_build(tmp_path, [study]))
    display = _display_efficacy_rows(data)
    assert len(display) == 1
    assert display[0]["numeric_projection"]["renderable"] is False
    assert display[0]["numeric_projection"]["raw_value"] == 92.7
    site = tmp_path / "site"
    render_report_a_site(data, site)
    html = (site / "efficacy.html").read_text(encoding="utf-8")
    assert "92.7受试者比例" in html
    assert "未绘图：来源未注明比例刻度（0–1 或 0–100）" in html


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
