"""Representation changes do not authorize changed clinical values or wider conditions."""
import json

import pytest

from ciw.verify.design_labels import _atoms, _check, _inline_list_labels, _quantities


def atom_case(source, chinese, *, quote=None, condition="", condition_zh=""):
    c = dict(rows=[dict(trial_id="synthetic", design_excerpts=[dict(topic_id="dose", snippets=[dict(
        text=source, condition=condition, cohort_quote="", timeframe="", source_id="synthetic-source",
        field="eligibility", criterion_role="inclusion", context=source+condition)])])])
    atoms = _atoms(c)
    atom = next(iter(atoms.values()))
    item = dict(clause_id=atom['clause_id'], text_zh=chinese, condition_zh=condition_zh,
                cohort_zh="", timeframe_zh="", quote=source if quote is None else quote)
    return c, atoms, item


@pytest.mark.parametrize('indent', ['  ', '\t'])
def test_only_leading_indentation_can_differ_in_the_retained_quote(indent):
    _, atoms, item = atom_case(indent+'The daily dose is 7 mg.', '每日剂量7 mg。', quote='The daily dose is 7 mg.')
    assert _check(item, atoms)[0]
    assert not _check({**item, 'quote': 'The daily dose is 8 mg.'}, atoms)[0]
    assert not _check({**item, 'text_zh': '每日剂量8 mg。'}, atoms)[0]


@pytest.mark.parametrize('value,expected', [('3', True), ('4', False)])
def test_written_cardinal_subject_count_is_preserved(value, expected):
    _, atoms, item = atom_case('Three participants receive 7 mg daily.', f'{value}名受试者每日接受7 mg。')
    assert _check(item, atoms)[0] == expected


def test_grammatical_one_of_is_not_invented_as_a_measurement():
    assert _quantities('One of the following: age ≥21 years.') == _quantities('以下任一：年龄 ≥21岁。')


def test_identical_ordered_labels_can_precede_numeric_items_inline():
    source = '1. 24-hour collection.\n2. 7 mg daily.'
    label = '1. 24小时采集；2. 7 mg每日。'
    assert _quantities(source) == _quantities(_inline_list_labels(label, source))
    # A changed clinical value is not a numbered list marker.
    assert _quantities(source) != _quantities(_inline_list_labels(label.replace('7 mg', '8 mg'), source))
    assert _inline_list_labels(label.replace('2. ', '3. '), source) == label.replace('2. ', '3. ')


def test_html_comment_close_cannot_form_a_comparison_with_the_next_list_number():
    _, atoms, item = atom_case('<!-- source list -->\n1. The daily dose is 7 mg.', '1. 每日剂量7 mg。')
    assert _check(item, atoms)[0]
    assert not _check({**item, 'text_zh': '1. 每日剂量8 mg。'}, atoms)[0]


def test_condition_translation_cannot_be_rebound_to_a_wider_context():
    _, atoms, item = atom_case('The daily dose is 7 mg.', '每日剂量7 mg。',
                              condition='Only if age ≥21 years.', condition_zh='仅年龄 ≥21岁。')
    assert _check(item, atoms)[0]
    valid, reason = _check({**item, 'condition_zh': '仅年龄 ≥21岁且剂量9 mg。'}, atoms)
    assert not valid and 'condition' in reason


def test_saved_exact_verifier_response_is_rechecked_without_rewriting_its_quote(ws):
    from ciw.verify.crosscheck import crosscheck
    from ciw.verify.design_labels import _task, enrich_design_labels
    from ciw.verify.llm import CachedBackend, FakeBackend

    c, atoms, item = atom_case('  The daily dose is 7 mg.', '每日剂量7 mg。', quote='The daily dose is 7 mg.')
    roles = {}
    for family, role in [('deepseek', 'extractor_a'), ('glm', 'verifier')]:
        backend = FakeBackend(family, family+'-synthetic', None)
        def response(system, user, backend=backend, family=family):
            backend.receipt = dict(response_id='synthetic-'+family)
            return json.dumps(dict(items=[item]))
        backend.responder = response
        roles[role] = CachedBackend(backend, ws)
    result = crosscheck(_task(atoms), roles)[0]
    key = 'design-reading:legacy:'+item['clause_id']
    ws.save_verification(key, 'needs_review', dict(item=item, source_id='synthetic-source', calls=result.calls,
                         note='核对结果未通过来源校验：阅读要点未对应当前原文字段'))
    with ws.db() as db:
        before = db.execute('SELECT cache_key,response,metadata FROM llm_cache ORDER BY 1').fetchall()
    assert not enrich_design_labels(ws, c, None)
    record = ws.verifications()[key]
    assert record['status'] == 'verified' and record['item'] == item
    assert record['item']['quote'] == 'The daily dose is 7 mg.'
    with ws.db() as db:
        assert db.execute('SELECT cache_key,response,metadata FROM llm_cache ORDER BY 1').fetchall() == before


@pytest.mark.parametrize('field', ['text', 'condition'])
@pytest.mark.parametrize('label,valid', [
    ('仅年龄≥21岁。', False),
    ('仅活检确诊且年龄≥21岁。', True),
    ('仅biopsy确诊且年龄≥21岁。', True),
])
def test_explicit_biopsy_prerequisite_cannot_disappear_behind_unchanged_age(field,label,valid):
    source='Only if biopsy confirms diagnosis and age ≥21 years.'
    kwargs=dict(condition=source,condition_zh=label) if field=='condition' else {}
    _,atoms,item=atom_case('The daily dose is 7 mg.' if field=='condition' else source,
                         '每日剂量7 mg。' if field=='condition' else label,**kwargs)
    assert _check(item,atoms)[0] == valid


@pytest.mark.parametrize('marker',['）','．','、'])
def test_identical_full_width_ordered_markers_are_not_extra_measurements(marker):
    source='1. The age is ≥21 years.\n2. The daily dose is 7 mg.'
    label=f'1{marker} 年龄≥21岁；2{marker} 每日剂量7 mg。'
    _,atoms,item=atom_case(source,label)
    assert _check(item,atoms)[0]
    assert not _check({**item,'text_zh':label.replace('7 mg','8 mg')},atoms)[0]


@pytest.mark.parametrize('field',['text','condition'])
def test_biopsy_word_presence_does_not_authorize_an_omission_permission(field):
    source='Only if biopsy confirms diagnosis and age ≥21 years.'
    kwargs=dict(condition=source,condition_zh='仅年龄≥21岁，无需活检。') if field=='condition' else {}
    _,atoms,item=atom_case('The daily dose is 7 mg.' if field=='condition' else source,
                         '每日剂量7 mg。' if field=='condition' else '仅年龄≥21岁，无需活检。',**kwargs)
    assert not _check(item,atoms)[0]


def test_actual_source_permission_to_omit_biopsy_remains_a_valid_exception():
    _,atoms,item=atom_case('Biopsy may be omitted if antibody ≥20 RU/mL.', '抗体≥20 RU/mL时可免活检。')
    assert _check(item,atoms)[0]


@pytest.mark.parametrize('source,label',[
    ('Participants may be eligible for the study without undergoing a kidney biopsy, after review.',
     '经审核后参与者可无需进行肾活检而可能符合研究资格。'),
    ('Patients can be included without a new renal biopsy, provided that other criteria apply.',
     '满足其他条件的患者可无需重新肾活检而入组。'),
    ('Diagnosis confirmed by biopsy, or biopsy exemption for antibody ≥20 RU/mL.',
     '经活检确诊，或抗体≥20 RU/mL者可豁免活检。'),
])
def test_source_bound_biopsy_exceptions_are_preserved_not_blanket_rejected(source,label):
    _,atoms,item=atom_case(source,label)
    assert _check(item,atoms)[0]


@pytest.mark.parametrize('source',[
    'Patients cannot be included without a kidney biopsy.',
    'There is no biopsy exemption for these patients.',
])
def test_without_or_exemption_word_alone_does_not_grant_permission(source):
    _,atoms,item=atom_case(source,'患者无需肾活检。')
    assert not _check(item,atoms)[0]


def test_full_width_parenthesis_without_whitespace_preserves_identical_source_order():
    _,atoms,item=atom_case('1. Age ≥21 years.\n2. Daily dose 7 mg.','1）年龄≥21岁；2）每日剂量7 mg。')
    assert _check(item,atoms)[0]
    assert not _check({**item,'text_zh':item['text_zh'].replace('2）','3）')},atoms)[0]
