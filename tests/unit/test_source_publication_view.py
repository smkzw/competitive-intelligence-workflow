"""Source publication composite cells route into the existing B views intact.

One production contract family for ``build_source_publication_views``: a
pure adapter that routes only ``composite_count_and_percent`` source contexts
in the efficacy/adverse-events domains into the existing ``efficacy`` and
``safety`` view mappings, one display row per parent fact. The view value is
the independently printed percent token (never recomputed, never a ratio),
the printed count rides along as ``reported_count`` with no denominator, and
product/arm/NCT identities stay unknown. Threshold and footnote cells stay
in-domain but ``unresolved_due_to_route``; every fact outside this bounded
composite adapter is returned verbatim under ``unhandled`` — nothing is
dropped, relabelled or persisted here.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from ci_workflow.application.source_research_service import (
    ResearchFact,
    ResearchResultContext,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.source_clause_context import (
    SourceClauseContext,
    SourceClauseReference,
)
from ci_workflow.reports.b.publication_components import publication_value_components
from ci_workflow.reports.b.source_publication import build_source_publication_views

_CELL_PATH = "/article/body[1]/sec[2]/sec[3]/p[2]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[2]"
_ACTIVE_PATH = _CELL_PATH.replace("td[2]", "td[3]")
_TEAE_PATH = _CELL_PATH.replace("td[2]", "td[4]")
_THRESHOLD_PATH = _CELL_PATH.replace("tr[2]", "tr[3]")
_HEADER_PATH = "/article/body[1]/sec[2]/sec[3]/p[2]/table-wrap[1]/table[1]/thead[1]/tr[2]/th[1]"
_ROW_LABEL_PATH = (
    "/article/body[1]/sec[2]/sec[3]/p[2]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[1]"
)
_VERSIONS = {"pubmed-record-37142763": "srcver:PMC10202800:1"}
_FACT_VERSIONS = {
    f"pubfact:PMC10202800:{path}": f"factver:PMC10202800:{path}:1"
    for path in (_CELL_PATH, _ACTIVE_PATH, _TEAE_PATH, _THRESHOLD_PATH)
}


def _locator(field_path: str) -> EvidenceLocator:
    return EvidenceLocator(
        document_role="original_linked_publication", field_path=field_path,
        url="https://pmc-oa-opendata.example/PMC10202800.1.xml",
    )


def _clause_context(
    column_header: str, *, scope_extra: dict[str, Any] | None = None,
) -> SourceClauseContext:
    scope: dict[str, Any] = {
        "cell_not_split": True,
        "column_header_path": _HEADER_PATH,
        "nct_assignment": "unresolved",
        "primary_for_this_study": True,
        "proposal_role": "primary_endpoint_result",
        "row_label_path": _ROW_LABEL_PATH,
        "study_label": "PRIME",
        "timepoint_token": "week 24",
    }
    scope.update(scope_extra or {})
    return SourceClauseContext(
        label_zh="PRIME 主要终点单元格",
        scope_note_zh="单元格同时写人数和百分数，未拆开，也未用列标题的 n 作分母重算。",
        scientific_scope=scope,
        continuations=(
            SourceClauseReference(
                reference_id=f"ctx:{_ROW_LABEL_PATH}", source_id="pubmed-record-37142763",
                label_zh="行标签", locator=_locator(_ROW_LABEL_PATH),
                original_text=(
                    "WI-NRS improvement (reduction) by ≥4 from baseline to week 24a, n (%)"
                ),
            ),
            SourceClauseReference(
                reference_id=f"ctx:{_HEADER_PATH}", source_id="pubmed-record-37142763",
                label_zh="列标题", locator=_locator(_HEADER_PATH),
                original_text=column_header,
            ),
        ),
    )


def _result_context(**overrides: Any) -> ResearchResultContext:
    values: dict[str, Any] = {
        "result_key": "pubresult:PMC10202800:week24:primary:placebo",
        "category": "outcome", "trial_id": "PRIME",
        "group_id": _HEADER_PATH,
        "group_title": "Placebo n = 76", "arm": "Placebo n = 76",
        "term": "WI-NRS improvement (reduction) by ≥4 from baseline to week 24a, n (%)",
        "endpoint": "WI-NRS improvement (reduction) by ≥4 from baseline to week 24a, n (%)",
        "timepoint": "week 24", "value_role": "reported_measure",
        "source_unit": "n (%)", "domain": "efficacy", "metric": "unresolved",
        "source_measure_path": _CELL_PATH,
        "raw_value_type": "composite_count_and_percent",
        "analysis_population": "full analysis set (source wording, not re-qualified here)",
    }
    values.update(overrides)
    return ResearchResultContext(**values)


def _fact(
    raw_value: str, *,
    fact_id: str | None = None,
    cell_path: str = _CELL_PATH,
    original_text: str | None = None,
    disclosure_state: str = "reported_value",
    with_clause: bool = True,
    scope_extra: dict[str, Any] | None = None,
    **context_overrides: Any,
) -> ResearchFact:
    context = _result_context(source_measure_path=cell_path, **context_overrides)
    values: dict[str, Any] = {
        "fact_id": fact_id or f"pubfact:PMC10202800:{cell_path}",
        "row_ref": f"source:PMC10202800:{cell_path}",
        "entity_id": "pubmed-record-37142763:source-trial-label:PRIME",
        "entity_type": "clinical_trial", "canonical_name": "PRIME",
        "field_id": "efficacy.primary.prime.week24.arm_cell",
        "raw_value": raw_value,
        "normalized_value": None,
        "disclosure_state": disclosure_state,
        "source_id": "pubmed-record-37142763",
        "locator": _locator(cell_path),
        "original_text": original_text if original_text is not None else raw_value,
        "result_context": context,
    }
    if with_clause:
        values["source_clause_context"] = _clause_context(
            context.group_title, scope_extra=scope_extra,
        )
    return ResearchFact(**values)


def _plain_fact(fact_id: str, raw_value: str) -> ResearchFact:
    """A fact outside the composite adapter (no n (%) declaration)."""
    return _fact(
        raw_value, fact_id=fact_id,
        raw_value_type="single_source_token", source_unit="hazard ratio",
    )


def _views(facts: list[ResearchFact]) -> dict[str, Any]:
    return build_source_publication_views(
        facts, source_versions=dict(_VERSIONS), fact_versions=dict(_FACT_VERSIONS),
    )


def test_concrete_percent_cells_route_with_printed_tokens_and_no_denominator() -> None:
    active = _fact(
        "45 (60.0)", cell_path=_ACTIVE_PATH,
        group_id=_HEADER_PATH.replace("th[1]", "th[2]"),
        group_title="Dupilumab 300 mg every 2 weeks n = 75",
        arm="Dupilumab 300 mg every 2 weeks n = 75",
    )
    views = _views([_fact("14 (18.4)"), active])
    assert set(views) == {"efficacy", "safety", "unhandled"}
    assert not views["safety"]["facts"] and not views["unhandled"]
    rows = {row["row_id"]: row for row in views["efficacy"]["facts"]}
    placebo = rows[f"pubfact:PMC10202800:{_CELL_PATH}"]
    assert placebo["source_row_id"] == placebo["row_id"]
    assert placebo["value"] == 18.4 and placebo["unit"] == "%"
    assert placebo["reported_count"] == 14
    assert placebo["numerator"] is None and placebo["denominator"] is None
    assert placebo["statistic_form"] == "proportion"
    assert "18.42" not in json.dumps(placebo, ensure_ascii=False)
    active_row = rows[f"pubfact:PMC10202800:{_ACTIVE_PATH}"]
    assert active_row["value"] == 60.0 and active_row["reported_count"] == 45


def test_safety_teae_cell_keeps_independent_count_and_percent() -> None:
    views = _views([
        _fact(
            "452 (89)", cell_path=_TEAE_PATH,
            category="teae", domain="adverse_events", source_unit="TEAEs, n (%)",
            term="TEAEs", endpoint="TEAEs", timepoint="week 16",
        ),
    ])
    assert not views["efficacy"]["facts"] and not views["unhandled"]
    (row,) = views["safety"]["facts"]
    assert row["value"] == 89.0 and row["unit"] == "%"
    assert row["reported_count"] == 452
    assert row["numerator"] is None and row["denominator"] is None
    assert row["statistic_form"] == "proportion"
    assert row["source_domain"] == "adverse_events"


def test_explicit_zero_preserves_source_disclosure_state() -> None:
    (row,) = _views([_fact("0 (0.0)", disclosure_state="reported_zero")])[
        "efficacy"]["facts"]
    assert row["disclosure_state"] == "reported_zero"
    assert row["value"] == 0.0 and row["reported_count"] == 0
    (row,) = _views([_fact("0 (0)")])["efficacy"]["facts"]
    assert row["disclosure_state"] == "reported_value"
    assert row["value"] == 0.0 and row["reported_count"] == 0


def test_declared_zero_with_nonzero_printed_cell_is_not_a_false_zero() -> None:
    views = _views([_fact("14 (18.4)", disclosure_state="reported_zero")])
    (row,) = views["efficacy"]["facts"]
    assert row["disclosure_state"] == "unresolved_due_to_route"
    assert row["value"] is None and row["reported_count"] is None
    assert row["source_disclosure_state"] == "reported_zero"
    assert row["projection_reason"]


def test_threshold_and_footnote_cells_stay_in_domain_but_unresolved() -> None:
    threshold = _fact(
        "2 (<1)", cell_path=_TEAE_PATH,
        category="teae", domain="adverse_events", source_unit="TEAEs, n (%)",
        term="TEAEs", endpoint="TEAEs", timepoint="week 16",
    )
    footnote = _fact(
        "1 (<1) b", cell_path=_THRESHOLD_PATH,
        category="teae", domain="adverse_events", source_unit="TEAEs, n (%)",
        term="TEAEs", endpoint="TEAEs", timepoint="week 16",
    )
    views = _views([threshold, footnote])
    assert not views["unhandled"] and not views["efficacy"]["facts"]
    rows = {row["raw_value"]: row for row in views["safety"]["facts"]}
    assert set(rows) == {"2 (<1)", "1 (<1) b"}
    for row in rows.values():
        assert row["value"] is None and row["reported_count"] is None
        assert row["unit"] is None and row["statistic_form"] is None
        assert row["numerator"] is None and row["denominator"] is None
        assert row["disclosure_state"] == "unresolved_due_to_route"
        assert row["source_disclosure_state"] == "reported_value"
        assert row["projection_reason"]
        assert row["source_component_projection"]["state"] == "unresolved"


def test_no_product_arm_or_nct_identity_is_invented() -> None:
    (row,) = _views([_fact("14 (18.4)")])["efficacy"]["facts"]
    assert row["product_id"] is None
    assert row["arm_role"] == "unknown"
    assert row["group_assignment_state"] == "unknown"
    assert row["trial_id"] == "pubmed-record-37142763:source-trial-label:PRIME"
    assert row["source_trial_label"] == "PRIME"
    assert row["group_id"] == _HEADER_PATH
    assert row["source_group_title"] == "Placebo n = 76"
    assert row["source_timepoint"] == "week 24"
    assert row["analysis_population"] == (
        "full analysis set (source wording, not re-qualified here)"
    )
    rendered = json.dumps(row, ensure_ascii=False)
    assert "NCT" not in rendered and "NUMBER" not in rendered
    scope = row["source_clause_context"]["scientific_scope"]
    assert scope["nct_assignment"] == "unresolved"
    assert scope["study_label"] == "PRIME"
    assert row["source_result_context"]["source_param_type"] is None


def test_partition_is_total_and_non_composites_stay_unhandled() -> None:
    composite = _fact("14 (18.4)")
    teae = _fact(
        "452 (89)", cell_path=_TEAE_PATH,
        category="teae", domain="adverse_events", source_unit="TEAEs, n (%)",
        term="TEAEs", endpoint="TEAEs", timepoint="week 16",
    )
    threshold = _fact(
        "2 (<1)", cell_path=_THRESHOLD_PATH,
        category="teae", domain="adverse_events", source_unit="TEAEs, n (%)",
        term="TEAEs", endpoint="TEAEs", timepoint="week 16",
    )
    plain = _plain_fact("pubfact:PMC10202800:plain-hr", "0.78 (0.62-0.97)")
    no_context = ResearchFact.model_validate({
        **_fact("14 (18.4)", fact_id="pubfact:PMC10202800:no-ctx").model_dump(
            mode="json", exclude={"result_context"},
        ),
    })
    other_domain = _fact(
        "1 (50.0)", fact_id="pubfact:PMC10202800:other-domain",
        domain="unresolved",
    )
    facts = [composite, teae, threshold, plain, no_context, other_domain]
    views = _views(facts)
    assert [row["row_id"] for row in views["efficacy"]["facts"]] == [composite.fact_id]
    assert [row["row_id"] for row in views["safety"]["facts"]] == [
        teae.fact_id, threshold.fact_id,
    ]
    by_id = {item.fact_id: item for item in views["unhandled"]}
    assert set(by_id) == {
        "pubfact:PMC10202800:no-ctx", "pubfact:PMC10202800:other-domain",
        "pubfact:PMC10202800:plain-hr",
    }
    assert by_id[plain.fact_id] is plain
    assert by_id[no_context.fact_id] is no_context
    assert by_id[other_domain.fact_id] is other_domain
    seen = (
        [row["row_id"] for row in views["efficacy"]["facts"]]
        + [row["row_id"] for row in views["safety"]["facts"]]
        + sorted(by_id)
    )
    assert sorted(seen) == sorted(item.fact_id for item in facts)


def test_missing_or_blank_version_ids_fail_closed() -> None:
    with pytest.raises(ValueError, match="pubmed-record-37142763"):
        build_source_publication_views(
            [_fact("14 (18.4)")], source_versions={}, fact_versions=_FACT_VERSIONS,
        )
    with pytest.raises(ValueError, match="pubfact:PMC10202800"):
        build_source_publication_views(
            [_fact("14 (18.4)")], source_versions=_VERSIONS,
            fact_versions={"pubfact:PMC10202800:/other": "factver:x"},
        )
    with pytest.raises(ValueError, match="事实"):
        build_source_publication_views(
            [_fact("14 (18.4)")], source_versions=_VERSIONS,
            fact_versions={f"pubfact:PMC10202800:{_CELL_PATH}": "  "},
        )
    # Facts outside the composite adapter never demand version closures.
    outside = build_source_publication_views(
        [_plain_fact("pubfact:PMC10202800:plain-hr", "0.78")],
        source_versions={}, fact_versions={},
    )
    assert [item.fact_id for item in outside["unhandled"]] == (
        ["pubfact:PMC10202800:plain-hr"]
    )


def test_duplicate_fact_ids_raise_instead_of_first_wins() -> None:
    with pytest.raises(ValueError, match="重复"):
        _views([_fact("14 (18.4)"), _fact("45 (60.0)")])


def test_conflicting_predeclared_scope_identity_is_rejected() -> None:
    stale_version = _fact(
        "14 (18.4)",
        scope_extra={"source_version_id": "srcver:PMC10202800:9"},
    )
    with pytest.raises(ValueError, match="source_version_id"):
        _views([stale_version])
    stale_path = _fact(
        "14 (18.4)",
        scope_extra={"source_measure_path": "/article/body[1]/other/cell"},
    )
    with pytest.raises(ValueError, match="source_measure_path"):
        _views([stale_path])
    matched = _views([_fact(
        "14 (18.4)",
        scope_extra={
            "source_version_id": "srcver:PMC10202800:1",
            "source_measure_path": _CELL_PATH,
        },
    )])
    scope = matched["efficacy"]["facts"][0]["source_clause_context"]["scientific_scope"]
    assert scope["source_version_id"] == "srcver:PMC10202800:1"
    assert scope["source_measure_path"] == _CELL_PATH


@pytest.mark.parametrize("key", ["source_version_id", "source_measure_path"])
@pytest.mark.parametrize("value", [None, ""])
def test_explicit_empty_scope_identity_is_not_treated_as_an_absent_key(key, value) -> None:
    with pytest.raises(ValueError, match=key):
        _views([_fact("14 (18.4)", scope_extra={key: value})])


def test_display_scope_copy_adds_only_version_and_measure_path() -> None:
    fact = _fact("14 (18.4)")
    before = fact.model_dump(mode="json")
    (row,) = _views([fact])["efficacy"]["facts"]
    clause = row["source_clause_context"]
    original_clause = before["source_clause_context"]
    assert set(clause) == set(original_clause)
    assert clause["continuations"] == original_clause["continuations"]
    assert clause["relations"] == original_clause["relations"]
    assert clause["label_zh"] == original_clause["label_zh"]
    assert clause["scope_note_zh"] == original_clause["scope_note_zh"]
    scope = clause["scientific_scope"]
    assert set(scope) == set(original_clause["scientific_scope"]) | {
        "source_version_id", "source_measure_path",
    }
    assert scope["source_version_id"] == "srcver:PMC10202800:1"
    assert scope["source_measure_path"] == _CELL_PATH
    for key, value in original_clause["scientific_scope"].items():
        assert scope[key] == value
    assert fact.model_dump(mode="json") == before
    assert "source_version_id" not in fact.source_clause_context.scientific_scope


def test_source_payloads_are_retained_verbatim_and_inputs_immutable() -> None:
    fact = _fact("14 (18.4)")
    context = fact.result_context
    assert context is not None
    source_versions = dict(_VERSIONS)
    fact_versions = dict(_FACT_VERSIONS)
    fact_before = fact.model_dump(mode="json")
    mappings_before = (copy.deepcopy(source_versions), copy.deepcopy(fact_versions))
    (row,) = _views([fact])["efficacy"]["facts"]
    assert row["source_fact"] == fact_before
    assert row["source_result_context"] == context.model_dump(mode="json")
    assert row["source_component_projection"] == (
        publication_value_components(fact)["projection"]
    )
    assert row["source_component_projection"]["components"][1] == {
        "kind": "percent", "raw_token": "18.4",
        "token_span": [4, 8], "value": 18.4, "unit": "%",
    }
    assert row["source_locator"] == fact.locator.model_dump(mode="json")
    assert row["source_id"] == fact.source_id
    assert row["source_value_role"] == "reported_measure"
    assert row["source_domain"] == "efficacy"
    assert row["source_metric"] == "unresolved"
    assert row["raw_value"] == "14 (18.4)"
    assert row["source_text"] == "14 (18.4)"
    assert row["source_fact_version_id"] == f"factver:PMC10202800:{_CELL_PATH}:1"
    assert row["source_version_id"] == "srcver:PMC10202800:1"
    assert fact.model_dump(mode="json") == fact_before
    assert (copy.deepcopy(source_versions), copy.deepcopy(fact_versions)) == mappings_before


def test_ordinary_renderer_retains_complete_measurement_axes_without_null_override() -> None:
    from ci_workflow.renderers.portal import report_b

    fact = _fact("14 (18.4)")
    context = fact.result_context
    source = _views([fact])["efficacy"]["facts"][0]
    assert "source_param_type" not in source
    assert source["source_measure_path"] == context.source_measure_path
    assert source["source_measure_definition"] == context.endpoint
    assert source["source_analysis_population"] == context.analysis_population
    assert source["endpoint"] == context.endpoint
    assert source["timepoint"] == context.timepoint
    assert not source.get("difference_labels_zh")
    row = report_b._project_record(source, domain="efficacy", names={}, trial_names={},
                                   fallback=fact.fact_id)
    assert row["statistical_form_family"] == "proportion"
    assert row["value"] == 18.4 and row["reported_count"] == 14
    assert row["source_measure_path"] == context.source_measure_path
    assert row["source_measure_definition"] == context.endpoint
    assert row["source_fact"] == fact.model_dump(mode="json")
    assert row["source_result_context"] == context.model_dump(mode="json")
    assert row["renderable"] is False  # no fabricated product assignment


def test_explicit_source_statistic_is_retained_but_missing_is_omitted() -> None:
    source = _views([_fact("14 (18.4)", source_param_type="NUMBER")])["efficacy"]["facts"][0]
    assert source["source_param_type"] == "NUMBER"
    source = _views([_fact("14 (18.4)")])["efficacy"]["facts"][0]
    assert "source_param_type" not in source
    assert source["source_fact"]["result_context"]["source_param_type"] is None


def test_order_independence_and_json_roundtrip() -> None:
    placebo = _fact("14 (18.4)")
    active = _fact(
        "45 (60.0)", cell_path=_ACTIVE_PATH,
        group_id=_HEADER_PATH.replace("th[1]", "th[2]"),
        group_title="Dupilumab 300 mg every 2 weeks n = 75",
        arm="Dupilumab 300 mg every 2 weeks n = 75",
    )
    teae = _fact(
        "452 (89)", cell_path=_TEAE_PATH,
        category="teae", domain="adverse_events", source_unit="TEAEs, n (%)",
        term="TEAEs", endpoint="TEAEs", timepoint="week 16",
    )
    plain = _plain_fact("pubfact:PMC10202800:plain-hr", "0.78")
    forward = _views([placebo, active, teae, plain])
    backward = _views([plain, teae, active, placebo])
    assert forward == backward
    for view_name in ("efficacy", "safety"):
        restored = json.loads(json.dumps(forward[view_name], ensure_ascii=False))
        assert restored == json.loads(json.dumps(
            {"facts": list(forward[view_name]["facts"])}, ensure_ascii=False,
        ))
    assert [item.fact_id for item in forward["unhandled"]] == (
        ["pubfact:PMC10202800:plain-hr"]
    )
