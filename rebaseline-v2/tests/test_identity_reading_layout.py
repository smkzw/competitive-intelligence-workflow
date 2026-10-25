"""Reading regressions found in the actual A/C certificate slice."""
from test_nmpa_current_projection import activate, atom
from test_nmpa_current_projection import workspace as workspace  # noqa: PLC0414 - pytest fixture re-export

from ciw2.render.portal import render_report, report_data


def test_a_does_not_repeat_equal_chinese_name_or_expose_internal_route(workspace):
    svc,pid,drug,_,_=workspace
    svc.db.execute('UPDATE entities SET name=?,found_by=? WHERE id=?',
        ('药物甲注射液','["china:browser_smoke"]',drug))
    atom(workspace,'identity.name_zh','药物甲注射液');activate(workspace)
    html=render_report(svc.db,pid,'A')
    assert '<div class="muted">药物甲注射液</div>' not in html
    assert '<th>发现路线</th>' not in html and 'china:browser_smoke' not in html
    assert svc.db.entities(pid,'drug')[0]['found_by']==['china:browser_smoke']


def test_c_legacy_drug_field_uses_the_same_verified_name(workspace):
    svc,pid,_,trial,sid=workspace
    atom(workspace,'identity.name_zh','药物甲注射液');activate(workspace)
    svc.db.add_fact({'project_id':pid,'entity_id':trial,'source_id':sid,'field':'design.phase',
        'value':'phase2','tier':'standard','status':'verified','extracted_by':'code:test'})
    row=report_data(svc.db,pid,'C')['rows'][0]
    assert row['drugs']==row['identity']['drugs']==['药物甲注射液']


def test_a_unknown_china_sites_are_not_zero(workspace):
    svc,pid,_,_,_=workspace
    row=report_data(svc.db,pid,'A')['rows'][0]
    assert row['n_china_trials'] is None and row['n_china_trials_unknown']==1


def test_a_explicit_domestic_source_and_unknown_neighbor_show_lower_bound(workspace):
    svc,pid,drug,trial,sid=workspace
    svc.db.add_fact({'project_id':pid,'entity_id':trial,'source_id':sid,'field':'design.trial_scope',
        'value':'国内试验','tier':'standard','status':'verified','extracted_by':'code:test'})
    second,_=svc.db.upsert_entity(pid,'trial','CTR20260001')
    svc.db.link(pid,drug,'drug-trial',second)
    row=report_data(svc.db,pid,'A')['rows'][0]
    assert row['n_china_trials']==1 and row['n_china_trials_unknown']==1
    assert '大陆 ≥1' in render_report(svc.db,pid,'A')
