"""Execute production interaction against a minimal DOM; real pixels use Ego."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_original_evidence_native_reader_moves_content_then_restores_actual_trigger():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    source = Path(__file__).resolve().parents[1] / 'src/ciw2/render/static/portal.js'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const events={},life={}; let focused=0,opened=0;
const content={textContent:'Full original AND/OR criteria'}, origin={open:false,appendChild(n){n.parentElement=this;}};
content.parentElement=origin; origin.querySelector=()=>content;
const trigger={parentElement:origin,closest:()=>({dataset:{trial:'<untrusted-study>'}}),focus(){focused++;},
  addEventListener(k,fn){events[k]=fn;}};
const dialog={open:false,addEventListener(k,fn){events['dialog:'+k]=fn;},
  showModal(){this.open=true;opened++;},close(){this.open=false;events['dialog:close']();}};
const body={appendChild(n){n.parentElement=this;}};
const title={textContent:''};
const close={addEventListener(k,fn){events['close:'+k]=fn;}};
const elements={'design-evidence-dialog':dialog,'design-evidence-body':body,'design-evidence-title':title,'design-evidence-close':close};
const document={getElementById:id=>elements[id],querySelectorAll:s=>s==='.design-evidence > summary'?[trigger]:[]};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{addEventListener(k,fn){life[k]=fn;}}});
assert.equal(typeof events.click,'function');
let prevented=false;events.click({preventDefault(){prevented=true;}});
assert.equal(prevented,true);assert.equal(opened,1);assert.equal(content.parentElement,body);
assert.ok(title.textContent.includes('<untrusted-study>'));
events['close:click']();assert.equal(content.parentElement,origin);assert.equal(focused,1);assert.equal(origin.open,false);
events.click({preventDefault(){}});dialog.close();assert.equal(focused,2);assert.equal(content.parentElement,origin);
events.click({preventDefault(){}});life.pagehide();assert.equal(dialog.open,false);assert.equal(content.parentElement,origin);
'''
    result = subprocess.run([node, '-e', script, str(source)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr

SOURCE = Path(__file__).resolve().parents[1] / 'src/ciw2/render/static/portal.js'


def run_portal(script):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable: production JS behavior not run')
    result = subprocess.run([node, '-e', script, str(SOURCE)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_dense_design_overview_is_compact_keeps_every_point_and_reports_full_phase_counts():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const rows=[];
for(let i=0;i<284;i++){
  const phase=i<160?'III期':i<260?'II期':i<282?'I期':i<283?'III期':'未知期别';
  rows.push({dataset:{trial:'NCT'+i,phase:phase,phaseStatus:i===282?'unverified':'verified'},style:{},textContent:'NCT'+i});
}
const labels=rows.slice(0,282).map(r=>r.dataset.trial);
const values=labels.map((_,i)=>i<5?0:i);
const phase=[{name:'III期',value:160},{name:'II期',value:100},{name:'I期',value:22},{name:'未知期别',value:1}];
const elements={},charts={};
for(const id of ['chart-size','chart-phase-pie']){const card={hidden:false};elements[id]={id,style:{},closest:()=>card};}
elements.charts={textContent:JSON.stringify({size:{labels,values},phase})};
elements['design-count']={};
elements['tbl-c']={id:'tbl-c',querySelectorAll:()=>rows};
let input;
const filter={value:'',getAttribute:()=>'tbl-c',addEventListener:(_,fn)=>{input=fn;}};
const echarts={init(node){const chart={options:[],resize(){},dispose(){},setOption(o){this.options.push(o);}};charts[node.id]=chart;return chart;}};
const document={documentElement:{},getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[filter]:[]};
const window={echarts,addEventListener(){},matchMedia:()=>({matches:true}),getComputedStyle:()=>({getPropertyValue:k=>k==='--report-font-body'?'18px':'ExampleFont'})};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window,echarts,ResizeObserver:class{observe(){} disconnect(){}},Set,Math,Array,JSON});
const initialSize=charts['chart-size'].options[0],initialPie=charts['chart-phase-pie'].options[0];
const height=id=>parseInt(elements[id].style.height,10);
assert.equal(initialSize.textStyle.fontSize,18);
assert.equal(initialSize.textStyle.fontFamily,'ExampleFont');
assert.equal(initialSize.animation,false);
assert.ok(initialSize.xAxis.axisLabel.fontSize>=16 && initialSize.yAxis.axisLabel.fontSize>=16);
assert.ok(initialSize.series[0].label.fontSize>=16);
assert.equal(JSON.stringify(initialSize.series[0].data),JSON.stringify(values));
assert.ok(initialSize.series[0].data.includes(0));
assert.ok(height('chart-size')<=336 && height('chart-size')>=300);
const zoom=initialSize.dataZoom[0];
assert.equal(zoom.filterMode,'filter');
assert.equal(zoom.endValue-zoom.startValue+1,12);
assert.ok(zoom.endValue<labels.length-1);
assert.equal(initialPie.series[0].type,'pie');
assert.equal(initialPie.series[0].label.show,false);
assert.equal(initialPie.series[0].labelLine.show,false);
assert.ok(initialPie.legend&&initialPie.legend.formatter('III期')==='III期 160 项');
assert.ok(initialPie.legend.formatter('未知期别')==='未知期别 1 项');
assert.equal(initialPie.legend.textStyle.fontSize,18);
assert.ok(height('chart-phase-pie')<=200 && height('chart-phase-pie')>=120);
rows.forEach((r,i)=>{r.textContent=i===260?'chosen':'other';});
filter.value='chosen';input();
const sparseSize=charts['chart-size'].options.at(-1);
assert.equal(JSON.stringify(sparseSize.series[0].data),JSON.stringify([values[260]]));
assert.ok(height('chart-size')<=144 && height('chart-size')>=100);
assert.equal(height('chart-phase-pie'),120);
const sparsePie=charts['chart-phase-pie'].options.at(-1);
assert.equal(JSON.stringify(sparsePie.series[0].data),JSON.stringify([{name:'I期',value:1}]));
assert.equal(sparsePie.legend.formatter('I期'),'I期 1 项');
assert.equal(elements['chart-phase-pie'].closest().hidden,false);
filter.value='no-match';input();
assert.equal(elements['chart-size'].closest().hidden,true);
assert.equal(elements['chart-phase-pie'].closest().hidden,true);
assert.equal(elements['design-count'].textContent,'0 / 284 项研究');
filter.value='';rows.forEach(r=>{r.textContent=r.dataset.trial;});input();
const restoredSize=charts['chart-size'].options.at(-1);
assert.equal(JSON.stringify(restoredSize.series[0].data),JSON.stringify(values));
assert.equal(JSON.stringify(restoredSize.yAxis.data),JSON.stringify(labels));
assert.equal(restoredSize.dataZoom[0].endValue,11);
assert.equal(height('chart-size'),336);
const restoredPie=charts['chart-phase-pie'].options.at(-1);
assert.equal(JSON.stringify(restoredPie.series[0].data),JSON.stringify(phase));
assert.equal(restoredPie.legend.formatter('III期'),'III期 160 项');
assert.equal(elements['chart-phase-pie'].closest().hidden,false);
assert.equal(elements['design-count'].textContent,'284 / 284 项研究');
'''
    run_portal(script)


def test_phase_only_filters_without_size_data_and_never_counts_unknown_phase():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const rows=[
  {dataset:{trial:'NCT-A',phase:'III期',phaseStatus:'verified'},style:{},textContent:'NCT-A'},
  {dataset:{trial:'NCT-B',phase:'II期',phaseStatus:'verified'},style:{},textContent:'NCT-B'},
  {dataset:{trial:'NCT-C',phase:'III期',phaseStatus:'unverified'},style:{},textContent:'NCT-C'},
  {dataset:{trial:'NCT-D',phase:'',phaseStatus:'verified'},style:{},textContent:'NCT-D'}];
const phase=[{name:'III期',value:1},{name:'II期',value:1}];
const elements={},charts={};
const card={hidden:false};
elements['chart-phase-pie']={id:'chart-phase-pie',style:{},closest:()=>card};
elements.charts={textContent:JSON.stringify({phase})};
elements['design-count']={};
elements['tbl-c']={id:'tbl-c',querySelectorAll:()=>rows};
let input;
const filter={value:'',getAttribute:()=>'tbl-c',addEventListener:(_,fn)=>{input=fn;}};
const echarts={init(node){const chart={options:[],resize(){},dispose(){},setOption(o){this.options.push(o);}};charts[node.id]=chart;return chart;}};
const document={documentElement:{},getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[filter]:[]};
const window={echarts,addEventListener(){},matchMedia:()=>({matches:false}),getComputedStyle:()=>({getPropertyValue:()=>''})};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window,echarts,ResizeObserver:class{observe(){} disconnect(){}},Set,Math,Array,JSON});
assert.equal(charts['chart-size'],undefined);
assert.equal(parseInt(elements['chart-phase-pie'].style.height,10),120);
const initial=charts['chart-phase-pie'].options[0];
assert.equal(JSON.stringify(initial.series[0].data),JSON.stringify(phase));
assert.equal(initial.legend.formatter('III期'),'III期 1 项');
rows.forEach((r,i)=>{r.textContent=i===0?'alpha':'other';});
filter.value='alpha';input();
assert.equal(JSON.stringify(charts['chart-phase-pie'].options.at(-1).series[0].data),JSON.stringify([{name:'III期',value:1}]));
assert.equal(charts['chart-phase-pie'].options.at(-1).legend.formatter('III期'),'III期 1 项');
assert.equal(elements['chart-phase-pie'].style.height,'120px');
filter.value='unverified';rows.forEach((r,i)=>{r.textContent=i===2?'unverified':'other';});input();
assert.equal(card.hidden,true);
filter.value='empty';rows.forEach((r,i)=>{r.textContent=i===3?'empty':'other';});input();
assert.equal(card.hidden,true);
filter.value='';rows.forEach(r=>{r.textContent=r.dataset.trial;});input();
assert.equal(card.hidden,false);
assert.equal(JSON.stringify(charts['chart-phase-pie'].options.at(-1).series[0].data),JSON.stringify(phase));
assert.equal(elements['design-count'].textContent,'4 / 4 项研究');
'''
    run_portal(script)


def test_chart_source_labels_are_safe_text_and_missing_library_has_no_internal_path():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const attack='<img src=x onerror=alert(1)>';
const heat={id:'chart-heat',innerHTML:''};
const pie={id:'chart-phase-pie',style:{},closest:()=>({hidden:false})};
const payload={heat:{x:['I期'],y:[attack],data:[[0,0,1]]},phase:[{name:attack,value:2}]};
const elements={charts:{textContent:JSON.stringify(payload)},'chart-heat':heat,'chart-phase-pie':pie};
const charts={};
const document={getElementById:id=>elements[id]||null,querySelectorAll:()=>[]};
const echarts={init(node){const chart={options:[],resize(){},dispose(){},setOption(o){this.options.push(o);}};charts[node.id]=chart;return chart;}};
const env={document,window:{echarts,addEventListener(){}},echarts,ResizeObserver:class{observe(){} disconnect(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),env);
const tooltip=charts['chart-heat'].options[0].tooltip.formatter({value:[0,0,1]});
assert.ok(!tooltip.includes('<img')&&tooltip.includes('&lt;img'));
const pieTooltip=charts['chart-phase-pie'].options[0].tooltip.formatter({name:attack,value:2});
assert.ok(!pieTooltip.includes('<img')&&pieTooltip.includes('&lt;img'));
assert.ok(charts['chart-phase-pie'].options[0].legend.formatter(attack).includes(attack));
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{addEventListener(){}}});
assert.ok(heat.innerHTML.includes('数据表')&&!heat.innerHTML.includes('scripts/'));
'''
    run_portal(script)
