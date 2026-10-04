from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.sources.connectors.pubmed import PubMedRecord, classify_pubmed_records

FIXTURE = Path(__file__).parents[1] / "fixtures/pubmed/r24_cm310_cm326_records.json"


@pytest.mark.parametrize(
    ("pmid", "expected"),
    (
        ("41022848", "primary_report"),
        ("40824573", "primary_report"),
        ("39220573", "supporting_publication"),
        ("38482462", "supporting_publication"),
        ("37483544", "primary_report"),
    ),
)
def test_actual_record_role_is_whole_publication_not_one_phrase(
    pmid: str, expected: str,
) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    record = next(PubMedRecord.model_validate(row) for row in payload["records"]
                  if row["pmid"] == pmid)
    result, = classify_pubmed_records(
        (record,), target_nct_ids=tuple(payload["target_nct_ids"]),
    )
    assert result.role == expected
    assert result.can_replace_primary_report is (expected == "primary_report")
    assert result.record == record
    assert result.matched_nct_ids == record.registry_nct_ids


@pytest.mark.parametrize(
    ("title", "abstract", "types", "expected"),
    (
        (
            "Post-hoc subgroup analysis of a randomized trial",
            "The primary endpoint results are reported for the subgroup. NCT05324137.",
            ("Journal Article", "Randomized Controlled Trial"),
            "ad_hoc_analysis",
        ),
        (
            "Efficacy of a randomized clinical trial",
            "Primary endpoints were measured. RESULTS: A post-hoc analysis of a "
            "subgroup found a mean difference of -1.2. NCT05324137.",
            ("Journal Article",),
            "ad_hoc_analysis",
        ),
        (
            "Rationale and design of a randomized phase 3 study",
            "Previous trials reported efficacy and safety results. This study's "
            "primary endpoint will be measured in 180 patients. NCT05324137.",
            ("Journal Article",),
            "supporting_publication",
        ),
        (
            "Randomized phase 3 trial of a monoclonal antibody",
            "METHODS: Primary endpoints and efficacy and safety will be evaluated. "
            "RESULTS: The efficacy at 16 weeks will be verified. NCT05324137.",
            ("Journal Article", "Randomized Controlled Trial"),
            "supporting_publication",
        ),
        (
            "Randomized phase 3 trial of a monoclonal antibody",
            "The primary endpoint and efficacy and safety are described. NCT05324137.",
            ("Journal Article", "Randomized Controlled Trial"),
            "supporting_publication",
        ),
        (
            "Study protocol for a randomized trial",
            "The primary endpoint results are reported in another trial. NCT05324137.",
            ("Clinical Trial Protocol",),
            "supporting_publication",
        ),
        (
            "Systematic review of randomized phase 3 studies",
            "The primary endpoints and efficacy and safety results are reported. NCT05324137.",
            ("Review", "Meta-Analysis"),
            "review",
        ),
        (
            "A randomized trial with a secondary biomarker analysis",
            "The primary endpoints and safety results are reported. A post-hoc "
            "biomarker analysis is also reported. NCT05324137.",
            ("Journal Article", "Randomized Controlled Trial"),
            "primary_report",
        ),
        (
            "Unrelated randomized trial",
            "The primary endpoints and safety results are reported. NCT00000001.",
            ("Journal Article", "Randomized Controlled Trial"),
            "unclassified",  # another ID alone is not an exhaustive relationship proof
        ),
    ),
)
def test_role_boundaries_are_conservative_for_protocols_and_secondary_analyses(
    title: str, abstract: str, types: tuple[str, ...], expected: str,
) -> None:
    record = PubMedRecord(pmid="99900001", title=title, abstract=abstract,
                          publication_types=types)
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT05324137",))
    assert result.role == expected
    assert result.can_replace_primary_report is (expected == "primary_report")


@pytest.mark.parametrize(
    ("title", "abstract", "expected"),
    (
        ("A randomized phase 3 trial", "Primary endpoints were prespecified. RESULTS: "
         "Treatment significantly improved symptoms (difference -1.2, 95% CI -2.0 to -0.4; "
         "P=.02). NCT05324137.", "primary_report"),
        ("Design and rationale of a randomized phase 3 trial", "Primary endpoint: least "
         "squares mean at week 24. Expected response rate 55%. NCT05324137.",
         "supporting_publication"),
        ("A randomized trial analysis", "The primary endpoint was response. In this "
         "post-hoc subgroup analysis, we included participants with high biomarkers. "
         "Response rate was 55%. NCT05324137.", "ad_hoc_analysis"),
        ("A randomized phase 3 trial", "Primary endpoints were defined. METHODS: "
         "Response rate will be assessed at week 24 in 180 patients. RESULTS: "
         "The assumed response rate was 55% for sample-size planning. NCT05324137.",
         "supporting_publication"),
        ("A randomized phase 3 trial", "Primary endpoint results were reported previously. "
         "Response rate will be assessed at week 24. NCT05324137.",
         "supporting_publication"),
        ("A randomized phase 3 trial", "Primary endpoints were defined. METHODS: "
         "The anticipated response rate is 55%. RESULTS: treatment reduced symptoms "
         "(difference -1.2, 95% CI -2.0 to -0.4; P=.02). NCT05324137.", "primary_report"),
        ("A randomized phase 3 trial", "Primary endpoint response was assessed. RESULTS: "
         "The estimated least-squares mean difference was -1.2 (95% CI -2.0 to -0.4). "
         "A post-hoc biomarker analysis was also reported. NCT05324137.", "primary_report"),
        ("A randomized phase 3 trial", "Primary endpoint: least-squares mean at week 24 "
         "in 180 patients. NCT05324137.", "supporting_publication"),
    ),
)
def test_independent_review_counterexamples_call_production_classifier(
    title: str, abstract: str, expected: str,
) -> None:
    record = PubMedRecord(pmid="99900002", title=title, abstract=abstract,
                          publication_types=("Journal Article", "Randomized Controlled Trial"))
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT05324137",))
    assert result.role == expected
    assert result.record == record
    assert result.can_replace_primary_report is (expected == "primary_report")


@pytest.mark.parametrize(
    ("title", "abstract", "expected"),
    (
        ("Design of a randomized phase 3 trial", "Primary endpoints are change in "
         "NPS at week 24. The estimated least-squares mean difference is -2.3 "
         "(95% CI -2.6 to -1.9). NCT05324137.", "supporting_publication"),
        ("Trial design: a randomized phase 3 study", "Primary endpoints are change "
         "in NPS. Response rate 55% (95% CI 50-60). NCT05324137.", "supporting_publication"),
        ("Effect of mAb X on nasal polyps", "A post-hoc analysis of the randomized "
         "trial was conducted. Primary endpoints were met in the overall population. "
         "Response rate was 55% (95% CI 50-60). NCT05324137.", "ad_hoc_analysis"),
        ("An ad hoc analysis of a randomized trial", "Primary endpoint response rate "
         "was 55% (95% CI 50-60). NCT05324137.", "ad_hoc_analysis"),
        ("Effect of mAb X on nasal polyps", "Here we present a post hoc analysis "
         "of a randomized trial. Primary endpoint response rate was 55% "
         "(95% CI 50-60). NCT05324137.", "ad_hoc_analysis"),
        ("A randomized phase 3 trial", "Primary endpoints were prespecified. RESULTS: "
         "Treatment reduced NPS (least-squares mean difference -2.3; 95% CI -2.6 to -1.9). "
         "In this post-hoc analysis, high TSLP predicted benefit. NCT05324137.", "primary_report"),
        ("A randomized phase 3 trial", "METHODS: Primary endpoint estimated "
         "least-squares mean difference -2.3 (95% CI -2.6 to -1.9). NCT05324137.",
         "supporting_publication"),
        ("A randomized phase 3 trial", "Primary endpoint treatment response: the "
         "estimated least-squares mean difference was -2.3 (95% CI -2.6 to -1.9). "
         "NCT05324137.", "primary_report"),
    ),
)
def test_followup_whole_scope_not_any_secondary_sentence_or_planned_estimate(
    title: str, abstract: str, expected: str,
) -> None:
    record = PubMedRecord(pmid="99900003", title=title, abstract=abstract,
                          publication_types=("Journal Article", "Randomized Controlled Trial"))
    result, = classify_pubmed_records((record,), target_nct_ids=("NCT05324137",))
    assert result.role == expected
    assert result.record == record
    assert result.can_replace_primary_report is (expected == "primary_report")
