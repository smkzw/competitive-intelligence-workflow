"""离线验证同次运行 CDE 部分来源复用；不产生浏览器、来源或事实证据。"""
import json
from copy import deepcopy
from dataclasses import replace

import pytest
from test_cde_browser import FILTERS as ACCEPTANCE_FILTERS
from test_cde_review_capture import pages as review_pages

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources import cde_resume, china_browser
from ciw2.sources.cde_capture import parse_capture
from ciw2.sources.cde_review_capture import SCOPE, parse_review_capture

FILTERS = {**ACCEPTANCE_FILTERS}


def list_url(nonce='a'):
    return 'https://www.cde.org.cn/main/xxgk/listpage/' + nonce * 32


def row(ordinal, number):
    return [str(ordinal), number, '原药联合片', '化学药品', '新药', '1', '企业一', '2026-01-02']


def page(*, current=1, total=1, page_size=50, rows=None, filters=None, url=None):
    rows = rows if rows is not None else [row(1, 'CXHL2600001')]
    return {'url': url or list_url('a'), 'section': 'acceptance', 'filters': dict(filters or FILTERS),
            'headers': ['序号', '受理号', '药品名称', '药品类型', '申请类型', '注册分类',
                        '企业名称', '承办日期'],
            'rows': rows,
            'pagination': {'current': current, 'page_size': page_size, 'total_records': total,
                           'text': f'共 {total} 条'}}


def empty_page():
    page_obj = page(rows=[], total=0)
    page_obj['pagination'] = {'current': 0, 'page_size': None, 'total_records': 0, 'text': '暂无内容'}
    return page_obj


def payload(pages, *, section='acceptance', filters=None):
    return {'section': section, 'filters': dict(filters or FILTERS), 'pages': pages}


def acceptance_validate(filters=None):
    filters = dict(filters or FILTERS)
    return lambda pages: parse_capture(pages, filters=filters, allow_partial=True)


def review_validate():
    return lambda pages: parse_review_capture(pages, filters=SCOPE, allow_partial=True)


def store(ctx, *, raw, url, complete, section, filters, run_id=None, observation_complete=None,
          mode='browser_checked', meta=None):
    digest = ctx.cas.put(raw)
    source_id = ctx.db.add_source(ctx.project_id, 'cde', url, digest, title='测试来源',
                                  meta=meta if meta is not None else {
                                      'method': 'ego_public_ui', 'complete': complete,
                                      'request_context': {'registry': 'cde', 'section': section,
                                                          'filters': filters}})
    ctx.db.log_step(run_id or ctx.run_id, ctx.stage, 'source', 0, 'source_observation', {
        'project_id': ctx.project_id, 'source_id': source_id, 'mode': mode, 'url': url,
        'http_status': None, 'complete': complete if observation_complete is None else observation_complete})
    return source_id


def store_payload(ctx, capture, *, complete, section='acceptance', filters=None, url=None, **kw):
    pages = capture.get('pages') or []
    url = url or (pages[0].get('url') if pages else None)
    if not isinstance(url, str):
        raise TypeError('测试来源需要显式 URL')
    return store(ctx, raw=json.dumps(capture, ensure_ascii=False).encode('utf-8'), url=url,
                 complete=complete, section=section, filters=dict(filters or capture['filters']), **kw)


def snapshot(ctx):
    tables = ('sources', 'agent_steps', 'entities', 'facts', 'coverage')
    return {'db': {name: ctx.db.query(f'SELECT * FROM {name} ORDER BY rowid') for name in tables},
            'cas': sorted(path.relative_to(ctx.cas.root).as_posix()
                          for path in ctx.cas.root.rglob('*') if path.is_file()),
            'extra': deepcopy(ctx.extra)}


@pytest.fixture
def ctx(settings):
    service = Service(replace(settings, china_ego_space_id=77),
                      llm_factory=lambda s: (ScriptedLLM([]), None))
    project_id = service.create_project('部分恢复离线测试', ['A'])
    return service.context(project_id, service.db.create_run(project_id)).tool_ctx()


def test_acceptance_partial_preserves_raw_pages_and_exact_gap(ctx, monkeypatch):
    monkeypatch.setattr(china_browser, '_invoke',
                        lambda *a, **k: pytest.fail('部分复用不得启动浏览器'))
    capture = payload([page(current=2, total=51, rows=[row(51, 'CXHL2600051')])])
    source_id = store_payload(ctx, capture, complete=False)
    before = snapshot(ctx)
    result = cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS),
                                     validate=acceptance_validate())
    assert result == {'source_id': source_id, 'pages': capture['pages'], 'pages_read': [2],
                      'pending_pages': [1], 'total_records': 51}
    source = ctx.db.one('SELECT * FROM sources WHERE id=?', (source_id,))
    assert ctx.cas.get(source['digest']) == json.dumps(capture, ensure_ascii=False).encode('utf-8')
    assert result['pages'][0]['rows'][0] == row(51, 'CXHL2600051')
    parsed = parse_capture(result['pages'], filters=FILTERS, allow_partial=True)
    assert parsed['results'][0]['raw_cells'] == row(51, 'CXHL2600051')
    assert parsed['pages_read'] == [2] and parsed['pending_pages'] == [1]
    assert snapshot(ctx) == before
    assert 'source_ids_read' not in ctx.extra


def test_review_partial_preserves_source_cells_and_gap(ctx, monkeypatch):
    monkeypatch.setattr(china_browser, '_invoke',
                        lambda *a, **k: pytest.fail('部分复用不得启动浏览器'))
    pages = review_pages()
    capture = payload([pages[0]], section='new_review_task', filters=SCOPE)
    source_id = store_payload(ctx, capture, complete=False, section='new_review_task', filters=SCOPE)
    result = cde_resume.load_partial(ctx, section='new_review_task', filters=dict(SCOPE),
                                     validate=review_validate())
    assert result['source_id'] == source_id and result['pages'] == [pages[0]]
    assert result['pages_read'] == [1] and result['pending_pages'] == [2] and result['total_records'] == 3
    hit = parse_review_capture(result['pages'], filters=SCOPE, acceptance_number='CYHL2600085',
                               allow_partial=True)['results'][0]
    assert hit['review_status_text'] == '排队待审评'
    assert hit['disciplines']['药理毒理']['status_text'] == '本专业已完成审评'
    assert hit['raw_cells'] == pages[0]['rows'][0]


def test_other_section_filters_run_or_project_never_match(ctx):
    capture = payload([page(current=2, total=51, rows=[row(51, 'CXHL2600051')])])
    store_payload(ctx, capture, complete=False)
    validate = acceptance_validate()
    assert cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS),
                                   validate=validate) is not None
    assert cde_resume.load_partial(ctx, section='acceptance',
                                   filters={**FILTERS, 'drug_name': '其他药'}, validate=validate) is None
    assert cde_resume.load_partial(ctx, section='acceptance',
                                   filters={**FILTERS, 'drug_name': ' 原药 '}, validate=validate) is None
    assert cde_resume.load_partial(ctx, section='new_review_task', filters=dict(FILTERS),
                                   validate=validate) is None
    fresh_run = ctx.db.create_run(ctx.project_id)
    assert cde_resume.load_partial(replace(ctx, run_id=fresh_run), section='acceptance',
                                   filters=dict(FILTERS), validate=validate) is None
    other_project = ctx.db.create_project('其他项目', ['A'])
    other_ctx = replace(ctx, project_id=other_project, run_id=ctx.db.create_run(other_project))
    store_payload(other_ctx, capture, complete=False)
    another_run = ctx.db.create_run(ctx.project_id)
    assert cde_resume.load_partial(replace(ctx, run_id=another_run), section='acceptance',
                                   filters=dict(FILTERS), validate=validate) is None
    assert cde_resume.load_partial(other_ctx, section='acceptance', filters=dict(FILTERS),
                                   validate=validate) is not None
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(replace(ctx, run_id=other_ctx.run_id), section='acceptance',
                                filters=dict(FILTERS), validate=validate)


def test_latest_complete_suppresses_older_partial(ctx):
    partial = payload([page(current=2, total=51, rows=[row(51, 'CXHL2600051')])])
    store_payload(ctx, partial, complete=False)
    newer = payload([page(current=2, total=51, rows=[row(51, 'CXHL2600052')])])
    store_payload(ctx, newer, complete=True)
    assert cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS),
                                   validate=acceptance_validate()) is None


def test_process_incomplete_but_validated_complete_capture_is_not_partial(ctx):
    for capture in (payload([page()]), payload([empty_page()])):
        run_id = ctx.db.create_run(ctx.project_id)
        store_payload(replace(ctx, run_id=run_id), capture, complete=False, run_id=run_id)
        assert cde_resume.load_partial(replace(ctx, run_id=run_id), section='acceptance',
                                       filters=dict(FILTERS), validate=acceptance_validate()) is None


def test_duplicate_pages_follow_production_parser_not_first_wins(ctx):
    page_obj = review_pages()[0]
    capture = payload([page_obj, deepcopy(page_obj)], section='new_review_task', filters=SCOPE)
    store_payload(ctx, capture, complete=False, section='new_review_task', filters=SCOPE)
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx, section='new_review_task', filters=dict(SCOPE),
                                validate=review_validate())


@pytest.mark.parametrize('damage', ['corrupt_bytes', 'missing_bytes', 'malformed_json',
                                    'payload_section', 'payload_filters', 'missing_pages',
                                    'empty_pages'])
def test_unusable_matching_evidence_fails_closed_without_older_fallback(ctx, damage):
    older = payload([page(current=2, total=51, rows=[row(49, 'CXHL2600049')])])
    store_payload(ctx, older, complete=False)
    newest = payload([page(current=2, total=51, rows=[row(51, 'CXHL2600051')])])
    if damage in {'corrupt_bytes', 'missing_bytes'}:
        source_id = store_payload(ctx, newest, complete=False)
        source = ctx.db.one('SELECT * FROM sources WHERE id=?', (source_id,))
        path = ctx.cas._path(source['digest'])
        path.write_bytes(b'corrupt owned test CAS') if damage == 'corrupt_bytes' else path.unlink()
    elif damage == 'malformed_json':
        store(ctx, raw=b'{"section": "acceptance",', url=list_url('b'), complete=False,
              section='acceptance', filters=FILTERS)
    else:
        damaged = deepcopy(newest)
        if damage == 'payload_section':
            damaged['section'] = 'new_review_task'
        elif damage == 'payload_filters':
            damaged['filters'] = {**FILTERS, 'drug_name': '其他药'}
        elif damage == 'missing_pages':
            damaged.pop('pages')
        else:
            damaged['pages'] = []
        store_payload(ctx, damaged, complete=False, url=list_url('b'), filters=FILTERS)
    with pytest.raises(china_browser.BrowserFailed) as error:
        cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS),
                                validate=acceptance_validate())
    assert '原药' not in str(error.value)


@pytest.mark.parametrize('validate', [
    lambda pages: None,
    lambda pages: {'complete': 'no'},
    lambda pages: {'complete': False},
    lambda pages: {'complete': False, 'pages_read': [], 'pending_pages': [1], 'total_records': 51},
    lambda pages: {'complete': False, 'pages_read': [2, 2], 'pending_pages': [1], 'total_records': 51},
    lambda pages: {'complete': False, 'pages_read': [True], 'pending_pages': [2], 'total_records': 51},
    lambda pages: {'complete': False, 'pages_read': [2], 'pending_pages': [], 'total_records': 51},
    lambda pages: {'complete': False, 'pages_read': [2], 'pending_pages': [2], 'total_records': 51},
    lambda pages: {'complete': False, 'pages_read': [2], 'pending_pages': [1], 'total_records': True},
    lambda pages: {'complete': False, 'pages_read': [2], 'pending_pages': [1], 'total_records': 0},
    lambda pages: {'complete': False, 'pages_read': [2], 'pending_pages': [1]},
    lambda pages: {'complete': False, 'pages_read': [2, 3], 'pending_pages': [1], 'total_records': 51},
    lambda pages: (_ for _ in ()).throw(ValueError('broken validator')),
], ids=['none', 'complete_type', 'missing_read', 'empty_read', 'duplicate_read', 'bool_page',
        'empty_pending', 'overlap', 'bool_total', 'zero_total', 'missing_total', 'read_count',
        'validator_raises'])
def test_invalid_validator_shapes_fail_closed(ctx, validate):
    store_payload(ctx, payload([page(current=2, total=51, rows=[row(51, 'CXHL2600051')])]),
                  complete=False)
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS), validate=validate)


def test_non_callable_validator_fails_closed(ctx):
    store_payload(ctx, payload([page(current=2, total=51, rows=[row(51, 'CXHL2600051')])]),
                  complete=False)
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS), validate=None)


def test_incomplete_metadata_requires_matching_incomplete_observation(ctx):
    store_payload(ctx, payload([page(current=2, total=51, rows=[row(51, 'CXHL2600051')])]),
                  complete=False, observation_complete=True)
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS),
                                validate=acceptance_validate())


def test_malformed_metadata_or_observation_records_fail_closed(ctx):
    source_id = store_payload(ctx, payload([page(current=2, total=51,
                                                 rows=[row(51, 'CXHL2600051')])]), complete=False)
    ctx.db.execute('UPDATE sources SET meta=? WHERE id=?', ('{broken', source_id))
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS),
                                validate=acceptance_validate())
    ctx.db.execute("UPDATE sources SET meta=? WHERE id=?",
                   (json.dumps({'complete': False, 'request_context': {
                       'registry': 'cde', 'section': 'acceptance', 'filters': FILTERS}}), source_id))
    ctx.db.log_step(ctx.run_id, ctx.stage, 'source', 0, 'source_observation', '{broken')
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx, section='acceptance', filters=dict(FILTERS),
                                validate=acceptance_validate())


def test_invalid_arguments_and_missing_context_fail_closed(ctx):
    validate = acceptance_validate()
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx, section='', filters=dict(FILTERS), validate=validate)
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx, section='acceptance', filters=None, validate=validate)
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(replace(ctx, db=None), section='acceptance', filters=dict(FILTERS),
                                validate=validate)
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(replace(ctx, run_id=None), section='acceptance',
                                filters=dict(FILTERS), validate=validate)


def test_real_acceptance_writer_method_is_accepted_not_mistaken_for_other_scope(ctx):
    from ciw2.sources.cde_browser import _save

    pages=[page(current=2,total=51,rows=[row(51,'CXHL2600051')])]
    sid=_save(ctx,pages,FILTERS,complete=False)
    result=cde_resume.load_partial(ctx,section='acceptance',filters=FILTERS,validate=acceptance_validate())
    assert result is not None and result['source_id']==sid and result['pages']==pages


@pytest.mark.parametrize('complete',[None,'false',0])
def test_matching_completion_flag_requires_actual_boolean_not_silent_fresh_retry(ctx,complete):
    source_id=store_payload(ctx,payload([page(current=2,total=51,rows=[row(51,'CXHL2600051')])]),complete=False)
    source=ctx.db.one('SELECT meta FROM sources WHERE id=?',(source_id,))
    meta=json.loads(source['meta']);meta['complete']=complete
    ctx.db.execute('UPDATE sources SET meta=? WHERE id=?',(json.dumps(meta),source_id))
    with pytest.raises(china_browser.BrowserFailed):
        cde_resume.load_partial(ctx,section='acceptance',filters=FILTERS,validate=acceptance_validate())
