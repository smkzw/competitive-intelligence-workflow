"""A summary packet cannot read unrelated current facts by guessing their IDs."""
import json

from test_analysis_budget import setup_analysis

from ciw2.harness.tools import REGISTRY


def test_summary_reader_enforces_alias_or_real_id_membership(settings, monkeypatch):
    rc, _, _ = setup_analysis(settings, monkeypatch, count=1)
    allowed = rc.db.current_facts(rc.project_id)[0]
    other = rc.db.add_fact({'project_id': rc.project_id, 'entity_id': allowed['entity_id'],
        'field': 'design.sample_size', 'value': 999, 'tier': 'critical',
        'status': 'verified', 'extracted_by': 'code:test'})
    ctx = rc.tool_ctx();ctx.extra['summary_fact_refs'] = {'summary_ref_0': allowed['id']}
    tool = REGISTRY.get('read_project_fact')
    result = json.loads(tool.run(ctx, {'fact_id': other}))
    assert result['status'] == 'tool_failed'
    assert 'fact' not in result
    for ref in ('summary_ref_0', allowed['id']):
        assert json.loads(tool.run(ctx, {'fact_id': ref}))['fact']['id'] == allowed['id']
    assert json.loads(tool.run(rc.tool_ctx(), {'fact_id': other}))['fact']['id'] == other
