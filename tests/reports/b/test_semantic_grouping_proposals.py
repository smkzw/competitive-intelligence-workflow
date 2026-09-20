"""Bound model proposals must reach the actual B chart grouping, without losing rows."""

from itertools import permutations

import pytest

from ci_workflow.renderers.portal.report_b import _groups_for_page
from tests.reports.b.test_r13_semantic_grouping import _project_efficacy


def _rows():
    first = _project_efficacy("first", "EASI-75", timepoint=48)
    first.update(
        semantic_direction="higher_is_better", semantic_estimand="treatment_policy",
        semantic_denominator="full_analysis_set", semantic_instrument_or_scale="EASI v1.0",
    )
    second = dict(
        first, row_id="second", trial_id="trial-b", actual_timepoint=50,
        semantic_definition="达到基线EASI改善不少于75%的比例",
        original_definition="达到基线EASI改善不少于75%的比例",
    )
    return first, second


def _proposal(first, second):
    from ci_workflow.reports.b.semantic_grouping import (
        SemanticGroupingProposal,
        semantic_row_digest,
    )

    return SemanticGroupingProposal(
        proposal_id="synthetic-proposal", row_ids=(first["row_id"], second["row_id"]),
        row_digests=(semantic_row_digest(first), semantic_row_digest(second)),
        compatible=True, rationale_zh="同一临床构念，实际时间分别为48与50周。",
        producer_id="synthetic-model", time_window_compatible=True,
    )


def _receipt(first, second):
    from ci_workflow.reports.b.semantic_contract import SemanticAdjudicationReceipt

    return SemanticAdjudicationReceipt(
        adjudication_id="adj-review-1",
        observation_ids=(first["row_id"], second["row_id"]),
        decision="compatible",
        model_id="model-a",
        independent_review_id="reviewer-x",
        independent_context="clean-context-1",
        rationale_zh="两种措辞指向同一临床构念，已经独立上下文复核。",
    )


def _approved(first, second):
    from ci_workflow.reports.b.semantic_grouping import ApprovedSemanticMerge

    return ApprovedSemanticMerge(
        merge_id="merge-review-1",
        proposal=_proposal(first, second),
        receipt=_receipt(first, second),
    )


def test_bound_wording_proposal_reaches_chart_groups() -> None:
    first, second = _rows()
    groups = _groups_for_page(
        "efficacy", [(first, None), (second, None)],
        semantic_proposals=(_proposal(first, second),),
        semantic_adjudications=(_approved(first, second),),
    )
    assert len(groups) == 1
    assert groups[0]["cross_trial"] is True
    assert {row["row_id"] for row in groups[0]["rows"]} == {"first", "second"}
    assert "48" in groups[0]["title_zh"] and "50" in groups[0]["title_zh"]


@pytest.mark.parametrize("change", ["semantic_analysis_set", "value", "source_version_id"])
def test_proposal_rejects_changed_observation(change: str) -> None:
    first, second = _rows()
    proposal = _proposal(first, second)
    second[change] = 99 if change == "value" else "changed"
    with pytest.raises(ValueError, match="摘要"):
        _groups_for_page(
            "efficacy", [(first, None), (second, None)], semantic_proposals=(proposal,),
        )


def test_model_cannot_override_known_hard_conflict() -> None:
    first, second = _rows()
    second["semantic_analysis_set"] = "per_protocol"
    groups = _groups_for_page(
        "efficacy", [(first, None), (second, None)],
        semantic_proposals=(_proposal(first, second),),
    )
    assert len(groups) == 2
    assert all(not group["cross_trial"] for group in groups)


def test_model_cannot_supply_missing_definition_by_copying_other_observation() -> None:
    first, second = _rows()
    first["semantic_definition"] = "not_reported"
    groups = _groups_for_page(
        "efficacy", [(first, None), (second, None)],
        semantic_proposals=(_proposal(first, second),),
    )
    assert len(groups) == 2


def test_pairwise_compatibility_is_not_transitive() -> None:
    first, second = _rows()
    third = dict(second, row_id="third", trial_id="trial-c", actual_timepoint=52,
                 semantic_definition="第三种定义措辞")
    groups = _groups_for_page(
        "efficacy", [(first, None), (second, None), (third, None)],
        semantic_proposals=(_proposal(first, second), _proposal(second, third)),
        semantic_adjudications=(_approved(first, second), _approved(second, third)),
    )
    assert len(groups) == 2
    assert sum(len(group["rows"]) for group in groups) == 3


def test_model_copy_cannot_forge_proposal_acceptance_state() -> None:
    first, second = _rows()
    forged = _proposal(first, second).model_copy(update={"status": "accepted"})
    with pytest.raises(ValueError):
        _groups_for_page("efficacy", [(first, None), (second, None)], semantic_proposals=(forged,))


@pytest.mark.parametrize("page", ["efficacy", "longitudinal-results"])
def test_no_proposal_still_applies_cross_trial_time_guard(page: str) -> None:
    first, _ = _rows()
    second = dict(first, row_id="second", trial_id="trial-b", actual_timepoint=56)
    groups = _groups_for_page(page, [(first, None), (second, None)])
    assert len(groups) == 2
    assert all(not group["cross_trial"] for group in groups)


def test_complete_link_partition_is_input_order_independent() -> None:
    first, second = _rows()
    third = dict(second, row_id="third", trial_id="trial-c", actual_timepoint=52,
                 semantic_definition="第三种定义措辞")
    proposals = (_proposal(first, second), _proposal(second, third))
    partitions = {
        frozenset(frozenset(row["row_id"] for row in group["rows"]) for group in
                  _groups_for_page("efficacy", [(row, None) for row in order],
                                   semantic_proposals=proposals))
        for order in permutations((first, second, third))
    }
    assert len(partitions) == 1


def test_source_locator_change_invalidates_bound_proposal() -> None:
    from ci_workflow.renderers.portal.report_b import (
        _display_trial_name,
        _efficacy_records,
    )
    from tests.browser.test_b_semantic_proposals import proposal_data

    data = proposal_data()
    names = {product.id: product.name for product in data.products}
    trials = {trial.id: _display_trial_name(trial, names[trial.product_id])
              for trial in data.trials}
    before = _efficacy_records(data, names, trials)
    proposal = _proposal(before[0][0], before[1][0])
    data.efficacy_views["facts"][0]["source_locator"] = {
        "document_role": "publication", "page": 99, "table": "Table 1",
    }
    after = _efficacy_records(data, names, trials)
    with pytest.raises(ValueError, match="摘要"):
        _groups_for_page("efficacy", after, semantic_proposals=(proposal,))


def test_detail_projects_full_scientific_partition_without_regrouping() -> None:
    from ci_workflow.renderers.portal.report_b import _project_scientific_groups

    first, second = _rows()
    third = dict(second, row_id="third", trial_id="trial-c", actual_timepoint=52,
                 semantic_definition="第三种定义措辞")
    proposals = (_proposal(first, second), _proposal(second, third))
    approved = (_approved(first, second), _approved(second, third))
    full = _groups_for_page("efficacy", [(row, None) for row in (first, second, third)],
                            semantic_proposals=proposals,
                            semantic_adjudications=approved)
    detail = _project_scientific_groups(full, [(second, None), (third, None)])
    assert {frozenset(row["row_id"] for row in group["rows"]) for group in detail} == {
        frozenset(("second",)), frozenset(("third",)),
    }
    assert {group["scientific_group_id"] for group in detail} == {
        group["scientific_group_id"] for group in full
    }


@pytest.mark.parametrize("page", ["baseline-overview", "disposition-overview",
                                   "efficacy-safety-matrix"])
def test_descriptive_domains_honor_veto_and_reject_positive_adjudication(page: str) -> None:
    from tests.reports.b.test_r13_semantic_grouping import _project_baseline

    first = _project_baseline("a", product_id="product-a", trial_id="trial-a", population="FAS")
    second = _project_baseline("b", product_id="product-b", trial_id="trial-b", population="FAS")
    # 页面按真实数据流为无域记录打标；已标异域记录会被入口拒绝（见护栏测试）。
    def _untagged(row: dict) -> dict:
        return {key: value for key, value in row.items() if key != "_domain"}

    rows = [(_untagged(first), None), (_untagged(second), None)]
    proposal = _proposal(first, second)
    groups = _groups_for_page(
        page, rows,
        semantic_proposals=(proposal.model_copy(update={"compatible": False}),),
    )
    assert len(groups) == 2
    with pytest.raises(ValueError, match="描述性"):
        _groups_for_page(page, rows, semantic_proposals=(proposal,))


def test_projection_rejects_changed_fact_instead_of_returning_previous_value() -> None:
    from ci_workflow.renderers.portal.report_b import _project_scientific_groups

    first, second = _rows()
    groups = _groups_for_page("efficacy", [(first, None), (second, None)],
                             semantic_proposals=(_proposal(first, second),))
    with pytest.raises(ValueError, match="摘要"):
        _project_scientific_groups(groups, [(dict(second, value=99), None)])


def test_duplicate_identity_rejects_conflicting_fact_or_domain() -> None:
    from ci_workflow.renderers.portal.report_b import _dedupe_records

    first, _ = _rows()
    assert len(_dedupe_records([(first, None), (dict(first), None)])) == 1
    for changed in (dict(first, value=99), dict(first, _domain="safety")):
        with pytest.raises(ValueError, match="冲突"):
            _dedupe_records([(first, None), (changed, None)])


def test_full_view_rejects_cross_domain_proposal_before_dispatch() -> None:
    from tests.reports.b.test_r13_semantic_grouping import _project_baseline

    first, _ = _rows()
    second = _project_baseline("baseline-b", product_id="b", trial_id="b", population="FAS")
    with pytest.raises(ValueError, match="跨域"):
        _groups_for_page("product-trial-profiles", [
            (dict(first, _domain="efficacy"), None),
            (dict(second, _domain="baseline"), None),
        ], semantic_proposals=(_proposal(first, second),))


def test_conflicting_identity_fails_before_touching_existing_site(tmp_path) -> None:
    from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
    from tests.browser.test_b_semantic_proposals import proposal_data

    payload = proposal_data().model_dump(mode="json")
    payload["semantic_proposals"] = []
    payload["safety_views"] = {"facts": [dict(
        payload["efficacy_views"]["facts"][0], value=2, original_endpoint="TEAE",
        original_definition="治疗期间不良事件", source_version_id="synthetic-safety-source",
    )]}
    site = tmp_path / "html"
    site.mkdir()
    sentinel = site / "keep.txt"
    sentinel.write_text("existing user artifact", encoding="utf-8")
    with pytest.raises(ValueError, match="冲突"):
        render_report_b_site(ReportBPortalData.model_validate(payload), site)
    assert sentinel.read_text(encoding="utf-8") == "existing user artifact"
    assert list(site.iterdir()) == [sentinel]
