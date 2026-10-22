import pytest

from ciw2.domain.models import ExtractedFact
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.stages import verify
from ciw2.service import Service
from ciw2.sources.http import register_text


@pytest.mark.parametrize('target', ['valid', 'other-field', 'other-project', 'unverified'])
def test_verified_design_revision_has_explicit_same_entity_field_lineage(settings, target):
    service = Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))
    pid = service.create_project('设计', ['C'])
    rid = service.db.create_run(pid)
    context = service.context(pid, rid)
    trial, _ = service.db.upsert_entity(pid, 'trial', 'NCT00000001')
    old_project = service.create_project('其他', ['C']) if target == 'other-project' else pid
    field = 'design.primary_endpoint' if target == 'other-field' else 'design.sample_size'
    old = service.db.add_fact({'project_id': old_project, 'entity_id': trial, 'field': field,
        'value': 941, 'tier': 'critical', 'status': 'verified', 'extracted_by': 'code:ctgov'})
    url = 'https://example.org/protocol'
    register_text(context.tool_ctx(), kind='web', url=url, text='The planned sample size was 1000 participants.')
    fact = ExtractedFact(entity='NCT00000001', field='design.sample_size', value=1000,
        source_url=url, quote='Not a real quotation' if target == 'unverified' else
        'The planned sample size was 1000 participants.', supersedes=old)
    service.db.set_stage(rid, 'extract_design', 'succeeded', output={'facts': [{**fact.model_dump(), 'drug': 'study-drug'}]})
    verify(context)
    stored = service.db.query('SELECT id,supersedes,status FROM facts WHERE project_id=? ORDER BY rowid', (pid,))
    latest = stored[-1]
    if target == 'valid':
        assert latest['supersedes'] == old and latest['status'] == 'verified'
        assert old not in {f['id'] for f in service.db.current_facts(pid)}
    else:
        assert latest['supersedes'] is None
        assert latest['status'] in {'unverified', 'conflict'}
        assert service.db.one('SELECT id FROM facts WHERE id=?', (old,)) is not None
