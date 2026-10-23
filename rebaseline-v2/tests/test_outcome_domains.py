"""Literal outcome-domain projection tests.

Titles are copied verbatim from the captured official study metadata in
``ciw-data/context/ciw2-outcome-domain_examples.json``. These assertions cover
the label projection only; they are not medical, statistical or release
acceptance, and they do not claim numeric comparability.
"""

from __future__ import annotations

import pytest

from ciw2.domain.outcomes import classify_outcome_domain

DOMAINS = {"clinical", "safety", "immunogenicity", "pk", "pd", "biomarker", "unresolved"}

PK_TITLES = (
    "Nemolizumab Serum Concentrations",
    "Apparent Total Body Clearance (Cl/F) of Nemolizumab",
    "Apparent Volume of Distribution (Vd/F) of Nemolizumab",
    "Absorption Rate Constant (Ka) of Nemolizumab",
    "Serum Concentration Observed Immediately Before Next Dosing (Ctrough) of Nemolizumab",
    "Area Under the Serum Concentration-Time Curve From Time Zero to Infinity (AUCinf) of Nemolizumab",
    "Apparent Terminal Half-life (t1/2) of Nemolizumab",
)

CLINICAL_TITLES = (
    "Percent Change From Baseline in Eczema Area and Severity Index (EASI) Score at Each Visit up to Week 52",
    "Absolute Change From Baseline in EASI Score",
    ("Number of Participants Achieving 50 Percent (%), 75% or 90% Response From Baseline in EASI "
     "(EASI-50, EASI-75 and EASI-90)"),
    "Number of Participants With Investigator's Global Assessment (IGA) Success Rate",
    "Change From Baseline in Body Surface Area (BSA) Involvement by Atopic Dermatitis (AD)",
    "Absolute Change From Baseline in Weekly Average of Peak Pruritus Numeric Rating Scale (PP NRS) Score",
    "Percent Change From Baseline in Weekly Average of PP NRS Score",
    "Percentage of Participants With an Improvement of >= 4 From Baseline in Weekly Average of PP NRS",
    "Absolute Change From Baseline in Weekly Average of Average Pruritus NRS Score",
    "Percent Change From Baseline in Weekly Average of Average Pruritus NRS Score",
    "Absolute Change From Baseline in Weekly Average of Sleep Disturbance NRS Score",
    "Percent Change From Baseline in Weekly Average of Sleep Disturbance NRS Score",
    "Percentage of Participants Receiving Any Rescue Therapy by Rescue Treatment",
    "Percent Change From Baseline in Scoring Atopic Dermatitis (SCORAD) Score",
    "Change From Baseline in Children's Dermatology Life Quality Index (cDLQI) For Participants >=4 Years of Age",
    ("Change From Baseline in Infants' Dermatology Life Quality Index (iDLQI) Score "
     "For Participants Less Than (<) 4 Years of Age"),
    "Change From Baseline in Patient-Oriented Eczema Measure (POEM)",
)

PKPD_TITLES = (
    ("Pharmacokinetic (PK)/Pharmacodynamic (PD) Relationship Between Nemolizumab Serum Concentration "
     "and Changes in PP NRS"),
    "PK/PD Relationship Between Nemolizumab Serum Concentration and Changes in EASI Score",
    "PK/PD Relationship Between Nemolizumab Serum Concentration and Changes in IGA Score",
)

SAFETY_TITLE = (
    "Number of Participants With Treatment Emergent Adverse Events (TEAEs), Adverse Events of Special "
    "Interest (AESIs), Adverse Events Leading to Discontinuation and Serious Adverse Events (SAEs)"
)

ADA_TITLE = "Number of Participants With Positive Anti-Drug Antibody (ADA) for Nemolizumab"


@pytest.mark.parametrize("title", PK_TITLES)
def test_sampled_primary_pk_titles_are_pk(title: str) -> None:
    assert classify_outcome_domain(title, drug_names=['Nemolizumab']) == "pk"


@pytest.mark.parametrize("title", CLINICAL_TITLES)
def test_sampled_secondary_clinical_titles_are_clinical(title: str) -> None:
    assert classify_outcome_domain(title) == "clinical"


def test_sampled_safety_title_is_safety() -> None:
    assert classify_outcome_domain(SAFETY_TITLE) == "safety"


@pytest.mark.parametrize("title", PKPD_TITLES)
def test_pkpd_relationship_titles_are_not_clinical(title: str) -> None:
    # Actual source units include L/ug: the relationship is not a concentration
    # merely because concentration appears in its title. Preserve it as mixed.
    assert classify_outcome_domain(title, drug_names=['Nemolizumab']) == "unresolved"


def test_sampled_anti_drug_antibody_title_is_immunogenicity() -> None:
    assert classify_outcome_domain(ADA_TITLE) == "immunogenicity"


def test_ada_is_not_the_ad_acronym() -> None:
    assert classify_outcome_domain("ADA Incidence") == "unresolved"
    # AD here is atopic dermatitis, not an anti-drug antibody abbreviation.
    ad_title = "Change From Baseline in Body Surface Area (BSA) Involvement by Atopic Dermatitis (AD)"
    assert classify_outcome_domain(ad_title) == "clinical"


def test_antibody_drug_identity_is_not_immunogenicity() -> None:
    assert classify_outcome_domain("Anti-IL-31 Receptor Alpha Antibody") == "unresolved"
    assert classify_outcome_domain(
        "Serum Concentrations of Anti-IL-31 Receptor Alpha Antibody"
    ) == "unresolved"
    assert classify_outcome_domain(
        "Serum Concentrations of Anti-IL-31 Receptor Alpha Antibody",
        drug_names=['Anti-IL-31 Receptor Alpha Antibody'],
    ) == "pk"
    assert classify_outcome_domain("Incidence of Anti-Drug Antibodies to Nemolizumab") == "immunogenicity"
    assert classify_outcome_domain("Serum Concentrations of Anti-Drug Antibody") == "immunogenicity"


def test_serum_drug_concentration_is_not_a_disease_biomarker() -> None:
    assert classify_outcome_domain("Nemolizumab Serum Concentrations", drug_names=['Nemolizumab']) == "pk"
    assert classify_outcome_domain("Serum Concentrations of Nemolizumab", drug_names=['Nemolizumab']) == "pk"
    assert classify_outcome_domain("Serum Concentrations of IgE") == "biomarker"
    assert classify_outcome_domain("Serum IgE Levels") == "biomarker"
    assert classify_outcome_domain("Serum Concentrations") == "unresolved"
    # A drug name in the population clause must not turn a disease analyte into PK.
    assert classify_outcome_domain(
        "Serum Concentrations of IgE in Participants Receiving Nemolizumab"
    ) == "biomarker"
    # Unknown numeric drug codes are not guessed into PK or biomarker.
    assert classify_outcome_domain("Serum Concentrations of CBP-201") == "unresolved"


def test_registry_hierarchy_does_not_decide_domain() -> None:
    assert classify_outcome_domain("Nemolizumab Serum Concentrations", "Primary outcome measure",
                                   drug_names=['Nemolizumab']) == "pk"
    assert classify_outcome_domain(
        "Absolute Change From Baseline in EASI Score", "Secondary outcome measure"
    ) == "clinical"
    assert classify_outcome_domain(
        "Absolute Change From Baseline in EASI Score", "Primary outcome measure"
    ) == "clinical"
    assert classify_outcome_domain(
        "Apparent Terminal Half-life (t1/2) of Nemolizumab", "Secondary outcome measure"
    ) == "pk"


@pytest.mark.parametrize("title", [
    "Non-serious TEAEs",
    "AEs not related to study drug",
    "Grade 1 or 2 AEs",
    "TEAEs without SAEs",
    "Serious Adverse Events",
    "Injection site reactions",
])
def test_safety_qualifiers_do_not_erase_safety_domain(title: str) -> None:
    assert classify_outcome_domain(title) == "safety"


@pytest.mark.parametrize("title", [
    "Change From Baseline in EASI Score and Incidence of Treatment Emergent Adverse Events",
    "Incidence of Anti-Drug Antibodies and Serious Adverse Events",
    "Serum Nemolizumab Concentrations and Change in EASI Score",
    "Serum IgE Levels and EASI Score",
    "Change From Baseline in EASI Score and Serum IgE Levels",
])
def test_mixed_measured_domains_are_unresolved(title: str) -> None:
    assert classify_outcome_domain(title) == "unresolved"


@pytest.mark.parametrize(("title", "description"), [
    ("Change From Baseline", None),
    ("Percentage of Participants", "Primary outcome measure"),
    ("Change From Baseline", "Secondary outcome measure; unit: score on a scale"),
    ("Incidence of Events", "Primary outcome measure"),
    ("Score on a Scale", None),
    ("Serum Concentrations", None),
])
def test_unknown_units_or_hierarchy_alone_are_unresolved(
    title: str, description: str | None
) -> None:
    assert classify_outcome_domain(title, description) == "unresolved"


def test_spelled_out_pk_and_pd_pair_is_unresolved() -> None:
    # Only the explicit PK/PD relationship scalar is projected; a combined pair
    # of measured domains is not collapsed into one of them.
    assert classify_outcome_domain(
        "Pharmacokinetic and Pharmacodynamic Parameters of Nemolizumab"
    ) == "unresolved"


def test_efficacy_word_alone_is_not_a_clinical_label() -> None:
    assert classify_outcome_domain("Efficacy of Nemolizumab") == "unresolved"
    assert classify_outcome_domain("Clinical Efficacy of Nemolizumab") == "unresolved"
    assert classify_outcome_domain("Efficacy and Safety of Nemolizumab") == "unresolved"
    # An explicit clinical endpoint can carry the domain; the word alone cannot.
    assert classify_outcome_domain("Efficacy of EASI Score") == "clinical"


def test_description_resolves_only_when_title_has_no_domain() -> None:
    assert classify_outcome_domain("Change From Baseline", "EASI score at week 16") == "clinical"
    assert classify_outcome_domain(
        "Serum Concentrations", "Trough concentrations of nemolizumab"
    ) == "unresolved"
    assert classify_outcome_domain(
        "Serum Concentrations", "Serum concentrations of nemolizumab", drug_names=['Nemolizumab']
    ) == "pk"
    assert classify_outcome_domain("Serum Concentrations", "Serum IgE levels") == "biomarker"
    assert classify_outcome_domain(
        "Change From Baseline", "EASI score and treatment emergent adverse events"
    ) == "unresolved"
    # The title is the measured target; a background description does not override it.
    assert classify_outcome_domain(
        "Absolute Change From Baseline in EASI Score",
        "Serum concentrations of nemolizumab were also measured",
    ) == "clinical"
    assert classify_outcome_domain(
        "Number of Participants With Treatment Emergent Adverse Events",
        "EASI score was also collected",
    ) == "safety"


def test_empty_title_uses_description_or_stays_unresolved() -> None:
    assert classify_outcome_domain("", None) == "unresolved"
    assert classify_outcome_domain("", "EASI score") == "clinical"
    assert classify_outcome_domain("   ", "Primary outcome measure") == "unresolved"


def test_explicit_pd_and_biomarker_wording() -> None:
    assert classify_outcome_domain("Receptor Occupancy of IL-31 Receptor Alpha") == "pd"
    assert classify_outcome_domain("Change From Baseline in Blood Eosinophil Counts") == "biomarker"


def test_iga_acronym_does_not_capture_serum_iga() -> None:
    assert classify_outcome_domain("IGA Success Rate") == "clinical"
    assert classify_outcome_domain("Serum IgA Levels") == "biomarker"
    assert classify_outcome_domain("Mucociliary Clearance") == "unresolved"


def test_bare_pd_is_not_guessed() -> None:
    assert classify_outcome_domain("Progressive Disease (PD)") == "unresolved"
    assert classify_outcome_domain("PD-L1 Expression") == "unresolved"


def test_every_projection_is_a_declared_domain() -> None:
    for title in (*PK_TITLES, *CLINICAL_TITLES, *PKPD_TITLES, SAFETY_TITLE, ADA_TITLE):
        assert classify_outcome_domain(title) in DOMAINS
