"""Shared site packaging/geometry contract; actual appearance needs Ego evidence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.renderers.portal.report_c import ReportCPortalData, render_report_c_site

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("kind", ["a", "b", "c"])
def test_ordinary_report_entry_packages_shared_kangzhe_scene(
    tmp_path: Path,
    kind: str,
) -> None:
    if kind == "c":
        payload = json.loads(
            (ROOT / "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json").read_text()
        )
        render_report_c_site(ReportCPortalData.model_validate(payload), tmp_path)
    else:
        payload = json.loads(
            (ROOT / "fixtures/synthetic/a-complete/inputs/report-data.json").read_text()
        )
        if kind == "a":
            render_report_a_site(ReportAPortalData.model_validate(payload), tmp_path)
        else:
            render_report_b_site(ReportBPortalData.model_validate(payload), tmp_path)
    for page in tmp_path.rglob("*.html"):
        text = page.read_text()
        assert 'data-kz-design="6.0"' in text, page
        assert "kangzhe-site.css" in text and "kangzhe-site.js" in text, page
        assert "kz-motion.js" in text, page
    for name in ("kangzhe-site.css", "kangzhe-site.js", "kz-motion.js"):
        assert (tmp_path / "assets" / name).read_bytes() == (
            ROOT / "src/ci_workflow/renderers/portal/assets" / name
        ).read_bytes()


def test_kangzhe_site_uses_one_source_of_geometry_and_no_network_runtime() -> None:
    assets = ROOT / "src/ci_workflow/renderers/portal/assets"
    css = (assets / "kangzhe-site.css").read_text()
    js = (assets / "kangzhe-site.js").read_text()
    assert "--portal-gutter" in css and "--portal-card-padding" in css
    assert "!important" not in css
    assert "global_procedural_optical_field" in js
    assert "KZMotion.Film" in js and "dispose" in js and "pageshow" in js
    for forbidden in ("fetch(", "XMLHttpRequest", "https://", "innerHTML"):
        assert forbidden not in js


def test_production_presentation_uses_complexity_not_fixed_half_or_full_rows() -> None:
    source = ROOT / "src/ci_workflow/renderers/portal/assets/charts.js"
    probe = r"""
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const sandbox = {window: {}, document: {readyState: 'loading', addEventListener() {}}};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const plan = sandbox.window.__CHART_SYNC__.presentationPlan;
function group(count, label='短标签', type='bar') {
  return {chart_type:type, rows:Array.from({length:count}, (_,i)=>({
    row_id:'f'+i, value:i+1, numeric_value:i+1, renderable:true, _chart_type:type,
    display_label_zh:label, product_zh:'产品', trial_id:'nct12345678', category:'观察'
  }))};
}
assert.equal(plan(group(1)).grid_span, 4);
const registry = group(1);
registry.rows[0].trial_zh = '完整登记长标题'.repeat(30);
assert.equal(plan(registry).grid_span, 4); // the visible identifier, not an unused title
assert.equal(plan(group(1,'非常长的临床定义与观察时间以及分析人群'.repeat(4))).grid_span, 6);
assert.equal(plan(group(2)).grid_span, 6);
assert.equal(plan(group(5)).grid_span, 6);
assert.equal(plan(group(8)).grid_span, 8);
assert.equal(plan(group(20)).grid_span, 12);
assert.ok(plan(group(2)).target_height < 220);
assert.ok(plan(group(5)).target_height < 300);
assert.equal(plan(group(20)).observation_ids.length, 20);
assert.equal(plan(group(20)).plotted_ids.length, 20);
"""
    result = subprocess.run(
        ["node", "-e", probe, str(source)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_rich_evidence_uses_wide_content_sized_modal_and_inert_background() -> None:
    assets = ROOT / "src/ci_workflow/renderers/portal/assets"
    css = (assets / "evidence-drawer.css").read_text()
    js = (assets / "evidence-drawer.js").read_text()
    assert "width: 82vw" in css
    assert "max-height: 94vh" in css
    assert "min(560px, 42vw)" not in css
    assert "min-height: 100%" not in css
    assert "setBackgroundInert(true)" in js and "setBackgroundInert(false)" in js
    assert "previousInert" in js
    # Shared source isolation leases the actual host, not the inner panel.
    # Reference-counted restoration is exercised by test_r24_reading_isolation.
    assert "__KZ_READING_ISOLATION__.acquire(host)" in js


def test_source_deep_link_close_reveals_same_fact_not_filtered_rows_or_page_top() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
function definition(name){
 const start=source.indexOf('  function '+name+'(');
 assert.ok(start>=0,name);
 const end=source.indexOf('\n  function ',start+5);
 return source.slice(start,end);
}
let focused='';
function node(id,parent=null){return {id,parentElement:parent,isConnected:true,
 tagName:'DIV',hidden:false,inert:false,tabIndex:-1,style:{},
 getAttribute(key){return key==='data-row-id'?id:null;},setAttribute(){},
 closest(){for(let n=this.parentElement;n;n=n.parentElement){
  if(n.tagName==='DETAILS'&&!n.open)return n;
 }return null;},
 getClientRects(){return this.hidden||this.closest()||!this.isConnected?[]:[{}];},
 focus(){focused=id;}};}
const main=node('page-top'),anchor=node('list-anchor',main);
const outer=node('outer',main);outer.tagName='DETAILS';outer.open=false;
const inner=node('inner',outer);inner.tagName='DETAILS';inner.open=false;
const row=node('same-fact',inner),other=node('other-fact',main);
let rows=[other,row];
const sandbox={host:{hidden:false},panel:{classList:{remove(){}}},
 openRowId:'same-fact',lastTrigger:null,showStatus(){},emitChange(){},
 setBackgroundInert(){},getComputedStyle(n){return {display:n.hidden?'none':'block',
 visibility:'visible'};},
 document:{querySelectorAll(){return rows;},querySelector(selector){
  return selector==='main'?main:anchor;}}};
// Execute the complete production close path and any helper it actually calls.
const helperStart=source.indexOf('  function restoreSameFactFocus(');
const helper=helperStart<0?'':definition('restoreSameFactFocus');
vm.runInNewContext(helper+'\n'+definition('closeInternal'),sandbox);
sandbox.closeInternal(true);
assert.equal(focused,'same-fact','deep-link close lost its fact to page top');
assert.equal(inner.open,true);assert.equal(outer.open,true);
outer.open=false;inner.open=false;row.hidden=true;focused='';
sandbox.host.hidden=false;sandbox.openRowId='same-fact';sandbox.closeInternal(true);
assert.equal(focused,'list-anchor','filtered fact must return to its list');
assert.equal(inner.open,false,'must not reveal filtered records');
assert.equal(outer.open,false);
rows=[other];focused='';sandbox.host.hidden=false;sandbox.openRowId='same-fact';
sandbox.closeInternal(true);assert.equal(focused,'list-anchor');
const trigger=node('original-trigger',main);sandbox.lastTrigger=trigger;
sandbox.host.hidden=false;sandbox.openRowId='same-fact';sandbox.closeInternal(true);
assert.equal(focused,'original-trigger','ordinary opening keeps actual trigger');
"""
    result = subprocess.run(
        ["node", "-e", probe,
         str(ROOT / "src/ci_workflow/renderers/portal/assets/evidence-drawer.js")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
