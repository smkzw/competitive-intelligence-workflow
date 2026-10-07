"""1007V1: preserve scientific display units and original arm identities."""

from __future__ import annotations

import pytest

from ci_workflow.renderers.portal.report_a import _native_arm_zh, _native_unit_zh


@pytest.mark.parametrize(
    ("source", "forbidden_fragments", "required_fragments"),
    [
        (
            "u*day/l/week",
            ("U·天/周", "登记报告单位"),
            ("U·天/L/周",),
        ),
        (
            "U*day/L/week",
            ("U·天/周", "登记报告单位"),
            ("U·天/L/周",),
        ),
        (
            "units * days per liter (u*day/l)/week",
            ("登记报告单位（详见登记来源）",),
            ("day", "l", "week"),
        ),
        (
            "Percent Change From Baseline in LDH (U/L)",
            ("登记报告单位（详见登记来源）",),
            ("Percent Change", "U/L"),
        ),
        (
            "hour (hr)*nanograms/milliliter (ng/ml)",
            ("登记报告单位（详见登记来源）",),
            ("ng/mL·h",),
        ),
        (
            "some unknown multi word unit",
            ("登记报告单位（详见登记来源）",),
            ("some unknown multi word unit",),
        ),
        (
            "equivalents (U*day/L) per liter",
            (),
            ("U*day/L", "per liter"),
        ),
    ],
)
def test_native_unit_zh_preserves_dimensions_and_qualifiers(
    source: str,
    forbidden_fragments: tuple[str, ...],
    required_fragments: tuple[str, ...],
) -> None:
    rendered = _native_unit_zh(source)
    low = rendered.casefold()
    for fragment in forbidden_fragments:
        assert fragment.casefold() not in low
        assert fragment not in rendered
    for fragment in required_fragments:
        assert fragment in rendered or fragment.casefold() in low


@pytest.mark.parametrize(
    ("source", "required_code", "forbidden_alias"),
    [
        ("Alxn2050 Bid", "ALXN2050", "Danicopan"),
        ("Ach-0144471 Bid", "ACH-0144471", "Danicopan"),
        ("Rva576 Bid", "RVA576", "Coversin"),
        ("ALXN2050 Open Label Extension", "ALXN2050", "Danicopan"),
        ("ACH-0144471 plus standard of care therapy", "ACH-0144471", "Danicopan"),
    ],
)
def test_native_arm_zh_preserves_original_codes(
    source: str,
    required_code: str,
    forbidden_alias: str,
) -> None:
    rendered = _native_arm_zh(source)
    assert required_code.casefold() in rendered.casefold()
    assert forbidden_alias.casefold() not in rendered.casefold()


def test_arm_code_alias_dictionary_has_no_identity_substitutions() -> None:
    import ci_workflow.renderers.portal.report_a as report_a

    assert report_a._ARM_CODE_ZH == {}
    for code in ("ALXN2050", "ACH-0144471", "RVA576", "LNP023", "ALN-CC5"):
        assert code not in report_a._ARM_CODE_ZH
