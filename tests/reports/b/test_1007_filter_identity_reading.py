"""Filter labels consume verified identity names, not internal lookup keys."""

import pytest

from ci_workflow.renderers.portal.report_b import _filter_value_label_zh


@pytest.mark.parametrize("key,label", (
    ("dupilumab-dose-a", "Dupilumab"),
    ("combination-regimen", "Drug A + Drug B"),
    ("drug-a-100mg", "药物甲100 mg"),
    ("nemolizumab-iv-a", "Nemolizumab 0.5 mg/kg infusion"),
))
def test_product_filter_preserves_source_identity_label(key, label) -> None:
    assert _filter_value_label_zh("product", key, label) == label


def test_long_english_study_title_uses_registry_id_without_discarding_source_title() -> None:
    title = "A Study to Assess the Efficacy and Safety of Drug A in Participants With Disease B"
    assert _filter_value_label_zh("trial", "nct04202679", title) == "NCT04202679"
    assert title.endswith("Disease B")


def test_known_short_acronym_study_name_is_not_replaced_by_internal_id() -> None:
    assert _filter_value_label_zh("trial", "study-prime2", "PRIME2") == "PRIME2"
