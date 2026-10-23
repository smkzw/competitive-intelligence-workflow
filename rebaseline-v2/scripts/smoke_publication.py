"""Isolated, explicitly bounded publication discovery/fetch; no model or report acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from ciw2.config import Settings
from ciw2.harness.tools import ToolContext
from ciw2.sources import pubmed
from ciw2.sources.http import source_text
from ciw2.store.cas import CAS
from ciw2.store.db import DB


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--query',action='append',default=[])
    parser.add_argument('--pmid',action='append',default=[])
    parser.add_argument('--max-results',type=int,required=True,help='明确每条发现检索预算，不代表全量文献')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not 1<=args.max_results<=100 or not (args.query or args.pmid):
        parser.error('提供查询或PMID及1–100的显式检索预算')
    output=args.output.resolve()
    if output.exists():
        parser.error('输出目录必须新建，不覆盖来源/回执')
    output.mkdir(parents=True)
    settings=replace(Settings(),data_dir=output/'data')
    settings.ensure_dirs()
    db,cas=DB(settings.db_path),CAS(settings.cas_dir)
    pid=db.create_project('公开文献来源验证',['C'])
    rid=db.create_run(pid)
    ctx=ToolContext(db=db,cas=cas,settings=settings,project_id=pid,run_id=rid,
                    stage='publication_source_smoke',extra={'fetch_cache':{}})
    result={'queries':[],'articles':[],'fetched':[],'errors':[]}
    for query in args.query:
        try:
            ids=pubmed.esearch(ctx,query,args.max_results)
            result['queries'].append({'query':query,'pmids':ids,'budget':args.max_results})
        except (RuntimeError,ValueError,OSError,KeyError) as exc:
            result['errors'].append({'operation':'search','error_type':type(exc).__name__})
    ids=list(dict.fromkeys(pmid for query in result['queries'] for pmid in query['pmids']))
    if ids:
        try:
            result['articles']=pubmed.esummary(ctx,ids)
        except (RuntimeError,ValueError,OSError,KeyError) as exc:
            result['errors'].append({'operation':'summary','error_type':type(exc).__name__})
    for pmid in args.pmid:
        try:
            response=pubmed._pubmed_fetch(ctx,pubmed.PubFetchArgs(pmid=pmid,full_text=True))
            text=source_text(ctx,response['source_id']) or ''
            result['fetched'].append({'pmid':pmid,'source_id':response['source_id'],
                'url':response['source_url'],'chars':len(text)})
        except (RuntimeError,ValueError,OSError,KeyError) as exc:
            result['errors'].append({'operation':'fetch','pmid':pmid,'error_type':type(exc).__name__})
    result.update(scope='BOUNDED_PUBLICATION_SOURCE_ONLY',model_calls=0,full_literature_coverage=False,
        scientific_revision_acceptance='NOT_RUN',pipeline_acceptance='NOT_RUN',project_id=pid,run_id=rid,
        sources=db.query('SELECT id,kind,url,digest,text_digest FROM sources WHERE project_id=?',(pid,)),
        code_sha256=hashlib.sha256(Path(pubmed.__file__).read_bytes()).hexdigest())
    (output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('scope','queries','articles','fetched','errors','model_calls')},ensure_ascii=False))
    return int(bool(result['errors']))


if __name__=='__main__':
    raise SystemExit(main())
