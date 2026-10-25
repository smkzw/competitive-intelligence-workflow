"""Response reading keeps full thresholds and sources, without changing comparison frames."""
from html import unescape

import pytest
from test_result_presentation import project

from ciw2.render.endpoint_label import endpoint_label
from ciw2.render.portal import data_b, render_report

COMPOSITE='Number of Participants Achieving 50 Percent (%), 75% or 90% Response From Baseline in EASI (EASI-50, EASI-75 and EASI-90)'
SINGLE='Percentage of Participants With an Improvement of >= 4 From Baseline in Weekly Average of PP NRS'


@pytest.mark.parametrize('raw,reading',[
    (COMPOSITE,'EASI · 较基线应答50%、75%或90%'),
    (COMPOSITE.replace('Number of','Percentage of'),'EASI · 较基线应答50%、75%或90%'),
    (SINGLE,'PP NRS（每周均值） · 较基线改善≥4 · 受试者比例'),
    (SINGLE.replace('>= 4','> 3.5'),'PP NRS（每周均值） · 较基线改善>3.5 · 受试者比例'),
])
def test_complete_response_grammar_keeps_threshold_operation_and_measure(raw,reading):
    assert endpoint_label(raw)==reading


@pytest.mark.parametrize('raw',[
    COMPOSITE.replace('EASI-75','EASI-70'),
    COMPOSITE.replace('75% or 90%','75% and 90%'),
    COMPOSITE+' without rescue therapy',
    SINGLE+' at Week 16 versus placebo',
    SINGLE.replace('>= 4','>= 4%'),
    SINGLE.replace('Improvement','Deterioration'),
])
def test_unparsed_conditions_inconsistent_codes_and_composite_logic_are_preserved(raw):
    assert endpoint_label(raw)==raw


def test_response_names_are_shared_by_chart_and_table_without_changing_science(settings,monkeypatch):
    from ciw2.render import results
    db,pid,ids=project(settings,[{'context':{'endpoint':COMPOSITE,'category':'EASI - 50','unit':'Percentage'},'value':0},
                               {'context':{'endpoint':COMPOSITE,'category':'EASI - 75','unit':'Percentage'},'value':21}])
    before=db.current_facts(pid)
    projected=data_b(db,pid)['charts']['groups']
    monkeypatch.setattr(results,'endpoint_label',lambda raw:raw)
    original=data_b(db,pid)['charts']['groups']
    assert [{k:v for k,v in g.items() if k!='label'} for g in projected]==[{k:v for k,v in g.items() if k!='label'} for g in original]
    assert len(projected)==2 and {p['fact_id'] for g in projected for p in g['points']}==set(ids)
    html=unescape(render_report(db,pid,'B'))
    assert 'EASI · 较基线应答50%、75%或90%' in html and COMPOSITE in html
    assert db.current_facts(pid)==before


def test_selected_response_facet_names_only_the_curve_shown(settings):
    db,pid,_=project(settings,[{'context':{'endpoint':COMPOSITE,'category':'EASI - 50'},'value':0},
                              {'context':{'endpoint':COMPOSITE,'category':'EASI - 75'},'value':21}])
    groups=data_b(db,pid)['charts']['groups']
    assert {g['label'] for g in groups}=={'EASI - 50 · 较基线应答','EASI - 75 · 较基线应答'}
    assert all(g['title']==COMPOSITE for g in groups)


def test_unknown_response_facet_cannot_be_relabelled_as_a_known_threshold(settings):
    db,pid,_=project(settings,[{'context':{'endpoint':COMPOSITE,'category':'EASI - 70'}}])
    g=data_b(db,pid)['charts']['groups'][0]
    assert g['label']=='EASI - 70 · EASI · 较基线应答50%、75%或90%'
