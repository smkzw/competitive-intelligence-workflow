"""Reading regressions from public CTR20263748 capture ee5ed367…, not eligibility decisions."""
import pytest

from ciw2.render.eligibility import eligibility_reading


def lossless(text):
    out=eligibility_reading(text)
    assert ''.join(s['text'] for s in out['segments'])==text
    assert all(text[r['source_start']:r['source_end']]==r['quote'] for r in out['rules'])
    return out


@pytest.mark.parametrize('text',[
    '入选标准\n筛选和基线时，IGA评分为2或3，EASI评分≥5，AD受累BSA≥5%且≤20%（头皮、掌心和足底除外）；',
    '入选标准\nAt screening, IGA score is 2 or 3, EASI >= 5; BSA >= 5% and <= 20%.'])
def test_discrete_scores_and_both_bounds_are_not_lower_bound_or_range_inventions(text):
    out=lossless(text)
    iga=[r for r in out['rules'] if r['measure']=='IGA']
    assert len(iga)==1 and iga[0]['operator']=='one_of' and iga[0]['value']==[2.0,3.0]
    bsa=[r for r in out['rules'] if r['measure']=='BSA']
    assert [(r['operator'],r['value'],r['unit']) for r in bsa]==[('>=',5.0,'%'),('<=',20.0,'%')]
    assert all(r['section']=='inclusion' for r in out['rules'])
    emphasis=''.join(s['text'] for s in out['segments'] if s['emphasis']=='threshold')
    assert '20%' in emphasis and '2' in emphasis and '3' in emphasis


@pytest.mark.parametrize('text,measure',[
    ('排除标准\n天冬氨酸转氨酶或丙氨酸转氨酶（AST/ALT）>1.5倍正常值上限；','AST/ALT'),
    ('排除标准\n(AST/ALT) > 1.5 times ULN;','AST/ALT'),
    ('排除标准\n血清肌酐（SCr）>1.5倍正常值上限；','SCr')])
def test_parenthesized_labs_and_explicit_chinese_upper_normal_unit_are_one_source_object(text,measure):
    out=lossless(text)
    assert len(out['rules'])==1
    rule=out['rules'][0]
    assert (rule['measure'],rule['operator'],rule['value'],rule['unit'])==(measure,'>',1.5,'× ULN')
    assert rule['section']=='exclusion'
    assert '(' in rule['quote'] or '（' in rule['quote']
    assert '或' not in rule['label']  # Slash is not evidence of OR.


@pytest.mark.parametrize('text',[
    'BSA≥5%；IGA≤3；且≤20%',
    'BSA≥5%\n且≤20%',
    'BSA≥5%，其他实验室指标且≤20%',
    'BSA≥5%且ALT≤20 U/L',
    'IGA评分为2或3个访视后改善；EASI-75≥50%',
    'IGA评分为2或3.5个访视后改善；EASI-75≥50%',
])
def test_continuations_do_not_cross_clauses_named_measures_or_turn_visit_counts_into_scores(text):
    out=lossless(text)
    assert not any(r['measure']=='BSA' and r['value']==20 for r in out['rules'])
    if '个访视' in text:assert not any(r['operator']=='one_of' for r in out['rules'])


def test_continuation_retains_original_connector_and_does_not_fill_a_missing_percent():
    out=lossless('入选标准\nBSA≥5%或≤20')
    assert [(r['operator'],r['unit']) for r in out['rules']]==[('>=','%'),('<=',None)]
    assert '或' in ''.join(s['text'] for s in out['segments'] if s['emphasis']=='logic')
    assert out['rules'][1]['quote']=='或≤20'
