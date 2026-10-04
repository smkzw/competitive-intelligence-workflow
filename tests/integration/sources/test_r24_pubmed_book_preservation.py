"""Native book records are returned evidence, not explained EFetch attrition."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.sources.connectors.pubmed import parse_pubmed_efetch_xml
from ci_workflow.sources.connectors.pubmed_fetch import fetch_pubmed_results
from tests.integration.sources.test_pubmed_fetch import (
    Pages,
    _records_xml,
    _search_page,
)


@pytest.mark.parametrize("chapter", [False, True])
def test_native_book_document_keeps_own_identity_types_and_abstract(chapter: bool) -> None:
    # Synthetic exact NLM node shapes; not a copied commercial chapter.
    title = '<ArticleTitle>A <i>chapter</i> title</ArticleTitle>' if chapter else ''
    xml = f'''<PubmedArticleSet><PubmedBookArticle><BookDocument>
    <PMID>222</PMID><Book><BookTitle>A monograph</BookTitle></Book>{title}
    <PublicationType>Review</PublicationType>
    <Abstract><AbstractText Label="RESULTS">Native abstract.</AbstractText></Abstract>
    <CommentsCorrectionsList><PMID>999</PMID></CommentsCorrectionsList>
    </BookDocument></PubmedBookArticle></PubmedArticleSet>'''
    records = parse_pubmed_efetch_xml(xml)
    assert len(records) == 1
    record, = records
    assert record.pmid == '222'  # Never borrow a nested bibliography PMID.
    assert record.title == ('A chapter title' if chapter else 'A monograph')
    assert record.publication_types == ('Review',)  # Not relabeled Journal Article.
    assert record.abstract == 'RESULTS: Native abstract.'
    assert record.registry_nct_ids == ()


def test_mixed_native_records_close_exact_search_set_without_summary(
    tmp_path: Path,
) -> None:
    article = _records_xml('111').decode().split('<PubmedArticleSet>', 1)[1].split(
        '</PubmedArticleSet>', 1,
    )[0]
    book = '''<PubmedBookArticle><BookDocument><PMID>222</PMID>
    <Book><BookTitle>Monograph</BookTitle></Book>
    <PublicationType>Review</PublicationType></BookDocument></PubmedBookArticle>'''
    transport = Pages([_search_page(2, 0, 2, ['111', '222']),
                       f'<PubmedArticleSet>{book}{article}</PubmedArticleSet>'.encode(),
                       json.dumps({'result': {'222': {'uid': '222',
                                                      'pubstatus': 'ppublish'}}}).encode()])
    result = fetch_pubmed_results(tmp_path, 'synthetic', transport=transport)
    assert result.status == 'complete' and result.pagination_complete
    assert {record.pmid for record in result.records} == {'111', '222'}
    assert len(transport.urls) == 2  # Neither node is a missing/unavailable record.
    assert not result.attrition and not result.summary_pages


@pytest.mark.parametrize('state', ['ppublish', 'epublish', 'in process', 'not_in_pubmed',
                                 'unknown'])
def test_summary_status_does_not_prove_a_missing_record_is_unavailable(
    tmp_path: Path, state: str,
) -> None:
    summary = json.dumps({'result': {'222': {'uid': '222', 'pubstatus': state}}}).encode()
    transport = Pages([_search_page(2, 0, 2, ['111', '222']),
                       _records_xml('111'), summary])
    result = fetch_pubmed_results(tmp_path, 'synthetic', transport=transport)
    assert result.status == 'incomplete' and not result.pagination_complete
    assert [record.pmid for record in result.records] == ['111']
    assert result.universe_closed is False
    assert result.summary_pages  # Original diagnostic evidence stays recoverable.
