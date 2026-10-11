"""Shared single-fact geometry: full study context, wrapped original units.

The frozen B 1440/1600 reading shows one shared card family, not a numeric
eligibility change. Production ``charts.js`` still mounts the value, the full
study context and the evidence button. ``portal.css`` must not keep the long
original unit in a nowrap auto column that squeezes the middle context to one
character. No font shrink, clipping, ellipsis or unit conversion.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets"
SOURCE = ASSETS / "charts.js"
PORTAL_CSS = ASSETS / "portal.css"
REPORT_B_CSS = ASSETS / "report-b.css"


def _compact(block: str) -> str:
    return re.sub(r"\s+", "", block)


def _block(css: str, selector: str) -> str:
    matched = re.search(re.escape(selector) + r"\s*\{([^}]+)\}", css)
    assert matched is not None, selector
    return matched.group(1)


def test_single_fact_keeps_full_study_context_and_wraps_original_unit() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let axes=0;
function node(tag){
  const n={tag:tag||'div',style:{},children:[],attributes:{},listeners:{},
    textContent:'',className:'',type:''};
  n.classList={
    add(c){n.className=(n.className+' '+c).trim();},
    remove(c){n.className=n.className.split(' ').filter(x=>x&&x!==c).join(' ');}
  };
  n.appendChild=(child)=>{n.children.push(child);child.parentElement=n;return child;};
  n.setAttribute=(k,v)=>{n.attributes[k]=String(v);};
  n.getAttribute=(k)=>n.attributes[k];
  n.addEventListener=(k,v)=>{n.listeners[k]=v;};
  n.querySelector=()=>null;
  return n;
}
const sandbox={window:{echarts:{init(){axes++;throw Error('single fact must not create axes')}}},
 document:{readyState:'loading',addEventListener(){},createElement:node}};
const text=fs.readFileSync(process.argv[1],'utf8').replace(
 'presentationPlan: presentationPlan,',
 'presentationPlan: presentationPlan, testMount: initGroupChart,');
vm.runInNewContext(text,sandbox);
const api=sandbox.window.__CHART_SYNC__;
const unit='报告未注明统计口径，原单位全文保留不翻译不换算';
const row={row_id:'fact-long-unit',display_value:'12',numeric_value:12,value:12,unit,
 renderable:true,_chart_type:'bar',disclosure_state:'reported_value',
 product_zh:'合成研究语境必须完整逐字保留，不能在单事实窄卡里被压成竖排的一个字',
 trial_id:'nct01234567',trial_zh:'不得用试验中文名替换登记号',
 arm_role_label_zh:'试验组',category:'不得用类别替换角色',display_label_zh:'受累人数'};
const group={chart_type:'bar',rows:[row],title_zh:'受累人数'};
const plan=api.presentationPlan(group);
assert.equal(plan.kind,'single_fact');
assert.equal(plan.grid_span,6,'current length plan stays span 6');
assert.equal(plan.target_height,0);
assert.deepEqual(Array.from(plan.plotted_ids),[row.row_id]);
const host=node('div'),target=node('div');
host.appendChild(target);
api.testMount(target,0,group);
assert.equal(axes,0);
assert.equal(target.attributes.role,'group');
assert.equal(target.attributes['data-chart-type'],'single-fact');
assert.equal(target.style.height,'auto');
assert.ok(target.className.split(' ').includes('kz-chart-group__chart--single-fact'));
assert.equal(target.children.length,3);
const value=target.children[0],context=target.children[1],button=target.children[2];
assert.equal(value.className,'kz-chart-single-fact__value');
assert.equal(value.textContent,'12 '+unit,'original unit text stays on the value');
assert.equal(context.className,'kz-chart-single-fact__context');
const study=[row.product_zh,'NCT01234567',row.arm_role_label_zh].join(' · ');
assert.equal(context.textContent,study,'full study context stays one text node');
assert.ok(study.length>48);
assert.equal(button.className,'kz-chart-single-fact__source');
assert.equal(button.type,'button');
assert.equal(button.textContent,'查看依据');
assert.equal(button.attributes['data-chart-evidence-open'],row.row_id);
assert.equal(button.attributes['data-row-id'],row.row_id);
assert.equal(typeof button.listeners.click,'function');
"""
    rendered = subprocess.run(
        ["node", "-e", probe, str(SOURCE)],
        capture_output=True, text=True, check=False,
    )
    assert rendered.returncode == 0, rendered.stderr

    portal = PORTAL_CSS.read_text(encoding="utf-8")
    card = _compact(_block(
        portal, ".kz-chart-group__chart.kz-chart-group__chart--single-fact"))
    value = _compact(_block(portal, ".kz-chart-single-fact__value"))
    context = _compact(_block(portal, ".kz-chart-single-fact__context"))
    source = _compact(_block(portal, ".kz-chart-single-fact__source"))
    focus = _compact(_block(portal, ".kz-chart-single-fact__source:focus-visible"))
    for block in (card, value, context, source, focus):
        assert "!important" not in block
        assert "ellipsis" not in block
        assert "overflow:hidden" not in block
        assert "line-clamp" not in block

    assert "display:grid" in card
    assert "grid-template-columns:minmax(0,1fr)auto" in card
    assert "automax(0,1fr)auto" not in card
    assert "overflow:visible" in card
    assert "min-width:0" in card

    assert "grid-column:1" in value and "grid-row:1" in value
    assert "minmax" not in value
    assert "min-width:0" in value
    assert "white-space:normal" in value
    assert "nowrap" not in value
    assert "overflow-wrap:anywhere" in value
    assert "font-size:21px" in value
    assert "font-size:16px" not in value

    assert "grid-column:1/-1" in context
    assert "grid-row:2" in context
    assert "font-size:16px" in context
    assert "nowrap" not in context
    assert "overflow-wrap:anywhere" in context

    assert "grid-column:2" in source and "grid-row:1" in source
    assert "min-height:36px" in source
    assert "padding:5px9px" in source
    assert "font:60016px/1.25var(--font-sans)" in source
    assert "min-width:0" not in source
    assert focus == "outline:3pxsolidvar(--kz-orange);outline-offset:2px;"

    report_b = REPORT_B_CSS.read_text(encoding="utf-8")
    measurement = _compact(_block(
        report_b, ".kz-b-measurement-observations .kz-chart-group__chart--single-fact"))
    assert measurement == "grid-template-columns:minmax(0,1fr)auto;"
    assert "grid-column" not in measurement
    chart_clip = _compact(_block(report_b, ".kz-chart-group__chart"))
    assert "overflow:hidden" in chart_clip
    assert ".kz-chart-group__chart.kz-chart-group__chart--single-fact" not in report_b
