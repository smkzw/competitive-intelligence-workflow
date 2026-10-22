"""Execute production interaction against a minimal DOM; real pixels use Ego."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_design_chart_query_preserves_all_rows_and_compacts_both_panels():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable: production JS behavior not run')
    source = Path(__file__).resolve().parents[1] / 'src/ciw2/render/static/portal.js'
    script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
const rows = Array.from({length:40}, (_,i) => ({dataset:{trial:'NCT'+i,phase:'III期',phaseStatus:i===39?'unverified':'verified'},style:{},textContent:'NCT'+i}));
const elements = {}, charts = {};
for (const id of ['chart-size','chart-phase-pie']) {
  const card = {hidden:false};
  elements[id] = {id,style:{},closest:()=>card};
}
elements.charts = {textContent:JSON.stringify({size:{labels:rows.map(r=>r.dataset.trial),values:rows.map((_,i)=>i)},phase:[{name:'III期',value:39}]})};
elements['design-count'] = {};
const table = {id:'tbl-c', querySelectorAll:()=>rows};
elements['tbl-c'] = table;
let input;
const filter = {value:'',getAttribute:()=> 'tbl-c',addEventListener:(_,fn)=>{input=fn;}};
const echarts = {init(node){ const chart = {options:[],resize(){},dispose(){},setOption(o){this.options.push(o);}}; charts[node.id]=chart;return chart;}};
const document = {getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[filter]:[]};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,ResizeObserver:class{observe(){} disconnect(){}},Set,Math,Array,JSON});
const initial = charts['chart-size'].options[0];
assert.equal(initial.series[0].data.length,40);
assert.ok(initial.dataZoom.some(z=>z.type==='slider' && z.yAxisIndex===0));
assert.ok(initial.dataZoom[0].endValue < 40);
rows.forEach((r,i)=>{r.textContent=i<2?'chosen':'other';}); filter.value='chosen';input();
assert.equal(charts['chart-size'].options.at(-1).series[0].data.length,2);
assert.equal(elements['chart-size'].style.height,elements['chart-phase-pie'].style.height);
assert.ok(parseInt(elements['chart-size'].style.height)<300);
filter.value='NCT39';rows.forEach(r=>{r.textContent=r.dataset.trial;});input();
assert.equal(elements['chart-phase-pie'].closest().hidden,true);
assert.equal(elements['chart-size'].closest().hidden,false);
filter.value='no-match';input();
assert.equal(elements['chart-size'].closest().hidden,true);
filter.value='';input();
assert.equal(charts['chart-size'].options.at(-1).series[0].data.length,40);
assert.equal(elements['chart-phase-pie'].closest().hidden,false);
'''
    result = subprocess.run([node, '-e', script, str(source)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
