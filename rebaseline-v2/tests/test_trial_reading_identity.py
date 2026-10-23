import json

import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.render.portal import render_report, report_data
from ciw2.service import Service
from ciw2.sources.ctgov import API, _activate_trial
from ciw2.sources.http import register_text


@pytest.fixture
def identity_project(settings,study):
    svc=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=svc.create_project('特应性皮炎',['A','B','C'])
    svc.db.execute('UPDATE projects SET indication_aliases=? WHERE id=?',
        (json.dumps(['Atopic Dermatitis']),pid))
    rc=svc.context(pid,svc.db.create_run(pid))
    study['protocolSection']['conditionsModule']={'conditions':['Atopic Dermatitis']}
    study['protocolSection']['sponsorCollaboratorsModule']={'leadSponsor':{'name':'Source Sponsor Ltd.'}}
    sid=register_text(rc.tool_ctx(),kind='ctgov',url=f'{API}/NCT03985943',text=json.dumps(study))
    trial=_activate_trial(rc.tool_ctx(),'NCT03985943',study,sid,'test')['entity_id']
    drug,_=svc.db.upsert_entity(pid,'drug','nemolizumab',name_zh='奈莫利珠单抗',
        attrs={'china_mah':'Unverified Holder','china_mah_group':'Guessed Group'})
    svc.db.link(pid,drug,'drug-trial',trial)
    return svc,pid,trial,drug,sid


def test_c_foregrounds_clinical_identity_and_keeps_registry_id_secondary(identity_project):
    svc,pid,trial,_,_=identity_project
    row=report_data(svc.db,pid,'C')['rows'][0]
    assert row['identity']['drug_label']=='奈莫利珠单抗'
    assert row['identity']['indication']=='特应性皮炎'
    assert row['identity']['phase_label']=='III 期'
    assert row['identity']['companies'][0]['role']=='申办方'
    assert row['identity']['companies'][0]['name']=='Source Sponsor Ltd.'
    assert 'NCT03985943' not in row['identity']['label']
    assert report_data(svc.db,pid,'C')['charts']['size']['identities'][0]['registry_id']=='NCT03985943'
    html=render_report(svc.db,pid,'C')
    assert 'class="trial-clinical-name"' in html and 'class="registry-id"' in html
    assert 'Unverified Holder' not in html and 'Guessed Group' not in html
    assert 'Unverified Holder' not in render_report(svc.db,pid,'A')
    assert 'data-trial="NCT03985943"' in html
    assert svc.db.entities(pid,'trial')[0]['id']==trial


def test_mah_uses_verified_project_source_not_unchecked_company_attrs(identity_project):
    from ciw2.render.trial_identity import trial_identities
    svc,pid,trial,drug,sid=identity_project
    fid=svc.db.add_fact({'project_id':pid,'entity_id':drug,'field':'status.china_mah',
        'value':'Verified Legal Holder','status':'verified','tier':'critical','source_id':sid,
        'quote':'Verified Legal Holder','context':{'jurisdiction':'CN'},'extracted_by':'code:test'})
    ident=trial_identities(svc.db,pid)[trial]
    holder=next(c for c in ident['companies'] if c['role']=='中国MAH')
    assert holder['name']=='Verified Legal Holder' and holder['fact_id']==fid and holder['source_id']==sid
    assert not any(c['name']=='Guessed Group' for c in ident['companies'])


def test_unverified_or_foreign_source_mah_does_not_become_displayed_holder(identity_project):
    from ciw2.render.trial_identity import trial_identities
    svc,pid,trial,drug,sid=identity_project
    other=svc.create_project('Other',['C'])
    foreign=svc.db.add_source(other,'web','https://example.org/other','test')
    for status,source,name in [('unverified',sid,'Unverified'),('verified',foreign,'Foreign')]:
        svc.db.add_fact({'project_id':pid,'entity_id':drug,'field':'status.china_mah','value':name,
            'status':status,'tier':'critical','source_id':source,'quote':name,'extracted_by':'code:test'})
    assert all(c['role']!='中国MAH' for c in trial_identities(svc.db,pid)[trial]['companies'])


def test_original_disease_context_not_replaced_by_unrelated_project_label(identity_project):
    from ciw2.render.trial_identity import trial_identities
    svc,pid,trial,_,_=identity_project
    attrs=svc.db.entities(pid,'trial')[0]['attrs']
    attrs['conditions']=['Source disease without established translation']
    svc.db.execute('UPDATE entities SET attrs=? WHERE id=?',(json.dumps(attrs),trial))
    ident=trial_identities(svc.db,pid)[trial]
    assert ident['indication']=='Source disease without established translation'
    assert ident['scope_indication']=='特应性皮炎'


@pytest.mark.parametrize('condition,short',[
    ('本品适用于治疗急性湿疹、接触性皮炎、特应性皮炎、慢性湿疹。','特应性皮炎'),
    ('本品适用于治疗非特应性皮炎。','本品适用于治疗非特应性皮炎。'),
    ('本品适用于治疗特应性皮炎，但不包括中重度患者。','本品适用于治疗特应性皮炎，但不包括中重度患者。'),
])
def test_explicit_multi_indication_list_focus_is_concise_and_complete_original_remains_reachable(identity_project,condition,short):
    from ciw2.render.trial_identity import trial_identities
    svc,pid,trial,_,_=identity_project
    attrs=svc.db.entities(pid,'trial')[0]['attrs']
    attrs['conditions']=[condition]
    svc.db.execute('UPDATE entities SET attrs=? WHERE id=?',(json.dumps(attrs),trial))
    ident=trial_identities(svc.db,pid)[trial]
    assert ident['indication']==short and ident['conditions_original']==[condition]
    html=render_report(svc.db,pid,'C')
    assert condition in html
    if short!=condition:assert '原登记适应症' in html


def test_result_points_and_a_trial_list_share_context_without_changing_arm_identity(identity_project):
    svc,pid,trial,drug,sid=identity_project
    svc.db.add_fact({'project_id':pid,'entity_id':trial,'field':'result.primary.value','value':25.0,
        'status':'verified','tier':'critical','source_id':sid,'quote':'25.0',
        'context':{'endpoint':'EASI-75','timepoint':'Week 16','stat_type':'proportion','unit':'%',
                   'population':'ITT','arm':'Nemolizumab'},'extracted_by':'code:test'})
    b=report_data(svc.db,pid,'B')
    row=next(r for r in b['results'] if r['value']==25.0)
    assert row['identity']['drug_label']=='奈莫利珠单抗'
    point=next(p for g in b['charts']['groups'] for p in g['points'] if p['fact_id']==row['id'])
    assert 'III 期' in point['trial_label'] and '特应性皮炎' in point['trial_label']
    assert point['trial']=='NCT03985943'
    a=report_data(svc.db,pid,'A')['rows'][0]
    assert a['trials'][0]['registry_id']=='NCT03985943'
    assert a['trials'][0]['drug_label']=='奈莫利珠单抗'
    assert svc.db.entities(pid,'drug')[0]['id']==drug


def test_identity_does_not_turn_source_strings_into_executable_links(identity_project):
    svc,pid,trial,_,_=identity_project
    attrs=svc.db.entities(pid,'trial')[0]['attrs']
    attrs['url']='javascript:alert(1)'
    attrs['sponsor']='<img src=x onerror=alert(1)>'
    svc.db.execute('UPDATE entities SET attrs=? WHERE id=?',(json.dumps(attrs),trial))
    html=render_report(svc.db,pid,'C')
    assert 'href="javascript:' not in html
    assert '<img src=x onerror' not in html and '&lt;img' in html


def test_readonly_legacy_registry_keeps_source_backed_sponsor_without_migration(identity_project):
    from ciw2.render.trial_identity import trial_identities
    svc,pid,trial,_,sid=identity_project
    svc.db.execute("DELETE FROM links WHERE project_id=? AND src=? AND rel='ctgov-current'",(pid,trial))
    before=svc.db.query('SELECT * FROM facts WHERE project_id=? ORDER BY id',(pid,))
    identity=trial_identities(svc.db,pid)[trial]
    assert identity['companies'][0]['name']=='Source Sponsor Ltd.'
    assert identity['companies'][0]['source_id']==sid
    assert svc.db.query('SELECT * FROM facts WHERE project_id=? ORDER BY id',(pid,))==before


def test_legacy_multi_version_registry_does_not_guess_which_sponsor_is_current(identity_project):
    from ciw2.render.trial_identity import trial_identities
    svc,pid,trial,_,_=identity_project
    svc.db.execute("DELETE FROM links WHERE project_id=? AND src=? AND rel='ctgov-current'",(pid,trial))
    sid=svc.db.add_source(pid,'ctgov','https://example.org/second','other')
    svc.db.add_fact({'project_id':pid,'entity_id':trial,'field':'design.phase','value':'phase2',
        'tier':'standard','status':'verified','source_id':sid,'extracted_by':'code:ctgov'})
    assert all(c['role']!='申办方' for c in trial_identities(svc.db,pid)[trial]['companies'])
