"""Literal cohort headings label clauses; they do not split studies or their enrollment."""
from copy import deepcopy

import pytest

from ciw.models import Design, Locator, Trial


def mixed(text):
    return Trial(trial_id='synthetic', registry='ctgov', locator=Locator(source_id='source'),
                 conditions=['Condition A (AAA)', 'Condition B'], design=Design(eligibility_text=text, enrollment=24))


@pytest.mark.parametrize('heading', ['Condition A (AAA)', 'For patients with AAA:', '  * Condition A (AAA):'])
def test_source_heading_has_exact_offsets_and_never_uses_an_unrelated_peer(heading):
    from ciw.normalize.design import source_cohort_heading
    text=(f'Inclusion Criteria:\n{heading}\nMarker ≥7 mg.\nCondition B:\nMarker ≥8 mg.\n'
          'Exclusion Criteria:\nMarker <9 mg.')
    trial=mixed(text)
    before=deepcopy(trial)
    bound=source_cohort_heading(trial, 'eligibility', 'Marker ≥7 mg.')
    assert bound and bound['source_id']=='source' and bound['field']=='eligibility'
    assert text[bound['start']:bound['end']]==bound['quote']
    assert bound['label']==bound['quote'] and 'AAA' in bound['quote']
    assert source_cohort_heading(trial, 'eligibility', 'Marker ≥8 mg.')['quote']=='Condition B'
    assert not source_cohort_heading(trial, 'eligibility', 'Marker <9 mg.')
    assert not source_cohort_heading(trial, 'eligibility', 'Marker ≥7 mg.\nCondition B:\nMarker ≥8 mg.')
    assert trial==before and trial.design.enrollment==24


def test_local_primary_qualification_is_a_literal_heading_not_a_global_alias():
    from ciw.normalize.design import source_cohort_heading
    trial=mixed('Primary Condition B:\nMarker ≥7 mg.')
    bound=source_cohort_heading(trial, 'eligibility', 'Marker ≥7 mg.')
    assert bound['quote']=='Primary Condition B'
    assert trial.conditions==['Condition A (AAA)', 'Condition B']
    trial.design.eligibility_text='Condition B has primary and secondary causes.\nMarker ≥7 mg.'
    assert not source_cohort_heading(trial, 'eligibility', 'Marker ≥7 mg.')


@pytest.mark.parametrize('text', [
    'Marker ≥7 mg.\nCondition B:\nMarker ≥8 mg.',
    'Condition A (AAA):\nMarker ≥7 mg.\nCondition B:\nMarker ≥7 mg.',
    'AAA is not a defined cohort here.\nMarker ≥7 mg.',
    'Condition A (AAA) or Condition B:\nMarker ≥7 mg.',
    'Condition A (AAA):\nMarker ≥8 mg.\nOther criteria:\nMarker ≥7 mg.',
])
def test_no_guessed_scope_before_heading_in_duplicate_or_multi_disease_text(text):
    from ciw.normalize.design import source_cohort_heading
    assert not source_cohort_heading(mixed(text), 'eligibility', 'Marker ≥7 mg.')


def test_explicit_inline_heading_preserves_the_source_declared_abbreviation():
    from ciw.normalize.design import source_cohort_heading
    text='* Condition B (BBB): Marker ≥7 mg.\n  1. Daily dose is 8 mg.'
    bound=source_cohort_heading(mixed(text),'eligibility','Daily dose is 8 mg.')
    assert bound['quote']=='Condition B (BBB)' and text[bound['start']:bound['end']]==bound['quote']


def test_shared_list_parent_can_precede_one_cohort_but_cannot_hide_a_second_cohort():
    from ciw.normalize.design import source_cohort_heading
    shared='Inclusion Criteria:\nAll of the following:\n1. Age ≥21 years.\n'
    first='* Condition A (AAA): Diagnosis confirmed by biopsy.\n'
    second='* Condition B: Diagnosis confirmed by antibody.\n'
    trial=mixed(shared+first+second)
    assert source_cohort_heading(trial,'eligibility',shared+first)['quote']=='Condition A (AAA)'
    assert not source_cohort_heading(trial,'eligibility',shared+first+second)


def test_heading_projection_does_not_change_scientific_atom_identity_or_accepted_reading(ws, cfg):
    from ciw.verify.design_labels import _atoms, enrich_design_labels
    text='Condition A (AAA):\nThe daily dose is 7 mg.\nCondition B:\nThe daily dose is 8 mg.'
    trial=mixed(text)
    snippet=dict(text='The daily dose is 7 mg.',source_id='source',field='eligibility',
                 context='The daily dose is 7 mg.')
    c=dict(rows=[dict(trial_id='synthetic',design_excerpts=[dict(topic_id='dose',snippets=[snippet])])])
    atoms=_atoms(c)
    key=next(iter(atoms))
    item=dict(clause_id=key,quote=snippet['text'],text_zh='每日剂量7 mg。',condition_zh='',cohort_zh='',timeframe_zh='')
    ws.write_stage('research-design-reading',dict(items={key:item}))
    assert not enrich_design_labels(ws,c,None,trials=[trial],cfg=cfg)
    assert snippet['source_heading']['quote']=='Condition A (AAA)'
    assert snippet['reading']['text_zh']==item['text_zh'] and _atoms(c)==atoms


def test_new_source_heading_cannot_bind_an_old_source_or_reuse_its_accepted_chinese(ws):
    from ciw.verify.design_labels import _atoms, enrich_design_labels
    text='Condition A (AAA):\nThe daily dose is 7 mg.'
    trial=mixed(text)
    snippet=dict(text='The daily dose is 7 mg.',source_id='source',field='eligibility')
    c=dict(rows=[dict(trial_id='synthetic',design_excerpts=[dict(topic_id='dose',snippets=[snippet])])])
    old=deepcopy(_atoms(c))
    key=next(iter(old))
    item=dict(clause_id=key,quote=snippet['text'],text_zh='每日剂量7 mg。',
              condition_zh='',cohort_zh='',timeframe_zh='')
    ws.write_stage('research-design-reading',dict(items={key:item}))
    trial.locator.source_id='new-content-addressed-source'
    trial.design.eligibility_text=text.replace('Condition A (AAA)', 'Condition B')
    assert not enrich_design_labels(ws,c,None,trials=[trial])
    assert 'source_heading' not in snippet and snippet['reading']['text_zh']==item['text_zh']
    snippet.pop('reading')
    snippet['source_id']=trial.locator.source_id
    assert set(_atoms(c))!=set(old)
    assert enrich_design_labels(ws,c,None,trials=[trial]) and 'reading' not in snippet
    assert snippet['source_heading']['quote']=='Condition B'
