"""Current source-path / claim-semantic oracles for R24 coverage migration.

These checks bind the frozen AD registry fixture to decisive raw paths and
current safety-concept categories. They deliberately do not restore legacy
magic issue totals and do not compute expectations from
``audit_clinicaltrials_result_coverage``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.application.source_research_service import (
    FreshAResearchContent,
    ResearchFact,
    SourceCapture,
    _outcome_category,
    audit_clinicaltrials_result_coverage,
    extract_ctgov_atomic_results,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.reports.b.registry_observation import is_safety_domain_endpoint
from ci_workflow.reports.b.safety_concepts import describe_safety_concept

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "fixtures/positive/a-atopic-dermatitis/research-content.json"

# Exact SAE -> common_ae move retained by current claim semantics:
# NCT02277743 outcomeMeasures[19] TESAE is serious_teae_subset, not any_sae.
NCT02277743_TESAE_MEASURE = (
    "resultsSection.outcomeMeasuresModule.outcomeMeasures[19]"
)
NCT02277743_DISCONTINUATION_MEASURE = (
    "resultsSection.outcomeMeasuresModule.outcomeMeasures[20]"
)
NCT02277743_SKIN_TEAE_MEASURE = (
    "resultsSection.outcomeMeasuresModule.outcomeMeasures[18]"
)


def _payload() -> dict[str, object]:
    return json.loads(CONTENT.read_text(encoding="utf-8"))


def _fixture() -> tuple[dict[str, object], ReportAPortalData, tuple[SourceCapture, ...]]:
    payload = _payload()
    report = ReportAPortalData.model_validate(payload["report_data"])
    sources = tuple(SourceCapture.model_validate(item) for item in payload["sources"])
    return payload, report, sources


def _source(sources: tuple[SourceCapture, ...], nct_id: str) -> SourceCapture:
    return next(item for item in sources if item.query_or_identifier == nct_id)


def _facts(payload: dict[str, object]) -> tuple[ResearchFact, ...]:
    values = payload["facts"]
    assert isinstance(values, list)
    return tuple(ResearchFact.model_validate(item) for item in values)


def test_old_ad_source_coverage_still_fails_with_study_and_death_visibility() -> None:
    payload, report, sources = _fixture()
    audit = audit_clinicaltrials_result_coverage(report, sources, facts=_facts(payload))

    assert not audit.passed
    assert len(audit.audited_trial_ids) == 44
    assert len(audit.trial_coverage) == len(report.trials) == 49
    assert audit.inventory_counts["death"] == 104
    assert any(item.category == "death" and item.status == "missing" for item in audit.issues)
    assert any(
        item.status == "missing"
        and item.source_path.endswith("seriousEvents[16].stats[7].numAffected")
        for item in audit.issues
    )
    assert sum("0/0" in item.reason_zh for item in audit.issues) == 7
    assert sum("明示未报告" in item.reason_zh for item in audit.issues) == 3
    assert {
        item.trial_id
        for item in audit.trial_coverage
        if item.status == "reported_not_projected"
    } == {
        "nct02277743", "nct03131648", "nct04146363", "nct03985943",
        "nct03349060", "nct03569293", "nct03334396", "nct03745638",
        "nct02118792", "nct05014568", "nct04773587", "nct05131477",
        "nct05651711", "nct03703102", "nct03809663", "nct03533751",
        "nct04021862",
    }


def test_ada_and_viga_grade_improvement_remain_non_ae_outcomes() -> None:
    _, _, sources = _fixture()
    ada_title = "Frequency of Anti-drug Antibodies"
    viga_title = (
        "Number of Participants Who Achieved a Reduction of ≥ 2 Points From Baseline "
        "in the Validated Investigator's Global Assessment for Atopic Dermatitis "
        "(vIGA-AD) at Week 16"
    )

    assert not is_safety_domain_endpoint(ada_title)
    assert not is_safety_domain_endpoint(viga_title)
    assert describe_safety_concept(ada_title).key == "unknown"
    assert describe_safety_concept(viga_title).key != "grade_specific"
    assert _outcome_category(ada_title) == "outcome"
    assert _outcome_category(viga_title) == "outcome"

    ada_source = _source(sources, "NCT03131648")
    viga_source = _source(sources, "NCT03533751")
    ada_atoms, _ = extract_ctgov_atomic_results(ada_source)
    viga_atoms, _ = extract_ctgov_atomic_results(viga_source)
    assert {
        atom.category
        for atom in ada_atoms
        if atom.endpoint == ada_title
    } == {"outcome"}
    assert {
        atom.category
        for atom in viga_atoms
        if "Reduction of ≥ 2 Points" in atom.endpoint and "vIGA-AD" in atom.endpoint
    } == {"outcome"}


def test_tesae_outcome_paths_moved_from_sae_to_common_ae_subset() -> None:
    """Document the exact NCT02277743 path that left the SAE inventory.

    Legacy audits counted TESAE under SAE because the title contains
    "Serious Adverse Events". Current semantics keep it as
    ``serious_teae_subset`` / ``common_ae`` so it cannot overwrite any_sae.
    """
    _, _, sources = _fixture()
    source = _source(sources, "NCT02277743")
    record = json.loads(source.content_text)
    measure = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][19]
    title = measure["title"]
    assert "TESAE" in title or "Treatment Emergent Serious Adverse Events" in title
    concept = describe_safety_concept(title)
    assert concept.key == "serious_teae_subset"
    assert concept.teae is True
    assert concept.seriousness == "serious"
    assert _outcome_category(title) == "common_ae"
    assert _outcome_category(
        record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][20]["title"]
    ) == "common_ae"
    assert _outcome_category(
        record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][18]["title"]
    ) == "teae"

    atoms, _ = extract_ctgov_atomic_results(source)
    tesae_paths = {
        (atom.value_locator.field_path or "").removeprefix("$.")
        for atom in atoms
        if (atom.value_locator.field_path or "").startswith(f"$.{NCT02277743_TESAE_MEASURE}")
    }
    assert tesae_paths == {
        f"{NCT02277743_TESAE_MEASURE}.classes[0].categories[0].measurements[0].value",
        f"{NCT02277743_TESAE_MEASURE}.classes[0].categories[0].measurements[1].value",
        f"{NCT02277743_TESAE_MEASURE}.classes[0].categories[0].measurements[2].value",
    }
    assert {
        atom.category
        for atom in atoms
        if (atom.value_locator.field_path or "").startswith(f"$.{NCT02277743_TESAE_MEASURE}")
    } == {"common_ae"}
    assert {
        atom.category
        for atom in atoms
        if (atom.value_locator.field_path or "").startswith(
            f"$.{NCT02277743_DISCONTINUATION_MEASURE}"
        )
    } == {"common_ae"}
    assert {
        atom.category
        for atom in atoms
        if (atom.value_locator.field_path or "").startswith(
            f"$.{NCT02277743_SKIN_TEAE_MEASURE}"
        )
    } == {"teae"}


def test_sae_teae_and_participant_affected_basis_remain_distinct() -> None:
    _, _, sources = _fixture()
    source = _source(sources, "NCT02277743")
    atoms, _ = extract_ctgov_atomic_results(source)

    sae_group = next(
        atom for atom in atoms
        if atom.category == "sae"
        and (atom.value_locator.field_path or "").endswith(
            "eventGroups[0].seriousNumAffected"
        )
    )
    teae_skin = next(
        atom for atom in atoms
        if atom.category == "teae"
        and NCT02277743_SKIN_TEAE_MEASURE in (atom.value_locator.field_path or "")
    )
    assert sae_group.term == "任何SAE"
    assert sae_group.numerator == 12
    assert sae_group.denominator == 222
    assert sae_group.display_unit == "%"
    # Registry AE aggregates remain participant affected/at-risk counts, never
    # an event-count substitute for TEAE or a guessed zero.
    assert teae_skin.endpoint.startswith(
        "Percentage of Participants With Skin Infection Treatment Emergent"
    )
    assert teae_skin.category == "teae"
    assert sae_group.category != teae_skin.category


def test_unmarked_ai_synthesis_claim_still_fails_before_product_status() -> None:
    payload = _payload()
    changed = json.loads(json.dumps(payload, ensure_ascii=False))
    products = changed["report_data"]["products"]
    assert isinstance(products, list)
    for product in products:
        if product["id"] == "dupilumab":
            product["result_status"] = "暂无公开关键结果"
    claims = changed["claims"]
    assert isinstance(claims, list)
    target = next(claim for claim in claims if claim["claim_id"] == "claim-universe-closed")
    assert target["claim_kind"] == "synthesis"
    assert not str(target.get("claim_text", "")).startswith("AI 综合判断：")
    assert target.get("synthesis_method_zh") is None
    assert target.get("ai_disclosure_label_zh") is None

    with pytest.raises(ValueError, match="AI 综合判断必须明确文字标识和方法"):
        FreshAResearchContent.model_validate(changed)
