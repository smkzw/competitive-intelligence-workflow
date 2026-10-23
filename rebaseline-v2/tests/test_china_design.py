"""Structured Chinese registry design is copied by field, never guessed by an LLM."""
from copy import deepcopy

import pytest
from test_china_detail import capture

from ciw2.sources.china_design import parse_design
from ciw2.sources.china_detail import parse_capture
from ciw2.verify.quote import normalize


def nested(label, rows):
    return {'rows':[[label,'\n'.join('\t'.join(r) for r in rows)]],
            'nested':[{'row':0,'column':1,'rows':rows}]}


def design_capture():
    raw=capture()
    raw['tables'][1]['rows'].append(['随机化','随机化','盲法','开放','试验范围','国内试验'])
    raw['tables'][3]['rows']=[['目标入组人数','国内:\u00a072；国际:120；'],
        ['已入组人数','国内:1；'],['实际入组总人数','国内:0；国际:登记人暂未填写该信息；']]
    treatment=[['序号','名称','用法'],['1','中文通用名:0.5%原药软膏\n英文通用名:Original 0.5%','一天两次，8周'],
               ['2','中文通用名:1.0%原药软膏\n英文通用名:Original 1.0%','一天两次，8周']]
    comparator=[['序号','名称','用法'],['1','中文通用名:安慰剂软膏','一天两次，8周']]
    arms=nested('试验药',treatment)
    arms['rows'].append(['对照药','\n'.join('\t'.join(r) for r in comparator)])
    arms['nested'].append({'row':1,'column':1,'rows':comparator})
    primary=[['序号','指标','评价时间','终点指标选择'],['1','EASI评分较基线变化百分比','第8周','有效性指标'],
             ['2','如观察到系统暴露，则计算原药及代谢物的AUC和Cmax','整个试验期间','安全性指标']]
    endpoints=nested('主要终点指标及评价时间',primary)
    absent=[['序号','指标','评价时间','终点指标选择'],['暂未填写此信息']]
    endpoints['rows'].append(['次要终点指标及评价时间','\n'.join('\t'.join(r) for r in absent)])
    endpoints['nested'].append({'row':1,'column':1,'rows':absent})
    raw['tables'] += [arms,endpoints]
    return raw


def facts(bundle,field):return [f for f in bundle['facts'] if f['field']==field]


def test_all_primary_endpoints_keep_time_condition_class_and_exact_source():
    raw=design_capture()
    out=parse_design(raw)
    endpoints=facts(out,'design.primary_endpoint')
    assert len(endpoints)==2
    assert endpoints[0]['value']['measure']=='EASI评分较基线变化百分比'
    assert endpoints[0]['value']['time_frame']=='第8周'
    assert endpoints[1]['value']['measure'].startswith('如观察到系统暴露')
    assert endpoints[1]['context']['registry_endpoint_class']=='安全性指标'
    assert endpoints[1]['value']['time_frame']=='整个试验期间'
    assert not facts(out,'design.secondary_endpoint')
    assert any(g['field']=='design.secondary_endpoint' and g['reason']=='not_reported' for g in out['gaps'])
    text=parse_capture(raw,ctr=raw['registry_id'],detail_id=raw['detail_id'])['source_text']
    assert all(normalize(f['quote']) in normalize(text) for f in endpoints)
    assert all(f['context']['json_path'].startswith('$.tables[') for f in endpoints)


def test_full_criteria_retains_both_sections_logic_and_all_thresholds():
    raw=design_capture()
    out=parse_design(raw)
    criteria=facts(out,'design.eligibility.criteria')
    assert len(criteria)==1
    assert '入选标准' in criteria[0]['value'] and '排除标准' in criteria[0]['value']
    assert '评分≥12且≤24；并且筛选期与基线均满足。' in criteria[0]['value']
    assert 'ALT > 3×ULN；或既往感染。' in criteria[0]['value']
    assert len(criteria[0]['context']['source_paths'])==2


def test_plan_actual_region_zero_and_missing_remain_distinct_observations():
    out=parse_design(design_capture())
    sample=facts(out,'design.sample_size')
    values={(f['context']['enrollment_type'],f['context']['population']):f for f in sample}
    assert values['ESTIMATED','国内']['value']==72
    assert values['ESTIMATED','国际']['value']==120
    assert values['ACTUAL','国内']['value']==0 and values['ACTUAL','国内']['status']=='verified'
    assert values['ACTUAL','国际']['value'] is None and values['ACTUAL','国际']['status']=='unknown'
    assert not any(f['value']==192 for f in sample)
    enrolled=facts(out,'design.enrolled_to_date')
    assert len(enrolled)==1 and enrolled[0]['value']==1


def test_unparseable_enrollment_is_not_misreported_as_not_disclosed_or_zero():
    raw=design_capture()
    raw['tables'][3]['rows'][0][1]='国内: 大约72（待修订）；'
    out=parse_design(raw)
    selected=[f for f in facts(out,'design.sample_size') if f['context']['enrollment_type']=='ESTIMATED']
    assert selected[0]['value'] is None and selected[0]['status']=='unknown'
    assert any(g['field']=='design.sample_size' and g['reason']=='unparsed_enrollment' for g in out['gaps'])


def test_all_strengths_and_control_roles_preserved_without_making_drug_identity_claims():
    out=parse_design(design_capture())
    arms=facts(out,'design.arms')[0]['value']
    assert len(arms)==3
    assert arms[0]['interventions']==['0.5%原药软膏']
    assert arms[1]['interventions']==['1.0%原药软膏']
    assert arms[2]['interventions']==['安慰剂软膏']
    assert arms[2]['type']=='COMPARATOR'
    assert all(a['description']=='一天两次，8周' for a in arms)


def test_applicant_is_literal_role_not_mah_or_verified_group_and_phase_keeps_source_words():
    raw=design_capture()
    out=parse_design(raw)
    assert facts(out,'trial.applicant')[0]['value']=='原申请人公司'
    assert facts(out,'design.phase')[0]['value']=='I期'
    assert not any(f['field'].startswith('status.china_mah') for f in out['facts'])
    assert out['attrs']['conditions']==['登记适应症']
    assert out['attrs']['registry']=='chinadrugtrials'


def test_table_reordering_changes_locators_not_scientific_values_or_coverage():
    a=design_capture()
    b=deepcopy(a)
    b['tables']=list(reversed(b['tables']))
    def values(raw):return sorted(repr((f['field'],f['value'],f['status'],
        f['context'].get('population'),f['context'].get('enrollment_type'))) for f in parse_design(raw)['facts'])
    assert values(a)==values(b)


def test_mismatched_source_cells_reject_before_any_fact_bundle():
    raw=design_capture()
    raw['tables'][-1]['nested'][0]['rows'][1][1]='被改写的终点'
    with pytest.raises(ValueError):parse_design(raw)


@pytest.mark.parametrize('age,expected',[('18岁(最小年龄)至45岁(最大年龄)',{'min':'18岁','max':'45岁'}),
                                        ('登记人暂未填写该信息',None)])
def test_explicit_age_range_and_trial_scope_are_not_inferred_from_indication(age,expected):
    raw=design_capture()
    raw['tables'].append({'rows':[['年龄',age]],'nested':[]})
    out=parse_design(raw)
    assert facts(out,'design.eligibility.age')[0]['value']==expected
    assert facts(out,'design.trial_scope')[0]['value']=='国内试验'


@pytest.mark.parametrize('tail',['','历史登记原名'])
def test_explicit_former_name_label_is_separate_from_main_drug_name_without_alias_inference(tail):
    raw=design_capture()
    raw['tables'][0]['rows'][1][1]='原药（联合方案）  曾用名:'+tail
    out=parse_design(raw)
    assert out['attrs']['registry_drug_name']=='原药（联合方案）'
    assert out['attrs']['registry_drug_name_raw']==raw['tables'][0]['rows'][1][1]
    assert out['attrs']['registry_former_name']==(tail or None)


@pytest.mark.parametrize('marker,reason',[('企业选择不公示','withheld'),('登记人暂未填写该信息','not_reported')])
def test_four_cell_explicitly_unreported_endpoint_is_gap_not_phantom_or_whole_trial_failure(marker,reason):
    raw=design_capture()
    table=raw['tables'][-1]
    rows=[['序号','指标','评价时间','终点指标选择'],['1','','',marker]]
    table['nested'][1]['rows']=rows
    table['rows'][1][1]='\n'.join('\t'.join(r) for r in rows)
    out=parse_design(raw)
    assert len(facts(out,'design.primary_endpoint'))==2 and not facts(out,'design.secondary_endpoint')
    gap=next(g for g in out['gaps'] if g['field']=='design.secondary_endpoint')
    assert gap['reason']==reason and gap['json_path'].endswith('.rows[1]')
    assert gap['source_ordinal']=='1' and gap['source_notice']==marker
    assert facts(out,'design.eligibility.criteria') and facts(out,'trial.applicant')


def test_empty_endpoint_measure_with_unexplained_clinical_cells_still_rejects():
    raw=design_capture()
    table=raw['tables'][-1]
    rows=[['序号','指标','评价时间','终点指标选择'],['1','','第16周','有效性指标']]
    table['nested'][1]['rows']=rows
    table['rows'][1][1]='\n'.join('\t'.join(r) for r in rows)
    with pytest.raises(ValueError,match='终点'):parse_design(raw)


def test_non_numeric_age_bound_is_not_a_scientific_age_or_an_invented_no_upper_limit():
    raw=design_capture()
    raw['tables'].append({'rows':[['年龄','18岁(最小年龄)至无岁(最大年龄)']],'nested':[]})
    out=parse_design(raw)
    age=facts(out,'design.eligibility.age')[0]
    assert age['value']=={'min':'18岁','max':None}
    assert '无岁' in age['quote'] and age['context']['raw_age'].endswith('无岁(最大年龄)')
    assert any(g['field']=='design.eligibility.age' and g.get('bound')=='max'
               and g['reason']=='non_numeric_age_bound' for g in out['gaps'])
