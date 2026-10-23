"""Smoke-driver metadata only; no source/model/clinical acceptance."""
import json

from test_drug_enrichment import setup

from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service


def test_selected_unit_smoke_does_not_leave_a_queued_or_successful_full_research_run(settings,tmp_path,monkeypatch):
    import scripts.smoke_drug_profile as smoke
    original,_,_=setup(settings)
    output=tmp_path/'smoke-output'
    monkeypatch.setattr(smoke,'Service',lambda s:Service(s,llm_factory=lambda _:(ScriptedLLM([]),None)))
    monkeypatch.setattr(smoke,'_call',lambda *_:{'facts':[],'gaps':[],'extraction_model':'scripted'})
    monkeypatch.setattr('sys.argv',['smoke_drug_profile.py','--source-data',str(original.settings.data_dir),
        '--drug','ExampleDrug','--url','https://example.org/unused-fixture','--output',str(output)])
    assert smoke.main()==0
    receipt=json.loads((output/'receipt.json').read_text())
    svc=Service(type(settings)(data_dir=output/'data'),llm_factory=lambda _:(ScriptedLLM([]),None))
    assert svc.db.run(receipt['run_id'])['status']=='failed'
    assert svc.db.project(receipt['project_id'])['reports']==list('ABC')
    assert receipt['original_reports']==['A'] and original.db.project(receipt['project_id'])['reports']==['A']
    assert receipt['state']=='RETURNED' and receipt['full_M3']=='NOT_ACCEPTED'
