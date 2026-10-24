import json

import pytest
from test_trial_reading_identity import identity_project  # noqa: F401 - shared production fixture

from ciw2.render.portal import render_report, report_data
from ciw2.sources.http import register_text


def add_profile(fixture):
    svc,pid,trial,did,sid=fixture
    rc=svc.context(pid,svc.db.create_run(pid))
    text='Known Group owns Legal Holder. nemolizumab targets IL-31RA; China 特应性皮炎 III期. 2025-12-31.'
    sid=register_text(rc.tool_ctx(),kind='company',url='https://example.org/group',text=text)
    for field,value,context in [
        ('status.china_mah','Legal Holder',{'jurisdiction':'CN'}),
        ('status.china_mah_group','Known Group',{'legal_entity':'Legal Holder','jurisdiction':'CN',
             'relationship':'wholly_owned','as_of':'2025-12-31'}),
        ('identity.target','IL-31RA',{}),
        ('identity.developer','Known Group',{'as_of':'2025-12-31'}),
        ('status.china.development','III期',{'indication':'特应性皮炎','jurisdiction':'CN','as_of':'2025-12-31'}),
    ]:
        svc.db.add_fact({'project_id':pid,'entity_id':did,'field':field,'value':value,'context':context,
            'source_id':sid,'quote':text,'status':'verified','tier':'critical','extracted_by':'code:synthetic'})
    return svc,pid,trial,did,sid


def test_a_uses_current_profile_not_unverified_discovery_fields(identity_project):  # noqa: F811 - pytest fixture
    svc,pid,_,did,_=identity_project
    entity=next(e for e in svc.db.entities(pid,'drug') if e['id']==did)
    svc.db.execute('UPDATE entities SET attrs=? WHERE id=?',(json.dumps({**entity['attrs'],
        'targets':['Unverified Target'],'companies':['Unverified Company'],'highest_phase_china':'approved'}),did))
    row=report_data(svc.db,pid,'A')['rows'][0]
    assert row['targets']==[] and row['companies']==[] and row['phase_china']=='unknown'
    assert 'Unverified Target' not in render_report(svc.db,pid,'A')


def test_shared_profile_and_group_are_reachable_across_a_b_c(identity_project):  # noqa: F811 - pytest fixture
    svc,pid,trial,did,sid=add_profile(identity_project)
    svc.db.add_fact({'project_id':pid,'entity_id':trial,'field':'result.primary.value','value':25.0,
        'status':'verified','tier':'critical','source_id':sid,'quote':'25.0',
        'context':{'endpoint':'EASI-75','timepoint':'Week 16','stat_type':'proportion','unit':'%',
                   'population':'ITT','arm':'Nemolizumab'},'extracted_by':'code:synthetic'})
    a=report_data(svc.db,pid,'A')['rows'][0]
    assert a['targets']==['IL-31RA'] and a['phase_china']=='phase3'
    for report in 'ABC':
        html=render_report(svc.db,pid,report)
        assert 'Known Group' in html and 'Legal Holder' in html and '2025-12-31' in html
        assert 'IL-31RA' in html and 'https://example.org/group' in html
        assert '中国MAH所属集团' in html
    assert svc.db.entities(pid,'drug')[0]['id']==did


@pytest.mark.parametrize('report',list('ABC'))
def test_profile_evidence_uses_one_shared_reader_without_expanding_table_column(identity_project,report):  # noqa: F811
    svc,pid,trial,_,sid=add_profile(identity_project)
    if report=='B':
        svc.db.add_fact({'project_id':pid,'entity_id':trial,'field':'result.primary.value','value':25,
            'status':'verified','tier':'critical','source_id':sid,'quote':'25',
            'context':{'endpoint':'EASI-75','timepoint':'Week 16','stat_type':'proportion','unit':'%',
                       'arm':'Nemolizumab'},'extracted_by':'code:synthetic'})
    html=render_report(svc.db,pid,report)
    assert html.count('id="design-evidence-dialog"')==1
    assert 'class="shared-evidence"' in html
    title='药物身份依据' if report=='A' else '研究身份依据'
    assert f'data-reading-title="{title}"' in html
    for fact in svc.db.current_facts(pid):
        if fact['entity_id']==svc.db.entities(pid,'drug')[0]['id'] and fact['status']=='verified':
            assert f'data-fact-id="{fact["id"]}"' in html


def test_chinese_type_display_deduplicates_known_labels_without_changing_source_values(identity_project):  # noqa: F811
    svc,pid,_,did,_=identity_project
    rc=svc.context(pid,svc.db.create_run(pid))
    text='nemolizumab is a monoclonal antibody (mAb).'
    sid=register_text(rc.tool_ctx(),kind='company',url='https://example.org/modality',text=text)
    for value in ('monoclonal antibody','mAb'):
        svc.db.add_fact({'project_id':pid,'entity_id':did,'field':'identity.modality','value':value,
            'source_id':sid,'quote':text,'status':'verified','tier':'standard','extracted_by':'code:synthetic'})
    before=svc.db.query('SELECT * FROM facts ORDER BY id')
    html=render_report(svc.db,pid,'A')
    assert '<td>单克隆抗体</td>' in html
    assert '单克隆抗体 / 单克隆抗体' not in html and text in html
    assert set(report_data(svc.db,pid,'A')['rows'][0]['modality'].split(' / '))=={'monoclonal antibody','mAb'}
    assert svc.db.query('SELECT * FROM facts ORDER BY id')==before
