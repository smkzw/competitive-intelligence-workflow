"""Production safety semantics keep each conjunct and its actual qualifiers."""

import pytest

from ci_workflow.reports.b.safety_concepts import describe_safety_concept


@pytest.mark.parametrize(("title", "children"), [
    ("Non-serious TEAEs and SAEs", ("non_serious_teae", "any_sae")),
    ("SAEs, Grade 3/4 AEs, and events leading to discontinuation",
     ("any_sae", "grade_3_plus", "discontinuation_ae")),
    ("TEAEs and AEs leading to death", ("any_teae", "specific_ae")),
])
def test_each_composite_measure_retains_all_explicit_children(title, children):
    concept = describe_safety_concept(title)
    assert concept.key == "composite_ae"
    assert concept.children == children
    assert concept.at_risk_stat is None
    assert concept.count_basis == "mixed"


@pytest.mark.parametrize("title", ["No TEAEs", "Participants without any TEAEs"])
def test_negative_teae_presence_never_becomes_positive_or_zero_events(title):
    concept = describe_safety_concept(title)
    assert concept.key == "unknown"
    assert concept.polarity == "negative_presence"
    assert concept.teae is not True
    assert concept.at_risk_stat is None


def test_nonserious_generic_ae_retains_negation_without_inventing_teae():
    concept = describe_safety_concept("Non-serious adverse events")
    assert concept.key == "generic_ae"
    assert concept.polarity == "negative_seriousness"
    assert concept.seriousness == "non_serious"
    assert concept.teae is None


def test_grade_is_not_a_replacement_for_seriousness_or_relatedness():
    concept = describe_safety_concept("Grade 3 serious possibly related TEAEs")
    assert concept.key == "grade_specific"
    assert concept.grade_set == (3,)
    assert concept.seriousness == "serious"
    assert concept.relatedness == "possibly_related"
    assert concept.teae is True


@pytest.mark.parametrize("title", ["AEs leading to death", "Adverse events leading to death"])
def test_fatal_ae_subset_is_not_all_cause_mortality(title):
    assert describe_safety_concept(title).key == "specific_ae"


@pytest.mark.parametrize(("title", "key"), [
    ("Grade 3 and 4 AEs", "grade_3_plus"),
    ("Number of participants with any TEAEs", "any_teae"),
    ("All-cause deaths", "death"),
    ("Participants without any SAEs", "absence_sae"),
])
def test_single_measure_controls_do_not_become_composites(title, key):
    assert describe_safety_concept(title).key == key
