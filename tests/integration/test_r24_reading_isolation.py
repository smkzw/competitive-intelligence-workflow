"""Production modal owners and shared LG-05 isolation, not aesthetic acceptance."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src/ci_workflow/renderers/portal/assets"

HARNESS = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const base=process.argv[1],mode=process.argv[2];
function definition(file,name){
 const source=fs.readFileSync(base+'/'+file,'utf8');
 const start=source.indexOf('  function '+name+'(');
 assert.ok(start>=0,'Production '+name+' missing');
 const end=source.indexOf('\n  }',start)+5;
 return source.slice(start,end);
}
function node(tag,classes=[],inert=false,role=null){
 const values=new Set(classes);
 return {tagName:tag,inert,children:[],parentElement:null,style:{filter:'contrast(.95)'},
  getAttribute(key){return key==='role'?role:null;},
  contains(n){for(let p=n;p;p=p.parentElement){if(p===this)return true;}return false;},
  classList:{contains(c){return values.has(c);},add(c){values.add(c);},
   remove(c){values.delete(c);}}};
}
const main=node('MAIN'),header=node('HEADER',['kz-reading-background-isolated'],true);
const modal=node('ASIDE',[],false,'dialog'),other=node('ASIDE',[],false,'dialog');
const script=node('SCRIPT'),body=node('BODY');
body.children=[main,header,modal,other,script];body.children.forEach(n=>n.parentElement=body);
const sandbox={document:{body},window:{}};
if(mode==='shared'||mode==='nested'){
 vm.runInNewContext(definition('portal.js','createReadingIsolation'),sandbox);
 const api=sandbox.createReadingIsolation();
 if(mode==='nested'){
  body.children=[main,header,script];main.children=[modal,other,node('SECTION')];
  main.children.forEach(n=>n.parentElement=main);
  const release=api.acquire(modal);
  assert.equal(main.classList.contains('kz-reading-background-isolated'),false);
  assert.equal(main.children[2].classList.contains('kz-reading-background-isolated'),true);
  assert.equal(modal.inert,false);assert.equal(other.inert,false);
  release();assert.equal(main.children[2].inert,false);
 }else{
  const releaseA=api.acquire(modal),releaseB=api.acquire(other);
  assert.equal(main.inert,true);assert.equal(main.classList.contains('kz-reading-background-isolated'),true);
  assert.equal(modal.inert,false);assert.equal(other.inert,false);assert.equal(script.inert,false);
  releaseA();releaseA(); // idempotent release must not steal another owner's lease
  assert.equal(main.inert,true);assert.equal(main.classList.contains('kz-reading-background-isolated'),true);
  releaseB();assert.equal(main.inert,false);assert.equal(main.classList.contains('kz-reading-background-isolated'),false);
  assert.equal(header.inert,true);assert.equal(header.classList.contains('kz-reading-background-isolated'),true);
  assert.equal(main.style.filter,'contrast(.95)');assert.equal(modal.style.filter,'contrast(.95)');
 }
}else{
 let acquisitions=0,releases=0;
 sandbox.window.__KZ_READING_ISOLATION__={acquire(target){
  assert.equal(target,modal);acquisitions++;return ()=>{releases++;};
 }};
 sandbox.productInsightDrawer=modal;sandbox.productInsightInert=null;
 sandbox.host=modal;sandbox.previousInert=null;
 vm.runInNewContext(definition(mode==='a'?'report-a.js':'evidence-drawer.js',
  mode==='a'?'setInsightBackgroundInert':'setBackgroundInert'),sandbox);
 const call=mode==='a'?sandbox.setInsightBackgroundInert:sandbox.setBackgroundInert;
 call(true);call(true);assert.equal(acquisitions,1,'one open owns one lease');
 call(false);call(false);assert.equal(releases,1,'one close releases once');
 call(true);call(false);assert.equal(acquisitions,2);assert.equal(releases,2);
}
"""


@pytest.mark.parametrize("mode", ["shared", "nested", "a", "evidence"])
def test_production_reading_isolation_and_owner_lifecycle(mode: str) -> None:
    result = subprocess.run(
        ["node", "-e", HARNESS, str(ASSETS), mode],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
