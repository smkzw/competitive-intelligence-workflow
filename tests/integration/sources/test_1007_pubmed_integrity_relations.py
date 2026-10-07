"""Native correction links survive retrieval; flagged papers cannot auto-replace results."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.sources.connectors.pubmed import (
    PubMedRecord,
    classify_pubmed_records,
    parse_pubmed_efetch_xml,
)


def article(relations: str = "", types: str = "") -> str:
    return f'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>38629497</PMID>
      <Article><ArticleTitle>Randomized phase 3 study</ArticleTitle>
      <Abstract><AbstractText>Primary endpoints were prespecified. RESULTS:
      Response rate was 55% (95% CI 50-60). NCT04501666.</AbstractText></Abstract>
      <PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType>
      {types}</PublicationTypeList></Article>{relations}</MedlineCitation>
      <PubmedData><ReferenceList><Reference><ArticleIdList>
      <ArticleId IdType="pubmed">99999999</ArticleId></ArticleIdList>
      </Reference></ReferenceList></PubmedData></PubmedArticle></PubmedArticleSet>'''


def test_native_erratum_and_comment_remain_distinct_located_source_relations() -> None:
    record, = parse_pubmed_efetch_xml(article('''<CommentsCorrectionsList>
      <CommentsCorrections RefType="CommentIn"><RefSource>Editorial source</RefSource>
      <PMID>38703061</PMID></CommentsCorrections>
      <CommentsCorrections RefType="ErratumIn"><RefSource>Correction source</RefSource>
      <PMID>39226086</PMID><Note>Corrected source text</Note></CommentsCorrections>
      </CommentsCorrectionsList>'''))
    rows = record.model_dump(mode="json").get("relation_candidates", [])
    assert [(row["ref_type"], row["pmid"]) for row in rows] == [
        ("CommentIn", "38703061"), ("ErratumIn", "39226086")]
    assert rows[1]["reference"] == "Correction source"
    assert rows[1]["note"] == "Corrected source text"
    assert rows[1]["field_path"] == (
        "./MedlineCitation[1]/CommentsCorrectionsList[1]/CommentsCorrections[2]")
    assert record.pmid == "38629497"
    assert "99999999" not in {row["pmid"] for row in rows}


@pytest.mark.parametrize("ref_type", (
    "ErratumIn", "ErratumFor", "RetractionIn", "RetractionOf",
    "ExpressionOfConcernIn", "ExpressionOfConcernFor",
    "CorrectedandRepublishedIn", "CorrectedandRepublishedFrom",
    "RetractedandRepublishedIn", "RetractedandRepublishedFrom", "UpdateIn", "UpdateOf",
))
def test_integrity_relation_keeps_paper_reviewable_but_not_auto_primary(ref_type: str) -> None:
    record, = parse_pubmed_efetch_xml(article(f'''<CommentsCorrectionsList>
      <CommentsCorrections RefType="{ref_type}"><RefSource>Source</RefSource>
      <PMID>39226086</PMID></CommentsCorrections></CommentsCorrectionsList>'''))
    verdict, = classify_pubmed_records((record,), target_nct_ids=("NCT04501666",))
    assert verdict.role == "unclassified"
    assert not verdict.can_replace_primary_report
    assert verdict.matched_nct_ids == ("NCT04501666",)
    assert ref_type in " ".join(verdict.classification_signals)
    assert verdict.record == record


@pytest.mark.parametrize("publication_type", (
    "Retracted Publication", "Retraction of Publication", "Expression of Concern",
    "Published Erratum", "Corrected and Republished Article",
))
def test_integrity_publication_type_alone_also_blocks_auto_primary(publication_type: str) -> None:
    record, = parse_pubmed_efetch_xml(article(
        types=f"<PublicationType>{publication_type}</PublicationType>",
    ))
    verdict, = classify_pubmed_records((record,), target_nct_ids=("NCT04501666",))
    assert verdict.role == "unclassified"
    assert not verdict.can_replace_primary_report
    assert publication_type in " ".join(verdict.classification_signals)


@pytest.mark.parametrize("ref_type", ("CommentIn", "CommentOn", "Cites", "AssociatedPublication"))
def test_ordinary_comment_is_preserved_without_inventing_a_correction(ref_type: str) -> None:
    record, = parse_pubmed_efetch_xml(article(f'''<CommentsCorrectionsList>
      <CommentsCorrections RefType="{ref_type}"><RefSource>Source</RefSource>
      <PMID>39226086</PMID></CommentsCorrections></CommentsCorrectionsList>'''))
    verdict, = classify_pubmed_records((record,), target_nct_ids=("NCT04501666",))
    assert verdict.role == "primary_report"
    assert verdict.can_replace_primary_report
    assert record.model_dump(mode="json")["relation_candidates"][0]["ref_type"] == ref_type


def test_incomplete_and_repeated_relations_are_not_first_wins_or_dropped() -> None:
    record, = parse_pubmed_efetch_xml(article('''<CommentsCorrectionsList>
      <CommentsCorrections RefType="ErratumIn"><RefSource>Source</RefSource></CommentsCorrections>
      <CommentsCorrections RefType="ErratumIn"><RefSource>Other source</RefSource>
      <PMID>39226086</PMID></CommentsCorrections>
      <CommentsCorrections RefType="FutureRelation"><RefSource>Unknown relation</RefSource>
      <PMID>invalid</PMID></CommentsCorrections></CommentsCorrectionsList>'''))
    rows = record.model_dump(mode="json").get("relation_candidates", [])
    assert [row["pmid"] for row in rows] == ["", "39226086", "invalid"]
    assert len({row["field_path"] for row in rows}) == 3
    verdict, = classify_pubmed_records((record,), target_nct_ids=("NCT04501666",))
    assert not verdict.can_replace_primary_report  # missing linked PMID is not clearance


def test_legacy_metadata_is_not_fabricated_or_added_to_serialization() -> None:
    record = PubMedRecord(pmid="111", title="Old record", abstract="", publication_types=())
    assert "relation_candidates" not in record.model_dump(mode="json")


def test_production_fetch_cli_retains_integrity_links_in_its_compact_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from ci_workflow.cli import main
    from ci_workflow.sources.connectors import pubmed_fetch
    from tests.integration.sources.test_pubmed_fetch import Pages, _search_page
    from tests.integration.test_research_package_submission import _project

    root = _project(tmp_path)
    xml = article('''<CommentsCorrectionsList>
      <CommentsCorrections RefType="ErratumIn"><RefSource>Correction source</RefSource>
      <PMID>39226086</PMID></CommentsCorrections></CommentsCorrectionsList>''').encode()
    monkeypatch.setattr(pubmed_fetch, "_download", Pages([
        _search_page(1, 0, 200, ["38629497"]), xml,
    ]))
    assert main(["research", "fetch-pubmed", "--root", str(root), "--term", "NCT04501666"]) == 0
    pointer = json.loads(capsys.readouterr().out)
    receipt = json.loads((root / pointer["capture_path"]).read_bytes())
    assert receipt["records"][0]["relation_candidates"][0]["ref_type"] == "ErratumIn"
    assert receipt["records"][0]["relation_candidates"][0]["pmid"] == "39226086"
    assert receipt["acquisition"]["universe_closed"] is False
    assert "abstract" not in receipt["records"][0]
