"""Mainland site presence is distinct from other regions and from China eligibility."""
from html import unescape

import pytest
from test_m1_design import add_fact
from test_m1_design import design_project as design_project  # noqa: PLC0414 - pytest fixture

from ciw2.render.drug_identity import china_trial_sites
from ciw2.render.portal import data_c, render_report
from ciw2.sources.ctgov import design_facts, parse_study


@pytest.mark.parametrize('countries,expected',[
    (['Taiwan'],False),(['Hong Kong'],False),(['Macao'],False),(['Macau'],False),
    (['China','Taiwan','Hong Kong','Macao'],True),(['United States',None],None),
    (['China',None],True),([None],None),([],None),
])
def test_mainland_flag_does_not_merge_regions_or_turn_unreported_locations_into_no(study,countries,expected):
    study['protocolSection']['contactsLocationsModule']={'locations':[{'country':c} for c in countries]}
    parsed=parse_study(study);assert parsed['china_site'] is expected
    assert parsed['countries']==(sorted({c for c in countries if c}) or None)
    facts={f['field']:f for f in design_facts(parsed)}
    assert facts['trial.china_site']['context']['geographic_scope']=='mainland_china'
    assert facts['trial.countries']['context']['locations_complete']==bool(countries and all(countries))


def test_legacy_broad_flags_cannot_acquire_a_mainland_meaning(design_project):
    legacy=add_fact(design_project,'trial.china_site',True)
    country=add_fact(design_project,'trial.countries',['Taiwan'])
    db,pid,trial,_=design_project;before=db.current_facts(pid)
    assert china_trial_sites(db,pid).get(trial) is None
    data=data_c(db,pid);assert legacy not in {r['fact_id'] for row in data['rows'] for rs in row['observations'].values() for r in rs}
    assert legacy in data['legacy_geography_ids']
    from ciw2.pipeline.stages import _compact
    task=_compact(data)
    assert 'legacy_geography_ids' not in task
    assert 'legacy_geography' not in task['rows'][0]['sources']
    html=unescape(render_report(db,pid,'C'));assert '台湾' in html
    assert '中国大陆站点 是' not in html and f'data-fact-id="{country}"' in html
    assert db.current_facts(pid)==before


@pytest.mark.parametrize('countries,expected',[(['Taiwan'],False),(['China','Hong Kong','Macau'],True)])
def test_a_and_c_use_current_explicit_scope_without_changing_identity_or_eligibility(design_project,countries,expected):
    db,pid,trial,_=design_project
    add_fact(design_project,'trial.countries',countries,locations_complete=True)
    add_fact(design_project,'trial.china_site',expected,geographic_scope='mainland_china')
    before=db.current_facts(pid);entity=db.entities(pid,'trial')[0]
    assert china_trial_sites(db,pid)[trial] is expected
    html=unescape(render_report(db,pid,'C'))
    for original in countries:
        assert {'China':'中国大陆','Hong Kong':'香港','Macau':'澳门','Taiwan':'台湾'}[original] in html
        assert f'data-original-value="{original}"' in html
    assert data_c(db,pid)['legacy_geography_ids']==[]
    assert db.current_facts(pid)==before and db.entities(pid,'trial')[0]==entity


def test_conflicting_current_site_sources_remain_unresolved(design_project):
    db,pid,trial,_=design_project
    add_fact(design_project,'trial.china_site',False,geographic_scope='mainland_china')
    add_fact(design_project,'trial.countries',['China'],locations_complete=True)
    assert china_trial_sites(db,pid)[trial] is None
