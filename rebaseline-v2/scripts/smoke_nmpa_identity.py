"""Opt-in identity adoption on an isolated real-project copy; no LLM or trial refetch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from ciw2.config import Settings
from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.nmpa_evidence import collect
from ciw2.render.portal import render_report, report_data
from ciw2.service import Service
from ciw2.sources import china_ingest, nmpa_detail
from ciw2.store.backup import _snapshot_database


def scientific_rows(data: Path) -> dict:
    with sqlite3.connect('file:'+str(data/'ciw2.sqlite3')+'?mode=ro',uri=True) as db:
        return {table:db.execute(f'SELECT * FROM {table} ORDER BY 1,2').fetchall()
                for table in ('sources','facts','entities','links')}


def clone(source: Path, target: Path) -> dict:
    before=scientific_rows(source)
    target.mkdir(parents=True,exist_ok=False)
    _snapshot_database(source/'ciw2.sqlite3',target/'ciw2.sqlite3')
    with sqlite3.connect(target/'ciw2.sqlite3') as db:
        digests={value for row in db.execute('SELECT digest,text_digest FROM sources') for value in row if value}
    for digest in digests:
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Malformed source digest')
        original=source/'cas'/digest[:2]/digest
        assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
        destination=target/'cas'/digest[:2]/digest
        destination.parent.mkdir(parents=True,exist_ok=True)
        os.link(original,destination)
    assert scientific_rows(target)==before
    return before


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-data',type=Path,required=True)
    parser.add_argument('--certificate-receipt',type=Path,action='append',required=True)
    parser.add_argument('--space',type=int,required=True)
    parser.add_argument('--trial',action='append',default=[],help='可选的既有CTR，显式读取尚缺的研究原表')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    before=clone(args.source_data.resolve(),args.output.resolve()/'data')
    svc=Service(Settings(data_dir=args.output.resolve()/'data',china_ego_space_id=args.space),
                llm_factory=lambda _:(ScriptedLLM([]),None))
    projects=svc.db.query('SELECT id FROM projects')
    if len(projects)!=1:raise ValueError('Smoke needs one actual project')
    pid=projects[0]['id']
    original_reports=svc.db.project(pid)['reports']
    svc.db.execute('UPDATE projects SET reports=? WHERE id=?',(json.dumps(list('ABC')),pid))
    rc=svc.context(pid,svc.db.create_run(pid));rc.stage='trial_evidence'
    result={'scope':'REAL_CERTIFICATE_IDENTITY_SLICE_NOT_M3_OR_FULL_PIPELINE',
        'project_id':pid,'run_id':rc.run_id,'model_calls':0,'trial_refetches':0,'state':'STARTED'}
    (args.output/'started.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    try:
        captures=[]
        for path in args.certificate_receipt:
            record=json.loads(path.read_text())['results'][0]
            captures.append(nmpa_detail.browser_detail(rc.tool_ctx(),record['source_url'],
                record['registration_number'],record['category']))
        adopted=collect(rc)
        assert not adopted['pending_records']
        replay=collect(rc)
        assert replay['adopted']==0
        designs=[china_ingest.ingest_trial(rc.tool_ctx(),ctr) for ctr in args.trial]
        current=svc.db.current_facts(pid)
        old_rows=before['facts']
        with sqlite3.connect(svc.settings.db_path) as db:
            assert set(old_rows)<=set(db.execute('SELECT * FROM facts').fetchall())
        portals={}
        for report in 'ABC':
            html=render_report(svc.db,pid,report)
            (args.output/f'{report}.html').write_text(html)
            portals[report]=hashlib.sha256(html.encode()).hexdigest()
        assert scientific_rows(args.source_data.resolve())==before
        facts=[f for f in current if f['extracted_by']=='code:nmpa']
        a=report_data(svc.db,pid,'A')
        identities=[r for r in a['rows'] if r['name_refs']]
        result.update(state='RETURNED',adoption=adopted,replay=replay,portals=portals,designs=designs,
            trial_refetches=len(args.trial),
            nmpa_fact_ids=[f['id'] for f in facts],nmpa_facts=len(facts),
            adopted_drugs=[{'id':r['id'],'name':r['name'],'name_zh':r['name_zh'],
                'china_mah':r['china_mah'],'trials':r['n_trials']} for r in identities],
            source_versions=[{'source_id':r['source_id'],'digest':r['source_digest'],
                'text_digest':r['text_digest']} for r in captures],
            original_scientific_rows_unchanged=True,browser_visual='NOT_RUN',
            original_reports=original_reports,display_copy_reports=list('ABC'),
            code_hashes={str(p.relative_to(Path(__file__).resolve().parents[1])):
                hashlib.sha256(p.read_bytes()).hexdigest() for p in
                (Path(__file__).resolve().parents[1]/'src').rglob('*')
                if p.is_file() and '__pycache__' not in p.parts})
    except Exception as exc:  # noqa: BLE001 - Preserve failed evidence, never call it empty success.
        result.update(state='FAILED',error_type=type(exc).__name__,error=str(exc))
    (args.output/'receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('scope','state','model_calls','trial_refetches')},ensure_ascii=False))
    return 0 if result['state']=='RETURNED' else 1


if __name__=='__main__':raise SystemExit(main())
