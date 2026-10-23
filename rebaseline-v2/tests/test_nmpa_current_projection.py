"""Current certificate identity is common data, not a renderer name dictionary."""
import pytest

from ciw2.render.portal import report_data
from ciw2.service import Service


@pytest.fixture
def workspace(settings):
    svc=Service(settings)
    pid=svc.create_project('研究适应症',['A','B','C'])
    drug,_=svc.db.upsert_entity(pid,'drug','Drug A Injection',name_zh='未经证实的旧显示名')
    trial,_=svc.db.upsert_entity(pid,'trial','NCT00000001',attrs={'conditions':['研究适应症']})
    svc.db.link(pid,drug,'drug-trial',trial)
    sid=svc.db.add_source(pid,'nmpa','https://datasearch.nmpa.gov.cn/record','a'*64)
    return svc,pid,drug,trial,sid


def atom(w,field,value,*,sid=None,snapshot='s1',number='国药准字S20240001',status='verified'):
    svc,pid,drug,_,source=w
    return svc.db.add_fact({'project_id':pid,'entity_id':drug,'source_id':sid or source,
        'field':field,'value':value,'tier':'critical','status':status,'extracted_by':'code:nmpa',
        'quote':value,'context':{'source_snapshot':snapshot,'registration_number':number,
        'category':'境内生产药品','jurisdiction':'CN'}})


def activate(w,*,sid=None,snapshot='s1',number='国药准字S20240001'):
    from ciw2.sources.nmpa_ingest import EXTRACTOR_VERSION
    svc,pid,drug,_,source=w
    svc.db.link(pid,drug,'nmpa-current',sid or source,attrs={'snapshot':snapshot,
        'registration_number':number,'category':'境内生产药品','extractor_version':EXTRACTOR_VERSION})


def test_nmpa_atoms_without_matching_activation_are_not_current(workspace):
    atom(workspace,'identity.name_zh','药物甲注射液')
    assert workspace[0].db.current_facts(workspace[1])==[]


@pytest.mark.parametrize('mismatch',['snapshot','certificate','category'])
def test_activation_must_bind_snapshot_and_certificate_not_only_source(workspace,mismatch):
    import json

    from ciw2.sources.nmpa_ingest import EXTRACTOR_VERSION
    atom(workspace,'status.china_mah','原法律实体')
    activate(workspace)
    svc,pid,drug,_,_=workspace
    attrs={'snapshot':'s1','registration_number':'国药准字S20240001','category':'境内生产药品',
           'extractor_version':EXTRACTOR_VERSION}
    attrs[{'snapshot':'snapshot','certificate':'registration_number','category':'category'}[mismatch]]='wrong'
    svc.db.execute("UPDATE links SET attrs=? WHERE project_id=? AND src=? AND rel='nmpa-current'",
                   (json.dumps(attrs),pid,drug))
    assert svc.db.current_facts(pid)==[]


def test_other_certificates_remain_current_but_replaced_snapshot_stays_history(workspace):
    svc,pid,_,_,_=workspace
    old=atom(workspace,'status.china_mah','旧法律实体')
    sid2=svc.db.add_source(pid,'nmpa','https://datasearch.nmpa.gov.cn/record','b'*64)
    current=atom(workspace,'status.china_mah','新法律实体',sid=sid2,snapshot='s2')
    activate(workspace,sid=sid2,snapshot='s2')
    third=svc.db.add_source(pid,'nmpa','https://datasearch.nmpa.gov.cn/other','c'*64)
    other=atom(workspace,'status.china_mah','其他剂型许可实体',sid=third,snapshot='s3',number='国药准字S20240002')
    activate(workspace,sid=third,snapshot='s3',number='国药准字S20240002')
    assert {f['id'] for f in svc.db.current_facts(pid)}=={current,other}
    assert svc.db.one('SELECT id FROM facts WHERE id=?',(old,))


def test_all_portals_use_verified_name_instead_of_discovery_label(workspace):
    svc,pid,drug,trial,sid=workspace
    formal=atom(workspace,'identity.name_zh','药物甲注射液')
    atom(workspace,'status.china_mah','持有人法律实体')
    activate(workspace)
    svc.db.add_fact({'project_id':pid,'entity_id':trial,'source_id':sid,'field':'design.arms',
        'value':[{'label':'Arm A','interventions':['DRUG: Drug A Injection']}],
        'tier':'standard','status':'verified','extracted_by':'code:test'})
    svc.db.add_fact({'project_id':pid,'entity_id':trial,'source_id':sid,'field':'result.primary.value',
        'value':24,'tier':'critical','status':'verified','extracted_by':'code:test',
        'context':{'arm':'Arm A','endpoint':'Score','timepoint':'Week 12','stat_type':'mean','unit':'points'}})
    a=report_data(svc.db,pid,'A')['rows'][0]
    b=report_data(svc.db,pid,'B')['results'][0]
    c=report_data(svc.db,pid,'C')['rows'][0]
    assert a['name_zh']==b['identity']['drug_label']==c['identity']['drug_label']=='药物甲注射液'
    assert a['name_refs'][0]['fact_id']==formal
    assert b['display_drugs']==['药物甲注射液']
    assert '药物甲注射液' in b['arm_drug_label']
    assert {company['name'] for company in c['identity']['companies']}=={'持有人法律实体'}
    assert svc.db.entities(pid,'drug')[0]['name_zh']=='未经证实的旧显示名'
    assert svc.db.entities(pid,'drug')[0]['id']==drug


@pytest.mark.parametrize('invalid',['discovery_only','unverified','foreign_project'])
def test_unproven_name_cannot_be_presented_as_formal_chinese_identity(workspace,invalid):
    svc,pid,_,_,_=workspace
    if invalid!='discovery_only':
        sid=None
        if invalid=='foreign_project':
            other=svc.create_project('其他项目',['A'])
            sid=svc.db.add_source(other,'nmpa','https://datasearch.nmpa.gov.cn/other','d'*64)
        atom(workspace,'identity.name_zh','错误来源中文名',sid=sid,
             status='unverified' if invalid=='unverified' else 'verified')
        activate(workspace,sid=sid)
    assert report_data(svc.db,pid,'A')['rows'][0]['name_zh'] is None
    from ciw2.render.trial_identity import trial_identities
    assert trial_identities(svc.db,pid)[workspace[3]]['drug_label']=='Drug A Injection'


def test_multiple_verified_names_remain_explicit_not_first_wins(workspace):
    svc,pid,_,_,_=workspace
    atom(workspace,'identity.name_zh','药物甲注射液')
    activate(workspace)
    sid=svc.db.add_source(pid,'nmpa','https://datasearch.nmpa.gov.cn/other','e'*64)
    atom(workspace,'identity.name_zh','药物甲注射剂',sid=sid,snapshot='s2',number='国药准字S20240002')
    activate(workspace,sid=sid,snapshot='s2',number='国药准字S20240002')
    assert set(report_data(svc.db,pid,'A')['rows'][0]['name_zh'].split(' / '))=={'药物甲注射液','药物甲注射剂'}


@pytest.mark.parametrize('proven',[True,False])
def test_arm_binding_and_display_consume_same_source_name(workspace,proven):
    svc,pid,_,trial,sid=workspace
    if proven:
        atom(workspace,'identity.name_zh','药物甲注射液');activate(workspace)
    label='药物甲注射液' if proven else '未经证实的旧显示名'
    for field,value,context in [('design.arms',[{'label':'Arm A','interventions':['DRUG: '+label]}],{}),
        ('result.primary.value',24,{'arm':'Arm A','endpoint':'Score','timepoint':'Week 12',
                                   'stat_type':'mean','unit':'points'})]:
        svc.db.add_fact({'project_id':pid,'entity_id':trial,'source_id':sid,'field':field,'value':value,
            'context':context,'tier':'standard','status':'verified','extracted_by':'code:test'})
    row=report_data(svc.db,pid,'B')['results'][0]
    assert row['arm_binding_status']==('resolved' if proven else 'unresolved')
    assert row['drugs']==(['Drug A Injection'] if proven else [])
