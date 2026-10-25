"""Complete generic parameter labels; clinical facts and unknown qualifiers stay intact."""
from html import unescape

import pytest
from test_result_presentation import project

from ciw2.render.endpoint_label import endpoint_label
from ciw2.render.portal import data_b, render_report

SAFETY=('Number of Participants With Treatment Emergent Adverse Events (TEAEs), '
        'Adverse Events of Special Interest (AESIs), Adverse Events Leading to Discontinuation '
        'and Serious Adverse Events (SAEs)')
PARAMETERS=[
    ('Test-agent Serum Concentrations','Test-agent · 血清浓度'),
    ('Serum Concentration Observed Immediately Before Next Dosing (Ctrough) of Test-agent',
     'Test-agent · 下次给药前即刻血清浓度（Ctrough）'),
    ('Absorption Rate Constant (Ka) of Test-agent','Test-agent · 吸收速率常数（Ka）'),
    ('Apparent Terminal Half-life (t1/2) of Test-agent','Test-agent · 表观终末半衰期（t1/2）'),
    ('Apparent Total Body Clearance (Cl/F) of Test-agent','Test-agent · 表观全身清除率（Cl/F）'),
    ('Apparent Volume of Distribution (Vd/F) of Test-agent','Test-agent · 表观分布容积（Vd/F）'),
    ('Area Under the Serum Concentration-Time Curve From Time Zero to Infinity (AUCinf) of Test-agent',
     'Test-agent · 血清AUC（0至无穷，AUCinf）'),
    ('Number of Participants With Positive Anti-Drug Antibody (ADA) for Test-agent',
     'Test-agent · ADA阳性受试者人数'),
    ('PK/PD Relationship Between Test-agent Serum Concentration and Changes in EASI Score',
     'PK/PD关系 · Test-agent血清浓度与EASI变化'),
    ('Pharmacokinetic (PK)/Pharmacodynamic (PD) Relationship Between Test-agent Serum Concentration and Changes in PP NRS',
     'PK/PD关系 · Test-agent血清浓度与PP NRS变化'),
    ('Percentage of Participants Receiving Any Rescue Therapy by Rescue Treatment',
     '接受补救治疗的受试者比例 · 按补救治疗分层'),
    (SAFETY,'TEAE、AESI、因AE停药、SAE · 受试者人数'),
]


@pytest.mark.parametrize('raw,reading',PARAMETERS)
def test_full_parameter_names_have_compact_chinese_reading(raw,reading):
    assert endpoint_label(raw)==reading


@pytest.mark.parametrize('raw',[
    'Apparent Terminal Half-life (t1/2) of Test-agent excluding outliers',
    'Apparent Total Body Clearance (CL) of Test-agent',
    'Area Under the Serum Concentration-Time Curve From Time Zero to Last Observation (AUCinf) of Test-agent',
    'Percentage of Participants With Positive Anti-Drug Antibody (ADA) for Test-agent',
    'Number of Participants With Negative Anti-Drug Antibody (ADA) for Test-agent',
    'PK/PD Relationship Between Test-agent Serum Concentration and Changes in EASI Score without rescue',
    SAFETY.replace('and Serious','or Serious'),
    SAFETY.replace('Number of Participants','Number of Events'),
])
def test_unknown_or_changed_qualifiers_keep_full_original(raw):
    assert endpoint_label(raw)==raw


def test_labels_keep_source_measurements_groups_and_table_definitions(settings,monkeypatch):
    from ciw2.render import results
    records=[{'context':{'endpoint':raw,'population':'Source population','category':'TEAEs' if raw==SAFETY else None}}
             for raw,_ in PARAMETERS]
    db,pid,ids=project(settings,records);before=db.current_facts(pid)
    current=data_b(db,pid)['charts']['groups']
    monkeypatch.setattr(results,'endpoint_label',lambda v:v)
    monkeypatch.setattr(results,'response_facet_label',lambda *_:None)
    baseline=data_b(db,pid)['charts']['groups']
    assert [{k:v for k,v in g.items() if k!='label'} for g in current]==[{k:v for k,v in g.items() if k!='label'} for g in baseline]
    assert {p['fact_id'] for g in current for p in g['points']}==set(ids)
    html=unescape(render_report(db,pid,'B'))
    for raw,reading in PARAMETERS:
        assert raw in html and reading in html
    assert db.current_facts(pid)==before


@pytest.mark.parametrize('facet,expected',[
    ('TEAEs','TEAE · 受试者人数'),('AESIs','AESI · 受试者人数'),
    ('SAEs','SAE · 受试者人数'),('AE leading to discontinuation','因AE停药 · 受试者人数'),
])
def test_only_explicit_parent_members_shorten_the_selected_safety_curve(settings,facet,expected):
    db,pid,_=project(settings,[{'context':{'endpoint':SAFETY,'category':facet}}])
    group=data_b(db,pid)['charts']['groups'][0]
    assert group['label']==expected and group['title']==SAFETY


@pytest.mark.parametrize('facets',[['Grade ≥3 TEAEs'],['Non-serious AEs'],['TEAEs','SAEs']])
def test_unparsed_safety_facets_are_not_merged_into_a_parent_member(facets):
    from ciw2.render.parameter_reading import safety_facet_label
    assert safety_facet_label(SAFETY,facets) is None
    assert safety_facet_label(SAFETY+' excluding serious events',['TEAEs']) is None
