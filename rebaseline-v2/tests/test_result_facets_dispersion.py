"""Clinical class identity and uncertainty must survive the visible comparison."""
import re
from html import unescape

import pytest
from test_result_presentation import project

from ciw2.render.portal import data_b, render_report
from ciw2.render.results import arm_label, arm_tokens, dispersion_text, visit_label


@pytest.mark.parametrize(('raw','label'), [('Standard Deviation','SD'),('Standard Error','SE'),
    ('Confidence Interval','CI'),('Full Range','范围'),('Inter-Quartile Range','四分位距'),
    ('Unknown source dispersion','Unknown source dispersion')])
def test_exact_source_dispersion_text_and_original_scalar_type(raw,label):
    row={'dispersion_type':raw,'spread':'0'}
    assert dispersion_text(row)==label+' 0'
    assert row=={'dispersion_type':raw,'spread':'0'}


@pytest.mark.parametrize(('raw','parts'),[
    ('Cohort 1.1: Participants Aged 7-11 Years',['队列1.1','（7–11岁）']),
    ('Cohort 2: Participants Aged 2-6 Years',['队列2','（2–6岁）']),
    ('Source cohort with a longer, unknown age expression',['Source cohort with a longer, unknown age expression']),
])
def test_cohort_tokens_share_the_chart_label_without_reparsing_or_changing_unknown_names(raw,parts):
    assert arm_tokens(raw)==parts and arm_label(raw)==''.join(parts)


def test_compound_visit_strata_form_separate_longitudinal_curves_without_losing_facts(settings):
    observations=[]
    for threshold in (50,75):
        for week in (4,12):
            for arm in ('Cohort A','Cohort B'):
                observations.append({'value':week+threshold,'context':{
                    'endpoint':'Number of Participants Achieving 50%, 75% or 90% Response',
                    'class_title':f'Week {week}: EASI - {threshold}',
                    'stat_type':'count_participants','param_type':'COUNT_OF_PARTICIPANTS',
                    'unit':'participants','arm':arm,'group_id':arm}})
    observations.append({'value':None,'status':'unknown','context':{
        **observations[0]['context'],'class_title':'Week 8: EASI - 50'}})
    db,pid,ids=project(settings,observations);before=db.current_facts(pid)
    data=data_b(db,pid);groups=data['charts']['groups']
    assert len(groups)==2 and all(g['kind']=='line' for g in groups)
    assert [g['facets'][0] for g in groups]==['EASI - 50','EASI - 75']
    assert all(g['facets'][0] in g['label'] for g in groups)
    assert {p['fact_id'] for g in groups for p in g['points']}==set(ids[:-1])
    assert groups[0]['positions']==[28,56,84] and ids[-1] in data['plot_exclusions']
    assert all(p['visit'] in ('第4周','第12周') for g in groups for p in g['points'])
    assert db.current_facts(pid)==before


def test_compound_visit_does_not_override_a_conflicting_time_or_unknown_aggregate(settings):
    db,pid,ids=project(settings,[{'context':{'class_title':'Week 4: Response A','category':'Day 35'}},
                               {'context':{'class_title':'Weeks 4 to 12: Response A','category':None}}])
    groups=data_b(db,pid)['charts']['groups']
    assert len(groups)==2 and all(g['kind']=='bar' for g in groups)
    assert all(p['x'] is None for g in groups for p in g['points'])
    assert {p['fact_id'] for g in groups for p in g['points']}==set(ids)


def test_source_cohorts_are_legible_and_the_original_arm_names_remain(settings):
    original=['Cohort 1: Participants Aged 7-11 Year',
              'Cohort 1.1: Participants Aged 7-11 Years',
              'Cohort 2: Participants Aged 2-6 Years']
    db,pid,_=project(settings,[{'context':{'class_title':'Week 4','arm':arm,'group_id':str(i)}}
                             for i,arm in enumerate(original)])
    points=data_b(db,pid)['charts']['groups'][0]['points']
    assert [p['arm'] for p in points]==original
    assert [p['arm_label'] for p in points]==['队列1（7–11岁）','队列1.1（7–11岁）','队列2（2–6岁）']
    assert all(p['arm_label'] in p['axis_label'] for p in points)
    html=render_report(db,pid,'B')
    assert '<span class="arm-token">队列1.1</span><wbr><span class="arm-token">（7–11岁）</span>' in html
    assert 'Cohort 1.1: Participants Aged 7-11 Years' in html


def test_dispersion_zero_and_partial_interval_are_visible_and_not_invented(settings):
    db,pid,ids=project(settings,[{'value':0,'context':{'spread':0,'dispersion_type':'STANDARD_DEVIATION'}},
        {'value':-12.86,'context':{'spread':9.154,'dispersion_type':'STANDARD_DEVIATION'}},
        {'value':1.3,'context':{'lower':0,'upper':None,'dispersion_type':'CONFIDENCE_INTERVAL'}}])
    before=db.current_facts(pid);data=data_b(db,pid)
    points={p['fact_id']:p for g in data['charts']['groups'] for p in g['points']}
    assert points[ids[0]]['spread']==0 and points[ids[0]]['dispersion_label']=='SD'
    assert points[ids[1]]['spread']==9.154
    assert points[ids[2]]['lower']==0 and points[ids[2]]['upper'] is None
    html=render_report(db,pid,'B')
    for fid,dispersion in zip(ids,('SD 0','SD 9.154','CI 下限 0'),strict=True):
        row=re.search(r'<tr data-fact-id="'+re.escape(fid)+r'".*?</tr>',html,re.DOTALL)[0]
        cell=re.search(r'<td class="numeric">(.*?)</td>',row,re.DOTALL)[1]
        text=' '.join(unescape(re.sub(r'<[^>]+>',' ',cell)).split())
        assert dispersion in text
        if fid==ids[2]:
            assert '95%' not in text and '上限' not in text
    assert db.current_facts(pid)==before


def test_exact_day_week_conversion_retains_source_visit_labels(settings):
    db,pid,_=project(settings,[{'context':{'class_title':'Week 4','arm':'A'}},
        {'context':{'class_title':'Week 8','arm':'A'}},
        {'context':{'class_title':'Day 28','arm':'B'}},
        {'context':{'class_title':'Day 56','arm':'B'}}])
    groups=data_b(db,pid)['charts']['groups']
    assert len(groups)==1 and groups[0]['kind']=='line'
    assert groups[0]['display_axis']=='weeks'
    assert {p['visit'] for p in groups[0]['points']}=={'第4周','第8周','第28天','第56天'}


@pytest.mark.parametrize(('raw','label'),[
    ('Week 4','第4周'),('Day 28','第28天'),('Month 12','第12月'),
    ('Baseline','基线'),('Week 4: EASI - 75','第4周 · EASI - 75'),
    ('Weeks 4 to 12: Response A','Weeks 4 to 12: Response A'),
    ('At Week 12 after rescue','At Week 12 after rescue'),
])
def test_table_visit_translation_consumes_only_a_complete_single_visit(raw,label):
    assert visit_label(raw)==label


def test_table_visit_reading_preserves_original_class_and_source_context(settings):
    db,pid,ids=project(settings,[{'context':{'class_title':'Week 4: EASI - 75','category':'Day 28'}}])
    before=db.current_facts(pid);html=render_report(db,pid,'B')
    row=re.search(r'<tr data-fact-id="'+ids[0]+r'".*?</tr>',html,re.DOTALL)[0]
    assert '<td class="result-visit">' in row and '第4周 · EASI - 75' in row and '第28天' in row
    assert 'Week 4: EASI - 75' in row and 'Day 28' in row
    assert db.current_facts(pid)==before
