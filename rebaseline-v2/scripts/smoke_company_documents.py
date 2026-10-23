"""Qualify public text-PDF company sources; no clinical facts, entities or model adoption."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from ciw2.config import Settings
from ciw2.harness.llm import ScriptedLLM
from ciw2.service import Service
from ciw2.sources.http import fetch, register_text


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',action='append',required=True)
    parser.add_argument('--term',action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    binary=shutil.which('pdftotext')
    if not binary:raise ValueError('Existing native pdftotext unavailable; no installation or OCR attempted')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    svc=Service(Settings(data_dir=out/'data'),llm_factory=lambda _:(ScriptedLLM([]),None))
    pid=svc.create_project('公司关系公开来源资格核对',['A'])
    rc=svc.context(pid,svc.db.create_run(pid));rc.stage='company_document_source'
    version=subprocess.run([binary,'-v'],capture_output=True,text=True,check=True).stderr.splitlines()[0]
    receipt={'scope':'OFFICIAL_DOCUMENT_SOURCE_ONLY_NOT_ADOPTED_COMPANY_FACTS',
        'project_id':pid,'run_id':rc.run_id,'parser':version,'records':[],'model_calls':0,'adopted_facts':0}
    for url in args.url:
        try:
            result=fetch(None,url,kind='company',register=False)
            if not result.content.startswith(b'%PDF-'):raise ValueError('Official URL did not return PDF bytes')
            parsed=subprocess.run([binary,'-layout','-enc','UTF-8','-','-'],input=result.content,
                                  capture_output=True,check=True,timeout=90)
            text=parsed.stdout.decode('utf-8')
            if not text.strip():raise ValueError('Image-only/unextractable document; no OCR claimed')
            sid=register_text(rc.tool_ctx(),kind='company',url=result.url,text=text,raw=result.content,
                meta={'content_type':result.content_type,'text_parser':version,'layout':True})
            svc.db.log_step(rc.run_id,rc.stage,'source',0,'source_observation',{'project_id':pid,
                'source_id':sid,'url':result.url,'mode':result.mode,'http_status':result.status,
                'network_checked_at':result.network_checked_at})
            matches=[]
            for number,page in enumerate(text.split('\f'),start=1):
                for term in args.term:
                    start=page.casefold().find(term.casefold())
                    if start>=0:matches.append({'page':number,'term':term,'offset_in_page':start,
                        'text':page[max(0,start-500):start+700]})
            receipt['records'].append({'source_id':sid,'url':result.url,'http_status':result.status,
                'raw_sha256':hashlib.sha256(result.content).hexdigest(),
                'text_sha256':hashlib.sha256(parsed.stdout).hexdigest(),'chars':len(text),'matches':matches})
        except Exception as exc:  # noqa: BLE001 - Retain completed source neighbors, no false empty result.
            receipt['records'].append({'url':url,'state':'FAILED','error_type':type(exc).__name__})
    (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:receipt[key] for key in ('scope','parser','model_calls','adopted_facts')}))
    for record in receipt['records']:
        print(json.dumps({key:value for key,value in record.items() if key!='matches'},ensure_ascii=False))
        for match in record.get('matches',[]):print(json.dumps(match,ensure_ascii=False))
    return 1 if any(record.get('state')=='FAILED' for record in receipt['records']) else 0


if __name__=='__main__':
    raise SystemExit(main())
