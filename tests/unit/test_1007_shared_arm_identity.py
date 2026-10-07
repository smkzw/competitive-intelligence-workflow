"""Renderer labels must not independently rename a scientific drug identity."""

import pytest

from ci_workflow.renderers.portal.report_a import _native_arm_zh
from ci_workflow.renderers.portal.report_b import _arm_code_zh, _decode_arm_identifier


@pytest.mark.parametrize("code", ["ALXN2050", "ACH-0144471", "LNP023", "RVA576", "ALN-CC5"])
def test_original_code_survives_both_report_consumers(code: str) -> None:
    assert _arm_code_zh(code) == code
    assert code.casefold() in _native_arm_zh(code).casefold()
    decoded = _decode_arm_identifier(f"nct00000001-arm-{code}-lte") or ""
    assert code.casefold() in decoded.casefold()


def test_role_and_period_transcription_do_not_require_a_drug_alias() -> None:
    assert _arm_code_zh("placebo") == "安慰剂"
    assert _decode_arm_identifier("nct00000001-arm-ALXN2050-tp2") == "第2期 ALXN2050"
