"""Exact reported n (%) publication cells project to source-preserving components.

The projection helper may only split a cell the source itself declares as an
n (%) composite (``raw_value_type=composite_count_and_percent`` +
``value_role=reported_measure`` + explicit ``n (%)`` source unit). The
percentage is the one printed in the cell — never recomputed from a column
header N — and the result carries raw token spans so audit can prove both
components. Everything else stays original/raw/unresolved.
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

_CELL_PATH = "/article/body[1]/sec[2]/sec[3]/p[2]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[2]"
_HEADER_PATH = "/article/body[1]/sec[2]/sec[3]/p[2]/table-wrap[1]/table[1]/thead[1]/tr[2]/th[1]"
_ROW_LABEL_PATH = (
    "/article/body[1]/sec[2]/sec[3]/p[2]/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[1]"
)


def _locator(field_path: str) -> EvidenceLocator:
    return EvidenceLocator(
        document_role="original_linked_publication", field_path=field_path,
        url="https://pmc-oa-opendata.example/PMC10202800.1.xml",
    )


def _clause_context(column_header: str) -> SourceClauseContext:
    return SourceClauseContext(
        label_zh="PRIME 主要终点单元格",
        scope_note_zh="单元格同时写人数和百分数，未拆开，也未用列标题的 n 作分母重算。",
        scientific_scope={
            "cell_not_split": True,
            "column_header_path": _HEADER_PATH,
            "nct_assignment": "unresolved",
            "primary_for_this_study": True,
            "proposal_role": "primary_endpoint_result",
            "row_label_path": _ROW_LABEL_PATH,
            "study_label": "PRIME",
            "timepoint_token": "week 24",
        },
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
    original_text: str | None = None,
    disclosure_state: str = "reported_value",
    normalized_value: str | None = None,
    result_context: ResearchResultContext | None | Ellipsis = ...,
    with_clause: bool = True,
    column_header: str = "Placebo n = 76",
    **overrides: Any,
) -> ResearchFact:
    values: dict[str, Any] = {
        "fact_id": f"pubfact:PMC10202800:{_CELL_PATH}",
        "row_ref": f"source:PMC10202800:{_CELL_PATH}",
        "entity_id": "pubmed-record-37142763:source-trial-label:PRIME",
        "entity_type": "clinical_trial", "canonical_name": "PRIME",
        "field_id": "efficacy.primary.prime.week24.arm_cell",
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "disclosure_state": disclosure_state,
        "source_id": "pubmed-record-37142763",
        "locator": _locator(_CELL_PATH),
        "original_text": original_text if original_text is not None else raw_value,
    }
    if result_context is not ...:
        values["result_context"] = result_context
    else:
        values["result_context"] = _result_context()
    if with_clause:
        values["source_clause_context"] = _clause_context(column_header)
    values.update(overrides)
    return ResearchFact(**values)


_PROJECTION_KEYS = {"state", "reason", "span_basis", "components"}
_COMPONENT_KEYS = {"kind", "raw_token", "token_span", "value", "unit"}


def _projection(fact: ResearchFact) -> dict[str, Any]:
    result = publication_value_components(fact)
    assert set(result) == set(fact.model_dump(mode="json")) | {"projection"}
    projection = result["projection"]
    assert set(projection) == _PROJECTION_KEYS
    assert projection["span_basis"] == "original_text"
    for component in projection["components"]:
        assert set(component) == _COMPONENT_KEYS
        start, end = component["token_span"]
        assert fact.original_text[start:end] == component["raw_token"]
    if projection["state"] == "projected":
        assert projection["reason"] is None and len(projection["components"]) == 2
        assert [item["kind"] for item in projection["components"]] == ["count", "percent"]
    else:
        assert projection["state"] == "unresolved"
        assert projection["reason"]
        assert projection["components"] == ()
    return projection


def test_real_prime_week24_cells_project_both_printed_components() -> None:
    placebo = _projection(_fact("14 (18.4)"))
    active = _projection(_fact(
        "45 (60.0)",
        result_context=_result_context(
            group_id=_HEADER_PATH.replace("th[1]", "th[2]"),
            group_title="Dupilumab 300 mg every 2 weeks n = 75",
            arm="Dupilumab 300 mg every 2 weeks n = 75",
            source_measure_path=_CELL_PATH.replace("td[2]", "td[3]"),
        ),
        column_header="Dupilumab 300 mg every 2 weeks n = 75",
    ))
    assert [(item["raw_token"], item["value"], item["unit"])
            for item in placebo["components"]] == [
        ("14", 14, "n"), ("18.4", 18.4, "%"),
    ]
    assert [(item["raw_token"], item["value"], item["unit"])
            for item in active["components"]] == [
        ("45", 45, "n"), ("60.0", 60.0, "%"),
    ]
    assert placebo["components"][0]["token_span"] == [0, 2]
    assert placebo["components"][1]["token_span"] == [4, 8]


def test_reported_percent_is_never_recomputed_from_header_n() -> None:
    # Header says n = 76 while the cell says 14 (18.4); 100*14/76 = 18.42…,
    # so any recomputation would visibly differ from the printed 18.4.
    fact = _fact("14 (18.4)")
    projection = _projection(fact)
    assert projection["components"][1]["value"] == 18.4
    assert projection["components"][1]["raw_token"] == "18.4"
    projection_json = json.dumps(projection)
    assert "18.42" not in projection_json
    assert "denominator" not in projection_json and "arm" not in projection_json


def test_prefixed_unit_and_integer_percent_cell_projects() -> None:
    fact = _fact(
        "452 (89)",
        result_context=_result_context(
            category="teae", source_unit="TEAEs, n (%)",
            term="TEAEs", endpoint="TEAEs", timepoint="week 16",
        ),
    )
    projection = _projection(fact)
    assert [(item["raw_token"], item["value"], item["unit"])
            for item in projection["components"]] == [("452", 452, "n"), ("89", 89.0, "%")]


@pytest.mark.parametrize(("raw_value", "state"), [
    ("0 (0.0)", "reported_zero"), ("0 (0.0)", "reported_value"), ("0 (0)", "reported_zero"),
])
def test_explicit_zero_cell_is_valid(raw_value: str, state: str) -> None:
    projection = _projection(_fact(raw_value, disclosure_state=state))
    assert projection["state"] == "projected"
    assert [(item["value"], item["unit"]) for item in projection["components"]] == [
        (0, "n"), (0.0, "%"),
    ]


@pytest.mark.parametrize("raw_value", ["1 (<1)", "2 (<1)"])
def test_threshold_percent_stays_unresolved_with_original_payload(raw_value: str) -> None:
    fact = _fact(raw_value)
    projection = _projection(fact)
    assert projection["state"] == "unresolved"
    assert "百分数" in projection["reason"]
    assert projection["components"] == ()
    # The original payload is retained verbatim next to the unresolved state.
    result = publication_value_components(fact)
    assert result["raw_value"] == raw_value
    assert result["original_text"] == raw_value
    assert result["result_context"]["raw_value_type"] == "composite_count_and_percent"


def test_trailing_footnote_marker_stays_unresolved_even_with_valid_numbers() -> None:
    projection = _projection(_fact("1 (<1) b"))
    assert projection["state"] == "unresolved"
    projection = _projection(_fact("14 (18.4) a"))
    assert projection["state"] == "unresolved"
    assert "尾注" in projection["reason"] or "标记" in projection["reason"]


@pytest.mark.parametrize("raw_value", [
    "12.3 (4.5)",      # mean (SD) shape: count position is not an integer n
    "1.2 (0.8-1.9)",   # estimate (CI) shape
    "5 (nan)", "5 (inf)",
    "14 (18.4", "(18.4)", "14 18.4", "14 (18.4)(5)", "14 ( )",
])
def test_arbitrary_or_malformed_parenthesized_pairs_stay_unresolved(raw_value: str) -> None:
    assert _projection(_fact(raw_value))["state"] == "unresolved"


def test_mean_sd_unit_or_type_is_never_labelled_n_percent() -> None:
    # Explicit mean (SD) unit/type: the composite guard refuses before the text.
    fact = _fact(
        "12.3 (4.5)",
        result_context=_result_context(
            source_unit="体重 (kg), mean (SD)", raw_value_type="mean_and_sd",
        ),
    )
    projection = _projection(fact)
    assert projection["state"] == "unresolved"
    assert projection["components"] == ()
    # Decimal "count" with an n (%) declaration still fails the integer-n grammar.
    assert _projection(_fact("12.3 (4.5)"))["state"] == "unresolved"


@pytest.mark.parametrize(("overrides", "fragment"), [
    ({"result_context": None}, "结果上下文"),
    ({"result_context": _result_context(value_role="participant_count")}, "数值角色"),
    ({"result_context": _result_context(raw_value_type=None)}, "原始值形式"),
    ({"result_context": _result_context(raw_value_type="single_source_token")}, "原始值形式"),
    ({"result_context": _result_context(source_unit="percent of participants")}, "来源单位"),
    ({"result_context": _result_context(source_unit="百分比")}, "来源单位"),
    ({"result_context": _result_context(source_unit="(%)")}, "来源单位"),
])
def test_missing_or_unknown_type_role_unit_stays_unresolved(
    overrides: dict[str, Any], fragment: str,
) -> None:
    fact = _fact("14 (18.4)", **overrides)
    projection = _projection(fact)
    assert projection["state"] == "unresolved"
    assert fragment in projection["reason"]
    assert projection["components"] == ()


@pytest.mark.parametrize("disclosure_state", [
    "conflicting", "not_reported", "below_reporting_threshold",
    "not_publicly_disclosed", "not_applicable", "unresolved_due_to_route",
])
def test_unreported_or_conflicting_disclosure_states_stay_unresolved(
    disclosure_state: str,
) -> None:
    projection = _projection(_fact("14 (18.4)", disclosure_state=disclosure_state))
    assert projection["state"] == "unresolved"


def test_conflicting_raw_value_against_bound_quote_stays_unresolved() -> None:
    fact = _fact("14 (18.4)", original_text="14 (18.3)")
    projection = _projection(fact)
    assert projection["state"] == "unresolved"
    assert "冲突" in projection["reason"]
    # Benign whitespace differences are not conflicts; spans stay exact.
    padded = _projection(_fact("14 (18.4)", original_text=" 14 (18.4) "))
    assert padded["state"] == "projected"
    assert padded["components"][0]["token_span"] == [1, 3]


@pytest.mark.parametrize("raw_value", ["50 (120.5)", "-5 (18.4)", "45 (60.0%)"])
def test_out_of_range_or_non_numeric_token_stays_unresolved(raw_value: str) -> None:
    assert _projection(_fact(raw_value))["state"] == "unresolved"


def test_result_identity_is_exact_payload_and_fact_is_unchanged() -> None:
    fact = _fact("14 (18.4)", normalized_value="sentinel-not-touched")
    before = copy.deepcopy(fact.model_dump(mode="json"))
    result = publication_value_components(fact)
    after = fact.model_dump(mode="json")
    assert before == after
    assert result == {**after, "projection": result["projection"]}
    assert result["normalized_value"] == "sentinel-not-touched"
    assert result["fact_id"] == fact.fact_id and result["source_id"] == fact.source_id
    assert result["locator"] == before["locator"]
    assert result["source_clause_context"] == before["source_clause_context"]
    assert result["result_context"] == before["result_context"]
    assert result["source_clause_context"]["scientific_scope"]["cell_not_split"] is True
    assert result["result_context"]["group_title"] == "Placebo n = 76"
    assert result["source_clause_context"]["continuations"][1]["original_text"] == (
        "Placebo n = 76"
    )
    assert result["projection"]["state"] == "projected"
    # The whole returned tree is plain JSON data for downstream consumers.
    json.dumps(result, ensure_ascii=False)


def test_missing_clause_context_still_projects_exact_cell() -> None:
    # The clause context is preserved identity, not a projection precondition.
    fact = _fact("45 (60.0)", with_clause=False)
    result = publication_value_components(fact)
    assert "source_clause_context" not in result
    assert result["projection"]["state"] == "projected"
    assert [(item["value"], item["unit"]) for item in result["projection"]["components"]] == [
        (45, "n"), (60.0, "%"),
    ]
