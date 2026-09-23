from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.application.source_research_service import (
    FreshAResearchContent,
    ResearchFact,
    SourceCapture,
    _iter_adverse_event_results,
    audit_clinicaltrials_result_coverage,
    extract_ctgov_atomic_results,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData, SafetyRow

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "fixtures/positive/a-atopic-dermatitis/research-content.json"


def _fixture() -> tuple[dict[str, object], ReportAPortalData, tuple[SourceCapture, ...]]:
    payload = json.loads(CONTENT.read_text(encoding="utf-8"))
    report = ReportAPortalData.model_validate(payload["report_data"])
    sources = tuple(SourceCapture.model_validate(item) for item in payload["sources"])
    return payload, report, sources


def _source(sources: tuple[SourceCapture, ...], nct_id: str) -> SourceCapture:
    return next(item for item in sources if item.query_or_identifier == nct_id)


def _facts(payload: dict[str, object]) -> tuple[ResearchFact, ...]:
    values = payload["facts"]
    assert isinstance(values, list)
    return tuple(ResearchFact.model_validate(item) for item in values)


def test_audit_covers_every_registry_trial_and_preserves_secondary_source_status() -> None:
    payload, report, sources = _fixture()
    audit = audit_clinicaltrials_result_coverage(report, sources, facts=_facts(payload))

    # The captured registry payload omits one SAE affected count. Coverage
    # remains complete, but scientific acceptance must stay red until that
    # exact source field is recovered or explicitly resolved.
    assert not audit.passed
    assert len(audit.issues) == 1
    assert audit.issues[0].category == "sae"
    assert audit.issues[0].status == "missing"
    assert audit.issues[0].source_path.endswith(
        "seriousEvents[16].stats[7].numAffected"
    )
    assert len(audit.audited_trial_ids) == 44
    assert len(report.trials) == len(audit.trial_coverage) == 49
    assert len(audit.product_coverage) == 38
    assert {item.status for item in audit.trial_coverage} == {
        "registry_results_projected",
        "reported_by_secondary_source",
        "registry_results_not_posted",
        "reported_not_projected",
    }
    assert [
        item.trial_id
        for item in audit.trial_coverage
        if item.status == "reported_not_projected"
    ] == ["nct05131477"]
    secondary = {
        item.trial_id
        for item in audit.trial_coverage
        if item.status == "reported_by_secondary_source"
    }
    assert secondary >= {
        "nct06130566",
        "nct05265923",
        "nct06477835",
        "nct05549947",
        "nct04875169",
        "nct06136741",
        "nct05702268",
        "chictr2100051917",
        "nct05544591",
        "nct06035354",
        "pmid34710557",
        "nct03961529",
    }
    assert {
        item.product_id
        for item in audit.product_coverage
        if item.comparable_result_trial_ids
    } == {
        item.id for item in report.products if item.result_status == "有公开关键结果"
    }


def test_audit_rejects_model_copy_tampered_value_even_when_locator_is_unchanged() -> None:
    payload, report, sources = _fixture()
    facts = _facts(payload)
    original = next(row for row in report.efficacy if row.trial_id == "nct02277743")
    tampered = original.model_copy(update={"value": original.value + 1.0})
    report = report.model_copy(
        update={
            "efficacy": tuple(
                tampered if row.row_id == original.row_id else row for row in report.efficacy
            )
        }
    )

    audit = audit_clinicaltrials_result_coverage(report, sources, facts=facts)

    assert not audit.passed
    original_fact = next(
        fact for fact in facts if fact.row_ref == f"efficacy:{original.row_id}"
    )
    assert any(
        issue.category == "outcome"
        and issue.status == "missing"
        and issue.source_path == original_fact.locator.field_path
        for issue in audit.issues
    )


def test_product_result_status_cannot_hide_a_paired_public_result() -> None:
    payload, _report, _sources = _fixture()
    changed = json.loads(json.dumps(payload, ensure_ascii=False))
    products = changed["report_data"]["products"]
    assert isinstance(products, list)
    for product in products:
        if product["id"] == "dupilumab":
            product["result_status"] = "暂无公开关键结果"

    with pytest.raises(ValueError, match="报告产品结果状态"):
        FreshAResearchContent.model_validate(changed)


def test_audit_identifies_missing_outcomes_and_each_ae_family() -> None:
    _, report, sources = _fixture()
    report = report.model_copy(
        update={
            "efficacy": tuple(row for row in report.efficacy if row.trial_id != "nct02277743"),
            "safety": tuple(row for row in report.safety if row.trial_id != "nct02277743"),
        }
    )

    audit = audit_clinicaltrials_result_coverage(report, (_source(sources, "NCT02277743"),))

    assert not audit.passed
    assert audit.inventory_counts["outcome"] == 54
    assert audit.inventory_counts["teae"] == 6
    assert audit.inventory_counts["sae"] == 72
    assert audit.inventory_counts["aesi"] == 0
    assert audit.inventory_counts["common_ae"] == 21
    assert any(issue.category == "outcome" for issue in audit.issues)
    assert any(issue.category == "sae" for issue in audit.issues)
    assert any(issue.category == "common_ae" for issue in audit.issues)
    coverage = next(item for item in audit.trial_coverage if item.trial_id == "nct02277743")
    assert coverage.status == "reported_not_projected"


def test_audit_classifies_unreadable_registry_content_as_a_technical_failure() -> None:
    _, report, sources = _fixture()
    source = _source(sources, "NCT02277743").model_copy(update={"content_text": "{"})

    audit = audit_clinicaltrials_result_coverage(report, (source,))

    coverage = next(item for item in audit.trial_coverage if item.trial_id == "nct02277743")
    assert coverage.status == "source_parse_failure"
    assert any(issue.status == "parse_failure" for issue in audit.issues)


def test_other_num_affected_cannot_be_projected_as_teae() -> None:
    _, report, sources = _fixture()
    teae_row = SafetyRow(
        row_id="audit-teae-from-other-total",
        product_id="dupilumab",
        trial_id="nct02277743",
        arm="治疗组",
        category="治疗期间不良事件",
        term="任何TEAE",
        value=40.2,
        numerator=92,
        denominator=229,
        unit="%",
        time_window="主要对照期",
        disclosure_state="已公开",
    )
    report = report.model_copy(update={"safety": (*report.safety, teae_row)})

    audit = audit_clinicaltrials_result_coverage(report, (_source(sources, "NCT02277743"),))

    assert any(
        issue.category == "teae"
        and issue.status == "misclassified"
        and "otherNumAffected" in issue.reason_zh
        for issue in audit.issues
    )


def test_omitted_ae_affected_count_is_unknown_not_zero() -> None:
    _, report, sources = _fixture()

    audit = audit_clinicaltrials_result_coverage(report, (_source(sources, "NCT05131477"),))

    assert any(
        issue.status == "missing"
        and issue.source_path.endswith("seriousEvents[16].stats[7].numAffected")
        and "未知，待核" in issue.reason_zh
        for issue in audit.issues
    )


def test_registry_atoms_reextract_real_value_and_denominator_fields() -> None:
    _, _, sources = _fixture()
    atoms, issues = extract_ctgov_atomic_results(_source(sources, "NCT02277743"))

    assert not issues
    outcome = next(row for row in atoms if row.category == "outcome")
    assert outcome.value_quote == "10.3"
    assert outcome.value_locator.field_path is not None
    assert outcome.value_locator.field_path.endswith("measurements[0].value")
    assert outcome.denominator_locator is None
    zero = next(
        row for row in atoms
        if row.category == "sae" and row.endpoint == "" and row.value_quote == "0"
        and row.group_id == "EG001" and row.denominator_quote == "229"
    )
    assert zero.numerator == 0
    assert zero.display_value == 0
    assert zero.value_locator.field_path is not None
    assert zero.value_locator.field_path.endswith("seriousEvents[0].stats[1].numAffected")
    assert zero.denominator_locator is not None
    assert zero.denominator_locator.field_path is not None
    assert zero.denominator_locator.field_path.endswith("seriousEvents[0].stats[1].numAtRisk")


def test_registry_atoms_do_not_turn_missing_affected_into_zero() -> None:
    _, _, sources = _fixture()
    atoms, issues = extract_ctgov_atomic_results(_source(sources, "NCT05131477"))

    assert any(
        issue.status == "missing"
        and issue.source_path.endswith("seriousEvents[16].stats[7].numAffected")
        for issue in issues
    )
    assert not any(
        row.value_locator.field_path == "$.resultsSection.adverseEventsModule."
        "seriousEvents[16].stats[7].numAffected"
        for row in atoms
    )


def test_registry_participant_count_retains_both_raw_inputs() -> None:
    _, _, sources = _fixture()
    record = {
        "protocolSection": {"identificationModule": {"nctId": "NCT02277743"}},
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{
            "title": "Participants With Response",
            "timeFrame": "Week 16",
            "unitOfMeasure": "Participants",
            "groups": [{"id": "OG1", "title": "治疗组"}],
            "denoms": [{"counts": [{"groupId": "OG1", "value": "4"}]}],
            "classes": [{"categories": [{"measurements": [
                {"groupId": "OG1", "value": "1"}
            ]}]}],
        }]}},
    }
    source = _source(sources, "NCT02277743").model_copy(
        update={"content_text": json.dumps(record)}
    )

    atoms, issues = extract_ctgov_atomic_results(source)

    assert not issues and len(atoms) == 1
    assert atoms[0].display_value == 25.0
    assert (atoms[0].value_quote, atoms[0].denominator_quote) == ("1", "4")
    assert atoms[0].value_locator.field_path is not None
    assert atoms[0].value_locator.field_path.endswith("measurements[0].value")
    assert atoms[0].denominator_locator is not None
    assert atoms[0].denominator_locator.field_path is not None
    assert atoms[0].denominator_locator.field_path.endswith("denoms[0].counts[0].value")


def test_missing_group_affected_does_not_hide_other_valid_group_results() -> None:
    _, _, sources = _fixture()
    record = {
        "protocolSection": {"identificationModule": {"nctId": "NCT02277743"}},
        "resultsSection": {"adverseEventsModule": {"eventGroups": [
            {
                "id": "EG1", "title": "治疗组", "seriousNumAtRisk": 100,
                "otherNumAffected": 0, "otherNumAtRisk": 100,
            }
        ]}},
    }
    source = _source(sources, "NCT02277743").model_copy(
        update={"content_text": json.dumps(record)}
    )

    atoms, issues = extract_ctgov_atomic_results(source)

    assert len(atoms) == 1
    assert atoms[0].category == "common_ae"
    assert (atoms[0].value_quote, atoms[0].denominator_quote) == ("0", "100")
    assert len(issues) == 1
    assert issues[0].status == "missing"
    assert issues[0].source_path.endswith("eventGroups[0].seriousNumAffected")


def test_ae_explicit_zero_is_preserved_but_missing_affected_is_not_inferred() -> None:
    record = {
        "resultsSection": {
            "adverseEventsModule": {
                "eventGroups": [{"id": "EG1", "title": "治疗组"}],
                "seriousEvents": [
                    {
                        "term": "头痛",
                        "stats": [
                            {"groupId": "EG1", "numAtRisk": 100},
                            {"groupId": "EG1", "numAffected": 0, "numAtRisk": 100},
                        ],
                    }
                ],
            }
        }
    }
    issues = []
    rows = _iter_adverse_event_results(
        record=record, trial_id="nct-test", source_id="source-test", issues=issues
    )

    assert len(rows) == 1
    assert rows[0].numerator == 0
    assert rows[0].denominator == 100
    assert rows[0].value == 0
    assert len(issues) == 1
    assert issues[0].status == "missing"
    assert issues[0].source_path.endswith("seriousEvents[0].stats[0].numAffected")


def test_explicit_teae_and_aesi_are_separate_from_other_events() -> None:
    _, report, sources = _fixture()
    source = _source(sources, "NCT02277743")
    record = json.loads(source.content_text)
    group = record["resultsSection"]["adverseEventsModule"]["eventGroups"][0]
    group.update(teaeNumAffected=10, teaeNumAtRisk=222)
    record["resultsSection"]["adverseEventsModule"]["seriousEvents"][0]["isAESI"] = True
    changed = source.model_copy(update={"content_text": json.dumps(record, ensure_ascii=False)})

    audit = audit_clinicaltrials_result_coverage(report, (changed,))

    assert audit.inventory_counts["teae"] > 6
    assert audit.inventory_counts["aesi"] == 3
    assert any(issue.category == "teae" and issue.status == "missing" for issue in audit.issues)
    assert any(issue.category == "aesi" and issue.status == "missing" for issue in audit.issues)
