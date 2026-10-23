"""Each design-index entry carries its own current status, never a group status."""
import re

import pytest
from test_quote_requalification import _legacy, _source
from test_quote_requalification import env as env  # noqa: PLC0414 - pytest fixture registration

from ciw2.render.portal import render_report, report_data


def index_entry(html, fid):
    index=html.split('class="endpoint-index"',1)[1]
    index=re.sub(r'<details class="evidence">.*?</details>','',index,flags=re.DOTALL)
    return index.split(f'data-fact-id="{fid}"',1)[1].split('class="endpoint-entry"',1)[0].split('</td></tr>',1)[0]


@pytest.mark.parametrize('kind',['primary','secondary'])
def test_sole_pending_endpoint_status_is_outside_folded_source_evidence(env,kind):
    svc,rc,pid,trial=env
    sid=_source(rc)
    fid=_legacy(rc,trial,sid,field=f'design.{kind}_endpoint',
        value={'measure':'Outcome','time_frame':'Week 16','description':'Full definition.'})
    html=render_report(svc.db,pid,'C')
    assert 'badge unverified' in index_entry(html,fid)
    assert 'Full definition.' in html


def test_same_endpoint_group_keeps_verified_and_pending_studies_separate(env):
    svc,rc,pid,trial=env
    sid=_source(rc)
    value={'measure':'Outcome','time_frame':'Week 16','description':'Full definition.'}
    good=_legacy(rc,trial,sid,field='design.primary_endpoint',value=value,extracted_by='code:fixture')
    second,_=svc.db.upsert_entity(pid,'trial','NCT00000003')
    pending=_legacy(rc,second,sid,field='design.primary_endpoint',value=value)
    before=svc.db.query('SELECT * FROM facts ORDER BY id')
    groups=report_data(svc.db,pid,'C')['endpoint_groups']
    assert len(groups)==1 and {e['status'] for e in groups[0]['entries']}=={'verified','unverified'}
    html=render_report(svc.db,pid,'C')
    assert 'badge unverified' not in index_entry(html,good)
    assert 'badge unverified' in index_entry(html,pending)
    assert svc.db.query('SELECT * FROM facts ORDER BY id')==before
