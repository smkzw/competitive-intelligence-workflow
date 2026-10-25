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
const messages=[],captures=[],jumps=[],clicks=[];let current=1,jump=1,sequence='化药',taskType='IND';
const page={goto:async()=>{current=1;sequence='化药';taskType='IND';},waitForSelector:async()=>{},waitForFunction:async()=>{},
  selectOption:async()=>{current=1;},fill:async(s,v)=>{if(s.includes('laypage-skip'))jump=Number(v);},
  click:async(s)=>{
    clicks.push(s);
    if(input.strictAcceptance && s==="loc=role:button[name='查询']"){
      const e=new Error('Multiple CDE section buttons');e.name='ElementResolutionError';throw e;
    }
    if(s.includes('laypage-next'))current++;
    else if(s.includes('laypage-btn')){current=jump;jumps.push(jump);}
    else if(s.includes('layui-form-select')){
      const value=s.match(/dd\[lay-value="([^"]+)"\]/)?.[1];
      if(s.startsWith('#splxtype')){if(value){sequence=value;taskType=sequence==='生物'?'LCSYSQ':'IND';}}
      else{
        const active=sequence==='生物'?'#applytypecdeNewReportSw ':'#applytypecdeNewReport ';
        if(!s.startsWith(active))throw Error('Attempted hidden application control');
        if(value)taskType=value;
      }
    }
    else if(!s.includes('查询')&&!s.includes('审评任务公示')&&!s.includes('getAcceptList'))throw Error('Unexpected click '+s);
  },evaluate:async(fn,arg)=>{
    const code=fn.toString();
    if(code.includes('MutationObserver')||code.includes('Observer.disconnect')||code.includes('Observer?.disconnect'))return;
    if(code.includes('const tbody=')||code.includes('const tbody =')){
      const captured=structuredClone(input.pages[current-1]);
      if(captured.section==='new_review_task'&&
        (captured.filters.sequence!==sequence||captured.filters.task_type!==taskType))throw Error('Wrong active scope');
      captures.push(current);return captured;
    }
    if(code.includes("getElementById('splxtype')"))return sequence;
    if(code.includes('getElementById(id).value'))return '';
    if(code.includes("querySelectorAll('.layui-laypage')")||code.includes('querySelectorAll(".layui-laypage")'))return 'pager-'+current;
    throw Error('Unexpected evaluate callback');
  }};
const taskSpace=async()=>({page:()=>page});
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
new AsyncFunction('config','taskSpace','console',fs.readFileSync(process.argv[1],'utf8'))(
 input.config,taskSpace,{log:s=>messages.push(s)}).then(()=>console.log(JSON.stringify({messages,captures,jumps,clicks}))).catch(e=>{throw e;});
'''


def pages(section):
    result=[]
    for number,span in enumerate((range(1,51),range(51,101),range(101,102)),1):
        if section.startswith('new_review_task'):
            p=page([row(i) for i in span],number,101)
            p['pagination']['page_size']=50
            if section=='new_review_task_biological':
                p['filters']={'sequence':'生物','task_type':'LCSYSQ','ui_acceptance_number':''}
        else:
            p=capture(total=101,rows=[[str(i),f'CXSL2600{i:03}','药','化药','新药','','企业','2026-01-01'] for i in span])
            p['pagination']['current']=number
        result.append(p)
    return result


def run_driver(section,captures,resume,*,strict_acceptance=False):
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable: real collector protocol not tested')
    source=Path(__file__).parents[1]/'src/ciw2/sources'/('cde_review_browser.mjs' if section.startswith('new_review_task') else 'cde_browser.mjs')
    config={'space':63,'filters':captures[0]['filters'],'resume':resume}
    result=subprocess.run([node,'-e',DRIVER,str(source)],input=json.dumps({
        'pages':captures,'config':config,'strictAcceptance':strict_acceptance}),
                          capture_output=True,text=True,check=False,timeout=10)
    assert result.returncode==0,result.stderr
    out=json.loads(result.stdout)
    raw,end=_read_output('\n'.join(out['messages']))
    return out,raw,end


def test_acceptance_query_does_not_resolve_hidden_section_buttons():
    # Actual CDE has 20+ named query buttons, only one acceptance action.
    _,captured,end=run_driver('acceptance',pages('acceptance'),None,strict_acceptance=True)
    assert end['status']=='ok',end
    assert sum(len(p['rows'])for p in captured)==101


@pytest.mark.parametrize('section',['acceptance','new_review_task','new_review_task_biological'])
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
    if section=='new_review_task_biological':
        assert '#applytypecdeNewReportSw + .layui-form-select dd[lay-value="LCSYSQ"]' in out['clicks']


def test_actual_acceptance_driver_keeps_explicit_empty_page_zero():
    empty=capture(total=0,rows=[])
    empty['pagination']={'current':0,'page_size':None,'total_records':0,'text':'暂无内容'}
    _,captured,end=run_driver('acceptance',[empty],None)
    assert end['status']=='ok' and len(captured)==1
    assert end['new_pages_checked']==[0] and end['reused_pages']==[]
