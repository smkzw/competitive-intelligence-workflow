"""Measured concepts and source dispersion, not broad parent-title shortcuts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.source_research_service import (
    classify_source_outcome,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.evidence import CtgovRecordSelector
from ci_workflow.reports.b.safety_concepts import describe_safety_concept
from ci_workflow.sources.connectors.ctgov_fetch import DerivedCtgovStudy
from ci_workflow.storage.source_derivation import capture_source_text
from tests.integration.test_r24_a_builder_contract import _build, _study


@pytest.mark.parametrize(("title", "class_title", "category_title", "expected"), [
    ("Half-life of clinical response", "", "", "efficacy"),
    ("Quality of life half-life", "", "", "efficacy"),
    ("Platelet half-life", "", "", "efficacy"),
    ("Time to t1/2 reduction in EASI score", "", "", "efficacy"),
    ("AUC of itch NRS over 24 hours", "", "", "efficacy"),
    ("Half-life(t1/2) of Nemolizumab in ADA-positive participants", "", "", "pk_pd"),
    ("Half-life(t½) of Nemolizumab", "", "", "pk_pd"),
    ("Pharmacokinetic parameters", "Serious Adverse Events", "", "adverse_events"),
    ("Immunogenicity", "Week 16", "TESAEs", "adverse_events"),
    ("Half-life of anti-drug antibodies", "", "", "immunogenicity"),
    ("Percentage of ADA-positive participants", "", "", "immunogenicity"),
    ("Terminal half-life", "", "", "pk_pd"),
])
def test_scientific_domain_tracks_measured_quantity_not_population_or_parent(
    title: str, class_title: str, category_title: str, expected: str,
) -> None:
    assert classify_source_outcome(title, class_title, category_title) == expected


@pytest.mark.parametrize("title", ["TESAEs", "Number of Participants With TESAEs"])
def test_tesae_is_serious_treatment_emergent_subset(title: str) -> None:
    concept = describe_safety_concept(title)
    assert (concept.key, concept.seriousness, concept.teae) == (
        "serious_teae_subset", "serious", True)


@pytest.mark.parametrize("title", ["No TESAEs", "Participants without TESAEs", "Non-TESAEs"])
def test_negative_tesae_is_not_positive_safety_count(title: str) -> None:
    concept = describe_safety_concept(title)
    assert concept.key != "serious_teae_subset" and concept.teae is not True


def _measure() -> dict[str, Any]:
    return {
        "title": "Half-life (t1/2) of Nemolizumab", "timeFrame": "Pre-dose through Day 85",
        "paramType": "MEAN", "dispersionType": "STANDARD_DEVIATION", "unitOfMeasure": "days",
        "populationDescription": "Healthy volunteers with evaluable PK samples",
        "groups": [{"id": "OG000", "title": "AI"}, {"id": "OG001", "title": "DCS"}],
        "denoms": [{"units": "Participants", "counts": [
            {"groupId": "OG000", "value": "95"}, {"groupId": "OG001", "value": "96"}]}],
        "classes": [{"categories": [{"measurements": [
            {"groupId": "OG000", "value": "18.0", "spread": "5.91"},
            {"groupId": "OG001", "value": "18.5", "spread": "4.52"}]}]}],
    }


def _capture(tmp_path: Path, measure: dict[str, Any]) -> Any:
    record = {"protocolSection": {
                  "identificationModule": {"nctId": "NCT05405985", "briefTitle": "Synthetic PK"},
                  "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-08-01"}}},
              "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [measure]}}}
    text, receipt = capture_source_text(
        tmp_path, json.dumps({"studies": [record]}).encode(), media_type="application/json",
        record_selector=CtgovRecordSelector(study_index=0, nct_id="NCT05405985"))
    return source_capture_from_ctgov_study(tmp_path, DerivedCtgovStudy(
        nct_id="NCT05405985", title="Synthetic PK", record_url="https://clinicaltrials.gov/study/NCT05405985",
        registry_posted_version_date="2026-08-01", acquired_at=datetime(2026, 8, 3, tzinfo=UTC),
        content_text=text, text_derivation=receipt))


def test_mean_sd_and_analysis_n_are_separate_exact_source_atoms(tmp_path: Path) -> None:
    atoms, issues = extract_ctgov_atomic_results(_capture(tmp_path, _measure()))
    assert not issues and len(atoms) == 2
    for atom, raw_mean, raw_sd, n in zip(
        atoms, ("18.0", "18.5"), ("5.91", "4.52"), (95, 96), strict=True,
    ):
        assert atom.numerator is None and atom.denominator is None
        assert atom.display_unit == "days" and atom.value_quote == raw_mean
        assert atom.denominator_candidates[0].parsed_value == n
        facts = research_facts_from_ctgov_atom(atom)
        by_role = {f.result_context.value_role: f for f in facts if f.result_context}
        assert set(by_role) == {"reported_measure", "dispersion"}
        spread = by_role["dispersion"]
        assert spread.original_text == raw_sd and spread.raw_value == raw_sd
        assert atom.value_locator.field_path is not None
        assert spread.locator.field_path == (
            atom.value_locator.field_path.removesuffix("value") + "spread")
        assert spread.result_context and spread.result_context.source_unit == "days"
        assert spread.result_context.source_dispersion_type == "STANDARD_DEVIATION"
        assert spread.result_context.analysis_population == (
            "Healthy volunteers with evaluable PK samples")


@pytest.mark.parametrize("invalid", ["broken", "-5.91", None])
def test_bad_sd_does_not_erase_mean_or_peer_measurement(tmp_path: Path, invalid: Any) -> None:
    measure = _measure()
    measure["classes"][0]["categories"][0]["measurements"][0]["spread"] = invalid
    atoms, issues = extract_ctgov_atomic_results(_capture(tmp_path, measure))
    assert len(atoms) == 2 and [a.value_quote for a in atoms] == ["18.0", "18.5"]
    assert len(research_facts_from_ctgov_atom(atoms[0])) == 1
    assert len(research_facts_from_ctgov_atom(atoms[1])) == 2
    assert len(issues) == 1 and issues[0].source_path.endswith("measurements[0].spread")
    assert issues[0].status == "parse_failure"


def test_generic_builder_preserves_supporting_pk_statistics(tmp_path: Path) -> None:
    study = _study("NCT05405985", 192, "ACTUAL", [
        {"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]}])
    study["resultsSection"] = {"outcomeMeasuresModule": {"outcomeMeasures": [_measure()]}}
    rows = _build(tmp_path, [study])["additional_observations"]
    assert len(rows) == 2
    assert [(r["raw_dispersion"], r["analysis_n"]) for r in rows] == [("5.91", 95), ("4.52", 96)]
    assert all(r["source_param_type"] == "MEAN" and r["raw_unit"] == "days" for r in rows)
    assert all(r["dispersion_source_path"].endswith(".spread") for r in rows)
    assert all(r["analysis_population"] == "Healthy volunteers with evaluable PK samples"
               for r in rows)
