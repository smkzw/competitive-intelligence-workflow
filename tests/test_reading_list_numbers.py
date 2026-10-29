"""Source-declared list ordinals may move inline; independent clinical measurements remain mandatory."""
import pytest

from ciw.verify.design_labels import _atom, _check


def reading(value):
    source = ("* Meets one of the following:\n"
              "  1. Newly diagnosed disease with eGFR ≥30 mL/min.\n"
              "  2. Relapsed disease after prior treatment with eGFR ≥40 mL/min.")
    atom = _atom(dict(text=source, context=source, condition="", source_id="s", field="eligibility"))
    item = dict(clause_id=atom["clause_id"], quote=source, text_zh=value,
                condition_zh="", cohort_zh="", timeframe_zh="")
    return _check(item, {atom["clause_id"]: atom})[0]


@pytest.mark.parametrize("style", ["inline", "lines", "unlabelled"])
def test_only_source_declared_ordinals_can_change_layout(style):
    if style == "inline":
        label = "符合以下之一：1. 新诊断疾病，eGFR≥30 mL/min；2. 既往治疗后复发，eGFR≥40 mL/min。"
    elif style == "lines":
        label = "符合以下之一：\n1. 新诊断疾病，eGFR≥30 mL/min；\n2. 既往治疗后复发，eGFR≥40 mL/min。"
    else:
        label = "符合以下之一：新诊断疾病，eGFR≥30 mL/min；或既往治疗后复发，eGFR≥40 mL/min。"
    assert reading(label)


@pytest.mark.parametrize("label", [
    "符合以下之一：1. 新诊断疾病，eGFR≥40 mL/min；2. 既往治疗后复发，eGFR≥40 mL/min。",
    "符合以下之一：1. 新诊断疾病；2. 既往治疗后复发，eGFR≥40 mL/min。",
    "符合以下之一：1. 新诊断疾病，eGFR≥30 mL/min；2. 既往治疗后复发，eGFR≥40 μL/min。",
])
def test_ordinal_folding_cannot_erase_changed_or_missing_measurements(label):
    assert not reading(label)


def test_unlisted_inline_numbers_are_real_values():
    source = "Patients receive 1 mg or 2 mg, according to the assigned arm."
    atom = _atom(dict(text=source, context=source, condition="", source_id="s", field="arms"))
    item = dict(clause_id=atom["clause_id"], quote=source, text_zh="患者根据分组接受1 mg或2 mg。",
                condition_zh="", cohort_zh="", timeframe_zh="")
    assert _check(item, {atom["clause_id"]: atom})[0]
    item["text_zh"] = "患者根据分组接受2 mg。"
    assert not _check(item, {atom["clause_id"]: atom})[0]
