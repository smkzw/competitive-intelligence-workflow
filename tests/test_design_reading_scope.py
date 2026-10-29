"""The reading projection retains the complete supplied applicability context and temporal direction."""

from copy import deepcopy

import pytest

from ciw.verify.design_labels import _atom, _check, _quantities


@pytest.mark.parametrize("marker", ["* ", "- "])
def test_introduced_alternatives_translate_the_supplied_group_once_without_mutating_source(marker):
    context = (
        marker + "Meets one of the following:\n"
        "  1. Newly diagnosed disease with no prior IST.\n"
        "  2. Relapsed disease after IST, remission then proteinuria ≥3 g/g."
    )
    snippet = dict(
        text="Relapsed disease after IST, remission then proteinuria ≥3 g/g.",
        condition="Meets one of the following:",
        cohort_quote="",
        timeframe="",
        source_id="s",
        field="eligibility",
        criterion_role="inclusion",
        context=context,
        condition_source={"binding": "introduced-list"},
    )
    original = deepcopy(snippet)
    atom = _atom(snippet)
    assert atom["text"] == context and atom["condition"] == ""
    assert snippet == original
    assert _quantities(context) == _quantities("新诊断且既往未接受IST；或IST后缓解再复发，蛋白尿≥3 g/g。")


@pytest.mark.parametrize(
    "source",
    [
        "Participants have not had a biopsy within 5 years of signing the ICF.",
        "Diagnosis must be confirmed with a kidney biopsy either during Screening or within 5 years of signing "
        "the informed consent form (ICF).",
    ],
)
@pytest.mark.parametrize("direction,valid", [("前", True), ("的", False), ("后", False)])
def test_past_diagnostic_windows_cannot_lose_or_reverse_direction(source, direction, valid):
    snippet = dict(
        text=source,
        condition="",
        cohort_quote="",
        timeframe="",
        source_id="s",
        field="eligibility",
        criterion_role="inclusion",
        context=source,
    )
    atom = _atom(snippet)
    item = dict(
        clause_id=atom["clause_id"],
        quote=source,
        text_zh=f"签署ICF{direction}5年内的肾活检记录。",
        condition_zh="",
        cohort_zh="",
        timeframe_zh="",
    )
    assert _check(item, {atom["clause_id"]: atom})[0] == valid


def test_explicit_prospective_sampling_is_not_forced_into_a_history_window():
    source = "Participants will undergo a kidney biopsy within 5 years of signing the ICF."
    atom = _atom(dict(text=source, context=source, source_id="s", field="eligibility", criterion_role="unspecified"))
    item = dict(
        clause_id=atom["clause_id"],
        quote=source,
        text_zh="受试者将在签署ICF后5年内进行肾活检。",
        condition_zh="",
        cohort_zh="",
        timeframe_zh="",
    )
    assert _check(item, {atom["clause_id"]: atom})[0]


def test_full_applicability_already_promoted_into_body_is_not_mistaken_for_missing_condition():
    full = (
        "Participants with a positive antibody titer ≥20 RU/mL may omit biopsy only based on "
        "monitor review of normal renal function and a negative secondary-cause work-up."
    )
    source = dict(
        text="positive antibody titer ≥20 RU/mL",
        condition=full,
        context=full,
        source_id="s",
        field="eligibility",
        criterion_role="inclusion",
    )
    before = deepcopy(source)
    atom = _atom(source)
    assert atom["text"] == full and not atom["condition"]
    assert "monitor review" in atom["text"] and "secondary-cause" in atom["text"]
    assert source == before
