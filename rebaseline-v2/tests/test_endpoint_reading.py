"""Short expert labels must leave full source semantics and graph identity intact."""
import pytest
from test_result_presentation import project

from ciw2.render.portal import data_b, render_report


@pytest.mark.parametrize('raw,reading', [
    ('Absolute Change From Baseline in EASI Score','EASI · 较基线绝对变化'),
    ('Percent Change From Baseline in Eczema Area and Severity Index (EASI) Score at Each Visit up to Week 52',
     'EASI · 较基线百分比变化 · 各访视至第52周'),
    ('Absolute Change From Baseline in Weekly Average of Peak Pruritus Numeric Rating Scale (PP NRS) Score',
     'PP NRS（每周均值） · 较基线绝对变化'),
    ("Change From Baseline in Children's Dermatology Life Quality Index (cDLQI) For Participants >=4 Years of Age",
     'cDLQI · 较基线变化 · ≥4岁'),
    ("Change From Baseline in Infants' Dermatology Life Quality Index (iDLQI) Score For Participants Less Than (<) 4 Years of Age",
     'iDLQI · 较基线变化 · <4岁'),
    ('Change From Baseline in Patient-Oriented Eczema Measure (POEM)','POEM · 较基线变化'),
])
def test_short_labels_show_in_selector_and_table_with_source_in_details(settings,raw,reading):
    db,pid,ids=project(settings,[{'context':{'endpoint':raw},'value':-2.3}])
    before=db.current_facts(pid)
    group=data_b(db,pid)['charts']['groups'][0]
    assert group.get('label')==reading
    assert group['title']==raw and group['values']==[-2.3]
    html=render_report(db,pid,'B')
    from html import escape, unescape
    escaped=escape(reading)
    assert f'1 · {escaped}</option>' in html and f'<summary>{escaped}</summary>' in html
    assert raw in unescape(html) and f'data-fact-id="{ids[0]}"' in html
    assert db.current_facts(pid)==before


@pytest.mark.parametrize('raw', [
    'Percent Change From Baseline in EASI Score except participants without rescue therapy',
    'Absolute Change From Baseline in EASI Score and SCORAD Score',
    'Number of Participants With Treatment Emergent Adverse Events (TEAEs), Serious Adverse Events (SAEs)',
    'Percent Change From Baseline in EASI Score at Week 12 versus placebo',
    'Probability of participants with EASI-75',
    'Absolute Change From Baseline in Pain Score >=3 (PS)',
    'Change From Baseline in Clinical Scale in Subgroup A (CS)',
    'Percent Change From Baseline in Scale during Rescue Treatment (SR)',
    'Change From Baseline in Severity Grade 3 Index (SGI)',
    'Change From Baseline in Seventy Five Percent Improvement (EASI)',
])
def test_unparsed_conditions_composites_and_statistical_forms_are_not_shortened(settings,raw):
    db,pid,_=project(settings,[{'context':{'endpoint':raw},'value':0}])
    group=data_b(db,pid)['charts']['groups'][0]
    assert group.get('label',group['title'])==raw
    assert group['title']==raw and group['values']==[0]


def test_identical_reading_names_never_merge_scientific_groups_or_change_values(settings,monkeypatch):
    from ciw2.render import results
    db,pid,ids=project(settings,[{'context':{'endpoint':'Absolute Change From Baseline in EASI Score'},'value':0},
        {'context':{'endpoint':'Percent Change From Baseline in EASI Score'},'value':-12.5}])
    original=data_b(db,pid)['charts']['groups']
    monkeypatch.setattr(results,'endpoint_label',lambda value:'同一显示名')
    projected=data_b(db,pid)['charts']['groups']
    assert len(original)==len(projected)==2
    assert {p['fact_id'] for g in projected for p in g['points']}==set(ids)
    assert [{k:v for k,v in g.items() if k!='label'} for g in original]==[
        {k:v for k,v in g.items() if k!='label'} for g in projected]


@pytest.mark.parametrize(('raw','reading'),[
    ('Absolute Change From Baseline in Weekly Average of Average Pruritus NRS Score','平均瘙痒NRS（每周均值） · 较基线绝对变化'),
    ('Percent Change From Baseline in Weekly Average of Sleep Disturbance NRS Score','睡眠障碍NRS（每周均值） · 较基线百分比变化'),
    ('Change From Baseline in Worst Pain Numeric Rating Scale (NRS) Score','最严重疼痛NRS · 较基线变化'),
    ('Change From Baseline in Peak Pruritus NRS Score','峰值瘙痒NRS · 较基线变化'),
])
def test_complete_generic_nrs_metric_keeps_intensity_and_aggregation(raw,reading):
    from ciw2.render.endpoint_label import endpoint_label
    assert endpoint_label(raw)==reading


@pytest.mark.parametrize('raw',[
    'Change From Baseline in Seventy Five (EASI)',
    'Change From Baseline in Twenty Item Clinical Assessment (TICA)',
    'Change From Baseline in Percentile Index (PI)',
    'Change From Baseline in Percentage Index (PI)',
    'Change From Baseline in Average Pruritus NRS after rescue',
    'Change From Baseline in Sleep Disturbance NRS and Pain NRS',
    'Change From Baseline in Worst Anxiety Numeric Rating Scale (NRS) Score',
])
def test_spelled_thresholds_statistical_modifiers_and_unparsed_nrs_stay_verbatim(raw):
    from ciw2.render.endpoint_label import endpoint_label
    assert endpoint_label(raw)==raw
