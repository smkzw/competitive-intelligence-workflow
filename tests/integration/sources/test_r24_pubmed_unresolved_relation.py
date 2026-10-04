"""A missing target identifier is not scientific evidence of unrelatedness."""
from __future__ import annotations

import pytest

from ci_workflow.reports.b.contracts import build_trial_role_output
from ci_workflow.reports.common.study_roles import StudyRole
from ci_workflow.sources.connectors.pubmed import (
    PubMedRecord,
    classify_pubmed_records,
    parse_pubmed_efetch_xml,
)
from tests.reports.b.test_trial_roles import _candidate


@pytest.mark.parametrize('abstract', [
    'Primary endpoint results are reported for this randomized study.',
    'Forty-one adults received cream for 48–52 weeks; skin damage scores improved.',
    'A randomized phase 3 trial reported its primary endpoint response rate of 55%.',
    'Only another registration is named here: NCT00000002.',
    'An inexact identifier NCT000000019 cannot establish a relationship.',
    '',
])
def test_target_not_matched_remains_unclassified_and_available(abstract: str) -> None:
    record = PubMedRecord(pmid='99900004', title='Potentially relevant trial paper',
                          abstract=abstract, publication_types=('Randomized Controlled Trial',))
    classified, = classify_pubmed_records((record,), target_nct_ids=('NCT00000001',))
    assert classified.role == 'unclassified'
    assert classified.record == record
    assert classified.matched_nct_ids == ()
    assert not classified.can_replace_primary_report
    assert '未确定' in classified.rationale_zh and '排除' in classified.rationale_zh


def test_unresolved_paper_keeps_independently_qualified_b_trial_role() -> None:
    record = PubMedRecord(pmid='99900004', title='Potential related publication',
                          abstract='', publication_types=('Journal Article',))
    classified, = classify_pubmed_records((record,), target_nct_ids=('NCT00000001',))
    output = build_trial_role_output(_candidate(), publication=classified)
    assert output.study_role is StudyRole.CORE
    assert output.publication_id == record.pmid
    assert output.publication_role == 'unclassified'
    assert output.publication_matched_study_ids == ()


def test_comment_reference_or_unknown_token_cannot_promote_unknown_to_primary() -> None:
    xml = '''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>99900004</PMID>
    <Article><ArticleTitle>A randomized study</ArticleTitle><Abstract><AbstractText>
    Primary endpoint results were reported.</AbstractText></Abstract>
    <PublicationTypeList><PublicationType>Randomized Controlled Trial</PublicationType>
    </PublicationTypeList></Article></MedlineCitation><PubmedData><ReferenceList>
    <Reference><Citation>NCT00000001</Citation></Reference></ReferenceList></PubmedData>
    </PubmedArticle></PubmedArticleSet>'''
    record, = parse_pubmed_efetch_xml(xml)
    classified, = classify_pubmed_records((record,), target_nct_ids=('NCT00000001',))
    assert classified.role == 'unclassified'
    assert classified.matched_nct_ids == ()
    forged = classified.model_copy(update={'role': 'primary_report',
                                          'matched_nct_ids': ('NCT00000001',),
                                          'can_replace_primary_report': True})
    with pytest.raises(ValueError, match='重新分类'):
        build_trial_role_output(_candidate(), publication=forged)
