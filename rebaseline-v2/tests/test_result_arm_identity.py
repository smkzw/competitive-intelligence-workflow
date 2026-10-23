import pytest

from ciw2.render.portal import data_b, render_report
from ciw2.service import Service


@pytest.fixture
def workspace(settings):
    svc = Service(settings)
    pid = svc.create_project('组别身份', ['B'])
    tid, _ = svc.db.upsert_entity(pid, 'trial', 'NCT00000001')
    sid = svc.db.add_source(pid, 'ctgov', 'https://example.org/study', 'a' * 64)
    return svc.db, pid, tid, sid


def drug(w, name, *, aliases=None, chinese=None, linked=True):
    db, pid, tid, _ = w
    eid, _ = db.upsert_entity(pid, 'drug', name, aliases=aliases, name_zh=chinese)
    if chinese:
        db.add_fact({'project_id':pid,'entity_id':eid,'source_id':w[3],
            'field':'identity.name_zh','value':chinese,'quote':chinese,
            'tier':'standard','status':'verified','extracted_by':'code:test'})
    if linked:
        db.link(pid, eid, 'drug-trial', tid)
    return eid


def fact(w, field, value, *, context=None, source=None, status='verified'):
    db, pid, tid, sid = w
    return db.add_fact({'project_id': pid, 'entity_id': tid, 'field': field, 'value': value,
                        'source_id': source or sid, 'tier': 'standard', 'status': status, 'extracted_by': 'code:ctgov',
                        'context': context or {}, 'quote': 'Original source'})


def arm(w, label, interventions, **kw):
    return fact(w, 'design.arms', [{'label': label, 'interventions': interventions}], **kw)


def result(w, label, **kw):
    return fact(w, 'result.primary.value', 23, context={'arm': label, 'endpoint': 'Score',
                'timepoint': 'Week 12', 'stat_type': 'mean', 'unit': 'points'}, **kw)


def row(w):
    return data_b(w[0], w[1])['results'][0]


@pytest.mark.parametrize('name,chinese,label,intervention', [
    ('KX', None, '组甲', 'DRUG: KX'),
    ('AB-CD', None, 'Arm A', 'BIOLOGICAL: AB-CD'),
    ('Original', '正式药名', '治疗组', 'Drug: 正式药名'),
])
def test_explicit_relation_resolves_short_chinese_and_punctuated_names(workspace, name, chinese, label, intervention):
    drug(workspace, name, chinese=chinese)
    design = arm(workspace, label, [intervention])
    result(workspace, label)
    projected = row(workspace)
    assert projected['arm_drugs'] == [name]
    assert projected['drugs'] == [name]
    assert projected['arm_binding_refs'] == [design]
    assert projected['arm_binding_status'] == 'resolved'
    assert name in data_b(workspace[0], workspace[1])['charts']['groups'][0]['labels'][0]


@pytest.mark.parametrize('intervention', ['Drug: ABCD', 'Drug: ABCD-123', 'Drug: AB-CD + Another'])
def test_punctuation_prefix_or_composite_cannot_imply_one_drug(workspace, intervention):
    drug(workspace, 'AB-CD', aliases=['Placebo'])
    arm(workspace, 'AB-CD treatment arm', [intervention])
    result(workspace, 'AB-CD treatment arm')
    projected = row(workspace)
    assert projected['arm_drugs'] == []
    assert projected['drugs'] == []
    assert projected['arm_binding_status'] == 'unresolved'
    assert projected['arm'] == 'AB-CD treatment arm' and projected['value'] == 23


def test_control_group_not_labelled_with_trial_drugs(workspace):
    drug(workspace, 'Active', aliases=['Placebo'])
    arm(workspace, 'Placebo', ['Drug: Placebo'])
    result(workspace, 'Placebo')
    projected = row(workspace)
    assert projected['drugs'] == [] and projected['trial_drugs'] == ['Active']
    assert projected['arm_binding_status'] == 'control'


def test_combination_preserves_every_declared_drug(workspace):
    drug(workspace, 'Beta')
    drug(workspace, 'Alpha')
    arm(workspace, 'Combination', ['DRUG: Beta', 'DRUG: Alpha'])
    result(workspace, 'Combination')
    projected = row(workspace)
    assert projected['arm_drugs'] == ['Alpha', 'Beta']
    assert projected['arm_drug'] == 'Alpha / Beta'


def test_shared_alias_and_conflicting_relations_do_not_pick_first(workspace):
    drug(workspace, 'Alpha', aliases=['Shared'])
    drug(workspace, 'Beta', aliases=['Shared'])
    arm(workspace, 'Arm A', ['Drug: Shared'])
    result(workspace, 'Arm A')
    assert row(workspace)['arm_binding_reason'] == 'ambiguous_drug_identity'
    arm(workspace, 'Arm A', ['Drug: Alpha'])
    assert row(workspace)['arm_binding_reason'] == 'conflicting_arm_relations'


def test_cross_source_and_unverified_design_cannot_bind_result(workspace):
    drug(workspace, 'Alpha')
    other = workspace[0].add_source(workspace[1], 'ctgov', 'https://example.org/old', 'b' * 64)
    arm(workspace, 'Alpha', ['Drug: Alpha'], source=other)
    arm(workspace, 'Alpha', ['Drug: Alpha'], status='unverified')
    result(workspace, 'Alpha')
    assert row(workspace)['arm_binding_reason'] == 'source_arm_relation_missing'


def test_project_and_trial_candidates_cannot_supply_unrelated_identity(workspace):
    drug(workspace, 'Alpha', linked=False)
    arm(workspace, 'Arm A', ['Drug: Alpha'])
    result(workspace, 'Arm A')
    assert row(workspace)['arm_binding_reason'] == 'unresolved_drug_identity'


def test_same_arm_title_in_another_study_does_not_leak(workspace):
    db, pid, _, sid = workspace
    other_tid, _ = db.upsert_entity(pid, 'trial', 'NCT00000002')
    second = db, pid, other_tid, sid
    drug(workspace, 'Alpha')
    arm(second, 'Alpha', ['Drug: Alpha'])
    result(workspace, 'Alpha')
    assert row(workspace)['arm_binding_reason'] == 'source_arm_relation_missing'


def test_table_and_chart_use_same_explicit_arm_binding(workspace):
    drug(workspace, 'Alpha')
    drug(workspace, 'Beta')
    arm(workspace, 'Arm A', ['Drug: Alpha'])
    result(workspace, 'Arm A')
    html = render_report(workspace[0], workspace[1], 'B')
    assert '<td>Alpha</td>' in html
    assert '<td>Alpha/Beta</td>' not in html and '<td>Beta/Alpha</td>' not in html
