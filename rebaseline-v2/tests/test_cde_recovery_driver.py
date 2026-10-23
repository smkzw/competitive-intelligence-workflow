"""Run the installed collector's actual control flow; DOM pixels use Ego."""
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from test_cde_browser import capture
from test_cde_review_capture import page, row

from ciw2.sources.cde_browser import page_anchor
from ciw2.sources.china_browser import _read_output

DRIVER = r'''
const fs=require('fs');const input=JSON.parse(fs.readFileSync(0,'utf8'));
const messages=[],captures=[],jumps=[];let current=1,jump=1;
const page={goto:async()=>{current=1;},waitForSelector:async()=>{},waitForFunction:async()=>{},
  selectOption:async()=>{current=1;},fill:async(s,v)=>{if(s.includes('laypage-skip'))jump=Number(v);},
  click:async(s)=>{
    if(s.includes('laypage-next'))current++;
    else if(s.includes('laypage-btn')){current=jump;jumps.push(jump);}
    else if(!s.includes('查询')&&!s.includes('审评任务公示'))throw Error('Unexpected click '+s);
  },evaluate:async(fn,arg)=>{
    const code=fn.toString();
    if(code.includes('MutationObserver')||code.includes('Observer.disconnect')||code.includes('Observer?.disconnect'))return;
    if(code.includes('const tbody=')||code.includes('const tbody =')){captures.push(current);return structuredClone(input.pages[current-1]);}
    if(code.includes("getElementById('splxtype')"))return ['化药','IND'];
    if(code.includes('getElementById(id).value'))return '';
    if(code.includes("querySelectorAll('.layui-laypage')")||code.includes('querySelectorAll(".layui-laypage")'))return 'pager-'+current;
    throw Error('Unexpected evaluate callback');
  }};
const taskSpace=async()=>({page:()=>page});
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
new AsyncFunction('config','taskSpace','console',fs.readFileSync(process.argv[1],'utf8'))(
 input.config,taskSpace,{log:s=>messages.push(s)}).then(()=>console.log(JSON.stringify({messages,captures,jumps}))).catch(e=>{throw e;});
'''


def pages(section):
    result=[]
    for number,span in enumerate((range(1,51),range(51,101),range(101,102)),1):
        if section=='new_review_task':
            p=page([row(i) for i in span],number,101)
            p['pagination']['page_size']=50
        else:
            p=capture(total=101,rows=[[str(i),f'CXSL2600{i:03}','药','化药','新药','','企业','2026-01-01'] for i in span])
            p['pagination']['current']=number
        result.append(p)
    return result


def run_driver(section,captures,resume):
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable: real collector protocol not tested')
    source=Path(__file__).parents[1]/'src/ciw2/sources'/('cde_review_browser.mjs' if section=='new_review_task' else 'cde_browser.mjs')
    config={'space':63,'filters':captures[0]['filters'],'resume':resume}
    result=subprocess.run([node,'-e',DRIVER,str(source)],input=json.dumps({'pages':captures,'config':config}),
                          capture_output=True,text=True,check=False,timeout=10)
    assert result.returncode==0,result.stderr
    out=json.loads(result.stdout)
    raw,end=_read_output('\n'.join(out['messages']))
    return out,raw,end


@pytest.mark.parametrize('section',['acceptance','new_review_task'])
@pytest.mark.parametrize('changed',[False,True])
def test_actual_driver_jumps_missing_pages_or_discards_changed_anchor(section,changed):
    original=pages(section)
    first=original[0]
    resume={'pages_read':[1,2],'total_records':101,'page_size':50,'first_page_sha256':page_anchor(first)}
    fresh=deepcopy(original)
    if changed:
        if section=='acceptance':fresh[0]['rows'][0][2]='改'
        else:fresh[0]['rows'][0][2]['text']='改'
    out,captured,end=run_driver(section,fresh,resume)
    assert end['status']=='ok'
    assert out['captures']==([1,2,3] if changed else [1,3])
    assert out['jumps']==([] if changed else [3])
    assert end['resume_used'] is not changed
    assert end['new_pages_checked']==out['captures']
    assert end['reused_pages']==([] if changed else [2])
    assert [p['pagination']['current'] for p in captured]==out['captures']


def test_actual_acceptance_driver_keeps_explicit_empty_page_zero():
    empty=capture(total=0,rows=[])
    empty['pagination']={'current':0,'page_size':None,'total_records':0,'text':'暂无内容'}
    _,captured,end=run_driver('acceptance',[empty],None)
    assert end['status']=='ok' and len(captured)==1
    assert end['new_pages_checked']==[0] and end['reused_pages']==[]
