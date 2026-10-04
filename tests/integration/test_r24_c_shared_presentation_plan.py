"""Normal C dependency closure and production-call geometry, not visual acceptance."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'src/ci_workflow/renderers/portal/assets'


def node_probe(script: str) -> None:
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node production-call geometry unavailable; not browser PASS')
    result = subprocess.run([node, '-e', script, str(ASSETS)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_normal_c_pages_copy_and_load_shared_planner_before_c_controller(tmp_path: Path) -> None:
    data = ReportCPortalData.model_validate_json(
        (ROOT / 'fixtures/positive/c-atopic-dermatitis/inputs/report-data.json').read_bytes())
    render_report_c_site(data, tmp_path)
    assert (tmp_path / 'assets/charts.js').read_bytes() == (ASSETS / 'charts.js').read_bytes()
    for path in tmp_path.rglob('*.html'):
        html = path.read_text()
        assert html.index('/charts.js') < html.index('/report-c.js')
        assert html.index('window.__C_PAGE_ID__') < html.index('/charts.js')


def test_shared_design_plan_uses_actual_axes_not_full_source_text() -> None:
    node_probe(r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context={window:{__C_PAGE_ID__:'visit-duration-followup'},document:{
 readyState:'loading',addEventListener(){
  throw Error('C must not register a second chart controller');}}};
vm.runInNewContext(fs.readFileSync(process.argv[1]+'/charts.js','utf8'),context);
const plan=context.window.__PRESENTATION_PLAN__;
assert.equal(typeof plan,'function','Shared pure planner must be available to C');
function group(n){return {rows:Array.from({length:n},(_,i)=>({
 row_id:'f'+i,source_text:'原文'.repeat(5000)})),
 design_layout:{kind:'visit-timeline',x_labels:['基线','第48周'],
 y_labels:Array.from({length:n},(_,i)=>'NCT'+String(i).padStart(8,'0')),glyph_count:n}};}
const dense=plan(group(20)),sparse=plan(group(2)),empty=plan(group(0));
assert.ok(dense.target_height>sparse.target_height);
assert.ok(sparse.target_height<300 && sparse.target_height>=120);
assert.equal(dense.observation_ids.length,20);assert.equal(dense.glyph_count,20);
assert.equal(empty.target_height,0);assert.equal(empty.glyph_count,0);
const short=group(2),before=JSON.stringify(short),p=plan(short);
assert.equal(JSON.stringify(short),before,'Planner must not rewrite scientific rows');
short.rows.forEach(r=>r.source_text='短原文');assert.equal(plan(short).target_height,p.target_height);
short.design_layout.y_labels=['很长的实际纵轴标签'.repeat(4),'另一个标签'];
assert.ok(plan(short).target_height>p.target_height);
""")


def test_production_c_filter_recomputes_timeline_height_and_retains_controller() -> None:
    node_probe(r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let visible=20,disposed=0,initialized=0,resized=0;
class Element{constructor(){this.style={};this.attrs={};this.children=[];this.clientWidth=1200;
 this.classList={add(){},remove(){}};}setAttribute(k,v){this.attrs[k]=v;}
 appendChild(c){this.children.push(c);return c;}set innerHTML(v){this.children=[];}}
const host=new Element(),rows=Array.from({length:20},(_,i)=>({row_id:'f'+i,
 trial_display_id:'NCT'+String(i).padStart(8,'0'),element_zh:'随访时间',time:'第48周',
 source_text:'原文'.repeat(1000),disclosure_state:'reported_value'}));
const table=rows.map(r=>({style:{},getAttribute(){return r.row_id;}}));
const win={__C_PAGE_ID__:'visit-duration-followup',__CHART_GROUPS__:[{rows}],
 location:{search:'',hash:''},setTimeout(){},echarts:{init(){initialized++;
 return {dispose(){disposed++;},setOption(){},on(){},resize(){resized++;}};}}};
const doc={readyState:'loading',addEventListener(){},createElement(){return new Element();},
 getElementById(id){return id==='kz-c-chart-visuals'?host:null;},
 querySelectorAll(selector){return selector.includes('kz-chart-table__row')
 ?table.map((e,i)=>{e.style.display=i<visible?'':'none';return e;}):[];}};
const ctx={window:win,document:doc,URLSearchParams,URL};
vm.runInNewContext(fs.readFileSync(process.argv[1]+'/charts.js','utf8'),ctx);
const source=fs.readFileSync(process.argv[1]+'/report-c.js','utf8');
const testSource=source.replace('window.__CHART_SYNC__ = {',
 'window.__CHART_SYNC__ = {testRender:renderCChart,testResize:resizeCChart,');
assert.notEqual(testSource,source);vm.runInNewContext(testSource,ctx);
const sync=win.__CHART_SYNC__;
sync.testRender();const dense=parseFloat(host.children[1].style.height);
visible=2;sync.testRender();const sparse=parseFloat(host.children[1].style.height);
assert.ok(sparse<dense && sparse<300,'20→2 must shrink the actual chart');
assert.deepEqual(Array.from(win.__C_VISIBLE_CHART_ROW_IDS__),['f0','f1']);
assert.equal(typeof sync.presentationPlan,'function','C controller retains shared planner');
sync.testResize();assert.equal(resized,1);
visible=0;sync.testRender();assert.equal(initialized,2);assert.equal(disposed,2);
assert.equal(host.children[1].style.height,'auto');
assert.equal(host.children[1].attrs.role,'status');
assert.deepEqual(Array.from(win.__C_VISIBLE_CHART_ROW_IDS__),[]);
""")


def test_empty_c_canvas_has_no_fixed_minimum_blank_plot() -> None:
    css = (ASSETS / 'report-c.css').read_text()
    start = css.index('.kz-c-chart-canvas {')
    rule = css[start:css.index('}', start)]
    assert 'min-height: 0' in rule
    assert 'min-height: 300px' not in rule
