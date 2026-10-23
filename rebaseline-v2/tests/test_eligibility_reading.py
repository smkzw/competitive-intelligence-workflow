from __future__ import annotations

import json
from pathlib import Path

from ciw2.render.eligibility import eligibility_reading

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ctgov_NCT03985943_trimmed.json"
ROLES = {None, "threshold", "logic", "negation", "heading"}
RULE_KEYS = {"section", "kind", "measure", "operator", "value", "unit",
             "source_start", "source_end", "quote", "rule_text", "label", "section_title", "clause_start"}


def joined(reading: dict) -> str:
    return "".join(segment["text"] for segment in reading["segments"])


def emphasized(reading: dict, role: str) -> str:
    return "".join(s["text"] for s in reading["segments"] if s["emphasis"] == role)


def test_source_spans_sections_units_and_labels():
    text = (
        "Key Inclusion Criteria:\n"
        "* EASI score of at least 16 at screening and baseline.\n"
        "* IGA score \u2265 3.\n"
        "* ALT or AST > 3 \u00d7 ULN.\n"
        "Key Exclusion Criteria:\n"
        "* BSA > 80%\n"
        "* eGFR < 60 mL/min/1.73 m2\n"
    )
    reading = eligibility_reading(text)
    assert joined(reading) == text
    assert all(segment["emphasis"] in ROLES for segment in reading["segments"])

    rules = reading["rules"]
    assert [rule["measure"] for rule in rules] == ["EASI", "IGA", "ALT or AST", "BSA", "eGFR"]
    assert [rule["section"] for rule in rules] == [
        "inclusion", "inclusion", "inclusion", "exclusion", "exclusion"]
    assert [rule["kind"] for rule in rules] == ["score", "score", "lab", "score", "lab"]

    easi = rules[0]
    assert easi["quote"] == "EASI score of at least 16"
    assert text[easi["source_start"]:easi["source_end"]] == easi["quote"]
    assert (easi["operator"], easi["value"], easi["unit"]) == (">=", 16.0, None)
    assert easi["rule_text"] == "EASI score of at least 16 at screening and baseline."
    assert easi["label"] == "EASI \u8bc4\u5206 \u2265 16"
    assert "screening and baseline" in easi["rule_text"]

    assert rules[1]["label"] == "IGA \u8bc4\u5206 \u2265 3"
    compound = rules[2]
    assert (compound["value"], compound["unit"], compound["operator"]) == (3.0, "\u00d7 ULN", ">")
    assert compound["quote"] == "ALT or AST > 3 \u00d7 ULN"
    assert compound["label"] == "ALT \u6216 AST > 3 \u00d7 ULN"
    assert rules[3]["unit"] == "%" and rules[3]["label"] == "BSA > 80%"
    assert rules[4]["unit"] == "mL/min/1.73 m2"
    assert rules[4]["label"] == "eGFR < 60 mL/min/1.73 m2"

    assert "Key Inclusion Criteria:" in emphasized(reading, "heading")
    assert "Key Exclusion Criteria:" in emphasized(reading, "heading")
    assert "EASI score of at least 16" in emphasized(reading, "threshold")
    assert "ALT " in emphasized(reading, "threshold")
    assert "AST > 3 \u00d7 ULN" in emphasized(reading, "threshold")
    assert "or" in emphasized(reading, "logic")
    assert set(compound) == RULE_KEYS

    inline = eligibility_reading("Inclusion Criteria: EASI >= 16")
    assert inline["rules"][0]["section"] == "inclusion"
    assert inline["rules"][0]["rule_text"] == "EASI >= 16"


def test_or_clause_stays_one_condition_and_same_clause_thresholds_group():
    text = (
        "Inclusion Criteria:\n"
        "EASI >= 16 OR IGA >= 3\n"
        "Exclusion Criteria:\n"
        "ALT or AST > 3 \u00d7 ULN"
    )
    reading = eligibility_reading(text)
    rules = reading["rules"]
    assert [rule["measure"] for rule in rules] == ["EASI", "IGA", "ALT or AST"]
    assert {rules[0]["rule_text"], rules[1]["rule_text"]} == {"EASI >= 16 OR IGA >= 3"}
    assert rules[0]["source_end"] <= rules[1]["source_start"]
    assert "OR" in emphasized(reading, "logic")
    assert rules[2]["section"] == "exclusion"
    assert rules[2]["measure"] == "ALT or AST"
    assert rules[2]["unit"] == "\u00d7 ULN"
    assert "or" in emphasized(reading, "logic")
    assert len([rule for rule in rules if "ALT" in rule["measure"] or "AST" in rule["measure"]]) == 1

    and_reading = eligibility_reading("Inclusion Criteria:\nEASI >= 16 AND IGA >= 3")
    assert {rule["rule_text"] for rule in and_reading["rules"]} == {"EASI >= 16 AND IGA >= 3"}
    assert "AND" in emphasized(and_reading, "logic")

    comma_reading = eligibility_reading("Inclusion Criteria:\nALT, AST > 3 \u00d7 ULN")
    assert [rule["measure"] for rule in comma_reading["rules"]] == ["ALT, AST"]
    assert comma_reading["rules"][0]["label"] == "ALT\u3001AST > 3 \u00d7 ULN"


def test_negation_is_marked_outside_comparator_phrases():
    text = (
        "Inclusion Criteria:\n"
        "No prior biologic therapy\n"
        "ALT > 3 \u00d7 ULN without cirrhosis\n"
        "EASI score of no less than 16"
    )
    reading = eligibility_reading(text)
    assert [rule["measure"] for rule in reading["rules"]] == ["ALT", "EASI"]
    negation = emphasized(reading, "negation")
    assert "No" in negation and "without" in negation
    assert "no less than" not in negation
    easi = reading["rules"][1]
    assert easi["quote"] == "EASI score of no less than 16"
    assert easi["operator"] == ">="
    assert easi["label"] == "EASI \u8bc4\u5206 \u2265 16"
    assert "EASI score of no less than 16" in emphasized(reading, "threshold")


def test_unit_normalisation_keeps_uln_and_lab_units():
    text = (
        "Inclusion Criteria:\n"
        "ALT \u2265 3 times ULN\n"
        "platelets < 100 \u00d7 10^9/L\n"
        "BSA \u2265 10 percent (%)\n"
        "neutrophils < 1,500/\u00b5L"
    )
    reading = eligibility_reading(text)
    rules = reading["rules"]
    assert [(rule["measure"], rule["unit"]) for rule in rules] == [
        ("ALT", "\u00d7 ULN"), ("platelets", "\u00d7 10^9/L"), ("BSA", "%"), ("neutrophils", "/\u00b5L")]
    assert [rule["value"] for rule in rules] == [3.0, 100.0, 10.0, 1500.0]
    assert [rule["label"] for rule in rules] == [
        "ALT \u2265 3 \u00d7 ULN", "\u8840\u5c0f\u677f < 100 \u00d7 10^9/L",
        "BSA \u2265 10%", "\u4e2d\u6027\u7c92\u7ec6\u80de < 1,500/\u00b5L"]


def test_chinese_inequalities_and_offsets_are_source_exact():
    text = ("\u5165\u9009\u6807\u51c6\uff1a\nEASI \u8bc4\u5206\u226516\uff0c\u4e14 IGA \u8bc4\u5206\u22653\u3002\n"
            "\u6392\u9664\u6807\u51c6\uff1a\nALT\u6216AST\uff1e3\u500dULN")
    reading = eligibility_reading(text)
    rules = reading["rules"]
    assert [rule["measure"] for rule in rules] == ["EASI", "IGA", "ALT or AST"]
    assert [rule["section"] for rule in rules] == ["inclusion", "inclusion", "exclusion"]
    assert rules[0]["quote"] == "EASI \u8bc4\u5206\u226516"
    assert rules[1]["quote"] == "IGA \u8bc4\u5206\u22653"
    assert rules[2]["quote"] == "ALT\u6216AST\uff1e3\u500dULN"
    assert (rules[2]["operator"], rules[2]["value"], rules[2]["unit"]) == (">", 3.0, "\u00d7 ULN")
    assert rules[2]["label"] == "ALT \u6216 AST > 3 \u00d7 ULN"
    assert "\u4e14" in emphasized(reading, "logic") and "\u6216" in emphasized(reading, "logic")
    assert rules[0]["rule_text"] == "EASI \u8bc4\u5206\u226516\uff0c\u4e14 IGA \u8bc4\u5206\u22653\u3002"
    for rule in rules:
        assert text[rule["source_start"]:rule["source_end"]] == rule["quote"]
    assert joined(reading) == text


def test_xss_payload_stays_plain_source_text():
    text = (
        "Inclusion Criteria:\n"
        "<img src=x onerror=alert(1)> EASI >= 16\n"
        "<script>alert('x')</script>"
    )
    reading = eligibility_reading(text)
    assert joined(reading) == text
    assert "<img src=x onerror=alert(1)>" in joined(reading)
    assert "&lt;" not in joined(reading) and "&amp;" not in joined(reading)
    assert "<b>" not in joined(reading)
    assert reading["rules"][0]["quote"] == "EASI >= 16"
    assert reading["rules"][0]["label"] == "EASI \u8bc4\u5206 \u2265 16"
    assert "EASI >= 16" in emphasized(reading, "threshold")


def test_unsupported_forms_are_preserved_without_rules():
    text = (
        "Inclusion Criteria:\n"
        "Body weight (<) 30 kilograms (kg)\n"
        "Age >= 18 years\n"
        "Prior therapy with no response\n"
        "EASI-75 \u2265 50%"
    )
    reading = eligibility_reading(text)
    assert reading["rules"] == []
    assert joined(reading) == text
    assert emphasized(reading, "threshold") == ""
    assert "no" in emphasized(reading, "negation")
    assert eligibility_reading("") == {"rules": [], "segments": []}
    assert eligibility_reading("EASI >= 16")["rules"][0]["section"] == "unspecified"


def test_registry_fixture_keeps_all_recognised_thresholds_and_original_text():
    criteria = json.loads(FIXTURE.read_text(encoding="utf-8"))[
        "protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    reading = eligibility_reading(criteria)
    assert joined(reading) == criteria
    by_measure = {rule["measure"]: rule for rule in reading["rules"]}
    assert {"EASI", "IGA", "BSA", "PP-NRS"} <= set(by_measure)
    assert by_measure["EASI"]["value"] == 16.0
    assert by_measure["IGA"]["value"] == 3.0
    assert (by_measure["BSA"]["value"], by_measure["BSA"]["unit"]) == (10.0, "%")
    assert "body surface area" in by_measure["BSA"]["quote"]
    assert by_measure["PP-NRS"]["value"] == 4.0
    assert by_measure["PP-NRS"]["label"] == "PP-NRS \u8bc4\u5206 \u2265 4.0"
    assert all(rule["section"] == "inclusion" for rule in reading["rules"])
    assert not any("weight" in rule["rule_text"].lower() for rule in reading["rules"])
    for rule in reading["rules"]:
        assert criteria[rule["source_start"]:rule["source_end"]] == rule["quote"]
    assert "Key Exclusion Criteria:" in joined(reading)


def test_every_supported_metric_is_returned_without_top_n():
    text = (
        "Inclusion Criteria:\n"
        "EASI >= 16\nIGA >= 3\nBSA >= 10%\nSCORAD >= 50\nPP-NRS >= 4\nWI-NRS >= 4\n"
        "ALT > 3 \u00d7 ULN\nAST > 3 \u00d7 ULN\neGFR < 60\nplatelets < 100 \u00d7 10^9/L\n"
        "neutrophils < 1.5 \u00d7 10^9/L\nhemoglobin < 100 g/L"
    )
    reading = eligibility_reading(text)
    assert len(reading["rules"]) == 12
    assert {rule["measure"] for rule in reading["rules"]} == {
        "EASI", "IGA", "BSA", "SCORAD", "PP-NRS", "WI-NRS",
        "ALT", "AST", "eGFR", "platelets", "neutrophils", "hemoglobin"}
    assert all(rule["section"] == "inclusion" for rule in reading["rules"])
    assert joined(reading) == text
