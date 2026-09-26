"""Production A -> B safety semantics from outcome-measure class context."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ci_workflow.application.source_research_service import (
    ClinicalTrialsResultCoverageIssue,
    _iter_outcome_results,
    _outcome_category,
)
from ci_workflow.renderers.portal.report_a import _safety_term_projection
from ci_workflow.renderers.portal.report_b import _project_record
from ci_workflow.reports.b.concept_catalog import spec_of
from ci_workflow.reports.b.safety_concepts import describe_safety_concept


@pytest.mark.parametrize(("source_class", "expected_key"), [
    ("Any Treatment-emergent SAE", "any_sae"),
    ("TEAE leading to study drug discontinuation", "discontinuation_ae"),
    ("TEAE leading to death", "specific_ae"),
    ("TEAE at least possibly related to study drug", "specific_ae"),
    ("Participants with any unrelated TEAE", "specific_ae"),
    ("Any Treatment-emergent EOI: Infusion reaction", "specific_ae"),
    ("Participants with severe TEAE", "severity_specific_teae"),
])
def test_explicit_safety_subset_is_not_promoted_to_all_teae(
    source_class: str, expected_key: str,
) -> None:
    assert describe_safety_concept(source_class).key == expected_key


@pytest.mark.parametrize(("source_class", "expected_relatedness"), [
    ("Participants with any unrelated TEAE", "unrelated"),
    ("Participants with any probably related TEAE", "probably_related"),
    ("TEAE at least possibly related to study drug", "at_least_possibly_related"),
])
def test_safety_relatedness_qualifier_remains_explicit(
    source_class: str, expected_relatedness: str,
) -> None:
    assert describe_safety_concept(source_class).relatedness == expected_relatedness


def test_a_display_keeps_typed_class_key_over_parent_title_alias() -> None:
    assert _safety_term_projection("Any TEAE", "serious_teae_subset")[0] == (
        "serious_teae_subset"
    )
    assert _safety_term_projection(
        "Percentage of Participants With Treatment Emergent Adverse Events (TEAEs)",
        "severity_specific_teae",
    )[0] == "severity_specific_teae"


def _build_classified_safety(tmp_path: Path) -> list[dict[str, object]]:
    root = Path(__file__).resolve().parents[2]
    cas = tmp_path / "cas" / "evidence" / "raw" / "sha256" / "aa"
    cas.mkdir(parents=True)
    measures = [
        {
            "title": "Percentage of Participants With Treatment Emergent Adverse Events (TEAEs)",
            "unitOfMeasure": "Percentage of participants",
            "timeFrame": "Week 24",
            "groups": [{"id": "OG1", "title": "Testdrug"}],
            "classes": [
                {"title": title, "categories": [{"measurements": [
                    {"groupId": "OG1", "value": value},
                ]}]}
                for title, value in (
                    ("Participants with any TEAE", "60"),
                    ("Participants with serious TEAE", "20"),
                    ("Participants with severe TEAE", "10"),
                )
            ],
        },
        {
            "title": "Number and Type of Adverse Events (AE)",
            "unitOfMeasure": "Events",
            "timeFrame": "Week 24",
            "groups": [{"id": "OG1", "title": "Testdrug"}],
            "classes": [{"title": "Serious Adverse Events (SAE)", "categories": [
                {"measurements": [{"groupId": "OG1", "value": "2"}]},
            ]}],
        },
        {
            "title": "Number of Participants With Adverse Events",
            "unitOfMeasure": "Participants",
            "timeFrame": "Week 24",
            "groups": [{"id": "OG1", "title": "Testdrug"}],
            "classes": [
                {"title": title, "categories": [{"measurements": [
                    {"groupId": "OG1", "value": value},
                ]}]}
                for title, value in (
                    ("At least 1 Treatment Emergent Adverse Event (TEAE)", "12"),
                    ("At least 1 Serious Adverse Event (SAE)", "3"),
                    ("At least 1 TEAE leading to discontinuation", "1"),
                )
            ],
        },
        {
            "title": (
                "Number of Participants With SAEs, Grade 3 AEs, "
                "and AEs Leading to Discontinuation"
            ),
            "unitOfMeasure": "Participants",
            "timeFrame": "Week 24",
            "groups": [{"id": "OG1", "title": "Testdrug"}],
            "classes": [
                {"title": title, "categories": [{"measurements": [
                    {"groupId": "OG1", "value": value},
                ]}]}
                for title, value in (
                    ("SAEs", "3"),
                    ("Grade 3 AEs", "4"),
                    ("AEs Leading to Discontinuation of Study Medication", "1"),
                )
            ],
        },
        {
            "title": "Long Term Safety Assessed by AEs, SAEs, and Standard Lab Tests",
            "unitOfMeasure": "Participants",
            "timeFrame": "Week 24",
            "groups": [{"id": "OG1", "title": "Testdrug"}],
            "classes": [{
                "title": "Clinically significant hemoglobin (low)",
                "categories": [{"measurements": [{"groupId": "OG1", "value": "1"}]}],
            }],
        },
    ]
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Safety trial"},
            "designModule": {"enrollmentInfo": {"count": 50}},
            "armsInterventionsModule": {
                "interventions": [{"name": "Testdrug", "type": "DRUG"}],
                "armGroups": [{"label": "Testdrug", "type": "EXPERIMENTAL"}],
            },
        },
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": measures}},
    }
    (cas / "page.bin").write_text(json.dumps({"studies": [record]}), encoding="utf-8")
    alias = tmp_path / "alias.json"
    alias.write_text(json.dumps({
        "map_id": "synthetic-v1", "canonical_by_alias": {"Testdrug": "testdrug"},
    }), encoding="utf-8")
    output = tmp_path / "a.json"
    subprocess.run(
        [
            sys.executable, str(root / "tools/build_a_payload.py"),
            "--cas-dir", str(tmp_path / "cas"), "--alias-map", str(alias),
            "--indication", "合成适应症", "--indication-id", "synthetic",
            "--output", str(output), "--cutoff", "2026-09-06",
        ],
        cwd=root, check=True, capture_output=True, text=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    return payload["safety"]


def test_builder_uses_class_context_without_collapsing_subsets(tmp_path: Path) -> None:
    rows = _build_classified_safety(tmp_path)
    by_class = {str(row["source_class_title"]): row for row in rows}
    assert len(by_class) == 11
    assert by_class["Participants with any TEAE"]["term_key"] == "any_teae"
    assert by_class["Participants with serious TEAE"]["term_key"] == "serious_teae_subset"
    assert by_class["Participants with severe TEAE"]["term_key"] == "severity_specific_teae"
    assert by_class["At least 1 Treatment Emergent Adverse Event (TEAE)"]["term_key"] == "any_teae"
    assert by_class["At least 1 Serious Adverse Event (SAE)"]["term_key"] == "any_sae"
    assert (
        by_class["At least 1 TEAE leading to discontinuation"]["term_key"]
        == "discontinuation_ae"
    )
    assert by_class["SAEs"]["term_key"] == "any_sae"
    assert by_class["Grade 3 AEs"]["term_key"] == "grade_specific"
    assert (
        by_class["AEs Leading to Discontinuation of Study Medication"]["term_key"]
        == "discontinuation_ae"
    )
    assert by_class["Clinically significant hemoglobin (low)"]["term_key"] == "unknown"
    events = by_class["Serious Adverse Events (SAE)"]
    assert events["term_key"] == "any_sae"
    assert (events["measure_object"], events["count_basis"], events["unit"]) == (
        "event_count", "events", "次",
    )
    assert events["numerator"] is None and events["denominator"] is None


def test_b_projection_preserves_machine_measure_and_class_definition(tmp_path: Path) -> None:
    rows = _build_classified_safety(tmp_path)
    by_class = {str(row["source_class_title"]): row for row in rows}
    for class_title in (
        "Participants with any TEAE",
        "Participants with serious TEAE",
        "Participants with severe TEAE",
    ):
        row = by_class[class_title]
        projected = _project_record(
            row, domain="safety", names={}, trial_names={}, fallback=str(row["row_id"]),
        )
        assert projected["measure_object"] == "participant_proportion"
        assert projected["semantic_definition"] == class_title
        assert projected["clinical_concept"] == row["term_key"]
        assert projected["display_label_zh"] == spec_of(str(row["term_key"])).label_zh
        assert projected["statistical_form_family"] == "proportion"
        assert projected["statistical_form_family_label_zh"] == "比例"
        assert projected["numeric_projection"]["kind"] == "participant_proportion"
    event_row = by_class["Serious Adverse Events (SAE)"]
    projected_event = _project_record(
        event_row, domain="safety", names={}, trial_names={},
        fallback=str(event_row["row_id"]),
    )
    assert projected_event["measure_object"] == "event_count"
    assert projected_event["count_basis"] == "events"
    assert projected_event["numeric_projection"]["kind"] == "event_count"
    assert projected_event["numerator"] is None
    assert projected_event["denominator"] is None


def test_source_atom_category_uses_explicit_class_of_composite_measure() -> None:
    title = (
        "Number of Participants With Treatment-emergent Adverse Events (TEAEs) "
        "and Serious TEAEs"
    )
    assert _outcome_category(title, "Participants with TEAEs") == "teae"
    assert _outcome_category(title, "Participants with Serious TEAEs") == "common_ae"
    # Without a class-specific measurement, the composite cannot be called an SAE rate.
    assert _outcome_category(title) == "outcome"

    record = {"resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{
        "title": title,
        "timeFrame": "Week 24",
        "unitOfMeasure": "Participants",
        "groups": [{"id": "OG1", "title": "Testdrug"}],
        "classes": [
            {"title": class_title, "categories": [{"measurements": [
                {"groupId": "OG1", "value": value},
            ]}]}
            for class_title, value in (
                ("Participants with TEAEs", "12"),
                ("Participants with Serious TEAEs", "3"),
            )
        ],
    }]}}}
    issues: list[ClinicalTrialsResultCoverageIssue] = []
    results = _iter_outcome_results(
        record=record, trial_id="NCT00000001", source_id="synthetic-r24",
        issues=issues,
    )
    assert len(issues) == 2
    assert all(issue.status == "missing" and "分母缺失" in issue.reason_zh for issue in issues)
    assert [(result.category, result.value) for result in results] == [
        ("teae", 12.0), ("common_ae", 3.0),
    ]


def test_fixed_50_study_source_paths_rebuild_without_array_order_identity(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[2]
    cas = repo / ".artifacts/source-cas/ctgov-live-20260906"
    old_path = (
        repo / ".artifacts/r24-pnh-auto-binding-full-20260926/inputs/"
        "report-a-r24-22-bound.json"
    )
    alias = repo / "packets/2026-09-11-pnh-vertical/pnh-alias-map-v1.json"
    if not all(path.exists() for path in (cas, old_path, alias)):
        pytest.skip("pinned offline PNH source candidate unavailable; no science PASS")
    output = tmp_path / "a.json"
    subprocess.run(
        [
            sys.executable, str(repo / "tools/build_a_payload.py"),
            "--cas-dir", str(cas), "--alias-map", str(alias),
            "--indication", "阵发性睡眠性血红蛋白尿症", "--indication-id", "pnh",
            "--output", str(output), "--cutoff", "2026-09-06",
        ],
        cwd=repo, check=True, capture_output=True, text=True,
    )
    old_rows = json.loads(old_path.read_text(encoding="utf-8"))["safety"]
    new_rows = json.loads(output.read_text(encoding="utf-8"))["safety"]
    sidecar = json.loads(
        output.with_name("a.derivation.json").read_text(encoding="utf-8")
    )
    old_by_source = {
        (row["trial_id"], row["source_field_path"]): row for row in old_rows
    }
    new_by_id = {row["row_id"]: row for row in new_rows}
    source_map = {
        (row["trial_id"], row["value_path"]): row["row_id"]
        for row in sidecar["row_source_map"] if row["domain"] == "safety"
    }
    assert len(old_by_source) == len(source_map) == len(new_by_id) == 514
    assert set(old_by_source) == set(source_map)
    for old_id, expected_key, expected_basis in (
        # A composite parent also mentions grade 3/4; the measured class is
        # the statistical object, so its SAE/TEAE/discontinuation rows must
        # not all inherit the parent's grade-specific label.
        ("safe-348", "any_sae", "participants"),
        ("safe-354", "discontinuation_ae", "participants"),
        ("safe-426", "any_teae", "participants"),
        ("safe-366", "serious_teae_subset", "participants"),
        ("safe-368", "severity_specific_teae", "participants"),
        ("safe-455", "any_sae", "events"),
    ):
        old = next(row for row in old_rows if row["row_id"] == old_id)
        new = new_by_id[source_map[(old["trial_id"], old["source_field_path"])]]
        assert (new["value"], new["unit"], new["source_class_title"]) == (
            old["value"], old["unit"], old["source_class_title"],
        )
        assert (new["term_key"], new["count_basis"]) == (expected_key, expected_basis)
