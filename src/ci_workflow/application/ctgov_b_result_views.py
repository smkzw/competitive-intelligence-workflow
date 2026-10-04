"""Preserve registry results in B when product association is not established.

This is a source-to-existing-view adapter, not scientific adoption or an arm
resolver. Source values are never replaced by the extractor's derived display
percentage. Missing/ambiguous denominator issues stay local and auditable.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ci_workflow.application.source_research_service import (
    ClinicalTrialsResultCoverageIssue,
    SourceCapture,
    _capture_version_id,
    ctgov_direct_safety_measure_identity,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.reports.b.safety_concepts import describe_measured_safety_concept


@dataclass(frozen=True)
class CtgovBUnassignedViews:
    efficacy: tuple[dict[str, Any], ...]
    safety: tuple[dict[str, Any], ...]
    supporting: tuple[dict[str, Any], ...]
    issues: tuple[ClinicalTrialsResultCoverageIssue, ...]


def project_unassigned_ctgov_results(
    sources: Sequence[SourceCapture],
) -> CtgovBUnassignedViews:
    """Expose all source atoms without inventing a product, rate or approval."""
    if len({source.source_id for source in sources}) != len(sources):
        raise ValueError("重复登记来源身份；请先明确选择来源版本")
    efficacy: list[dict[str, Any]] = []
    safety: list[dict[str, Any]] = []
    supporting: list[dict[str, Any]] = []
    issues: list[ClinicalTrialsResultCoverageIssue] = []
    for source in sources:
        atoms, source_issues = extract_ctgov_atomic_results(source)
        issues.extend(source_issues)
        source_version = _capture_version_id(source)
        for atom in atoms:
            facts = research_facts_from_ctgov_atom(atom)
            value_fact = facts[0]
            raw_value = float(atom.value_quote)
            unit = atom.raw_unit or atom.display_unit
            row: dict[str, Any] = {
                "row_id": stable_id("b-registry-result", value_fact.fact_id),
                "fact_id": value_fact.fact_id,
                "source_fact_ids": tuple(fact.fact_id for fact in facts),
                "trial_id": atom.trial_id.casefold(),
                "product_id": None,
                "group_id": atom.group_id,
                "group_name": atom.group_title,
                "arm_label": atom.arm or atom.group_title,
                "arm_role": "unknown",
                "group_assignment_state": "unknown",
                "endpoint": atom.endpoint or atom.term,
                "original_endpoint": atom.endpoint or atom.term,
                "term": atom.term,
                "original_variable": atom.endpoint or atom.term,
                "display_label_zh": atom.endpoint or atom.term,
                "category": atom.category,
                "domain": atom.domain,
                "metric": atom.metric,
                "value": raw_value,
                "unit": unit,
                "raw_unit": atom.raw_unit,
                "raw_value_type": atom.raw_value_type,
                "value_basis": "source_reported",
                "numerator": atom.numerator,
                "denominator": atom.denominator,
                "denominator_quote": atom.denominator_quote,
                "denominator_locator": (
                    atom.denominator_locator.model_dump(mode="json")
                    if atom.denominator_locator is not None else None
                ),
                "denominator_candidates": tuple(
                    candidate.model_dump(mode="json")
                    for candidate in atom.denominator_candidates
                ),
                "timepoint": atom.observation_timepoint or atom.timepoint,
                "analysis_population": atom.analysis_population,
                "source_class_title": atom.class_title,
                "source_category_title": atom.category_title,
                "source_measure_path": atom.source_measure_path,
                "source_param_type": atom.source_param_type,
                "source_dispersion_type": atom.source_dispersion_type,
                "statistic_form": atom.source_param_type,
                "source_version_id": source_version,
                "source_name": source.title,
                "source_url": source.url,
                "source_text": atom.value_quote,
                "source_locator": atom.value_locator.model_dump(mode="json"),
                "disclosure_state": value_fact.disclosure_state,
                "review_state": "candidate",
            }
            if atom.domain == "adverse_events":
                concept = describe_measured_safety_concept(
                    atom.endpoint or atom.term, atom.class_title, atom.category_title,
                )
                _, measure_object, count_basis = ctgov_direct_safety_measure_identity(
                    atom.endpoint or atom.term, atom.class_title, atom.category_title,
                    atom.raw_unit,
                )
                row.update({
                    "term_key": concept.key,
                    "polarity": concept.polarity,
                    "grade_set": concept.grade_set,
                    "seriousness": concept.seriousness,
                    "teae": concept.teae,
                    "relatedness": concept.relatedness,
                    "parent": concept.parent,
                    "children": concept.children,
                    "count_basis": count_basis,
                    "measure_object": measure_object,
                    "at_risk_stat": concept.at_risk_stat,
                })
            if atom.domain == "efficacy":
                efficacy.append(row)
            elif atom.domain == "adverse_events":
                safety.append(row)
            else:
                supporting.append(row)
    return CtgovBUnassignedViews(
        efficacy=tuple(efficacy), safety=tuple(safety),
        supporting=tuple(supporting), issues=tuple(issues),
    )
