"""R24-65 source-wording counterexamples exercise both production classifiers."""

from __future__ import annotations

import pytest

from ci_workflow.application.source_research_service import _outcome_category
from ci_workflow.reports.b.safety_concepts import (
    classify_safety_concept,
    describe_measured_safety_concept,
    describe_safety_concept,
)


@pytest.mark.parametrize("text,key,seriousness,relatedness", [
    ("Incidence of Treatment-emergent Adverse Events", "any_teae", "unspecified",
     "unspecified"),
    ("Participants with any possibly related TEAE", "specific_ae", "unspecified",
     "possibly_related"),
    ("Participants with any definitely related TEAE", "specific_ae", "unspecified",
     "definitely_related"),
    ("Any Treatment-emergent SAE", "serious_teae_subset", "serious", "unspecified"),
    ("Treatment Emergent Serious Adverse Events", "serious_teae_subset", "serious",
     "unspecified"),
    ("Treatment Emergent Adverse Event (TAEA)", "any_teae", "unspecified", "unspecified"),
    ("Any Treatment-emergent EOI: Serious infection", "specific_ae", "serious",
     "unspecified"),
    ("At least 1 TEAE leading to discontinuation", "discontinuation_ae", "unspecified",
     "unspecified"),
    ("Treatment-related TEAEs", "treatment_related_ae", "unspecified", "related"),
    ("Grade 3 TEAEs", "grade_specific", "graded", "unspecified"),
])
def test_source_teae_qualifiers_survive_both_public_classifiers(
    text: str, key: str, seriousness: str, relatedness: str,
) -> None:
    concept = describe_safety_concept(text)
    assert (concept.key, concept.seriousness, concept.relatedness, concept.teae) == (
        key, seriousness, relatedness, True,
    )
    assert classify_safety_concept(text) == key


@pytest.mark.parametrize("text", ["Serious AE", "Serious AEs"])
def test_serious_ae_abbreviation_is_not_generic_or_inherited_teae(text: str) -> None:
    concept = describe_measured_safety_concept("Number of Participants With TEAEs", text)
    assert (concept.key, concept.seriousness, concept.teae) == ("any_sae", "serious", None)
    assert classify_safety_concept(text) == "any_sae"
    assert _outcome_category("Number of Participants With TEAEs", text) == "sae"


@pytest.mark.parametrize("text,key", [
    ("Participants with any possibly related TEAE", "specific_ae"),
    ("Participants with any definitely related TEAE", "specific_ae"),
    ("Any Treatment-emergent SAE", "serious_teae_subset"),
    ("Any Treatment-emergent EOI: Serious infection", "specific_ae"),
    ("TEAE leading to death", "specific_ae"),
])
def test_source_subsets_are_not_ingested_as_overall_teae_or_sae(text: str, key: str) -> None:
    concept = describe_measured_safety_concept("Participants With TEAEs", text)
    assert concept.key == key
    assert _outcome_category("Participants With TEAEs", text) == "common_ae"


@pytest.mark.parametrize("text", [
    "Non-treatment-emergent adverse events", "Non-TEAEs", "No TEAEs",
])
def test_positive_alias_extension_does_not_invent_emergence_under_negation(text: str) -> None:
    concept = describe_safety_concept(text)
    assert concept.key != "any_teae"
    assert concept.teae is not True


def test_generic_class_does_not_inherit_parent_emergence() -> None:
    concept = describe_measured_safety_concept("TEAEs, SAEs and discontinuation", "Any AEs")
    assert concept.key == "generic_ae"
    assert concept.teae is None


def test_ingestion_generic_class_does_not_inherit_parent_emergence() -> None:
    assert _outcome_category("Participants with TEAEs", "Any AEs") == "common_ae"
