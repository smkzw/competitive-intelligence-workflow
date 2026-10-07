"""Display buckets must not veto an otherwise proven shared clinical frame."""

from copy import deepcopy

import pytest

from ci_workflow.reports.b.semantic_grouping import proposed_semantic_buckets


def _equivalent_rows() -> tuple[dict, dict]:
    left = {
        "row_id": "first", "trial_id": "trial-a", "product_id": "product-a",
        "clinical_concept": "easi75_response", "semantic_definition": "EASI改善不少于75%",
        "semantic_direction": "higher_is_better", "unit": "%",
        "semantic_estimand": "treatment_policy", "semantic_denominator": "full_analysis_set",
        "semantic_analysis_set": "FAS", "semantic_analysis_form": "response_rate",
        "semantic_instrument_or_scale": "EASI v1.0",
        "actual_timepoint": 48, "actual_timepoint_unit": "week",
    }
    right = dict(left, row_id="second", trial_id="trial-b", product_id="product-b",
                 actual_timepoint=50)
    return left, right


def test_native_equivalence_can_cross_display_bucket_without_per_pair_approval() -> None:
    left, right = _equivalent_rows()
    before = deepcopy((left, right))
    groups = proposed_semantic_buckets((((left, None),), ((right, None),)), ())
    assert len(groups) == 1
    assert {row["row_id"] for row, _ in groups[0]} == {"first", "second"}
    assert (left, right) == before


@pytest.mark.parametrize("field", [
    "semantic_analysis_set", "semantic_direction", "semantic_estimand",
    "semantic_denominator", "semantic_instrument_or_scale", "unit",
])
def test_display_independence_never_relaxes_scientific_hard_axes(field: str) -> None:
    left, right = _equivalent_rows()
    right[field] = "different"
    groups = proposed_semantic_buckets((((left, None),), ((right, None),)), ())
    assert len(groups) == 2
    assert sum(len(group) for group in groups) == 2


def test_unknown_definition_stays_reachable_but_not_equivalent() -> None:
    left, right = _equivalent_rows()
    right["semantic_definition"] = "unknown"
    groups = proposed_semantic_buckets((((left, None),), ((right, None),)), ())
    assert len(groups) == 2


def test_approximate_time_compatibility_is_not_transitive() -> None:
    left, right = _equivalent_rows()
    third = dict(right, row_id="third", trial_id="trial-c", actual_timepoint=52)
    groups = proposed_semantic_buckets(
        (((left, None),), ((right, None),), ((third, None),)), (),
    )
    assert sorted(len(group) for group in groups) == [1, 2]


def test_descriptive_buckets_do_not_claim_clinical_equivalence() -> None:
    left, right = _equivalent_rows()
    groups = proposed_semantic_buckets(
        (((left, None),), ((right, None),)), (), descriptive_only=True,
    )
    assert len(groups) == 2


@pytest.mark.parametrize("marker", [
    "not available", "N.A.", "n.a.", "not reported.", "TBD", "待核", "未明确",
    "未公开披露", "未知。", "未 知", "用户清除，待重新核实",
])
def test_unknown_spellings_never_license_a_shared_definition(marker: str) -> None:
    left, right = _equivalent_rows()
    left["semantic_definition"] = right["semantic_definition"] = marker
    assert len(proposed_semantic_buckets((((left, None), (right, None)),), ())) == 2


def test_same_trial_does_not_bypass_numeric_time_tolerance() -> None:
    left, right = _equivalent_rows()
    right.update(trial_id=left["trial_id"], product_id=left["product_id"], actual_timepoint=52)
    assert len(proposed_semantic_buckets((((left, None), (right, None)),), ())) == 2


def test_time_clique_does_not_change_when_source_row_ids_are_renamed() -> None:
    def frames(ids: tuple[str, ...]) -> set[tuple[int, ...]]:
        base, _ = _equivalent_rows()
        rows = [dict(base, row_id=row_id, trial_id=f"trial-{time}", actual_timepoint=time)
                for row_id, time in zip(ids, (48, 50, 52), strict=True)]
        return {tuple(sorted(row["actual_timepoint"] for row, _ in group))
                for group in proposed_semantic_buckets(tuple(((row, None),) for row in rows), ())}
    assert frames(("a", "b", "c")) == frames(("c", "b", "a"))


@pytest.mark.parametrize("source_domain", ["immunogenicity", "pk_pd", "biomarker", "unknown"])
def test_page_domain_stamp_cannot_override_explicit_source_domain(source_domain: str) -> None:
    left, right = _equivalent_rows()
    left.update(_domain="efficacy", source_domain="efficacy")
    right.update(_domain="efficacy", source_domain=source_domain)
    assert len(proposed_semantic_buckets((((left, None), (right, None)),), ())) == 2
