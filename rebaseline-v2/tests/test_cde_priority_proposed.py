"""The proposed directory is not the included list: dates, roles and raw gaps differ."""
import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_cde_review_browser import ctx as source_ctx
from test_cde_review_browser import invoke

from ciw2.sources import cde_priority, china, china_browser
from ciw2.sources.cde_capture import CaptureError


@pytest.fixture
def ctx(settings):
    return source_ctx.__wrapped__(settings)


def page():
    return json.loads((Path(__file__).parent/'fixtures/cde-priority-proposed.json').read_text())


def test_proposed_directory_preserves_source_roles_dates_and_missing_ids():
    raw=page();result=cde_priority.parse_capture([raw],section='priority_proposed')
    assert result['complete'] and result['total_records']==9
    assert [r['raw_cells'] for r in result['results']]==raw['rows']
    first=result['results'][0]
    assert first['acceptance_number'] is None and first['acceptance_number_text']=='无'
    assert first['application_date_text']=='2026-10-20' and first['publicity_date_text']=='2026-10-23'
    assert first['publicity_end_date_text']=='2026-10-30'
    assert first['registration_applicant_text']=='康方赛诺医药有限公司'
    assert not {'handled_date_text','directory_status_text','approved','mah'} & first.keys()


def test_proposed_is_not_accepted_under_included_column_contract():
    with pytest.raises(CaptureError):cde_priority.parse_capture([page()])
    wrong=deepcopy(page());wrong['headers'][6]='承办日期'
    with pytest.raises(CaptureError):cde_priority.parse_capture([wrong],section='priority_proposed')


def test_proposed_public_tool_uses_separate_request_scope_without_new_facts(ctx,monkeypatch):
    seen=[]
    def capture(*a,**kw):seen.append(kw['options']);return invoke([page()])
    monkeypatch.setattr(china_browser,'_invoke',capture)
    result=china._china(ctx,china.ChinaArgs(registry='cde',query='JXHS2600124',query_kind='acceptance_number',
                       cde_section='priority_proposed',route_id='proposed'))
    assert seen[0]['section']=='priority_proposed' and result['complete'] and result['count']==0
    source=ctx.db.one('SELECT * FROM sources WHERE id=?',(result['source_id'],))
    assert json.loads(source['meta'])['request_context']['section']=='priority_proposed'
    assert not ctx.db.current_facts(ctx.project_id) and not ctx.db.entities(ctx.project_id,'drug')


def test_two_priority_columns_and_cache_scopes_cannot_replace_each_other(ctx,monkeypatch):
    from test_cde_priority import captures
    seen=[]
    def capture(*a,**kw):
        section=kw['options']['section'];seen.append(section)
        return invoke([page()] if section=='priority_proposed' else captures())
    monkeypatch.setattr(china_browser,'_invoke',capture)
    included=cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number')
    proposed=cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number',section='priority_proposed')
    again=cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number',section='priority_proposed')
    assert seen==['priority_included','priority_proposed']
    assert included['source_id']!=proposed['source_id']==again['source_id']
    assert included['matched_count']==1 and proposed['matched_count']==0
    assert proposed['unresolved_acceptance_count']==9
    assert included['results'][0]['directory_status_text']=='已纳入'


def test_unobserved_priority_section_does_not_open_a_browser(ctx,monkeypatch):
    monkeypatch.setattr(china_browser,'_invoke',lambda *a,**kw:pytest.fail('Unknown source must not browse'))
    with pytest.raises(china_browser.BrowserBlocked):
        cde_priority.browser_search(ctx,'JXHS2600124','acceptance_number',section='unobserved')
