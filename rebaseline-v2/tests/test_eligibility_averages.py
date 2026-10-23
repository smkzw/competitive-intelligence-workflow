"""Literal average-score qualification; no eligibility decisions or inferred windows."""
import pytest

from ciw2.render.eligibility import eligibility_reading


@pytest.mark.parametrize('phrase,aggregation',[
    ('随机时每日最痒NRS评分的周平均值≥4分。','weekly_mean'),
    ('NRS评分平均值≥4分。','mean'),
    ('weekly mean WI-NRS score >= 4.','weekly_mean'),
    ('PP-NRS score weekly average >= 4.','weekly_mean'),
])
def test_named_average_score_is_emphasized_with_its_literal_qualifier(phrase,aggregation):
    text='入选标准\n'+phrase
    out=eligibility_reading(text)
    assert ''.join(s['text'] for s in out['segments'])==text
    assert len(out['rules'])==1
    rule=out['rules'][0]
    assert rule['value']==4 and rule['operator']=='>=' and rule['aggregation']==aggregation
    assert text[rule['source_start']:rule['source_end']]==rule['quote']
    assert ('周平均' if aggregation=='weekly_mean' else '平均') in rule['label']
    emphasized=''.join(s['text'] for s in out['segments'] if s['emphasis']=='threshold')
    assert '4' in emphasized and rule['rule_text']==phrase


@pytest.mark.parametrize('phrase',[
    'NRS评分，周平均值≥4分。',
    'NRS评分\n周平均值≥4分。',
    'NRS评分；EASI周平均值≥16分。',
    'Mean change in WI-NRS score from baseline: 4 points.',
])
def test_average_reader_does_not_borrow_a_different_measure_or_comparison(phrase):
    out=eligibility_reading(phrase)
    assert ''.join(s['text'] for s in out['segments'])==phrase
    assert not any(r['measure'] in {'NRS','WI-NRS'} for r in out['rules'])
