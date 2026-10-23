"""Small offline public-review captures; no inference of approval or indication."""
from copy import deepcopy

import pytest

from ciw2.sources.cde_review_capture import COLUMNS, CaptureError, parse_review_capture

URL='https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d'
FILTERS={'sequence':'化药','task_type':'IND','ui_acceptance_number':''}
LEGEND=[{'text':'：本专业正在审评','images':['/main/img/lamp.gif']},
        {'text':'：本专业排队待审评','images':['/main/img/lamp_y.jpg']},
        {'text':'：本专业已完成审评','images':['/main/img/lamp_shut.gif']},
        {'text':'空：本专业未启动','images':[]}]


def row(number,acceptance='CYHL2600085'):
    cells=[{'text':v,'images':[]} for v in [str(number),acceptance,'琥珀酰明胶电解质醋酸钠注射液',
        '2026-07-31','排队待审评','','','','','','','']]
    cells[5]['images']=['/main/img/lamp_shut.gif']
    return cells


def page(rows,number=1,total=3):
    return {'url':URL,'section':'new_review_task','filters':dict(FILTERS),'headers':list(COLUMNS),
        'rows':rows,'legend':deepcopy(LEGEND),'observed_at':'2026-10-24T00:00:00Z',
        'pagination':{'current':number,'page_size':2,'text':f'共 {total} 条'}}


def pages():
    return [page([row(1),row(2,'CXHL2600985')]),page([row(3,'CXHL2600990')],2)]


def test_full_scope_then_exact_lookup_keeps_regulatory_layers_and_original_locator():
    source=pages()
    out=parse_review_capture([source[1],source[0]],filters=FILTERS,acceptance_number='CYHL2600085')
    assert out['complete'] and out['total_records']==3 and out['matched_count']==1
    hit=out['results'][0]
    assert hit['review_status_text']=='排队待审评'
    assert hit['disciplines']['药理毒理']['status_text']=='本专业已完成审评'
    assert hit['disciplines']['临床']['status_text']=='本专业未启动'
    assert hit['center_entry_date_text']=='2026-07-31'
    assert hit['locator']=='$.pages[1].rows[0]' and hit['raw_cells']==source[0]['rows'][0]
    assert not {'approved','target_indication','mah','sponsor','acceptance_date'} & hit.keys()


def test_absent_exact_code_is_not_unfiltered_page_success():
    out=parse_review_capture(pages(),filters=FILTERS,acceptance_number='ZZZZ9999999')
    assert out['complete'] and out['matched_count']==0 and out['results']==[] and out['total_records']==3


def test_found_in_partial_scope_does_not_close_missing_pages():
    with pytest.raises(CaptureError):
        parse_review_capture(pages()[:1],filters=FILTERS,acceptance_number='CYHL2600085')
    out=parse_review_capture(pages()[:1],filters=FILTERS,acceptance_number='CYHL2600085',allow_partial=True)
    assert not out['complete'] and out['pending_pages']==[2] and out['matched_count']==1


def test_duplicate_acceptance_observations_retained_not_first_wins():
    source=pages()
    source[0]['rows'][1][1]['text']='CYHL2600085'
    source[0]['rows'][1][4]['text']='正在审评'
    out=parse_review_capture(source,filters=FILTERS,acceptance_number='CYHL2600085')
    assert out['matched_count']==2
    assert [r['review_status_text'] for r in out['results']]==['排队待审评','正在审评']


def test_unmapped_icon_is_unknown_not_guessed_from_filename():
    source=pages()
    source[0]['rows'][0][5]['images']=['/main/img/approved.gif']
    hit=parse_review_capture(source,filters=FILTERS,acceptance_number='CYHL2600085')['results'][0]
    assert hit['disciplines']['药理毒理']['status_text'] is None
    assert hit['issues'][0]['reason']=='unmapped_status_icon'


def test_icon_and_explicit_text_conflict_preserves_both_without_choosing():
    source=pages()
    source[0]['rows'][0][5]['text']='本专业未启动'
    hit=parse_review_capture(source,filters=FILTERS,acceptance_number='CYHL2600085')['results'][0]
    assert hit['disciplines']['药理毒理']['status_text'] is None
    assert hit['issues'][0]['reason']=='conflicting_status_signals'
    assert hit['raw_cells'][5]==source[0]['rows'][0][5]


@pytest.mark.parametrize('change',['wrong_scope','unapplied_lookup','header','gap','duplicate_page','date_column','secret_url'])
def test_source_scope_gaps_and_column_changes_fail_closed(change):
    source=pages()
    if change=='wrong_scope':
        source[0]['filters']['task_type']='NDA'
    elif change=='unapplied_lookup':
        source[0]['filters']['ui_acceptance_number']='CYHL2600085'
    elif change=='header':
        source[0]['section']='acceptance'
    elif change=='gap':
        source[1]['rows']=[]
    elif change=='duplicate_page':
        source[1]=deepcopy(source[0])
    elif change=='date_column':
        source[0]['headers'][3]='批准日期'
    else:
        source[0]['url']=URL+'?token=not-public'
    with pytest.raises(CaptureError) as error:
        parse_review_capture(source,filters=FILTERS)
    assert 'not-public' not in str(error.value)
