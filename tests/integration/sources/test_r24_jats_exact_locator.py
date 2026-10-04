"""Exact native JATS replay, not substring or whole-parent table proof."""
import pytest

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.storage.source_derivation import SourceDerivationError, extract_locator_quote

XML = (
    '<article><body><sec><p>Estimate <italic>82.3%</italic>. '
    '<table-wrap><table><tbody><tr><td>Arm</td><td>N</td></tr>'
    '<tr><td>Active</td><td>60</td></tr><tr><td>Placebo</td><td>60</td></tr>'
    '</tbody></table></table-wrap> Count 51/60.</p>'
    '<p>Estimate 82.3%.</p></sec></body></article>'
)
P = '/article/body[1]/sec[1]/p[1]'
CELL = P + '/table-wrap[1]/table[1]/tbody[1]/tr[2]/td[2]'


def quote(xml: str, path: str, media: str = 'application/xml') -> str:
    return extract_locator_quote(xml, media_type=media, locator=EvidenceLocator(
        document_role='original_linked_publication', field_path=path,
        # Deliberately wrong: XML must resolve its exact path, never OR-match anchors.
        paragraph='Estimate 82.3%.', row='Placebo', column='N',
    ))


@pytest.mark.parametrize('media', ['application/xml', 'text/xml'])
def test_exact_cell_not_another_same_value_or_parent(media: str) -> None:
    assert quote(XML, CELL, media) == '60'


def test_paragraph_normalization_excludes_anchored_floating_table() -> None:
    assert quote(XML, P) == 'Estimate 82.3%. Count 51/60.'


def test_known_single_article_wrapper_uses_same_article_path() -> None:
    assert quote('<pmc-articleset>' + XML + '</pmc-articleset>', CELL) == '60'


@pytest.mark.parametrize('path', [
    '/article', '/article/body[1]', '/article//td', CELL.replace('tr[2]', 'tr[*]'),
    CELL.replace('tr[2]', 'tr[0]'), CELL.replace('tr[2]', 'tr[9]'),
    CELL.replace('tr[2]', "tr[@id='other']"), P + '/table-wrap[1]/table[1]',
])
def test_coarse_invalid_or_absent_path_never_falls_back_to_anchor(path: str) -> None:
    with pytest.raises(SourceDerivationError):
        quote(XML, path)


@pytest.mark.parametrize('xml', [
    '<pmc-articleset>' + XML + XML + '</pmc-articleset>',
    '<unknown>' + XML + '</unknown>',
    '<!DOCTYPE article [<!ENTITY unsafe "60">]>' + XML,
    '<article><body>',
])
def test_unsafe_or_ambiguous_xml_is_rejected(xml: str) -> None:
    with pytest.raises(SourceDerivationError):
        quote(xml, CELL)


def test_missing_xml_path_cannot_be_proven_by_title_or_url() -> None:
    with pytest.raises(SourceDerivationError):
        extract_locator_quote(XML, media_type='application/xml', locator=EvidenceLocator(
            document_role='original_linked_publication', paragraph='Estimate 82.3%.',
        ))


def test_plain_text_anchor_behavior_is_unchanged() -> None:
    assert extract_locator_quote('row: 51/60', media_type='text/plain',
        locator=EvidenceLocator(document_role='source', row='row:')) == 'row: 51/60'
