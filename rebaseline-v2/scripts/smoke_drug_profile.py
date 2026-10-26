"""Opt-in real profile units on a recoverable copy, never a whole-universe acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
import runpy
from pathlib import Path

from ciw2.config import Settings
from ciw2.pipeline.extraction import _call, _key, _tasks
from ciw2.pipeline.requalify import requalify_project
from ciw2.pipeline.stages import verify
from ciw2.render.portal import render_report, report_data
from ciw2.service import Service
from ciw2.sources.nmpa_ingest import activate_source


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-data',type=Path,required=True)
    parser.add_argument('--drug',action='append',required=True,help='Exact existing drug entity name')
    parser.add_argument('--url',action='append',required=True,help='Official direct source lead; not a claim')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(exist_ok=False,parents=True)
    helpers=runpy.run_path(str(Path(__file__).with_name('smoke_nmpa_identity.py')))
    original=args.source_data.resolve()
    before=helpers['clone'](original,out/'data')
    settings=Settings(data_dir=out/'data')
    svc=Service(settings)
    projects=svc.db.query('SELECT id FROM projects')
    if len(projects)!=1:raise ValueError('Smoke requires exactly one existing source project')
    pid=projects[0]['id'];rid=svc.db.create_run(pid)
    original_reports=svc.db.project(pid)['reports']
    svc.db.execute('UPDATE projects SET reports=? WHERE id=?',(json.dumps(list('ABC')),pid))
    svc.db.set_run(rid,'running')
    rc=svc.context(pid,rid);rc.stage='enrich_drugs'
    selected=[d for d in svc.db.entities(pid,'drug') if d['name'] in set(args.drug)]
    if len(selected)!=len(set(args.drug)):raise ValueError('Every selected name must identify one existing drug')
    receipt={'scope':'SELECTED_REAL_PROFILE_UNITS_NOT_FULL_M3_OR_UNIVERSE','project_id':pid,'run_id':rid,
        'selected_drugs':args.drug,'state':'STARTED'}
    (out/'started.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    output={'facts':[],'gaps':[],'errors':[],'pending_drug_ids':[
        d['id'] for d in svc.db.entities(pid,'drug') if d['id'] not in {d['id'] for d in selected}]}
    try:
        # Quote-rule changes requalify the same original sources, without HTTP/model refetch.
        for source in svc.db.query("SELECT id FROM sources WHERE project_id=? AND kind='nmpa'",(pid,)):
            activate_source(rc.tool_ctx(),source['id'])
        receipt['old_llm_requalification']=requalify_project(svc.db,svc.cas,pid)
        for drug in selected:
            task=_tasks(rc,'extract-results',drug,{'mode':'identity_enrichment','evidence_urls':args.url})[0]
            result=_call(rc,'extract-results',task,_key(rc,'extract-results',task))
            output['facts'].extend({**fact,'drug':drug['name'],'drug_entity_id':drug['id'],
                                   'extraction_model':result['extraction_model']}
                                   for fact in result['facts'])
            output['gaps'].extend(result['gaps'])
        # This is a deliberately bounded source slice, not a completed normal stage.
        svc.db.set_stage(rid,'enrich_drugs','failed',error='Selected-unit smoke; remaining universe not run',output=output)
        receipt['verification']=verify(rc)
        receipt['replay']=verify(rc)
        hashes={}
        for report in 'ABC':
            html=render_report(svc.db,pid,report)
            (out/f'{report}.html').write_text(html)
            hashes[report]=hashlib.sha256(html.encode()).hexdigest()
        receipt.update(state='RETURNED',portals=hashes,profiles=[
            row for row in report_data(svc.db,pid,'A')['rows'] if row['id'] in {d['id'] for d in selected}])
    except Exception as exc:  # noqa: BLE001 - Persist a safe terminal receipt before returning failure.
        receipt.update(state='FAILED',error_type=type(exc).__name__)
        svc.db.set_stage(rid,'enrich_drugs','failed',error=type(exc).__name__,output=output)
    assert helpers['scientific_rows'](original)==before
    svc.db.set_run(rid,'failed',error='Selected profile units only; complete research pipeline not run')
    receipt.update(original_scientific_tables_unchanged=True,remaining_drugs=len(output['pending_drug_ids']),
        original_reports=original_reports,
        model_events=[json.loads(row['content']) for row in svc.db.query(
            "SELECT content FROM agent_steps WHERE run_id=? AND role='model' ORDER BY id",(rid,))],
        browser='NOT_RUN',full_M3='NOT_ACCEPTED')
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:receipt.get(key) for key in ('scope','state','project_id','run_id','verification',
        'replay','remaining_drugs','original_scientific_tables_unchanged','error_type')},ensure_ascii=False),flush=True)
    return 0 if receipt['state']=='RETURNED' else 1


if __name__=='__main__':
    raise SystemExit(main())
