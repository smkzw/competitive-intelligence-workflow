"""Per-visit N uses its source scope, never the overall N as a fallback.

Production parser and ordinary payload builder, including a frozen real record.
No historical fixture or accepted source is rewritten by these checks.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.source_research_service import (
    ResearchPackageError,
    _iter_outcome_results,
    bind_ctgov_outcome_to_a_row,
    extract_ctgov_atomic_results,
)
from ci_workflow.renderers.portal.report_a import EfficacyRow
from tests.integration.test_r24_a_builder_contract import _build, _study
from tests.integration.test_r24_source_measure_regressions import _parse, _record
from tests.integration.test_w07_ctgov_capture_bridge import _reported_count_source


def _denoms(*values: tuple[str, object]) -> list[dict[str, Any]]:
    return [{"units": "Participants", "counts": [
        {"groupId": group, "value": value} for group, value in values
    ]}]


def _scoped() -> dict[str, Any]:
    record = _record([("OG1", "3"), ("OG2", "4")],
                     [("OG1", "100", "Participants"), ("OG2", "120", "Participants")])
    measure = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]
    first = measure["classes"][0]
    first["title"] = "Week 4"
    first["denoms"] = _denoms(("OG1", "10"), ("OG2", "20"))
    second = deepcopy(first)
    second["title"] = "Week 8"
    second["denoms"] = _denoms(("OG1", "15"), ("OG2", "25"))
    measure["classes"].append(second)
    return record


def test_visits_resolve_class_denominators_and_exact_source_paths() -> None:
    results, issues = _parse(_scoped())
    assert not issues
    assert [r.denominator for r in results] == [10, 20, 15, 25]
    assert [r.value for r in results] == [30, 20, 20, 16]
    assert all(".classes[" in r.denominator_path for r in results)
    assert all(r.denominator_candidates[0].value_path == r.denominator_path for r in results)


@pytest.mark.parametrize("local", [[], _denoms(("OG2", "20")),
    _denoms(("OG1", None), ("OG2", "20")),
    _denoms(("OG1", "10"), ("OG1", "12"), ("OG2", "20")),
    _denoms(("OG1", "10"), ("OG1", "bad"), ("OG2", "20"))])
def test_local_gap_or_conflict_never_borrows_overall_n_or_drops_next_visit(
    local: list[dict[str, Any]],
) -> None:
    for ordering in (local, list(reversed(local))):
        record = _scoped()
        record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
            "classes"][0]["denoms"] = ordering
        results, issues = _parse(record)
        assert results[0].numerator == 3
        assert results[0].denominator is None
        assert results[0].value == 3
        assert [r.denominator for r in results[2:]] == [15, 25]
        assert issues and all("classes[0]" in issue.source_path for issue in issues)


def test_category_scope_and_explicit_zero_keep_raw_counts_without_rate() -> None:
    record = _scoped()
    category = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0][
        "classes"][0]["categories"][0]
    category["denoms"] = _denoms(("OG1", "0"), ("OG2", "8"))
    category["measurements"][0]["value"] = "0"
    results, issues = _parse(record)
    assert (results[0].numerator, results[0].denominator, results[0].value,
            results[0].unit) == (0, 0, 0, "人")
    assert results[1].denominator == 8
    assert ".categories[0].denoms[0]" in results[0].denominator_path
    assert any("0/0" in issue.reason_zh for issue in issues)


def test_current_binding_rejects_old_overall_n_without_overwriting_source(tmp_path: Path) -> None:
    source = _reported_count_source(tmp_path, unit="Score", classes=[{
        "title": "Week 26", "denoms": _denoms(("OG1", "10")),
        "categories": [{"measurements": [{"groupId": "OG1", "value": "30"}]}],
    }])
    atoms, issues = extract_ctgov_atomic_results(source)
    assert len(atoms) == 1 and not issues
    row = EfficacyRow(row_id="direct-score", product_id="studydrug", trial_id="nct02277743",
        endpoint="Participants With Response", arm="Drug 200 mg", group_id="OG1",
        unit="Score", population="登记结果人群", timepoint="Week 26", value=30, denominator=10)
    bound, facts = bind_ctgov_outcome_to_a_row(source, atoms[0], row)
    assert bound.denominator == 10
    assert facts[0].result_context.denominator_candidates[0].parsed_value == 10
    original = source.content_text
    with pytest.raises(ResearchPackageError):
        bind_ctgov_outcome_to_a_row(source, atoms[0], row.model_copy(update={"denominator": 35}))
    assert source.content_text == original


@pytest.mark.parametrize("invalid", [False, True])
def test_generic_builder_consumes_same_scoped_n_and_source_candidates(
    tmp_path: Path, invalid: bool,
) -> None:
    study = _study("NCT00000011", 40, "ACTUAL", [
        {"name": "Studydrug", "type": "DRUG", "armGroupLabels": ["Drug arm"]},
    ])
    study.update(_scoped())
    measure = study["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]
    measure["groups"][0]["title"] = "Drug arm"
    measure["groups"][1]["title"] = "Comparator arm"
    if invalid:
        measure["classes"][0]["denoms"] = _denoms(("OG1", "bad"), ("OG2", "20"))
    payload = _build(tmp_path, [study])
    assert [row["denominator"] for row in payload["efficacy"]] == [
        None if invalid else 10, 20, 15, 25,
    ]
    sidecar = json.loads((tmp_path / "report.derivation.json").read_bytes())
    candidates = [row["denominator_candidates"] for row in sidecar["row_source_map"]]
    assert all(".classes[" in group[0]["value_path"] for group in candidates if group)
    if invalid:
        assert candidates[0] == []
        assert sidecar["denominator_conflicts"][0]["status"] == "parse_failure"


def test_real_dupilumab_week_series_uses_every_visit_n_not_overall_78() -> None:
    path = (Path(__file__).resolve().parents[2]
            / ".artifacts/1007-real-efficacy-context-v1/source-contexts.json")
    if not path.is_file():
        pytest.skip("frozen real source context unavailable; not accepted")
    frozen = json.loads(path.read_bytes())
    # Frozen packet includes complete raw measures; its old adopted atoms remain
    # unchanged. Assert actual source values against production extraction.
    contexts = frozen["contexts"]
    context = next(c for c in contexts if c["trial_id"] == "NCT04202679"
                   and "[13]" in c["source_measure_path"])
    measure = context["source_measure"]
    issues: list[Any] = []
    results = _iter_outcome_results(record={"resultsSection": {"outcomeMeasuresModule": {
        "outcomeMeasures": [measure]}}}, trial_id="NCT04202679", source_id="frozen",
        issues=issues)
    assert not issues
    # Choose the adopted group's explicit identity, not array position.
    group_id = context["adopted_observations"][0]["result_context"]["group_id"]
    active = [r for r in results if r.group_id == group_id]
    assert len(active) == 24
    expected = [int(next(count["value"] for count in clazz["denoms"][0]["counts"]
                         if count["groupId"] == group_id)) for clazz in measure["classes"]]
    assert [r.denominator_candidates[0].parsed_value for r in active] == expected
    assert len({n for n in expected}) > 1
    assert all(".classes[" in r.denominator_candidates[0].value_path for r in active)
