"""Synthetic scalar edge cases through production extraction, current facts and B."""
import copy
import json

import pytest
from test_quote_requalification import _effective, _legacy, _requalify, _snapshot, _source
from test_quote_requalification import env as env  # noqa: PLC0414 - pytest fixture registration

from ciw2.domain.models import ExtractedFact
from ciw2.domain.semantics import derive_proportion, parse_number
from ciw2.render.portal import data_b, render_report
from ciw2.service import Service
from ciw2.sources.ctgov import API, _activate_trial, result_facts, stat_type_of
from ciw2.sources.http import register_text
from ciw2.verify.quote import check_quote


@pytest.mark.parametrize('operator',['<','>','<=','>=','≤','≥'])
@pytest.mark.parametrize('value',[5,'5','5.0'])
def test_quote_check_does_not_certify_a_threshold_as_an_exact_scalar(operator,value):
    text=f'The observed result was {operator} 5.0 units.'
    assert not check_quote(text,text,value).ok
    assert check_quote(text,text,f'{operator} 5.0').ok
    assert check_quote(text,text,{'operator':operator,'threshold':5}).ok


def test_exact_scalar_elsewhere_in_quote_is_not_rejected_by_an_unrelated_bound():
    text='Observed value 5.0 units; the separate sensitivity threshold was <5.0 units.'
    assert check_quote(text,text,5).ok


def test_true_inequality_cannot_requalify_a_legacy_exact_scalar(env):
    svc,rc,pid,trial=env
    fid=_legacy(rc,trial,_source(rc),value=3,quote='ALT < 3')
    before=_snapshot(svc.db)
    assert _requalify(svc.db,svc.cas,pid)['counts']['invalidated']==1
    assert _effective(svc.db,pid,fid)['status']=='unverified'
    assert _snapshot(svc.db)==before
    assert data_b(svc.db,pid)['plot_exclusions'][fid]=='unverified'


@pytest.mark.parametrize('raw', ['<5','>5','<=0.1','>=2','≤0.001','≥4',float('inf'),float('nan'),'1,2'])
def test_nonexact_or_invalid_scalars_never_become_exact_numbers(raw):
    assert parse_number(raw) is None
    assert derive_proportion(raw,100,'count_participants') is None
    assert derive_proportion(1,raw,'count_participants') is None


@pytest.mark.parametrize(('raw','value'), [('0',0),('-1.5',-1.5),('1,234.5',1234.5),
    ('1e-3',0.001),('+3.0',3.0),('.5',0.5)])
def test_explicit_finite_decimal_and_exponent_values_remain_exact(raw,value):
    assert parse_number(raw)==value


@pytest.mark.parametrize(('param','unit','kind'), [('GEOMETRIC_MEAN','%','geometric_mean'),
    ('Geometric Mean','ng/mL','geometric_mean'),('MEAN','%','mean'),
    ('Least Squares Mean','percentage of participants','ls_mean'),
    ('GEOMETRIC_LEAST_SQUARES_MEAN','ng/mL','geometric_ls_mean'),
    ('NUMBER','%','number'),('NUMBER','percentage of participants','proportion')])
def test_explicit_statistic_is_not_replaced_by_unit_or_arithmetic_mean(param,unit,kind):
    assert stat_type_of(param,unit)==kind
    fact=ExtractedFact(entity='test',field='result.primary.value',value=1,
        stat_type=kind,source_url='https://example.org/synthetic',quote='1')
    assert fact.stat_type==kind


@pytest.mark.parametrize(('raw','statistic','kind','label'),
    [('<5','Geometric Mean','geometric_mean','几何均值'),('≥0.01','MEAN','mean','均值')])
def test_censored_source_is_visible_verbatim_and_not_plotted_as_an_exact_point(
        settings,study,raw,statistic,kind,label):
    source=copy.deepcopy(study)
    outcome=source['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0]
    outcome['paramType']=statistic
    outcome['unitOfMeasure']='%'
    measurement=outcome['classes'][0]['categories'][0]['measurements'][0]
    measurement['value']=raw
    expected_path='outcomeMeasures[0].classes[0].categories[0]'
    parsed=next(f for f in result_facts(source) if f['context']['json_path']==expected_path)
    assert parsed['value']==raw and parsed['status']=='verified'
    assert parsed['quote']==parsed['context']['raw_value']==raw
    svc=Service(settings);pid=svc.create_project('Atopic Dermatitis',['B'])
    ctx=svc.context(pid,svc.db.create_run(pid)).tool_ctx()
    nct=source['protocolSection']['identificationModule']['nctId']
    sid=register_text(ctx,kind='ctgov',url=f'{API}/{nct}',text=json.dumps(source))
    first=_activate_trial(ctx,nct,source,sid,'synthetic-scalar-regression')
    before=svc.db.query('SELECT * FROM facts ORDER BY rowid')
    second=_activate_trial(ctx,nct,source,sid,'synthetic-scalar-regression')
    assert first['facts_added'] and second['facts_added']==0
    data=data_b(svc.db,pid)
    row=next(r for r in data['results'] if r['raw_value']==raw)
    assert row['value']==raw and data['plot_exclusions'][row['id']]=='non_numeric'
    assert row['stat_type']==kind
    assert row['id'] not in {p['fact_id'] for g in data['charts']['groups'] for p in g['points']}
    html=render_report(svc.db,pid,'B')
    assert ('&lt;5' if raw=='<5' else raw) in html and label in html
    assert svc.db.query('SELECT * FROM facts ORDER BY rowid')==before
