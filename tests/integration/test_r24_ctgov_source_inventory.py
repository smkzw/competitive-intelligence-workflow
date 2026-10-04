"""R24-93 CT.gov source inventory: pinned pages, aliases, and arm edges."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.build_ctgov_source_inventory import InventoryError, build_inventory

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "build_ctgov_source_inventory.py"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _study(
    nct: str,
    *,
    interventions: list[dict[str, Any]],
    arm_groups: list[dict[str, Any]] | None = None,
    enrollment_count: int | None = 40,
    enrollment_type: str | None = "ACTUAL",
    study_type: str = "INTERVENTIONAL",
    phases: list[str] | None = None,
    conditions: list[str] | None = None,
    references: list[dict[str, Any]] | None = None,
    has_results: bool = False,
    results_outcome_count: int = 0,
) -> dict[str, Any]:
    enrollment: dict[str, Any] = {}
    if enrollment_count is not None:
        enrollment["count"] = enrollment_count
    if enrollment_type is not None:
        enrollment["type"] = enrollment_type
    study: dict[str, Any] = {
        "hasResults": has_results,
        "protocolSection": {
            "identificationModule": {"nctId": nct, "briefTitle": nct},
            "statusModule": {"overallStatus": "RECRUITING"},
            "conditionsModule": {
                "conditions": conditions or ["Chronic Rhinosinusitis with Nasal Polyps"],
                "keywords": ["CRSwNP"],
            },
            "designModule": {
                "studyType": study_type,
                "phases": phases or ["PHASE2"],
                "enrollmentInfo": enrollment,
            },
            "armsInterventionsModule": {
                "armGroups": arm_groups or [],
                "interventions": interventions,
            },
            "outcomesModule": {
                "primaryOutcomes": [{"measure": "Primary"}],
                "secondaryOutcomes": [{"measure": "Secondary"}],
            },
            "referencesModule": {"references": references or []},
        },
    }
    if results_outcome_count:
        study["resultsSection"] = {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [
                    {"title": f"OM{index}"} for index in range(results_outcome_count)
                ]
            }
        }
    return study


def _write_cas(
    cas: Path,
    studies: list[dict[str, Any]],
    *,
    decoy_studies: list[dict[str, Any]] | None = None,
) -> Path:
    page = json.dumps({"studies": studies}, sort_keys=True).encode("utf-8")
    digest = _sha(page)
    relative = f"evidence/raw/sha256/{digest[:2]}/{digest}.bin"
    page_path = cas / relative
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_bytes(page)
    if decoy_studies is not None:
        decoy = cas / "evidence/raw/sha256/ff/decoy.bin"
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_text(json.dumps({"studies": decoy_studies}), encoding="utf-8")
    receipt = {
        "schema_version": "1.0",
        "projection_status": "complete",
        "limitation": "synthetic fixture",
        "records": [{"nct_id": study["protocolSection"]["identificationModule"]["nctId"]}
                    for study in studies],
        "acquisition": {
            "status": "complete",
            "pagination_complete": True,
            "universe_closed": False,
            "condition": "Chronic Rhinosinusitis with Nasal Polyps",
            "diagnostic": "fixture",
            "temporal_scope": "current_record",
            "total_count": len(studies),
            "pages": [
                {
                    "page_number": 1,
                    "acquired_at": "2026-10-03T09:22:09.637214Z",
                    "study_ids": [
                        study["protocolSection"]["identificationModule"]["nctId"]
                        for study in studies
                    ],
                    "raw_asset": {
                        "relative_path": relative,
                        "sha256": digest,
                        "byte_size": len(page),
                    },
                }
            ],
        },
    }
    receipt_path = cas / "capture.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    return receipt_path


def _run(cas: Path, receipt: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--cas-dir",
            str(cas),
            "--capture-receipt",
            str(receipt),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_batch_contract_red_then_repair_and_adjacent_receipt_arm_alias_cases(
    tmp_path: Path,
) -> None:
    """Root family: include all studies, pin pages, aliases, arms, no acceptance."""
    bound = _study(
        "NCT00000011",
        arm_groups=[
            {
                "label": "Drug arm",
                "type": "EXPERIMENTAL",
                "interventionNames": ["Drug: Studydrug"],
            },
            {
                "label": "Comparator arm",
                "type": "ACTIVE_COMPARATOR",
                "interventionNames": ["Drug: Activedrug"],
            },
        ],
        interventions=[
            {
                "type": "DRUG",
                "name": "Studydrug",
                "otherNames": ["AliasOne"],
                "armGroupLabels": ["Drug arm"],
            },
            {
                "type": "DRUG",
                "name": "Activedrug",
                "otherNames": ["AliasTwo"],
                "armGroupLabels": ["Comparator arm"],
            },
        ],
        references=[{"type": "RESULT", "pmid": "1"}, {"type": "BACKGROUND", "pmid": "2"}],
        has_results=True,
        results_outcome_count=2,
    )
    missing_edge = _study(
        "NCT00000012",
        interventions=[
            {
                "type": "DRUG",
                "name": "DUPIXENT®",
                "otherNames": ["dupilumab"],
            }
        ],
        enrollment_count=None,
        enrollment_type=None,
        study_type="OBSERVATIONAL",
        phases=[],
    )
    non_drug = _study(
        "NCT00000013",
        interventions=[
            {
                "type": "PROCEDURE",
                "name": "Functional Endoscopic Sinus Surgery",
                "armGroupLabels": ["Surgery arm"],
            }
        ],
        arm_groups=[{"label": "Surgery arm", "type": "EXPERIMENTAL", "interventionNames": [
            "Procedure: Functional Endoscopic Sinus Surgery",
        ]}],
    )
    standard = _study(
        "NCT00000014",
        interventions=[
            {
                "type": "DRUG",
                "name": "Placebo Oral Tablet",
                "otherNames": ["sugar pill"],
                "armGroupLabels": ["Placebo arm"],
            }
        ],
        arm_groups=[{"label": "Placebo arm", "type": "PLACEBO_COMPARATOR"}],
    )
    conflict_a = _study(
        "NCT00000015",
        interventions=[
            {
                "type": "BIOLOGICAL",
                "name": "DUPIXENT®",
                "otherNames": ["dupilumab"],
                "armGroupLabels": ["Drug arm"],
            }
        ],
        arm_groups=[{"label": "Drug arm", "type": "EXPERIMENTAL"}],
    )
    conflict_b = _study(
        "NCT00000016",
        interventions=[
            {
                "type": "BIOLOGICAL",
                "name": "Mepolizumab",
                "otherNames": ["Dupilumab", "Omalizumab"],
                "armGroupLabels": ["Drug arm"],
            }
        ],
        arm_groups=[{"label": "Drug arm", "type": "EXPERIMENTAL"}],
    )
    unknown_label = _study(
        "NCT00000017",
        interventions=[
            {
                "type": "DRUG",
                "name": "Studydrug",
                "armGroupLabels": ["Missing arm"],
            }
        ],
        arm_groups=[{"label": "Present arm", "type": "EXPERIMENTAL"}],
    )

    studies = [bound, missing_edge, non_drug, standard, conflict_a, conflict_b, unknown_label]
    cas = tmp_path / "cas"
    receipt = _write_cas(
        cas,
        studies,
        decoy_studies=[
            _study(
                "NCT99999999",
                interventions=[{"type": "DRUG", "name": "Decoy", "armGroupLabels": ["Drug arm"]}],
                arm_groups=[{"label": "Drug arm", "type": "EXPERIMENTAL"}],
            )
        ],
    )
    output = tmp_path / "inventory.json"

    # Adjacent receipt integrity failures must not create output.
    bad_receipt = json.loads(receipt.read_text(encoding="utf-8"))
    bad_receipt["records"][0]["nct_id"] = "NCT99999999"
    receipt.write_text(json.dumps(bad_receipt), encoding="utf-8")
    mismatched = tmp_path / "mismatched.json"
    assert _run(cas, receipt, mismatched).returncode != 0
    assert not mismatched.exists()

    bad_receipt["records"][0]["nct_id"] = "NCT00000011"
    bad_receipt["acquisition"]["pages"][0]["raw_asset"]["sha256"] = "0" * 64
    receipt.write_text(json.dumps(bad_receipt), encoding="utf-8")
    tampered = tmp_path / "tampered.json"
    assert _run(cas, receipt, tampered).returncode != 0
    assert not tampered.exists()

    # Restore valid receipt and repair the root contract.
    receipt = _write_cas(
        cas,
        studies,
        decoy_studies=[
            _study(
                "NCT99999999",
                interventions=[{"type": "DRUG", "name": "Decoy", "armGroupLabels": ["Drug arm"]}],
                arm_groups=[{"label": "Drug arm", "type": "EXPERIMENTAL"}],
            )
        ],
    )
    completed = _run(cas, receipt, output)
    assert completed.returncode == 0, completed.stderr
    inventory = json.loads(output.read_text(encoding="utf-8"))

    assert inventory["scientific_acceptance"] == "not_accepted"
    assert inventory["universe_closed"] is False
    assert inventory["accepted"] is False
    assert inventory["released"] is False
    assert inventory["counts"]["studies"] == 7
    assert {row["nct_id"] for row in inventory["studies"]} == {
        "NCT00000011",
        "NCT00000012",
        "NCT00000013",
        "NCT00000014",
        "NCT00000015",
        "NCT00000016",
        "NCT00000017",
    }
    assert "NCT99999999" not in {row["nct_id"] for row in inventory["studies"]}

    by_id = {row["nct_id"]: row for row in inventory["studies"]}
    bound_edges = [
        edge
        for edge in by_id["NCT00000011"]["arm_intervention_edges"]
        if edge["basis"] == "intervention.armGroupLabels"
    ]
    assert {edge["relationship_status"] for edge in bound_edges} == {"bound"}
    assert any(
        edge["basis"] == "armGroup.interventionNames"
        and edge["relationship_status"] == "arm_declared_intervention_name"
        for edge in by_id["NCT00000011"]["arm_intervention_edges"]
    )
    assert by_id["NCT00000012"]["arm_intervention_edges"][0]["relationship_status"] == (
        "missing_arm_labels"
    )
    assert by_id["NCT00000012"]["enrollment"]["missing_count"] is True
    assert by_id["NCT00000017"]["arm_intervention_edges"][0]["relationship_status"] == (
        "unknown_arm_label"
    )

    assert "AliasOne" in inventory["canonical_by_alias"]
    assert inventory["canonical_by_alias"]["AliasOne"]["name"] == "Studydrug"
    unresolved = {
        item["alias"].casefold(): item for item in inventory["unresolved_aliases"]
    }
    assert "dupilumab" in unresolved
    names = {candidate["name"] for candidate in unresolved["dupilumab"]["candidates"]}
    assert names == {"DUPIXENT®", "Mepolizumab"}

    proposals = inventory["proposals"]
    assert "NCT00000011" in {
        item["nct_id"] for item in proposals["innovative_inclusion_candidates"]
    }
    assert "NCT00000013" in {item["nct_id"] for item in proposals["non_drug"]}
    assert "NCT00000014" in {
        item["nct_id"] for item in proposals["standard_therapy_or_control"]
    }
    assert all(item.get("accepted") is not True for item in by_id.values())
    assert all(
        study["innovation_proposal"]["accepted"] is False for study in inventory["studies"]
    )
    assert by_id["NCT00000011"]["outcome_availability"]["reference_counts_by_type"] == {
        "BACKGROUND": 1,
        "RESULT": 1,
    }
    assert by_id["NCT00000011"]["outcome_availability"]["results_outcome_measure_count"] == 2

    # Exclusive output policy.
    again = _run(cas, receipt, output)
    assert again.returncode != 0
    assert "已存在" in again.stderr

    # Order of conflicting alias evidence must not overwrite into canonical.
    reversed_studies = list(reversed(studies))
    cas_b = tmp_path / "cas-b"
    receipt_b = _write_cas(cas_b, reversed_studies)
    output_b = tmp_path / "inventory-b.json"
    assert _run(cas_b, receipt_b, output_b).returncode == 0
    inventory_b = json.loads(output_b.read_text(encoding="utf-8"))
    unresolved_b = {
        item["alias"].casefold(): item for item in inventory_b["unresolved_aliases"]
    }
    assert "dupilumab" in unresolved_b
    assert "dupilumab" not in {
        key.casefold() for key in inventory_b["canonical_by_alias"]
    }


def test_build_inventory_helper_rejects_receipt_outside_cas(tmp_path: Path) -> None:
    cas = tmp_path / "cas"
    studies = [
        _study(
            "NCT00000021",
            interventions=[{"type": "DRUG", "name": "Studydrug", "armGroupLabels": ["Drug arm"]}],
            arm_groups=[{"label": "Drug arm", "type": "EXPERIMENTAL"}],
        )
    ]
    receipt = _write_cas(cas, studies)
    outside = tmp_path / "outside.json"
    outside.write_text(receipt.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(InventoryError, match="当前CAS"):
        build_inventory(cas_dir=cas, capture_receipt=outside, output=tmp_path / "nope.json")


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_arm_labels_are_ambiguous_not_last_wins(
    tmp_path: Path, reverse: bool,
) -> None:
    arms = [
        {"label": "Same label", "type": "EXPERIMENTAL"},
        {"label": "Same label", "type": "ACTIVE_COMPARATOR"},
    ]
    if reverse:
        arms.reverse()
    cas = tmp_path / "cas"
    receipt = _write_cas(cas, [_study(
        "NCT00000031", arm_groups=arms,
        interventions=[{"type": "DRUG", "name": "Studydrug",
                        "armGroupLabels": ["Same label"]}],
    )])
    inventory = build_inventory(cas_dir=cas, capture_receipt=receipt)
    edge = inventory["studies"][0]["arm_intervention_edges"][0]
    assert edge["relationship_status"] == "ambiguous_arm_label"
    assert edge["arm_index"] is None
    assert edge["candidate_arm_indices"] == [0, 1]
    assert len(inventory["studies"][0]["arms"]) == 2


@pytest.mark.parametrize("link_parent", [False, True])
def test_receipt_symlinks_are_not_pinned_regular_files(
    tmp_path: Path, link_parent: bool,
) -> None:
    cas = tmp_path / "cas"
    receipt = _write_cas(cas, [_study("NCT00000032", interventions=[])])
    if link_parent:
        (cas / "linked").symlink_to(cas, target_is_directory=True)
        receipt = cas / "linked" / "capture.json"
    else:
        linked = cas / "linked.json"
        linked.symlink_to(receipt)
        receipt = linked
    with pytest.raises(InventoryError, match="链接|普通文件"):
        build_inventory(cas_dir=cas, capture_receipt=receipt)


def test_content_addressed_receipt_must_match_its_own_digest(tmp_path: Path) -> None:
    cas = tmp_path / "cas"
    receipt = _write_cas(cas, [_study("NCT00000033", interventions=[])])
    raw = receipt.read_bytes()
    digest = _sha(raw)
    addressed = cas / "evidence" / "raw" / "sha256" / digest[:2] / (digest + ".bin")
    addressed.parent.mkdir(parents=True, exist_ok=True)
    addressed.write_bytes(raw)
    assert build_inventory(cas_dir=cas, capture_receipt=addressed)["counts"]["studies"] == 1
    altered = json.loads(raw)
    altered["limitation"] = "changed but still syntactically valid receipt"
    addressed.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(InventoryError, match="摘要|内容寻址"):
        build_inventory(cas_dir=cas, capture_receipt=addressed)
