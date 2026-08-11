from __future__ import annotations


def test_pubmed_nct_search_classifies_primary_report_adhoc_review_and_support() -> None:
    from ci_workflow.sources.connectors.pubmed import (
        PubMedRecord,
        build_pubmed_nct_search_url,
        classify_pubmed_records,
        parse_pubmed_efetch_xml,
    )

    records = (
        PubMedRecord(
            pmid="31543428",
            title="Dupilumab efficacy and safety in two randomized phase 3 trials",
            abstract=(
                "The co-primary endpoints and safety results are reported for NCT02912468 "
                "and NCT02898454."
            ),
            publication_types=("Journal Article", "Randomized Controlled Trial"),
        ),
        PubMedRecord(
            pmid="37026112",
            title="Clinical efficacy in obstructive lung disease features",
            abstract="Post hoc subgroup analysis of NCT02912468 and NCT02898454.",
            publication_types=("Journal Article",),
        ),
        PubMedRecord(
            pmid="40000001",
            title="Biologics for chronic rhinosinusitis: a systematic review",
            abstract="Systematic review and meta-analysis including NCT02912468.",
            publication_types=("Review", "Meta-Analysis"),
        ),
        PubMedRecord(
            pmid="40000002",
            title="Development and validation of a symptom instrument",
            abstract="Measurement work performed alongside NCT02912468.",
            publication_types=("Journal Article",),
        ),
        PubMedRecord(
            pmid="40000003",
            title="Study protocol for a randomized phase 3 trial",
            abstract="Protocol NCT02912468: the primary endpoint is change at week 24.",
            publication_types=("Clinical Trial Protocol",),
        ),
    )

    classified = classify_pubmed_records(records, target_nct_ids=("NCT02912468",))
    assert [item.role for item in classified] == [
        "primary_report",
        "ad_hoc_analysis",
        "review",
        "supporting_publication",
        "supporting_publication",
    ]
    assert classified[0].matched_nct_ids == ("NCT02912468",)
    assert "共同主要终点" in classified[0].rationale_zh
    assert "事后" in classified[1].rationale_zh
    assert classified[2].can_replace_primary_report is False
    assert classified[3].can_replace_primary_report is False
    assert build_pubmed_nct_search_url("NCT02912468").startswith(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
    )
    assert "NCT02912468%5BAll+Fields%5D" in build_pubmed_nct_search_url("NCT02912468")

    parsed = parse_pubmed_efetch_xml(
        """
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID Version="1">31543428</PMID>
              <Article>
                <ArticleTitle>Primary phase 3 report</ArticleTitle>
                <Abstract>
                  <AbstractText Label="BACKGROUND">Background.</AbstractText>
                  <AbstractText Label="RESULTS">NCT02912468 primary endpoints.</AbstractText>
                </Abstract>
                <PublicationTypeList>
                  <PublicationType>Journal Article</PublicationType>
                  <PublicationType>Randomized Controlled Trial</PublicationType>
                </PublicationTypeList>
              </Article>
              <CommentsCorrectionsList>
                <CommentsCorrections RefType="CommentIn">
                  <PMID Version="1">41442029</PMID>
                </CommentsCorrections>
              </CommentsCorrectionsList>
            </MedlineCitation>
          </PubmedArticle>
        </PubmedArticleSet>
        """
    )
    assert len(parsed) == 1
    assert parsed[0].pmid == "31543428"
    assert "41442029" not in {item.pmid for item in parsed}
    assert parsed[0].abstract == "BACKGROUND: Background. RESULTS: NCT02912468 primary endpoints."


def test_publication_never_replaces_registry_design_fields_and_supplement_can_be_not_required(  # noqa: E501
) -> None:
    from ci_workflow.sources.connectors.pubmed import (
        EvidenceContribution,
        assess_key_field_coverage,
    )

    contributions = (
        EvidenceContribution(
            field_id="design.eligibility_criteria",
            field_domain="trial_design",
            source_role="clinical_trial_registry",
            source_record_id="NCT02912468@2019-07-25",
        ),
        EvidenceContribution(
            field_id="design.eligibility_criteria",
            field_domain="trial_design",
            source_role="primary_publication",
            source_record_id="PMID31543428",
        ),
        EvidenceContribution(
            field_id="efficacy.primary_endpoint",
            field_domain="efficacy",
            source_role="clinical_trial_registry",
            source_record_id="NCT02912468@2019-07-25",
        ),
        EvidenceContribution(
            field_id="safety.serious_adverse_events",
            field_domain="safety",
            source_role="primary_publication",
            source_record_id="PMID31543428",
        ),
    )
    required = (
        "design.eligibility_criteria",
        "efficacy.primary_endpoint",
        "safety.serious_adverse_events",
    )
    coverage = assess_key_field_coverage(contributions, required_fields=required)

    assert coverage.supplement_state == "not_required"
    assert coverage.missing_fields == ()
    design = next(
        item
        for item in coverage.accepted_contributions
        if item.field_id == "design.eligibility_criteria"
    )
    assert design.source_role == "clinical_trial_registry"
    assert coverage.rejected_contributions[0].contribution.source_role == (
        "primary_publication"
    )
    assert "方案字段" in coverage.rejected_contributions[0].rationale_zh

    publication_only = assess_key_field_coverage(
        tuple(item for item in contributions if item.source_role == "primary_publication"),
        required_fields=required,
    )
    assert publication_only.supplement_state == "required"
    assert "design.eligibility_criteria" in publication_only.missing_fields

    supplement_only_design = assess_key_field_coverage(
        (
            EvidenceContribution(
                field_id="design.eligibility_criteria",
                field_domain="trial_design",
                source_role="supplementary_material",
                source_record_id="PMID31543428-supplement",
            ),
        ),
        required_fields=("design.eligibility_criteria",),
    )
    assert supplement_only_design.supplement_state == "required"
    assert supplement_only_design.accepted_contributions == ()
    assert "方案字段" in supplement_only_design.rejected_contributions[0].rationale_zh
