"""Native display cannot invent population criteria, drugs or count units."""

import json
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    _display_efficacy_rows,
    _native_population_zh,
    _native_unit_zh,
)


@pytest.mark.parametrize(("source", "display"), [
    ("All randomized participants", "全部随机受试者"),
    ("Full Analysis Set", "全分析集"),
    ("FAS", "全分析集（FAS）"),
    ("Safety population", "安全性分析人群"),
    ("Safety analysis set", "安全性分析集"),
    ("PK evaluable population", "药代动力学可评价人群"),
    ("Per-protocol analysis set", "符合方案分析集"),
    ("Severe pruritus population", "重度瘙痒人群"),
    ("Maintenance analysis set", "维持期分析集"),
    ("ITT population", "意向治疗人群（ITT）"),
    ("全分析集：至少接受一次治疗，按随机分组分析", "全分析集：至少接受一次治疗，按随机分组分析"),
    ("", ""),
])
def test_short_population_labels_do_not_add_missing_membership_conditions(source, display):
    assert _native_population_zh(source) == display


@pytest.mark.parametrize("source", [
    "Safety population: participants receiving at least one dose, regardless of evaluation.",
    "PK evaluable population: participants with an evaluable predose sample only.",
    "Severe pruritus population: baseline NRS greater than or equal to 8.",
    "Maintenance analysis set: Week 24 responders, including rescue treatment.",
    "Part 1 full analysis set: all randomized participants without imputation.",
    "Participants who did not respond at Week 12 remained in this analysis.",
    "Re-randomized participants receiving Lebrikizumab or placebo after Week 24.",
    "LTS evaluable population: participants age >= 16 who completed Week 52.",
    "All randomized participants excluding the prespecified subgroup.",
])
def test_long_or_unrecognized_population_definition_is_preserved_verbatim(source):
    assert _native_population_zh(source) == source + "（登记原文，未译）"


@pytest.mark.parametrize(("source", "display"), [
    ("Events", "次"), ("Number of events", "次"),
    ("Participants", "例"), ("Number of participants", "例"),
])
def test_event_occurrences_are_not_transcribed_as_participants(source, display):
    assert _native_unit_zh(source) == display


def test_ordinary_efficacy_projection_has_no_guessed_drug_or_population():
    fixture = (Path(__file__).resolve().parents[3]
               / "fixtures/synthetic/a-complete/inputs/report-data.json")
    raw = json.loads(fixture.read_bytes())
    row = raw["efficacy"][0]
    row.update(endpoint="Serum Trough Concentration of ALXN2050 at Week 8",
               population="All randomized participants", unit="ng/mL", value=2,
               numerator=None, denominator=None)
    data = ReportAPortalData.model_validate(raw)
    before = data.model_dump_json()
    displayed = _display_efficacy_rows(data)[0]
    assert displayed["population"] == "全部随机受试者"
    assert displayed["unit"] == "ng/mL"
    assert displayed["value"] == 2
    assert "Tezepelumab" not in displayed["endpoint"]
    assert displayed["endpoint"] == "血清药物浓度评价"
    assert displayed["endpoint_source"] == row["endpoint"]
    assert displayed["product_id"] == row["product_id"]
    assert data.model_dump_json() == before


@pytest.mark.parametrize(("unit", "display", "value"), [
    ("percentage of participants", "受试者百分比", 82.3),
    ("percent change", "百分比变化", -48.32),
    ("Participants", "例", 0),
    ("Events", "次", 0),
    ("proportion of participants", "受试者比例", 0.67),
    ("U*day/L/week", "U·天/L/周", 2.5),
    ("unresolved activity/day", "unresolved activity/day", None),
])
def test_comparison_display_uses_existing_unit_label_without_rewriting_source(unit, display, value):
    from ci_workflow.renderers.portal.report_a import _comparison_display_row

    row = {"row_id": "source-row", "unit": unit, "value": value,
           "numeric_value": value, "disclosure_state": "user_cleared" if value is None
           else "reported_value", "group_id": "OG001",
           "numeric_projection": {"raw_unit": unit, "plot_value": value}}
    before = json.dumps(row, sort_keys=True)
    shown = _comparison_display_row(row)
    assert shown["unit_label_zh"] == display
    assert {k:v for k,v in shown.items() if k != "unit_label_zh"} == row
    assert json.dumps(row, sort_keys=True) == before


@pytest.mark.parametrize(("source", "display"), [
    ("milligram per deciliter", "mg/dL"),
    ("milligrams per liter", "mg/L"),
    ("microgram per milliliter", "μg/mL"),
    ("nanomoles per microlitre", "nmol/μL"),
    ("millimoles per litre", "mmol/L"),
    ("micrograms (ug) per milliliter (mL)", "μg/mL"),
    ("milligrams (mg) per deciliter (dL)", "mg/dL"),
    ("micrograms per liter (ug/L)", "μg/L"),
    ("units per ml", "U/mL"),
    ("international units per ml", "IU/mL"),
    ("units (U) per ml (mL)", "U/mL"),
    ("units per liter (U/L)", "U/L"),
    ("milligrams (kg) per liter (L)", "milligrams (kg) per liter (L)"),
    ("micrograms (ug/mL) per liter", "micrograms (ug/mL) per liter"),
    ("units (PRBC) per ml", "units (PRBC) per ml"),
    ("units per ml (IU/mL)", "units per ml (IU/mL)"),
    ("milligrams per deciliter per week", "milligrams per deciliter per week"),
    ("U*day/L/week", "U·天/L/周"),
])
def test_scalar_unit_spelling_preserves_prefix_denominator_and_qualifiers(source, display):
    from ci_workflow.renderers.portal.report_a import _comparison_display_row

    assert _native_unit_zh(source) == display
    raw = {"row_id": "source-unit", "unit": source, "value": 2.5}
    assert _comparison_display_row(raw) == {**raw, "unit_label_zh": display}
    assert raw["unit"] == source and raw["value"] == 2.5
