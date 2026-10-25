"""Inspect official public review filters in an authorized Ego space; adopt no facts."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PROGRAM = """
const p=(await taskSpace(SPACE)).page('p1');
const url='https://www.cde.org.cn/main/xxgk/listpage/9f9c74c73e0f8f56a8bfbc646055026d';
if(REUSE_CURRENT){
 if(await p.evaluate(()=>location.href)!==url)throw Error('Current page is outside the expected public scope');
}else{
 await p.goto(url,{waitUntil:'domcontentloaded'});
 await p.click('text=审评任务公示',{label:'读取官方审评任务范围'});
}
await p.waitForFunction(()=>!!document.getElementById('newReportTbody')&&
 !document.body.innerText.includes('拼命加载中'),undefined,{timeout:30000});
if(SEQUENCE){
 await p.click('#splxtype + .layui-form-select .layui-select-title',{label:'展开官方审评序列'});
 await p.click('#splxtype + .layui-form-select dd[lay-value="'+SEQUENCE+'"]',{label:'选择官方审评序列'});
}
const taskControl=await p.evaluate(()=>{
 const controls=[...document.querySelectorAll('select[name="applytypecde"]')]
  .filter(n=>/^applytypecdeNewReport(?:Zy|Sw)?$/.test(n.id)&&n.parentElement.getBoundingClientRect().height>0);
 if(controls.length!==1)throw Error('Active official application filter is not unique');
 return controls[0].id;
});
if(TASK_TYPE){
 await p.click('#'+taskControl+' + .layui-form-select .layui-select-title',{label:'展开官方申请类型'});
 await p.click('#'+taskControl+' + .layui-form-select dd[lay-value="'+TASK_TYPE+'"]',{label:'选择官方申请类型'});
}
if(SEQUENCE||TASK_TYPE){
 await p.fill('#acceptid2','');
 await p.evaluate(()=>{
  window.__ciwScopeChanged=false;
  window.__ciwScopeObserver=new MutationObserver(()=>{window.__ciwScopeChanged=true;});
  window.__ciwScopeObserver.observe(document.getElementById('newReportTbody'),{childList:true,subtree:true});
 });
 await p.click('loc=role:button[name=查询]',{label:'核对所选公开审评序列'});
 await p.waitForFunction(()=>window.__ciwScopeChanged&&!document.body.innerText.includes('拼命加载中'),undefined,{timeout:30000});
 await p.evaluate(()=>window.__ciwScopeObserver.disconnect());
}
const result=await p.evaluate((taskControl)=>{
 const tbody=document.getElementById('newReportTbody');
 const table=tbody.closest('table');
 const selects=['splxtype',taskControl].map(id=>{
  const node=document.getElementById(id);
  return {id,value:node.value,options:[...node.options].map(o=>({value:o.value,text:o.text}))};
 });
 const pager=[...document.querySelectorAll('.layui-laypage')].find(e=>e.getBoundingClientRect().height>0);
 const legend=[...document.querySelectorAll('p')].find(e=>e.getBoundingClientRect().height>0&&e.innerText.includes('本专业'));
 return {url:location.href,observed_at:new Date().toISOString(),selects,section:'new_review_task',
  filters:{sequence:document.getElementById('splxtype').value,
    task_type:document.getElementById(taskControl).value,
    ui_acceptance_number:document.getElementById('acceptid2').value},
  headers:[...table.rows[0].cells].map(c=>c.innerText),
  rows:[...tbody.rows].map(r=>[...r.cells].map(c=>({text:c.innerText,
    images:[...c.querySelectorAll('img')].map(i=>i.getAttribute('src'))}))),
  legend:[...(legend?.querySelectorAll('span')||[])].map(s=>({text:s.innerText,
    images:[...s.querySelectorAll('img')].map(i=>i.getAttribute('src'))})),
  pagination:pager?{current:Number(pager.querySelector('.layui-laypage-curr em:last-child').innerText),
    page_size:Number(pager.querySelector('select').value),text:pager.innerText}:null};
},taskControl);
console.log('CIW_SCOPE:'+JSON.stringify(result));
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--space', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-current', action='store_true', help='retain loaded page after instrument failure; no fresh lookup')
    parser.add_argument('--sequence', choices=['化药', '生物', '中药'], help='observe one explicit public sequence after querying')
    parser.add_argument('--task-type', choices=['IND', 'NDA', 'ANDA', 'YZXLC', 'BCSQ', 'JKZZC', 'LCSYSQ', 'SSSQ', 'ZZC', 'FS'])
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must be new; preserve previous observations')
    args.output.mkdir(parents=True)
    program = PROGRAM.replace('SPACE', str(args.space)).replace('REUSE_CURRENT', json.dumps(args.reuse_current))
    program = program.replace('SEQUENCE', json.dumps(args.sequence)).replace('TASK_TYPE', json.dumps(args.task_type))
    program = 'try{'+program+'}catch(e){console.log("CIW_SCOPE_ERROR:"+JSON.stringify({name:e.name,message:e.message}));}'
    process = subprocess.run(['ego-browser', 'nodejs', '-e', program], check=False, capture_output=True, text=True)
    lines = [line.partition('CIW_SCOPE:')[2] for stream in (process.stdout, process.stderr)
             for line in stream.splitlines() if line.startswith('CIW_SCOPE:')]
    capture = json.loads(lines[0]) if len(lines) == 1 else None
    errors = [line.partition('CIW_SCOPE_ERROR:')[2] for stream in (process.stdout, process.stderr)
              for line in stream.splitlines() if line.startswith('CIW_SCOPE_ERROR:')]
    if capture:
        (args.output/'capture.json').write_text(json.dumps(capture, ensure_ascii=False, indent=2)+'\n')
    receipt = {'scope':'PUBLIC_UI_FILTER_OBSERVATION_ONLY', 'space':args.space,
               'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'process_exit':process.returncode, 'captured':capture is not None,
               'loaded_page_reused':args.reuse_current,
               'fresh_lookup_requested':not args.reuse_current or args.sequence is not None or args.task_type is not None,
               'sequence_query':args.sequence, 'task_type_query':args.task_type,
               'model_calls':0, 'adopted_facts':0, 'full_source_closure':'NOT_RUN',
               'error':None if capture else 'browser_observation_failed',
               'browser_errors':[json.loads(item) for item in errors]}
    (args.output/'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if process.returncode == 0 and capture is not None else 1


if __name__ == '__main__':
    raise SystemExit(main())
