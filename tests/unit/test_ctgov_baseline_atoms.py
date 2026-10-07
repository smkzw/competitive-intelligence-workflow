"""Baseline source extraction, not product association or clinical equivalence."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

import pytest

from ci_workflow.application.ctgov_baseline_atoms import extract_ctgov_baseline_atoms
from ci_workflow.application.source_research_service import ResearchPackageError, SourceCapture
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import extract_locator_quote


def _record() -> dict[str, Any]:
    return {
        "protocolSection": {"identificationModule": {"nctId": "NCT12345678"}},
        "resultsSection": {"baselineCharacteristicsModule": {
            "populationDescription": "All randomized participants.",
            "groups": [
                {"id": "BG7", "title": "Experimental", "description": "Original regimen."},
                {"id": "BG1", "title": "Control", "description": "Original comparator."},
                {"id": "BG9", "title": "Total", "description": "Total of all reporting groups"},
            ],
            "denoms": [{"units": "Participants", "counts": [
                {"groupId": "BG1", "value": "10"},
                {"groupId": "BG7", "value": "20"},
                {"groupId": "BG9", "value": "30"},
            ]}],
            "measures": [
                {"title": "Age, Continuous", "paramType": "MEAN",
                 "dispersionType": "STANDARD_DEVIATION", "unitOfMeasure": "Years",
                 "classes": [{"categories": [{"measurements": [
                     {"groupId": "BG7", "value": "51.0", "spread": "15.00"},
                     {"groupId": "BG1", "value": "46.7", "spread": "15.2"},
                 ]}]}]},
                {"title": "Sex: Female, Male", "paramType": "COUNT_OF_PARTICIPANTS",
                 "unitOfMeasure": "Participants", "classes": [{"categories": [
                     {"title": "Female", "measurements": [
                         {"groupId": "BG7", "value": "0"},
                         {"groupId": "BG1", "value": "5"},
                     ]},
                 ]}]},
            ],
        }},
    }


def _capture(record: dict[str, Any]) -> SourceCapture:
    return SourceCapture(
        source_id="baseline-source", route_id="ctgov", source_type="clinical_trial_registry",
        title="Fixed baseline", url="https://clinicaltrials.gov/study/NCT12345678",
        query_or_identifier="nct12345678", language="en", access_method="fixture",
        content_text=json.dumps(record), acquired_at=datetime(2026, 10, 7, tzinfo=UTC),
        published_at=None, effective_at=None, first_disclosed_at=None,
        locator=EvidenceLocator(
            document_role="clinical_trial_registry", field_path="$.resultsSection"
        ),
    )


def _module(record: dict[str, Any]) -> dict[str, Any]:
    return record["resultsSection"]["baselineCharacteristicsModule"]


def _numeric(batch: Any) -> list[Any]:
    return [fact for fact in batch.facts if fact.result_context is not None]


def test_every_scalar_reextracts_and_keeps_original_statistics_and_group_identity() -> None:
    source = _capture(_record())
    batch = extract_ctgov_baseline_atoms(source)
    assert batch.trial_id == "NCT12345678" and not batch.issues
    numbers = _numeric(batch)
    assert len(numbers) == 9  # three group Ns, two means, two SDs, two counts
    for fact in batch.facts:
        assert extract_locator_quote(source.content_text, media_type="application/json",
                                     locator=fact.locator) == fact.original_text
    age = next(fact for fact in numbers if fact.raw_value == "51.0")
    context = age.result_context
    assert context.domain == "baseline" and context.category == "baseline"
    assert context.source_unit == "Years" and context.source_param_type == "MEAN"
    assert context.source_dispersion_type == "STANDARD_DEVIATION"
    assert context.group_id == "BG7" and context.arm == "unknown"
    assert context.group_description == "Original regimen."
    assert context.analysis_population == "All randomized participants."
    assert age.normalized_value == "51.0"
    assert {item.parsed_value for item in context.denominator_candidates} == {20}
    assert any(fact.raw_value == "15.00" and fact.result_context.value_role == "dispersion"
               for fact in numbers)
    zero = next(fact for fact in numbers if fact.raw_value == "0")
    assert zero.disclosure_state == "reported_zero" and zero.normalized_value == "0"
    total = next(fact for fact in numbers if fact.raw_value == "30")
    assert total.result_context.group_description == "Total of all reporting groups"
    assert all(fact.result_context.metric != "proportion" for fact in numbers)


def test_array_reorder_never_assigns_product_or_uses_first_denominator() -> None:
    record = _record()
    left = extract_ctgov_baseline_atoms(_capture(record))
    _module(record)["groups"].reverse()
    _module(record)["denoms"][0]["counts"].reverse()
    right = extract_ctgov_baseline_atoms(_capture(record))
    def scope(batch: Any) -> set[tuple[Any, ...]]:
        return {(f.result_context.group_id, f.raw_value, f.result_context.value_role,
                 tuple(c.parsed_value for c in f.result_context.denominator_candidates))
                for f in _numeric(batch)}
    assert scope(left) == scope(right)


@pytest.mark.parametrize("count", [None, "0", "not available", "-1", "NaN", True])
def test_missing_zero_or_bad_group_n_does_not_drop_healthy_measures(count: object) -> None:
    record = _record()
    counts = _module(record)["denoms"][0]["counts"]
    if count is None:
        del counts[1]["value"]
    else:
        counts[1]["value"] = count
    batch = extract_ctgov_baseline_atoms(_capture(record))
    age = next(f for f in _numeric(batch) if f.raw_value == "51.0")
    assert age.normalized_value == "51.0"
    assert any(f.raw_value == "46.7" for f in _numeric(batch))
    if count == "0":
        assert [c.parsed_value for c in age.result_context.denominator_candidates] == [0]
    else:
        assert not age.result_context.denominator_candidates
        assert any("denoms" in issue.source_path for issue in batch.issues)
    assert not any(f.result_context.metric == "proportion" for f in _numeric(batch))


@pytest.mark.parametrize("second", ["20", "21"])
def test_duplicate_n_candidates_remain_visible_and_conflicts_are_scoped(second: str) -> None:
    record = _record()
    _module(record)["denoms"].append({"units": "Participants", "counts": [
        {"groupId": "BG7", "value": second},
    ]})
    batch = extract_ctgov_baseline_atoms(_capture(record))
    age = next(f for f in _numeric(batch) if f.raw_value == "51.0")
    assert [c.parsed_value for c in age.result_context.denominator_candidates] == [20, int(second)]
    assert sum(f.result_context.value_role == "denominator" for f in _numeric(batch)) == 4
    assert bool([i for i in batch.issues if i.status == "conflicting"]) == (second == "21")


def test_invalid_measure_is_local_and_raw_text_retained_without_faking_zero() -> None:
    record = _record()
    measurement = _module(record)["measures"][0]["classes"][0]["categories"][0]["measurements"][0]
    measurement["value"] = "not numeric"
    measurement["spread"] = None
    batch = extract_ctgov_baseline_atoms(_capture(record))
    bad = next(f for f in _numeric(batch) if f.raw_value == "not numeric")
    assert bad.normalized_value is None and bad.disclosure_state != "reported_zero"
    assert any(f.raw_value == "46.7" for f in _numeric(batch))
    assert {issue.status for issue in batch.issues} >= {"missing", "parse_failure"}


def test_unknown_and_duplicate_group_do_not_inherit_other_group_metadata() -> None:
    record = _record()
    module = _module(record)
    module["groups"].append(deepcopy(module["groups"][0]))
    module["measures"][0]["classes"][0]["categories"][0]["measurements"].append(
        {"groupId": "NO_GROUP", "value": "60", "spread": "12"}
    )
    batch = extract_ctgov_baseline_atoms(_capture(record))
    unknown = next(f for f in _numeric(batch) if f.raw_value == "60")
    duplicate = next(f for f in _numeric(batch) if f.raw_value == "51.0")
    assert unknown.result_context.group_title == ""
    assert duplicate.result_context.group_title == ""
    assert unknown.result_context.arm == duplicate.result_context.arm == "unknown"
    assert any(i.status == "conflicting" and "groups" in i.source_path for i in batch.issues)
    assert any(i.status == "missing" and "groupId" in i.source_path for i in batch.issues)


def test_absent_module_is_not_zero_and_identity_mismatch_fails_closed() -> None:
    record = _record()
    del record["resultsSection"]["baselineCharacteristicsModule"]
    batch = extract_ctgov_baseline_atoms(_capture(record))
    assert not batch.facts and len(batch.issues) == 1
    assert batch.issues[0].status == "missing"
    record["protocolSection"]["identificationModule"]["nctId"] = "NCT99999999"
    with pytest.raises(ResearchPackageError, match="身份"):
        extract_ctgov_baseline_atoms(_capture(record))


def test_identical_values_in_distinct_measure_instances_never_collapse() -> None:
    record = _record()
    module = _module(record)
    module["measures"].append(deepcopy(module["measures"][0]))
    batch = extract_ctgov_baseline_atoms(_capture(record))
    means = [f for f in _numeric(batch) if f.raw_value == "51.0"]
    assert len(means) == 2 and len({f.fact_id for f in means}) == 2
    assert len({f.result_context.source_measure_path for f in means}) == 2


def test_source_whitespace_is_not_stripped_from_reextractable_original_quote() -> None:
    record = _record()
    _module(record)["populationDescription"] = "  All randomized participants.\n"
    source = _capture(record)
    batch = extract_ctgov_baseline_atoms(source)
    population = next(f for f in batch.facts
                      if f.locator.field_path.endswith("populationDescription"))
    assert population.original_text == "  All randomized participants.\n"
    assert population.original_text == extract_locator_quote(
        source.content_text, media_type="application/json", locator=population.locator
    )


@pytest.mark.parametrize("field", ["title", "paramType", "unitOfMeasure"])
def test_malformed_measure_metadata_is_scoped_not_whole_module_failure(field: str) -> None:
    record = _record()
    _module(record)["measures"][0][field] = ["malformed"]
    batch = extract_ctgov_baseline_atoms(_capture(record))
    assert any(f.raw_value == "5" for f in _numeric(batch))
    assert any(i.status == "parse_failure" and i.source_path.endswith(field) for i in batch.issues)
    assert any(f.raw_value == "51.0" for f in _numeric(batch))


def test_measure_specific_n_is_not_replaced_by_global_or_array_order() -> None:
    record = _record()
    _module(record)["measures"][0]["denoms"] = [{"units": "Participants", "counts": [
        {"groupId": "BG7", "value": "18"}, {"groupId": "BG1", "value": "9"},
    ]}]
    batch = extract_ctgov_baseline_atoms(_capture(record))
    age = next(f for f in _numeric(batch) if f.raw_value == "51.0")
    sex = next(f for f in _numeric(batch) if f.raw_value == "5")
    assert [c.parsed_value for c in age.result_context.denominator_candidates] == [18]
    assert [c.parsed_value for c in sex.result_context.denominator_candidates] == [10]
    assert any(".measures[0].denoms[0]" in f.locator.field_path for f in _numeric(batch))


def test_count_exceeding_own_n_is_a_conflict_not_legal_proportion() -> None:
    record = _record()
    _module(record)["measures"][1]["classes"][0]["categories"][0]["measurements"][1]["value"] = "11"
    batch = extract_ctgov_baseline_atoms(_capture(record))
    assert any(f.raw_value == "11" for f in _numeric(batch))
    assert any(i.status == "conflicting" and ".measures[1]" in i.source_path for i in batch.issues)
    assert not any(f.result_context.metric == "proportion" for f in _numeric(batch))
