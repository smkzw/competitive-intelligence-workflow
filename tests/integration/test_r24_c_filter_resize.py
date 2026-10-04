"""Current C query must govern core-design-matrix resize redraws, not pixels."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / "src/ci_workflow/renderers/portal/assets/report-c.js"
MIRROR = ROOT / "assets/portal/report-c.js"

PROBE = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const caseName=process.argv[2];
const rows=Array.from({length:20},(_,i)=>({
  row_id:'r'+i,
  trial_display_id: i<10 ? 'NCT00000001' : 'NCT00000002',
  product_zh: i%2 ? 'P1' : 'P2',
  element_zh: '设计要素'+(i%5),
  value: 'V'+i,
  disclosure_state: 'reported_value',
  field_family_zh: '设计',
  status: '已公开'
}));
const dims={};
rows.forEach((row,i)=>{
  dims[row.row_id]={
    product: row.product_zh,
    trial: row.trial_display_id,
    element: i<2 ? 'keep' : 'drop'
  };
});
const optionRowIds=[];
const notes=[];
let clears=0, sets=0, resizes=0, disposed=0;
const chartHost={
  clientWidth:900,
  style:{},
  innerHTML:'',
  appendChild(node){notes.push(node && node.textContent || ''); return node;},
  removeChild(){}
};
const fakeChart={
  clear(){clears++;},
  setOption(option){
    sets++;
    const ids=[];
    (option.series||[]).forEach(series=>{
      (series.data||[]).forEach(point=>{
        (point.rowIds||[point.rowId]).forEach(id=>{ if(id!=null) ids.push(String(id)); });
      });
    });
    optionRowIds.splice(0, optionRowIds.length, ...ids);
  },
  resize(){resizes++;},
  dispose(){disposed++;},
  on(){}
};
const filterButtons=[
  ['product','P1'],['product','P2'],['product','missing'],
  ['trial','NCT00000001'],['trial','NCT00000002'],
  ['element','keep'],['element','drop']
].map(([dimension,value])=>({
  getAttribute(name){
    if(name==='data-filter-dimension') return dimension;
    if(name==='data-filter-value') return value;
    return null;
  }
}));
const sandbox={
  URL, URLSearchParams,
  window:{
    location:{search:'', hash:'', href:'https://example.test/c'},
    history:{replaceState(){}},
    setTimeout(){},
    echarts:{init(){return fakeChart;}},
    __C_PAGE_ID__:'overview',
    __C_FILTER_DIMENSIONS__:['product','trial','element'],
    __C_ROW_DIMENSIONS__:dims,
    __CHART_GROUPS__:[{rows}],
    __PRESENTATION_PLAN__:null
  },
  document:{
    readyState:'loading',
    addEventListener(){},
    createElement(tag){return {tagName:tag, className:'', textContent:'',
      remove(){notes.push('removed');}};},
    querySelector(){return null;},
    querySelectorAll(selector){
      if(selector==='button[data-filter-dimension]') return filterButtons;
      if(selector==='button[data-filter-dimension][data-filter-value]') return filterButtons;
      const dim=/#?button\[data-filter-dimension="([^"]+)"\]\[data-filter-value\]/.exec(selector)
        || /^button\[data-filter-dimension="([^"]+)"\]\[data-filter-value\]$/.exec(selector);
      if(dim) return filterButtons.filter(btn=>btn.getAttribute('data-filter-dimension')===dim[1]);
      return [];
    },
    getElementById(){return null;}
  }
};
const original=fs.readFileSync(process.argv[1],'utf8');
const source=original.replace(
  'window.__CHART_SYNC__ = {',
  'window.__CHART_SYNC__ = {testUpdate:updateChartFromState,testResize:resizeCChart,'+
  'testInit:function(pool,chart,host,kind){cChart=chart;chartContainerWidth=host.clientWidth;'+
  'chartState={rows:pool.slice(),kind:kind||"core-design-matrix",chart:host,emptyNote:null};},'
);
assert.notEqual(source, original, 'VM seam must expose resize/update without permanent hooks');
vm.runInNewContext(source, sandbox);
const api=sandbox.window.__CHART_SYNC__;
api.syncWithFilter=function(){};
function uniqueSorted(ids){return Array.from(new Set(ids)).sort();}
function currentIds(){return uniqueSorted(optionRowIds);}
function writeQuery(state){
  const params=new URLSearchParams();
  Object.keys(state).sort().forEach(key=>{
    (state[key]||[]).forEach(value=>params.append(key, value));
  });
  const search=params.toString();
  sandbox.window.location.search=search ? '?'+search : '';
  sandbox.window.location.href='https://example.test/c'+sandbox.window.location.search;
}
function applyQuery(state){
  writeQuery(state);
  api.testUpdate(state);
}

api.testInit(rows, fakeChart, chartHost, 'core-design-matrix');

if(caseName==='filter-20-to-2-resize'){
  applyQuery({product:[], trial:[], element:['keep']});
  assert.deepEqual(currentIds(), ['r0','r1'], 'filter must keep only two observations');
  const afterFilterSets=sets, afterFilterClears=clears;
  chartHost.clientWidth=1200;
  api.testResize();
  assert.equal(resizes, 1, 'resize must still call echarts.resize');
  assert.ok(sets>afterFilterSets, 'width change must redraw filtered matrix');
  assert.equal(clears, afterFilterClears, 'non-empty filter must not clear chart');
  assert.deepEqual(currentIds(), ['r0','r1'], 'resize must not restore the excluded 18');
  assert.deepEqual(rows.map(r=>r.value), Array.from({length:20},(_,i)=>'V'+i),
    'observation values must remain untouched');
}else if(caseName==='filter-zero-resize'){
  applyQuery({product:['missing'], trial:[], element:[]});
  assert.equal(clears, 1, 'empty query must clear former series');
  assert.ok(notes.some(x=>String(x).includes('筛选') && String(x).includes('无')));
  const setsAfterEmpty=sets;
  chartHost.clientWidth=1280;
  api.testResize();
  assert.equal(resizes, 1);
  assert.equal(sets, setsAfterEmpty, 'resize must not repaint excluded full pool');
  assert.ok(notes.some(x=>String(x).includes('筛选') && String(x).includes('无')));
}else if(caseName==='clear-filter-resize-restores-all'){
  applyQuery({product:[], trial:[], element:['keep']});
  assert.deepEqual(currentIds(), ['r0','r1']);
  applyQuery({product:[], trial:[], element:[]});
  assert.equal(currentIds().length, 20, 'clearing filter restores full original pool');
  chartHost.clientWidth=1440;
  api.testResize();
  assert.equal(currentIds().length, 20, 'resize after clear keeps the full pool');
  assert.deepEqual(currentIds(), rows.map(r=>r.row_id).sort());
}else if(caseName==='trial-dimension-remains'){
  applyQuery({product:[], trial:['NCT00000002'], element:[]});
  const expected=rows.filter(r=>r.trial_display_id==='NCT00000002').map(r=>r.row_id).sort();
  assert.deepEqual(currentIds(), expected, 'trial filter must apply before resize');
  chartHost.clientWidth=1600;
  api.testResize();
  assert.deepEqual(currentIds(), expected, 'selected trial remains after resize');
  applyQuery({product:['P1'], trial:['NCT00000002'], element:[]});
  const expected2=rows.filter(r=>r.trial_display_id==='NCT00000002' && r.product_zh==='P1')
    .map(r=>r.row_id).sort();
  chartHost.clientWidth=1920;
  api.testResize();
  assert.deepEqual(currentIds(), expected2, 'combined trial/product query remains');
}else{
  throw new Error('unknown case '+caseName);
}
assert.equal(disposed, 0, 'resize path must not dispose the live chart');
console.log(JSON.stringify({
  case: caseName,
  sets, clears, resizes, disposed,
  ids: currentIds()
}));
"""


def _run_case(case: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "-e", PROBE, str(ASSET), case],
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    "case",
    (
        "filter-20-to-2-resize",
        "filter-zero-resize",
        "clear-filter-resize-restores-all",
        "trial-dimension-remains",
    ),
)
def test_production_c_resize_uses_current_query_filter(case: str) -> None:
    assert ASSET.read_bytes() == MIRROR.read_bytes(), "asset module must mirror root asset"
    result = _run_case(case)
    assert result.returncode == 0, result.stderr or result.stdout
