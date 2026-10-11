"""Exact AE-module definition/population context and raw/display count units.

The captured ClinicalTrials.gov ``adverseEventsModule`` supplies one
module-level ``description`` (event definition and safety population) while
outcome measures supply their own ``populationDescription``. These are
different source definitions: neither may be replaced by the other, by a
class-derived display label, or by a translated count unit. Every check below
calls the real production parser, builder, coverage audit and fact derivation.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application import source_research_service
from ci_workflow.application.source_research_service import (
    ResearchPackageError,
    ResearchResultContext,
    audit_clinicaltrials_result_coverage,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.evidence import CtgovRecordSelector, EvidenceLocator
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.sources.connectors.ctgov_fetch import DerivedCtgovStudy
from ci_workflow.storage.source_derivation import capture_source_text, extract_locator_quote
from tests.integration.test_r24_a_builder_contract import _build, _study

NCT = "NCT04202679"

# Verbatim captured text from the same original ClinicalTrials.gov record the
# 1007 source-context candidate froze (source package sha256
# eed16decbf004cf2c477e1c489b6198cbd5d2ec8d0fe4481bc09084a07c9371e):
# ``$.resultsSection.adverseEventsModule.description`` and
# ``$.resultsSection.outcomeMeasuresModule.outcomeMeasures[21].populationDescription``.
AE_MODULE_DESCRIPTION = (
    "Reported AEs were TEAEs that developed/worsened in grade or became serious "
    "during TE period (defined as the time from the first IMP administration to the "
    "last IMP administration + 14 weeks). Analysis was performed on safety population."
)
AE_MODULE_TIMEFRAME = (
    "From the first IMP administration to the last IMP administration + 14 weeks "
    "(i.e., up to 36 weeks)"
)
OUTCOME_21_TITLE = (
    "Number of Participants With Treatment-emergent Adverse Events (TEAEs) and "
    "Treatment-emergent Serious Adverse Events (TESAEs)"
)
OUTCOME_21_POPULATION = (
    "Analysis was performed on safety population which included all participants "
    "who received at least 1 dose of study intervention analyzed according to the "
    "intervention actually received."
)
ITT_POPULATION = (
    "Analysis was performed on intent-to-treat (ITT) population which included all "
    "participants with a treatment kit number allocated and recorded as randomized."
)
DEFINITION_PATH = "resultsSection.adverseEventsModule.description"
DEFINITION_PATH_JSON = f"$.{DEFINITION_PATH}"


def _tesae_measure() -> dict[str, Any]:
    """Minimal faithful fixture around the captured measure 21 texts."""
    return {
        "title": OUTCOME_21_TITLE,
        "timeFrame": AE_MODULE_TIMEFRAME,
        "paramType": "COUNT_OF_PARTICIPANTS",
        "unitOfMeasure": "Participants",
        "populationDescription": OUTCOME_21_POPULATION,
        "groups": [{"id": "OG001", "title": "Drug arm"}],
        "denoms": [{"units": "Participants", "counts": [
            {"groupId": "OG001", "value": "77"}]}],
        "classes": [{"title": "TESAEs", "categories": [
            {"measurements": [{"groupId": "OG001", "value": "2"}]}]}],
    }


def _efficacy_measure() -> dict[str, Any]:
    return {
        "title": "Change From Baseline in WI-NRS Score at Week 24",
        "timeFrame": "Baseline to Week 24",
        "paramType": "MEAN",
        "dispersionType": "STANDARD_DEVIATION",
        "unitOfMeasure": "points",
        "populationDescription": ITT_POPULATION,
        "groups": [{"id": "OG002", "title": "Drug arm"}],
        "denoms": [{"units": "Participants", "counts": [
            {"groupId": "OG002", "value": "80"}]}],
        "classes": [{"categories": [{"measurements": [
            {"groupId": "OG002", "value": "-4.5", "spread": "2.1"}]}]}],
    }


def _ae_module(*, description: str | None) -> dict[str, Any]:
    module: dict[str, Any] = {
        "timeFrame": AE_MODULE_TIMEFRAME,
        "frequencyThreshold": "5",
        "eventGroups": [{
            "id": "EG001", "title": "Drug arm",
            "seriousNumAffected": 2, "seriousNumAtRisk": 77,
            "deathsNumAffected": 0, "deathsNumAtRisk": 77,
        }],
    }
    if description is not None:
        module["description"] = description
    return module


def _study_record(
    *, module_description: str | None, include_tesae: bool = True,
    include_efficacy: bool = False,
) -> dict[str, Any]:
    study = _study(NCT, 82, "ACTUAL", [
        {"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]}])
    study["protocolSection"]["statusModule"] = {
        "lastUpdatePostDateStruct": {"date": "2026-08-01"}}
    measures = []
    if include_tesae:
        measures.append(_tesae_measure())
    if include_efficacy:
        measures.append(_efficacy_measure())
    results: dict[str, Any] = {
        "adverseEventsModule": _ae_module(description=module_description),
    }
    if measures:
        results["outcomeMeasuresModule"] = {"outcomeMeasures": measures}
    study["resultsSection"] = results
    return study


def _capture(tmp_path: Path, study: dict[str, Any]) -> Any:
    identification = study["protocolSection"]["identificationModule"]
    title = str(identification.get("briefTitle") or NCT)
    text, receipt = capture_source_text(
        tmp_path, json.dumps({"studies": [study]}).encode(),
        media_type="application/json",
        record_selector=CtgovRecordSelector(study_index=0, nct_id=NCT))
    return source_capture_from_ctgov_study(tmp_path, DerivedCtgovStudy(
        nct_id=NCT, title=title,
        record_url=f"https://clinicaltrials.gov/study/{NCT}",
        registry_posted_version_date="2026-08-01",
        acquired_at=datetime(2026, 8, 3, tzinfo=UTC),
        content_text=text, text_derivation=receipt))


def _build_report_and_sidecar(
    tmp_path: Path, study: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _build(tmp_path, [study])
    sidecar = json.loads(
        (tmp_path / "report.derivation.json").read_text(encoding="utf-8"))
    return payload, sidecar


def _bound_report_and_facts(
    tmp_path: Path, study: dict[str, Any],
) -> tuple[ReportAPortalData, Any, tuple[Any, ...]]:
    """Build the ordinary A payload and bind each safety row to real facts."""
    payload, sidecar = _build_report_and_sidecar(tmp_path, study)
    report = ReportAPortalData.model_validate(payload)
    source = _capture(tmp_path, study)
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues
    by_path = {atom.value_locator.field_path or "": atom for atom in atoms}
    by_row = {entry["row_id"]: entry for entry in sidecar["row_source_map"]}
    facts: list[Any] = []
    for row in report.safety:
        atom = by_path[by_row[row.row_id]["value_path"]]
        facts.extend(
            research_facts_from_ctgov_atom(atom, report_row_ref=f"safety:{row.row_id}"))
    return report, source, tuple(facts)


def _context_conflicts(audit: Any) -> list[Any]:
    return [
        issue for issue in audit.issues
        if issue.status == "conflicting" and "来源人群/定义语境" in issue.reason_zh
    ]


def test_ae_module_definition_and_original_locator_survive_atom_and_facts(
    tmp_path: Path,
) -> None:
    source = _capture(tmp_path, _study_record(
        module_description=AE_MODULE_DESCRIPTION, include_tesae=False))
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues
    assert {atom.category for atom in atoms} == {"sae", "death"}
    for atom in atoms:
        assert atom.source_definition == AE_MODULE_DESCRIPTION
        assert atom.source_definition_path == DEFINITION_PATH
    # Provenance-bound: the exact module text is re-extractable at the locator.
    quote = extract_locator_quote(
        source.content_text, media_type=source.media_type,
        locator=EvidenceLocator(
            document_role="clinical_trial_registry",
            field_path=DEFINITION_PATH_JSON, url=source.url))
    assert quote == AE_MODULE_DESCRIPTION
    for atom in atoms:
        fact = research_facts_from_ctgov_atom(atom)[0]
        assert fact.result_context is not None
        assert fact.result_context.source_definition == AE_MODULE_DESCRIPTION
        assert fact.result_context.source_definition_path == DEFINITION_PATH
        # The module definition is context; the fact quote stays the count.
        assert fact.original_text == str(atom.numerator)


def test_ae_module_without_description_does_not_borrow_outcome_population(
    tmp_path: Path,
) -> None:
    study = _study_record(module_description=None, include_tesae=True)
    source = _capture(tmp_path, study)
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues
    module_atoms = [atom for atom in atoms if not atom.endpoint]
    measure_atoms = [atom for atom in atoms if atom.endpoint]
    assert {atom.category for atom in module_atoms} == {"sae", "death"}
    assert {atom.category for atom in measure_atoms} == {"tesae"}
    for atom in module_atoms:
        # Missing module definition stays absent; it must not take the
        # unrelated outcome population as a substitute definition.
        assert atom.source_definition == ""
        assert atom.source_definition_path == ""
        assert atom.analysis_population == ""
        fact = research_facts_from_ctgov_atom(atom)[0]
        assert fact.result_context is not None
        assert fact.result_context.source_definition is None
        assert fact.result_context.source_definition_path is None
        assert fact.result_context.analysis_population is None
    assert measure_atoms[0].analysis_population == OUTCOME_21_POPULATION


def test_module_definition_and_outcome_population_stay_distinct(
    tmp_path: Path,
) -> None:
    study = _study_record(
        module_description=AE_MODULE_DESCRIPTION, include_tesae=True)
    source = _capture(tmp_path, study)
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues
    by_category = {atom.category: atom for atom in atoms}
    sae_fact = research_facts_from_ctgov_atom(by_category["sae"])[0]
    tesae_fact = research_facts_from_ctgov_atom(by_category["tesae"])[0]
    assert sae_fact.result_context is not None
    assert tesae_fact.result_context is not None
    # The module-level AE definition and the outcome population definition are
    # different source texts and must never be harmonized into one field.
    assert AE_MODULE_DESCRIPTION != OUTCOME_21_POPULATION
    assert sae_fact.result_context.source_definition == AE_MODULE_DESCRIPTION
    assert sae_fact.result_context.analysis_population is None
    assert tesae_fact.result_context.analysis_population == OUTCOME_21_POPULATION
    assert tesae_fact.result_context.source_definition is None
    for fact in (sae_fact, tesae_fact):
        assert fact.result_context is not None
        assert fact.result_context.analysis_population != AE_MODULE_DESCRIPTION
        assert fact.result_context.source_definition != OUTCOME_21_POPULATION


def test_builder_derivation_keeps_outcome_population_and_module_definition(
    tmp_path: Path,
) -> None:
    study = _study_record(
        module_description=AE_MODULE_DESCRIPTION, include_tesae=True,
        include_efficacy=True)
    _, sidecar = _build_report_and_sidecar(tmp_path, study)
    entries = sidecar["row_source_map"]
    measure_safety = next(
        entry for entry in entries if entry["value_path"].endswith(
            "outcomeMeasures[0].classes[0].categories[0].measurements[0].value"))
    efficacy = next(entry for entry in entries if entry["domain"] == "efficacy")
    module_rows = [
        entry for entry in entries
        if entry["value_path"].endswith(
            ("seriousNumAffected", "deathsNumAffected"))]
    assert len(module_rows) == 2
    # Outcome analysis-population text survives the row-bound derivation and is
    # not replaced by the class-derived display label.
    assert measure_safety["analysis_population"] == OUTCOME_21_POPULATION
    assert measure_safety["display_population"] != OUTCOME_21_POPULATION
    assert efficacy["analysis_population"] == ITT_POPULATION
    assert efficacy["display_population"] != ITT_POPULATION
    # The AE module definition travels with its exact source path.
    for entry in module_rows:
        assert entry["source_definition"] == AE_MODULE_DESCRIPTION
        assert entry["source_definition_path"] == DEFINITION_PATH_JSON
        assert entry["analysis_population"] is None


@pytest.mark.parametrize(("path_suffix", "field", "wrong"), [
    ("seriousNumAffected", "source_definition", None),
    ("seriousNumAffected", "source_definition", "TEAEs were unrelated events."),
    ("seriousNumAffected", "source_definition_path",
     "resultsSection.adverseEventsModule.timeFrame"),
    ("deathsNumAffected", "source_definition", None),
    ("measurements[0].value", "analysis_population", None),
    ("measurements[0].value", "analysis_population",
     "Participants with mild disease only."),
])
def test_coverage_rejects_lost_or_changed_source_definition_and_population(
    tmp_path: Path, path_suffix: str, field: str, wrong: Any,
) -> None:
    study = _study_record(
        module_description=AE_MODULE_DESCRIPTION, include_tesae=True)
    report, source, facts = _bound_report_and_facts(tmp_path, study)
    clean = audit_clinicaltrials_result_coverage(report, (source,), facts=facts)
    assert not clean.issues
    target_ref = next(
        fact.row_ref for fact in facts
        if fact.result_context is not None
        and not fact.row_ref.endswith((":denominator", ":dispersion"))
        and (fact.locator.field_path or "").endswith(path_suffix))
    tampered = tuple(
        fact.model_copy(update={
            "result_context": fact.result_context.model_copy(update={field: wrong})})
        if fact.row_ref == target_ref and fact.result_context is not None else fact
        for fact in facts)
    audit = audit_clinicaltrials_result_coverage(report, (source,), facts=tampered)
    conflicts = _context_conflicts(audit)
    assert len(conflicts) == 1
    assert conflicts[0].report_row_ids == (target_ref.split(":", 1)[1],)


def test_count_display_unit_is_normalized_and_raw_unit_stays_in_source(
    tmp_path: Path,
) -> None:
    study = _study_record(
        module_description=AE_MODULE_DESCRIPTION, include_tesae=True,
        include_efficacy=True)
    source = _capture(tmp_path, study)
    atoms, issues = extract_ctgov_atomic_results(source)
    assert not issues
    sae = next(
        atom for atom in atoms
        if (atom.value_locator.field_path or "").endswith("seriousNumAffected"))
    # AE-module fields encode participant counts but contain no reported unit
    # text. Never manufacture an English source quote from that schema role.
    assert sae.raw_unit == ""
    assert sae.value_quote == "2"
    sae_fact = research_facts_from_ctgov_atom(sae)[0]
    assert sae_fact.result_context is not None
    assert sae_fact.result_context.source_unit == "人"
    assert sae_fact.original_text == "2" and sae_fact.original_text != "人"
    quote = extract_locator_quote(
        source.content_text, media_type=source.media_type,
        locator=sae.value_locator)
    assert quote == "2" and quote != "人"
    tesae = next(atom for atom in atoms if atom.category == "tesae")
    assert tesae.raw_unit == "Participants"
    tesae_fact = research_facts_from_ctgov_atom(tesae)[0]
    assert tesae_fact.result_context is not None
    assert tesae_fact.result_context.source_unit == "人"
    # Scalar roles keep the raw source unit verbatim.
    days = next(
        atom for atom in atoms
        if atom.endpoint and atom.category == "outcome")
    days_fact = research_facts_from_ctgov_atom(days)[0]
    assert days_fact.result_context is not None
    assert days_fact.result_context.source_unit == days.raw_unit
    # The normalized count semantics are documented on the context field.
    description = ResearchResultContext.model_fields["source_unit"].description or ""
    assert "归一化" in description and "人" in description
    # The ordinary builder keeps display unit and raw unit separate too.
    _, sidecar = _build_report_and_sidecar(tmp_path, study)
    entry = next(
        entry for entry in sidecar["row_source_map"]
        if entry["value_path"].endswith("seriousNumAffected"))
    assert entry["raw_unit"] is None
    assert entry["normalized_unit"] == "participants"
    assert entry["unit_origin"] == "registry_count_field_semantics"


def test_ordinary_builder_teae_matches_source_concept_not_display_alias(
    tmp_path: Path,
) -> None:
    study = _study_record(module_description=None, include_tesae=True)
    study["resultsSection"].pop("adverseEventsModule")
    measure = study["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]
    measure["classes"][0]["title"] = "TEAEs"
    report, source, facts = _bound_report_and_facts(tmp_path, study)
    assert len(report.safety) == 1
    assert report.safety[0].term_key == "any_teae"
    clean = audit_clinicaltrials_result_coverage(report, (source,), facts=facts)
    assert not clean.issues
    # Identical numbers cannot let a serious subset borrow the overall row.
    wrong_row = report.safety[0].model_copy(update={
        "term_key": "serious_teae_subset", "seriousness": "serious"})
    wrong = report.model_copy(update={"safety": (wrong_row,)})
    rejected = audit_clinicaltrials_result_coverage(wrong, (source,), facts=facts)
    assert any(issue.status == "missing" for issue in rejected.issues)


def test_definition_context_cannot_be_reextracted_from_a_wrong_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _capture(tmp_path, _study_record(
        module_description=AE_MODULE_DESCRIPTION, include_tesae=False))
    real = source_research_service._iter_adverse_event_results

    def fabricated(*, record: Any, trial_id: str, source_id: str,
                   issues: list[Any]) -> list[Any]:
        return [
            dataclasses.replace(result, source_definition="Fabricated definition")
            for result in real(record=record, trial_id=trial_id,
                               source_id=source_id, issues=issues)]

    monkeypatch.setattr(
        source_research_service, "_iter_adverse_event_results", fabricated)
    with pytest.raises(ResearchPackageError, match="定义语境"):
        extract_ctgov_atomic_results(source)


@pytest.mark.parametrize("field", ["time_window", "source_class_title", "source_category_title"])
def test_bound_safety_coverage_rejects_wrong_displayed_statistical_context(
    tmp_path: Path, field: str,
) -> None:
    source_record = _study_record(module_description=None, include_tesae=True)
    source_record["resultsSection"].pop("adverseEventsModule")
    report, source, facts = _bound_report_and_facts(tmp_path, source_record)
    assert not audit_clinicaltrials_result_coverage(report, (source,), facts=facts).issues
    row = report.safety[0].model_copy(update={field: "Different analysis at Day 1"})
    wrong = report.model_copy(update={"safety": (row,)})
    rejected = audit_clinicaltrials_result_coverage(wrong, (source,), facts=facts)
    assert any(issue.status in {"missing", "conflicting"} for issue in rejected.issues)


@pytest.mark.parametrize("lost_path", [False, True])
def test_atom_boundary_rejects_omission_even_when_parser_emits_empty_definition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lost_path: bool,
) -> None:
    source = _capture(tmp_path, _study_record(
        module_description=AE_MODULE_DESCRIPTION, include_tesae=False))
    real = source_research_service._iter_adverse_event_results

    def omitted(*, record: Any, trial_id: str, source_id: str,
                issues: list[Any]) -> list[Any]:
        return [dataclasses.replace(
            result, source_definition="",
            source_definition_path="" if lost_path else result.source_definition_path,
        ) for result in real(record=record, trial_id=trial_id,
                             source_id=source_id, issues=issues)]

    monkeypatch.setattr(source_research_service, "_iter_adverse_event_results", omitted)
    with pytest.raises(ResearchPackageError, match="定义语境"):
        extract_ctgov_atomic_results(source)
