"""Qualify public company/regulatory documents; no facts, entities or model adoption."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ciw2.config import Settings
from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources.websearch import FetchUrlArgs, _fetch_url


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',action='append',required=True)
    parser.add_argument('--term',action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--kind',choices=('company','regulator'),default='company')
    parser.add_argument('--allow-html',action='store_true',help='Explicitly accept ordinary HTML/text, not only PDFs')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    svc=Service(Settings(data_dir=out/'data'),llm_factory=lambda _:(ScriptedLLM([]),None))
    pid=svc.create_project('公司关系公开来源资格核对',['A'])
    rc=svc.context(pid,svc.db.create_run(pid));rc.stage='company_document_source'
    svc.db.set_run(rc.run_id,'running')
    ctx=rc.tool_ctx()
    receipt={'scope':'OFFICIAL_DOCUMENT_SOURCE_ONLY_NOT_ADOPTED_FACTS',
        'project_id':pid,'run_id':rc.run_id,'records':[],'model_calls':0,'adopted_facts':0}
    for url in args.url:
        try:
            result=_fetch_url(ctx,FetchUrlArgs(url=url,kind=args.kind))
            sid=result['source_id'];source=svc.db.one('SELECT * FROM sources WHERE id=?',(sid,))
            raw=svc.cas.get(source['digest']);text=svc.cas.get_text(source['text_digest'])
            pdf=bool(result['text_parser_id'] and b'%PDF-' in raw[:1024])
            if not pdf and not args.allow_html:
                raise ValueError('Official URL did not return a parsed PDF')
            if not text.strip():raise ValueError('Document text is empty')
            assert result['text']==text[:12000] and result['total_chars']==len(text)
            tail=_fetch_url(ctx,FetchUrlArgs(url=url,kind=args.kind,offset=max(0,len(text)-200)))
            assert tail['source_id']==sid and tail['text']==text[max(0,len(text)-200):]
            matches=[]
            for record in result['pages'] or [{'page':None,'start':0,'end':len(text)}]:
                number=record['page'];page=text[record['start']:record['end']]
                for term in args.term:
                    start=page.casefold().find(term.casefold())
                    if start>=0:matches.append({'page':number,'term':term,'offset_in_page':start,
                        'text':page[max(0,start-500):start+700]})
            receipt['records'].append({'source_id':sid,'url':result['source_url'],
                'raw_sha256':hashlib.sha256(raw).hexdigest(),'text_sha256':hashlib.sha256(text.encode()).hexdigest(),
                'parser_id':result['text_parser_id'],'pages':len(result['pages']),
                'format':'pdf' if pdf else 'html_or_text',
                'first_last_pages_read':pdf,'first_tail_text_read':True,'chars':len(text),'matches':matches})
        except Exception as exc:  # noqa: BLE001 - Retain completed source neighbors, no false empty result.
            receipt['records'].append({'url':url,'state':'FAILED','error_type':type(exc).__name__})
    failed=any(record.get('state')=='FAILED' for record in receipt['records'])
    svc.db.set_run(rc.run_id,'failed',error='Source qualification only, not complete research pipeline')
    receipt['state']='FAILED' if failed else 'RETURNED'
    receipt['source_events']=[json.loads(row['content']) for row in svc.db.query(
        "SELECT content FROM agent_steps WHERE run_id=? AND role IN ('source_observation','source_parse') ORDER BY id",(rc.run_id,))]
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:receipt[key] for key in ('scope','state','model_calls','adopted_facts')}))
    for record in receipt['records']:
        print(json.dumps({key:value for key,value in record.items() if key!='matches'},ensure_ascii=False))
        for match in record.get('matches',[]):print(json.dumps(match,ensure_ascii=False))
    return 1 if failed else 0


if __name__=='__main__':
    raise SystemExit(main())
