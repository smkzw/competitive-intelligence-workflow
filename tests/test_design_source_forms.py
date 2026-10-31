"""Literal protocol forms recover valid B items without weakening source scope."""
import pytest

from ciw.normalize.design import _criterion_role
from ciw.verify.design_clauses import DesignTopicReview, _check


def checked(source, text, *, field='eligibility', kind='eligibility_threshold', condition='',
            protocol_quote='', role='inclusion', quote=None):
    item=DesignTopicReview(topic_id='t',quote=source,clauses=[dict(field=field,text=text,
        quote=source if quote is None else quote,condition=condition,protocol_quote=protocol_quote,
        criterion_role=role)]).model_dump()
    return _check(item,{'t':dict(kind=kind)},[('source',source,field)])[0]


def test_criteria_mentions_inside_prose_do_not_change_the_actual_section_role():
    source='Inclusion Criteria:\nPatients meet inclusion/exclusion criteria.\neGFR ≥7 mL/min.'
    assert checked(source,'eGFR ≥7 mL/min.')
    assert not checked(source,'eGFR ≥7 mL/min.',role='exclusion')


def test_unique_quote_locates_a_repeated_criterion_without_silently_using_first_occurrence():
    source='Inclusion Criteria:\neGFR ≥7 mL/min.\nExclusion Criteria:\neGFR ≥7 mL/min.'
    quote='Exclusion Criteria:\neGFR ≥7 mL/min.'
    assert _criterion_role(source,'eGFR ≥7 mL/min.')=='unspecified'
    assert checked(source,'eGFR ≥7 mL/min.',quote=quote,role='exclusion')
    assert not checked(source,'eGFR ≥7 mL/min.',quote=quote,role='inclusion')


@pytest.mark.parametrize('marker',['4.','5)','* 5.'])
def test_source_backed_numeric_marker_is_part_of_a_literal_parent_not_a_clinical_quantity(marker):
    header=f'{marker} Patients must meet more than three of following items:'
    source=f'Inclusion Criteria:\n{header}\n  * eGFR ≥7 mL/min.\n  * Marker Q ≥8 mg.'
    assert checked(source,'eGFR ≥7 mL/min.',condition=header)
    assert not checked(source,'eGFR ≥7 mL/min.',condition=header.replace('three','two'))
    assert not checked(source,'eGFR ≥7 mL/min.',condition='9. '+header.split(' ',1)[1])


def test_numeric_parent_cannot_borrow_an_identical_child_from_a_peer_branch():
    source=('Inclusion Criteria:\n4. Meets all following items:\n  * eGFR ≥7 mL/min.\n'
            '5. Meets any following items:\n  * eGFR ≥7 mL/min.')
    assert not checked(source,'eGFR ≥7 mL/min.',condition='4. Meets all following items:')


@pytest.mark.parametrize('source,text',[
    ('Four dose cohorts, each receiving a single IV dose of 7 mg.', 'a single IV dose of 7 mg'),
    ('Participants who meet the prespecified assessment '+('after review, '*12)+
     'will receive a second course of 7 mg.', 'a second course of 7 mg'),
])
def test_explicit_cohort_or_conditional_participant_operation_is_not_rejected_by_a_magic_character_window(source,text):
    assert checked(source,text,field='detailed_description',kind='dosing_regimen',
                   protocol_quote=source,role='unspecified')


def test_an_adjacent_recommendation_cannot_borrow_a_real_protocol_sentence():
    source='Participants will receive 7 mg. A 9 mg dose is recommended for future studies.'
    assert not checked(source,'A 9 mg dose is recommended for future studies.',field='detailed_description',
                       kind='dosing_regimen',protocol_quote=source,role='unspecified')


@pytest.mark.parametrize('family',['role','operation'])
def test_newly_supported_forms_recheck_the_exact_saved_B_without_more_calls(cfg,ws,monkeypatch,family):
    from test_retained_source_facts import cached_roles

    import ciw.verify.design_clauses as clauses
    from ciw.analyze.design import build_design
    from ciw.config import DesignTopicCfg
    from ciw.models import Design, Locator, Trial

    cfg=cfg.model_copy(deep=True)
    if family=='role':
        source='Inclusion Criteria:\nAll following apply:\n  * eGFR ≥7 mL/min.'
        cfg.design_topics=[DesignTopicCfg(label='eGFR入排阈值',patterns=['eGFR'])]
        design=Design(eligibility_text=source)
        data=dict(field='eligibility',text='eGFR ≥7 mL/min.',quote=source,
                  condition='All following apply:',criterion_role='inclusion')
        name='_criterion_role'
        old=getattr(clauses,name)
        monkeypatch.setattr(clauses,name,lambda *args:'exclusion')
    else:
        source='Four dose cohorts, each receiving a single IV dose of 7 mg.'
        cfg.design_topics=[DesignTopicCfg(label='给药',patterns=['dose'],kind='dosing_regimen')]
        design=Design(detailed_description=source)
        data=dict(field='detailed_description',text=source,quote=source,
                  protocol_quote=source,criterion_role='unspecified')
        name='_protocol_sentence'
        old=getattr(clauses,name)
        monkeypatch.setattr(clauses,name,lambda *args:False)
    trial=Trial(trial_id='synthetic',registry='ctgov',locator=Locator(source_id='s'),design=design)
    item=clauses.DesignTopicReview(topic_id='design-topic-0',quote=source,clauses=[data]).model_dump()
    assert clauses.enrich_design_clauses(ws,cfg,[trial],build_design(cfg,[trial],{}),cached_roles(ws,[item]))
    with ws.db() as db:
        before=db.execute('SELECT * FROM llm_cache ORDER BY cache_key').fetchall()
    original=next(v for v in ws.verifications().values() if v.get('item'))
    assert original['status']=='needs_review'
    monkeypatch.setattr(clauses,name,old)
    assert not clauses.enrich_design_clauses(ws,cfg,[trial],build_design(cfg,[trial],{}),None)
    record=next(v for v in ws.verifications().values() if v.get('item'))
    assert record['status']=='verified' and record['item']==item and record['calls']==original['calls']
    with ws.db() as db:
        assert db.execute('SELECT * FROM llm_cache ORDER BY cache_key').fetchall()==before


def test_repair_feedback_identifies_the_bad_clause_and_real_field_ids():
    source='Inclusion Criteria:\neGFR ≥7 mL/min.'
    item=DesignTopicReview(topic_id='t',quote=source,clauses=[dict(
        field='arm:A0 (label)',text='eGFR ≥7 mL/min.',quote=source,criterion_role='inclusion')]).model_dump()
    ok,reason=_check(item,{'t':dict(kind='eligibility_threshold')},[('source',source,'eligibility')])
    assert not ok and 'clauses[0]' in reason and 'field=arm:A0 (label)' in reason
    assert '可用字段：eligibility' in reason
