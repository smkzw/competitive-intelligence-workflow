"""Opt-in real public registry smoke in an explicitly authorized Ego space."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import ciw2.sources  # noqa: F401 - register the ordinary production source tools
from ciw2.config import Settings
from ciw2.harness.tools import REGISTRY, ToolContext
from ciw2.store.cas import CAS
from ciw2.store.db import DB


def source_hashes(module: Path) -> dict[str,str]:
    files=('config.py','sources/china.py','sources/china_capture.py','sources/china_browser.py',
           'sources/china_browser.mjs','sources/http.py','sources/cde_browser.py',
           'sources/cde_browser.mjs','sources/cde_capture.py','sources/cde_resume.py','sources/cde_review_browser.py',
           'sources/cde_review_browser.mjs','sources/cde_review_capture.py','sources/cde_priority.py','sources/cde_priority.mjs')
    return {name:hashlib.sha256((module/name).read_bytes()).hexdigest() for name in files}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--space',type=int,required=True,help='已授权专用Ego空间，不自动创建或接管')
    parser.add_argument('--query',required=True)
    parser.add_argument('--registry',choices=['chinadrugtrials','cde'],default='chinadrugtrials')
    parser.add_argument('--cde-section',choices=['acceptance','new_review_task_chemical_ind',
                        'new_review_task_biological_trial','priority_included'],default='acceptance')
    parser.add_argument('--query-kind',choices=['keyword','drug_name','company','acceptance_number','indication','target'],
                        default='keyword')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume-output',type=Path,help='同一隔离冒烟的失败回执目录；复核来源锚点后补缺页，范围变化则重新采集')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('输出目录必须是新的，不覆盖来源或回执')
    output.mkdir(parents=True)
    module = Path(__file__).resolve().parents[1]/'src/ciw2'
    source_files = source_hashes(module)
    entrypoint_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    prior = json.loads((args.resume_output/'receipt.json').read_text()) if args.resume_output else None
    if prior and (prior['query'] != args.query or prior['space'] != args.space):
        parser.error('恢复输入与原查询/浏览器空间不符')
    if prior and (prior.get('registry','chinadrugtrials') != args.registry or prior.get('query_kind','keyword') != args.query_kind):
        parser.error('恢复检索类型与原来源不符')
    if prior and prior.get('cde_section','acceptance')!=args.cde_section:
        parser.error('恢复CDE栏目与原来源不符')
    settings = replace(Settings(),data_dir=(args.resume_output or output)/'data',china_ego_space_id=args.space)
    settings.ensure_dirs()
    db, cas = DB(settings.db_path), CAS(settings.cas_dir)
    if prior:
        pid,rid = prior['project_id'],prior['run_id']
        if not db.one('SELECT id FROM runs WHERE id=? AND project_id=? AND status=?',(rid,pid,'failed')):
            parser.error('只恢复属于原项目的失败冒烟，不更改健康或其他运行')
        db.set_run(rid,'running')
    else:
        pid = db.create_project(args.query,['A'])
        rid = db.create_run(pid)
    ctx = ToolContext(db=db,cas=cas,settings=settings,project_id=pid,run_id=rid,stage='china_source_smoke',extra={})
    try:
        tool = REGISTRY.get('china_registry_search')
        result = tool.fn(ctx,tool.args_model.model_validate({
            'registry':args.registry,'query':args.query,'query_kind':args.query_kind,'cde_section':args.cde_section,
            'route_id':f'china:{args.registry}:browser_smoke'}))
    except (RuntimeError,ValueError,OSError,KeyError) as exc:
        result = {'mode':'failed','error_type':type(exc).__name__}
    ok = result.get('mode') == 'browser' and result.get('complete') is True
    source = db.one('SELECT * FROM sources WHERE id=?',(result.get('source_id'),)) if ok else None
    if source:
        assert hashlib.sha256(cas.get(source['digest'])).hexdigest() == source['digest']
        assert len(result['results']) == result.get('matched_count',result['total_records'])
    (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    db.set_run(rid,'succeeded' if ok else 'failed',None if ok else '公开浏览器来源未完成')
    code_unchanged = all(hashlib.sha256((module/name).read_bytes()).hexdigest()==digest
                         for name,digest in source_files.items()) and entrypoint_sha256 == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    receipt = {'scope':'REAL_CHINA_SOURCE_TOOL_ONLY','query':args.query,'space':args.space,
        'resumed_from':args.resume_output.name if args.resume_output else None,
        'registry':args.registry,'query_kind':args.query_kind,'cde_section':args.cde_section,'entrypoint_sha256':entrypoint_sha256,
        'project_id':pid,'run_id':rid,'mode':result.get('mode'),'complete':bool(result.get('complete')),
        'rows':len(result.get('results',[])),'source_total_records':result.get('total_records'),'pages':result.get('pages_read'),
        'source_id':source['id'] if source else None,'source_sha256':source['digest'] if source else None,
        'source_files':source_files,'code_unchanged_during_run':code_unchanged,
        'retained_sources':[{'id':row['id'],'digest':row['digest'],'meta':json.loads(row['meta'])}
                            for row in db.query('SELECT * FROM sources WHERE project_id=?',(pid,))],
        'model_calls':0,'clinical_universe_accepted':False,'M2_acceptance':'NOT_RUN','pipeline_acceptance':'NOT_RUN'}
    (output/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_files'},ensure_ascii=False))
    return 0 if ok and code_unchanged else 1


if __name__ == '__main__':
    raise SystemExit(main())
