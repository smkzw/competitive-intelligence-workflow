"""A observation source navigation production functions; browser checked separately."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_chart_redraw_preserves_same_fact_focus_but_never_steals_modal_focus() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function renderCharts(');
const end=source.indexOf('\n  function ',start+5);
let restores=0;
const trigger={getAttribute(key){return key==='data-row-id'?'fact-1':null;},
 closest(){return null;},isConnected:true};
const host={getAttribute(){return 'safety';}};
const document={activeElement:trigger,querySelectorAll(){return [host];}};
const panel={hidden:true};
const sandbox={document,productInsightDrawer:panel,evidencePanelTrigger:null,
 renderSafety(){trigger.isConnected=false;document.activeElement={};},
 restoreInsightFocus(node){assert.equal(node,trigger);restores++;},
 renderProductInsight(){},productInsightId:null};
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.renderCharts();assert.equal(restores,1,'redraw detached the focused fact');
document.activeElement=trigger;trigger.isConnected=true;panel.hidden=false;
sandbox.renderCharts();assert.equal(restores,1,'redraw must not steal modal focus');
"""
    result = subprocess.run(
        ["node", "-e", probe, str(ROOT / "src/ci_workflow/renderers/portal/assets/report-a.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_clicked_observation_opens_its_evidence_not_a_default_efficacy_tab() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
function definition(name){
 const start=source.indexOf('  function '+name+'(');
 assert.ok(start>=0,name);
 const end=source.indexOf('\n  function ',start+5);
 return source.slice(start,end);
}
let chosen;
const row={row_id:'safety-zero',source_text:'0'};
const context={selectedEfficacy:null,eventRow:row,trial:{id:'nct-1'}};
const node={setAttribute(){},textContent:''};
const sandbox={document:{getElementById(){return node;}},
 productById(){return {id:'p1',name:'产品',phase:'III期'};},
 buildProductInsightContext(){return context;},productInsightDrawer:node,
 renderInsightSummary(){},renderInsightEfficacy(){},renderInsightSafety(){},
 renderInsightProfile(){},renderInsightEvidence(){},setProductInsightTab(tab){chosen=tab;}};
vm.runInNewContext(definition('renderProductInsight'),sandbox);
const trigger={getAttribute(key){return key==='data-row-id'?'safety-zero':null;}};
assert.equal(sandbox.renderProductInsight('p1',trigger),true);
assert.equal(chosen,'evidence','exact safety observation must expose its source on one click');
context.eventRow=null;context.selectedEfficacy={row_id:'eff-other-dose'};
sandbox.renderProductInsight('p1',trigger);
assert.equal(chosen,'evidence','exact efficacy dose must expose its own source');
context.selectedEfficacy=null;context.eventRow=row;
sandbox.renderProductInsight('p1',null);
assert.equal(chosen,'efficacy','generic product navigation keeps the product workflow');
"""
    result = subprocess.run(
        ["node", "-e", probe,
         str(ROOT / "src/ci_workflow/renderers/portal/assets/report-a.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_overlay_background_restores_preexisting_inert_state() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function setInsightBackgroundInert(');
assert.ok(start>=0,'actual overlay owner must suppress background interactions');
const end=source.indexOf('\n  function ',start+5);
const background={tagName:'MAIN',inert:false,contains(){return false;}};
const preexisting={tagName:'HEADER',inert:true,contains(){return false;}};
const overlay={tagName:'ASIDE',inert:false,contains(n){return n===this;}};
const sandbox={productInsightDrawer:overlay,productInsightInert:null,
 document:{body:{children:[background,preexisting,overlay]}},window:{}};
for(const node of sandbox.document.body.children){
 const classes=new Set();node.parentElement=sandbox.document.body;
 node.getAttribute=()=>null;
 node.classList={contains(c){return classes.has(c);},add(c){classes.add(c);},
  remove(c){classes.delete(c);}};
}
const portal=fs.readFileSync(process.argv[2],'utf8');
const sharedStart=portal.indexOf('  function createReadingIsolation(');
// The shared definition ends before the assignment and search initialization.
const sharedEnd=portal.indexOf('\n  window.__KZ_READING_ISOLATION__',sharedStart);
const sharedDefinition=portal.slice(sharedStart,sharedEnd);
vm.runInNewContext(sharedDefinition,sandbox);
sandbox.window.__KZ_READING_ISOLATION__=sandbox.createReadingIsolation();
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.setInsightBackgroundInert(true);
assert.equal(background.inert,true);assert.equal(preexisting.inert,true);
assert.equal(overlay.inert,false);
sandbox.setInsightBackgroundInert(true); // repeated open must not overwrite saved state
sandbox.setInsightBackgroundInert(false);
assert.equal(background.inert,false);assert.equal(preexisting.inert,true);
"""
    result = subprocess.run(
        ["node", "-e", probe,
         str(ROOT / "src/ci_workflow/renderers/portal/assets/report-a.js"),
         str(ROOT / "src/ci_workflow/renderers/portal/assets/portal.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_removed_trigger_restores_same_fact_or_stable_chart_anchor() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function restoreInsightFocus(');
assert.ok(start>=0,'removed glyph needs same-fact or stable list focus');
const end=source.indexOf('\n  function ',start+5);
let focused='';
const trigger={isConnected:false,getAttribute(key){return key==='data-row-id'?'f0':null;}};
function node(id,visible){return {isConnected:true,hidden:!visible,
 getAttribute(key){return key==='data-row-id'?id:null;},
 getClientRects(){return visible?[{}]:[];},closest(){return null;},
 focus(){focused=id;}};}
let candidates=[node('f0',false),node('f1',true),node('f0',true)];
const anchor=node('chart-anchor',true);
anchor.setAttribute=()=>{};
const sandbox={document:{querySelectorAll(){return candidates;},querySelector(){return anchor;}}};
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.restoreInsightFocus(trigger);assert.equal(focused,'f0');
candidates=[node('f0',false),node('f1',true)];
sandbox.restoreInsightFocus(trigger);assert.equal(focused,'chart-anchor');
"""
    result = subprocess.run(
        ["node", "-e", probe,
         str(ROOT / "src/ci_workflow/renderers/portal/assets/report-a.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_table_source_panel_uses_the_same_modal_lifecycle() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
function definition(name){
 const start=source.indexOf('  function '+name+'(');
 assert.ok(start>=0,name+' must have an actual shared-lifecycle entry');
 const end=source.indexOf('\n  function ',start+5);
 return source.slice(start,end);
}
let focused='',inert=false,rendered;
const trigger={getAttribute(key){return {'data-open-evidence':'原文依据',
 'data-evidence-row-id':'f-zero','data-evidence-collection':'safety'}[key]||null;}};
const close={focus(){focused='close';}};
const content={};
const panel={hidden:true,querySelector(selector){
 return selector==='[data-evidence-content]'?content:close;}};
const sandbox={document:{getElementById(){return panel;},
 body:{classList:{add(){},remove(){}}}},evidencePanelTrigger:null,
 closeProductInsight(){},setInsightBackgroundInert(open,target){
  assert.equal(target,panel);inert=open;
 },renderEvidencePanel(...args){rendered=args;},restoreInsightFocus(t){assert.equal(t,trigger);focused='f-zero';}};
vm.runInNewContext(definition('openEvidencePanel')+'\n'+definition('closeEvidencePanel'),sandbox);
sandbox.openEvidencePanel(trigger);
assert.equal(panel.hidden,false);assert.equal(inert,true);assert.equal(focused,'close');
assert.equal(rendered[3].rowId,'f-zero');assert.equal(rendered[3].collection,'safety');
sandbox.closeEvidencePanel();
assert.equal(panel.hidden,true);assert.equal(inert,false);assert.equal(focused,'f-zero');
"""
    result = subprocess.run(
        ["node", "-e", probe, str(ROOT / "src/ci_workflow/renderers/portal/assets/report-a.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_modal_tab_order_includes_edit_fields_and_source_disclosures() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function modalFocusableNodes(');
assert.ok(start>=0,'both source entry paths need full focusable fields');
const end=source.indexOf('\n  function ',start+5);
let selector;
function node(hidden){return {hidden,closest(){return null;},getClientRects(){return [{}];}};}
const visible=node(false),hidden=node(true);
const panel={querySelectorAll(value){selector=value;return [visible,hidden];}};
const sandbox={};vm.runInNewContext(source.slice(start,end),sandbox);
assert.equal(sandbox.modalFocusableNodes(panel).length,1);
for(const kind of ['input','select','textarea','summary']) assert.ok(selector.includes(kind),kind);
"""
    result = subprocess.run(
        ["node", "-e", probe, str(ROOT / "src/ci_workflow/renderers/portal/assets/report-a.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_personal_configuration_joins_existing_workspace_without_a_second_toolbar() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function mountPersonalViewControls(');
assert.ok(start>=0,'configuration controls should reuse the existing A workspace row');
const end=source.indexOf('\n  function ',start+5);
// Function ends before the next top-level statement in this production IIFE.
let braces=0,bodyStart=source.indexOf('{',start),bodyEnd=bodyStart;
for(let i=bodyStart;i<source.length;i++){
 if(source[i]==='{')braces++;if(source[i]==='}')braces--;
 if(!braces){bodyEnd=i+1;break;}
}
const sandbox={};vm.runInNewContext(source.slice(start,bodyEnd),sandbox);
let joined=0,inserted=0;const bar={};
const workspace={closest(){return null;},appendChild(node){assert.equal(node,bar);joined++;}};
const main={firstChild:{},querySelector(){return workspace;},insertBefore(){inserted++;}};
sandbox.mountPersonalViewControls(main,bar);assert.equal(joined,1);assert.equal(inserted,0);
main.querySelector=()=>null;
sandbox.mountPersonalViewControls(main,bar);assert.equal(inserted,1);
// B/C hide their old filter panel in comparison mode. Reuse the existing
// collapsed personal shell outside that panel, never mount inaccessible controls.
for(const report of ['B','C']){
 const shell={classList:{add(name){assert.equal(name,'kz-personal-view-shell');}}};
 const nested={closest(selector){return selector.includes('filter-panel')?{}:shell;},
  appendChild(node){assert.equal(node,bar);joined++;}};
 main.querySelector=()=>nested;let relocated=false;
 main.insertBefore=(node)=>{assert.equal(node,shell);relocated=true;};
 sandbox.mountPersonalViewControls(main,bar);
 assert.ok(relocated,report+' config remains inside hidden panel');
}
"""
    result = subprocess.run(
        ["node", "-e", probe, str(ROOT / "src/ci_workflow/renderers/portal/assets/portal.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
