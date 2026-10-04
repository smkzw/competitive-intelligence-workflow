"""Production XML associations must not depend on an NCT mention in the abstract."""

import pytest

from ci_workflow.sources.connectors.pubmed import classify_pubmed_records, parse_pubmed_efetch_xml


def _xml(databank: str = "", abstract: str = "Primary endpoint results are reported.") -> str:
    return f"""<PubmedArticleSet><PubmedArticle><MedlineCitation>
    <PMID>123456</PMID><Article><ArticleTitle>A randomized trial</ArticleTitle>
    <Abstract><AbstractText>{abstract}</AbstractText></Abstract>
    <PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType>
    </PublicationTypeList>{databank}</Article>
    <CommentsCorrectionsList><CommentsCorrections><RefSource>NCT00000001</RefSource>
    </CommentsCorrections></CommentsCorrectionsList></MedlineCitation>
    <PubmedData><ReferenceList><Reference><Citation>NCT00000001</Citation>
    </Reference></ReferenceList></PubmedData></PubmedArticle></PubmedArticleSet>"""


def _databank(name: str, accession: str) -> str:
    return f"""<DataBankList><DataBank><DataBankName>{name}</DataBankName>
    <AccessionNumberList><AccessionNumber>{accession}</AccessionNumber>
    </AccessionNumberList></DataBank></DataBankList>"""


def test_exact_pubmed_databank_association_survives_parse_and_reload() -> None:
    records = parse_pubmed_efetch_xml(_xml(_databank("ClinicalTrials.gov", "NCT00000001")))
    assert records[0].registry_nct_ids == ("NCT00000001",)
    restored = type(records[0]).model_validate_json(records[0].model_dump_json())
    classified = classify_pubmed_records((restored,), target_nct_ids=("NCT00000001",))[0]
    assert classified.matched_nct_ids == ("NCT00000001",)
    assert classified.role == "primary_report"  # heuristic candidate, not formal review


@pytest.mark.parametrize("name,accession", [
    ("GenBank", "NCT00000001"), ("ClinicalTrials.gov", "NCT000000019"),
    ("ClinicalTrials.gov", "xNCT00000001"),
])
def test_other_databank_or_inexact_accession_does_not_link(name: str, accession: str) -> None:
    records = parse_pubmed_efetch_xml(_xml(_databank(name, accession)))
    classified = classify_pubmed_records(records, target_nct_ids=("NCT00000001",))[0]
    assert classified.matched_nct_ids == ()


@pytest.mark.parametrize("mention", ["NCT000000019", "xNCT00000001", "NCT00000001suffix"])
def test_inexact_abstract_token_does_not_link(mention: str) -> None:
    records = parse_pubmed_efetch_xml(_xml(abstract=mention))
    classified = classify_pubmed_records(records, target_nct_ids=("NCT00000001",))[0]
    assert classified.matched_nct_ids == ()


def test_reference_and_comment_nct_are_not_article_registration() -> None:
    records = parse_pubmed_efetch_xml(_xml())
    classified, = classify_pubmed_records(records, target_nct_ids=("NCT00000001",))
    assert classified.role == "unclassified"
    assert classified.matched_nct_ids == ()
    assert not classified.can_replace_primary_report
