"""Shared-source drug identity projection. All fixtures are synthetic."""
import json

import pytest

from ciw2.render.drug_profile import drug_profiles
from ciw2.store.db import DB

QUOTE = '来源原文逐字片段，含 10 mg/kg 与 2025-01-02。'


@pytest.fixture
def project(settings):
    settings.ensure_dirs()
    db = DB(settings.db_path)
    pid = db.create_project('特应性皮炎', ['A'], aliases=['Atopic Dermatitis'])
    return db, pid


def add_drug(db, pid, name='示例单抗注射液', **attrs):
    entity_id, _ = db.upsert_entity(pid, 'drug', name, attrs=attrs or None)
    return entity_id


def add_source(db, pid, name='label', url=None, digest='a' * 64):
    return db.add_source(pid, 'nmpa', url or f'https://example.org/{name}', digest)


def add_fact(db, pid, entity_id, field, value, source_id, *, quote=QUOTE, status='verified',
             context=None, extracted_by='code:test'):
    return db.add_fact({'project_id': pid, 'entity_id': entity_id, 'field': field, 'value': value,
                        'tier': 'critical', 'status': status, 'source_id': source_id, 'quote': quote,
                        'context': {} if context is None else context, 'extracted_by': extracted_by})


def add_holder(db, pid, entity_id, source_id, name='示例药业有限公司', *, status='verified', **overrides):
    context = {'jurisdiction': 'CN'}
    context.update(overrides)
    return add_fact(db, pid, entity_id, 'status.china_mah', name, source_id, status=status, context=context)


def add_group(db, pid, entity_id, source_id, name='示例控股集团', **overrides):
    context = {'legal_entity': '示例药业有限公司', 'relationship': 'subsidiary',
               'jurisdiction': 'CN', 'as_of': '2025-01-02'}
    context.update(overrides)
    return add_fact(db, pid, entity_id, 'status.china_mah_group', name, source_id, context=context)


def add_development(db, pid, entity_id, source_id, value, *, region='china',
                    indication='特应性皮炎', jurisdiction='CN', as_of='2025-05-01'):
    field = 'status.china.development' if region == 'china' else 'status.global.development'
    context = {'indication': indication, 'jurisdiction': jurisdiction, 'as_of': as_of}
    return add_fact(db, pid, entity_id, field, value, source_id, context=context)


EMPTY = {'molecular_types': [], 'mechanism_classes': [], 'targets': [], 'modality': None, 'companies': [], 'group_refs': [],
         'phase_china': 'unknown', 'phase_global': 'unknown', 'profile_refs': [],
         'phase_china_refs': [], 'phase_global_refs': []}


def test_only_verified_current_project_facts_with_quote_count(project):
    db, pid = project
    eid = add_drug(db, pid)
    good = add_source(db, pid)
    other = db.create_project('其他项目', ['A'])
    foreign = db.add_source(other, 'nmpa', 'https://example.org/foreign', 'b' * 64)
    add_fact(db, pid, eid, 'identity.target', 'IL-31RA', good, quote='靶点：IL-31RA')
    add_fact(db, pid, eid, 'identity.target', '未核实靶点', foreign)
    add_fact(db, pid, eid, 'identity.target', '未核实状态靶点', good, status='unverified')
    add_fact(db, pid, eid, 'identity.target', '无引文靶点', good, quote=None)
    add_fact(db, pid, eid, 'identity.target', '空白引文靶点', good, quote='   ')
    add_fact(db, pid, eid, 'identity.target', 42, good)
    profile = drug_profiles(db, pid)[eid]
    assert profile['targets'] == ['IL-31RA']
    assert [ref['value'] for ref in profile['profile_refs']] == ['IL-31RA']


def test_every_drug_appears_including_excluded_candidates(project):
    db, pid = project
    kept = add_drug(db, pid, '甲药')
    dropped = add_drug(db, pid, '乙药')
    db.set_scope(dropped, False, '非目标药物')
    profiles = drug_profiles(db, pid)
    assert set(profiles) == {kept, dropped}
    assert profiles[dropped] == EMPTY


def test_discovery_attributes_never_certify_a_profile(project):
    db, pid = project
    eid = add_drug(db, pid, attrs={'targets': ['IL-31RA'], 'modality': '单抗', 'companies': ['猜测公司'],
                                   'china_mah': '猜测持有人', 'china_mah_group': '猜测集团',
                                   'highest_phase_global': 'approved', 'highest_phase_china': 'phase3'})
    assert drug_profiles(db, pid)[eid] == EMPTY


def test_companies_keep_role_legal_name_quote_and_explicit_context(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    dev = add_fact(db, pid, eid, 'identity.developer', '示例生物科技有限公司', sid,
                   context={'jurisdiction': 'CN', 'as_of': '2025-03-04'})
    rights = add_fact(db, pid, eid, 'identity.rights_holder', '示例药业集团', sid,
                      context={'jurisdiction': 'global'})
    companies = drug_profiles(db, pid)[eid]['companies']
    assert [company['role'] for company in companies] == ['研发方', '研发权益方']
    assert [company['fact_id'] for company in companies] == [dev, rights]
    assert companies[0]['name'] == '示例生物科技有限公司'
    assert companies[0]['source_id'] == sid and companies[0]['url'] == 'https://example.org/label'
    assert companies[0]['quote'] == QUOTE
    assert companies[0]['as_of'] == '2025-03-04' and companies[0]['jurisdiction'] == 'CN'
    assert companies[1]['as_of'] is None and companies[1]['jurisdiction'] == 'global'


def test_non_web_source_url_is_not_presented_as_a_link(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid, 'script', url='javascript:alert(1)')
    add_fact(db, pid, eid, 'identity.developer', '示例生物科技有限公司', sid)
    assert drug_profiles(db, pid)[eid]['companies'][0]['url'] is None


def test_group_requires_verified_holder_exact_relation_and_dated_context(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_holder(db, pid, eid, sid)
    add_group(db, pid, eid, sid)
    refs = drug_profiles(db, pid)[eid]['group_refs']
    assert len(refs) == 1
    assert refs[0]['name'] == '示例控股集团'
    assert refs[0]['legal_entity'] == '示例药业有限公司'
    assert refs[0]['relationship'] == 'subsidiary'
    assert refs[0]['as_of'] == '2025-01-02' and refs[0]['jurisdiction'] == 'CN'
    assert refs[0]['source_id'] == sid and refs[0]['quote'] == QUOTE


@pytest.mark.parametrize('case', [
    'unverified_holder', 'missing_holder', 'affiliate', 'joint_venture', 'unknown_relation',
    'future_as_of', 'bad_as_of', 'missing_as_of', 'foreign_jurisdiction', 'corporate_name_guess',
])
def test_group_does_not_qualify_without_exact_holder_relation(project, case):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    group = {}
    if case != 'missing_holder':
        add_holder(db, pid, eid, sid, status='unverified' if case == 'unverified_holder' else 'verified')
    group.update({'affiliate': {'relationship': 'affiliate'},
                  'joint_venture': {'relationship': 'joint_venture'},
                  'unknown_relation': {'relationship': 'unknown'},
                  'future_as_of': {'as_of': '2999-01-01'},
                  'bad_as_of': {'as_of': '2025-02-30'},
                  'missing_as_of': {'as_of': None},
                  'foreign_jurisdiction': {'jurisdiction': 'US'},
                  'corporate_name_guess': {'legal_entity': '示例药业'}}.get(case, {}))
    add_group(db, pid, eid, sid, **group)
    assert drug_profiles(db, pid)[eid]['group_refs'] == []


def test_multiple_valid_groups_stay_visible_and_dated(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_holder(db, pid, eid, sid)
    add_group(db, pid, eid, sid, '甲控股', relationship='wholly_owned', as_of='2024-05-06')
    add_group(db, pid, eid, sid, '乙控股', relationship='controlled', as_of='2025-07-08')
    first = drug_profiles(db, pid)[eid]['group_refs']
    assert {(ref['name'], ref['relationship'], ref['as_of']) for ref in first} == {
        ('甲控股', 'wholly_owned', '2024-05-06'), ('乙控股', 'controlled', '2025-07-08')}
    assert first == drug_profiles(db, pid)[eid]['group_refs']


def test_development_requires_project_indication_region_and_date(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    china = add_development(db, pid, eid, sid, 'phase2')
    add_development(db, pid, eid, sid, 'Phase III', region='global',
                    indication='Atopic Dermatitis', jurisdiction='global')
    profile = drug_profiles(db, pid)[eid]
    assert profile['phase_china'] == 'phase2'
    assert profile['phase_global'] == 'phase3'
    assert [ref['fact_id'] for ref in profile['phase_china_refs']] == [china]
    assert profile['phase_global_refs'][0]['quote'] == QUOTE


@pytest.mark.parametrize('case', [
    'other_indication', 'missing_indication', 'wrong_region', 'future_as_of', 'missing_as_of',
    'bad_as_of', 'generic_approval',
])
def test_development_does_not_qualify_outside_project_indication_region_or_date(project, case):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    options = {'indication': '特应性皮炎', 'jurisdiction': 'CN', 'as_of': '2025-05-01'}
    value = 'phase2'
    if case == 'other_indication':
        options['indication'] = '银屑病'
    elif case == 'missing_indication':
        options['indication'] = None
    elif case == 'wrong_region':
        options['jurisdiction'] = 'global'
    elif case == 'future_as_of':
        options['as_of'] = '2999-01-01'
    elif case == 'missing_as_of':
        options['as_of'] = None
    elif case == 'bad_as_of':
        options['as_of'] = '2025-1-2'
    elif case == 'generic_approval':
        options['indication'] = None
        value = '已上市'
    add_development(db, pid, eid, sid, value, **options)
    profile = drug_profiles(db, pid)[eid]
    assert profile['phase_china'] == 'unknown'
    assert profile['phase_china_refs'] == []


def test_conflicting_qualified_phases_are_unknown_not_latest_or_max(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_development(db, pid, eid, sid, 'phase2')
    add_development(db, pid, eid, sid, 'phase3')
    profile = drug_profiles(db, pid)[eid]
    assert profile['phase_china'] == 'unknown'
    assert {ref['value'] for ref in profile['phase_china_refs']} == {'phase2', 'phase3'}


def test_unsupported_status_is_retained_but_never_promoted(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_development(db, pid, eid, sid, 'completed')
    add_development(db, pid, eid, sid, '进行中')
    profile = drug_profiles(db, pid)[eid]
    assert profile['phase_china'] == 'unknown'
    assert {ref['value'] for ref in profile['phase_china_refs']} == {'completed', '进行中'}


@pytest.mark.parametrize('raw,phase', [
    ('preclinical', 'preclinical'), ('phase1_2', 'phase1_2'), ('nda_bla', 'nda_bla'),
    ('已上市', 'approved'), ('I 期', 'phase1'), ('II期', 'phase2'), ('Phase III', 'phase3'),
    ('批准上市','approved'),('获批上市','approved'),('Phase 3','phase3'),
    ('phase IV', 'phase4'), ('Ⅰ/Ⅱ期', 'phase1_2'), ('Ⅱ/Ⅲ 期', 'phase2_3'),
])
def test_explicit_codes_and_roman_phase_forms_normalize(project, raw, phase):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_development(db, pid, eid, sid, raw)
    assert drug_profiles(db, pid)[eid]['phase_china'] == phase


def test_bad_context_and_value_types_are_ignored_not_stringified(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_fact(db, pid, eid, 'status.china_mah_group', '示例集团', sid, context=['not', 'a', 'mapping'])
    add_fact(db, pid, eid, 'status.china.development', 'phase2', sid,
             context={'indication': ['特应性皮炎'], 'jurisdiction': 'CN', 'as_of': '2025-05-01'})
    add_fact(db, pid, eid, 'identity.developer', '示例公司', sid,
             context={'as_of': 20250304, 'jurisdiction': {'name': 'CN'}})
    add_fact(db, pid, eid, 'identity.target', None, sid)
    profile = drug_profiles(db, pid)[eid]
    assert profile['group_refs'] == [] and profile['phase_china'] == 'unknown'
    assert profile['targets'] == []
    assert profile['companies'][0]['as_of'] is None
    assert profile['companies'][0]['jurisdiction'] is None


def test_projection_is_read_only(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_holder(db, pid, eid, sid)
    add_group(db, pid, eid, sid)
    add_development(db, pid, eid, sid, 'phase2')
    add_fact(db, pid, eid, 'identity.developer', '示例公司', sid)
    before_facts = db.query('SELECT * FROM facts WHERE project_id=? ORDER BY id', (pid,))
    before_entities = db.query('SELECT * FROM entities WHERE project_id=? ORDER BY id', (pid,))
    before_sources = db.query('SELECT * FROM sources WHERE project_id=? ORDER BY id', (pid,))
    drug_profiles(db, pid)
    assert db.query('SELECT * FROM facts WHERE project_id=? ORDER BY id', (pid,)) == before_facts
    assert db.query('SELECT * FROM entities WHERE project_id=? ORDER BY id', (pid,)) == before_entities
    assert db.query('SELECT * FROM sources WHERE project_id=? ORDER BY id', (pid,)) == before_sources


def test_refs_and_targets_are_deterministically_ordered(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_fact(db, pid, eid, 'identity.target', 'IL-31RA', sid)
    add_fact(db, pid, eid, 'identity.target', 'CD141', sid)
    add_fact(db, pid, eid, 'identity.modality', 'mAb', sid)
    add_fact(db, pid, eid, 'identity.modality', 'ADC', sid)
    profile = drug_profiles(db, pid)[eid]
    assert profile['targets'] == ['CD141', 'IL-31RA']
    assert profile['modality'] == 'ADC / mAb'
    assert [ref['field'] for ref in profile['profile_refs']] == [
        'identity.target', 'identity.target', 'identity.modality', 'identity.modality']
    assert json.dumps(profile, sort_keys=True, ensure_ascii=False) == json.dumps(
        drug_profiles(db, pid)[eid], sort_keys=True, ensure_ascii=False)


def test_profile_fields_are_plain_strings_and_context_is_a_copy(project):
    db, pid = project
    eid = add_drug(db, pid)
    sid = add_source(db, pid)
    add_fact(db, pid, eid, 'identity.target', '<b>IL-31RA</b>', sid,
             context={'raw': '<img src=x onerror=alert(1)>'})
    profile = drug_profiles(db, pid)[eid]
    assert profile['targets'] == ['<b>IL-31RA</b>']
    profile['profile_refs'][0]['context']['raw'] = 'changed'
    assert drug_profiles(db, pid)[eid]['profile_refs'][0]['context']['raw'] == '<img src=x onerror=alert(1)>'


def test_empty_project_and_unknown_project_contract(project):
    db, pid = project
    assert drug_profiles(db, pid) == {}
    with pytest.raises(AssertionError):
        drug_profiles(db, 'prj_missing')


def test_sources_outside_the_project_never_anchor_a_group(project):
    db, pid = project
    eid = add_drug(db, pid)
    other = db.create_project('其他项目', ['A'])
    foreign = db.add_source(other, 'nmpa', 'https://example.org/foreign', 'd' * 64)
    add_holder(db, pid, eid, foreign)
    add_group(db, pid, eid, foreign)
    assert drug_profiles(db, pid)[eid]['group_refs'] == []
