"""Native own DOI/PMC candidates are lookup evidence, never bibliography IDs."""
from ci_workflow.sources.connectors.pubmed import PubMedRecord, parse_pubmed_efetch_xml


def article(data: str) -> str:
    return ('<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>111</PMID>'
            '<Article><ArticleTitle>Own paper</ArticleTitle></Article>'
            '</MedlineCitation>' + data + '</PubmedArticle></PubmedArticleSet>')


def test_own_identifiers_keep_values_and_precise_native_paths() -> None:
    record, = parse_pubmed_efetch_xml(article('''<PubmedData><ArticleIdList>
        <ArticleId IdType="doi">10.1234/own</ArticleId>
        <ArticleId IdType="pmc">PMC987</ArticleId></ArticleIdList>
        <ReferenceList><Reference><ArticleIdList><ArticleId IdType="doi">
        10.9999/other</ArticleId></ArticleIdList></Reference></ReferenceList></PubmedData>'''))
    assert [(i.id_type, i.value) for i in record.identifier_candidates] == [
        ('doi', '10.1234/own'), ('pmc', 'PMC987')]
    assert record.identifier_candidates[1].field_path == (
        './PubmedData[1]/ArticleIdList[1]/ArticleId[2]')


def test_conflicting_or_repeated_own_identifiers_are_not_first_wins() -> None:
    record, = parse_pubmed_efetch_xml(article('''<PubmedData><ArticleIdList>
        <ArticleId IdType="doi">10.1234/a</ArticleId>
        <ArticleId IdType="doi">10.1234/b</ArticleId>
        <ArticleId IdType="doi">10.1234/a</ArticleId></ArticleIdList></PubmedData>'''))
    assert [i.value for i in record.identifier_candidates] == [
        '10.1234/a', '10.1234/b', '10.1234/a']
    assert len({i.field_path for i in record.identifier_candidates}) == 3


def test_reference_only_ids_do_not_become_own_ids() -> None:
    record, = parse_pubmed_efetch_xml(article('''<PubmedData><ReferenceList>
        <Reference><ArticleIdList><ArticleId IdType="pmc">PMC999</ArticleId>
        </ArticleIdList></Reference></ReferenceList></PubmedData>'''))
    assert record.identifier_candidates == ()
    assert 'identifier_candidates' not in record.model_dump(mode='json')


def test_book_own_document_and_data_ids_are_kept_not_nested_book_or_reference() -> None:
    record, = parse_pubmed_efetch_xml('''<PubmedArticleSet><PubmedBookArticle>
      <BookDocument><PMID>222</PMID><ArticleTitle>Own chapter</ArticleTitle>
      <ArticleIdList><ArticleId IdType="bookaccession">NBK123</ArticleId></ArticleIdList>
      <Book><ArticleIdList><ArticleId IdType="doi">10.9999/wholebook</ArticleId>
      </ArticleIdList></Book></BookDocument><PubmedBookData><ArticleIdList>
      <ArticleId IdType="doi">10.1234/chapter</ArticleId></ArticleIdList></PubmedBookData>
      </PubmedBookArticle></PubmedArticleSet>''')
    assert [(i.id_type, i.value) for i in record.identifier_candidates] == [
        ('bookaccession', 'NBK123'), ('doi', '10.1234/chapter')]


def test_default_type_and_incomplete_values_are_preserved_not_fabricated() -> None:
    record, = parse_pubmed_efetch_xml(article('''<PubmedData><ArticleIdList>
        <ArticleId>111</ArticleId><ArticleId IdType="doi"> </ArticleId>
        <ArticleId IdType="">ambiguous</ArticleId></ArticleIdList></PubmedData>'''))
    assert [(i.id_type, i.value) for i in record.identifier_candidates] == [
        ('pubmed', '111'), ('doi', ''), ('', 'ambiguous')]


def test_legacy_record_does_not_gain_serialized_metadata_without_evidence() -> None:
    record = PubMedRecord(pmid='111', title='Own paper', abstract='', publication_types=())
    assert record.identifier_candidates == ()
    assert 'identifier_candidates' not in record.model_dump(mode='json')
