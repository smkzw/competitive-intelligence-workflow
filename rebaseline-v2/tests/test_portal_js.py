"""Execute production interaction against a minimal DOM; real pixels use Ego."""
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize('evidence_kind',['original','source'])
def test_original_evidence_native_reader_moves_content_then_restores_actual_trigger(evidence_kind):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    source = Path(__file__).resolve().parents[1] / 'src/ciw2/render/static/portal.js'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const events={},life={}; let focused=0,opened=0;
const kind=process.argv[2];
const content={textContent:'Full original AND/OR criteria'}, origin={open:false,appendChild(n){n.parentElement=this;}};
content.parentElement=origin; origin.querySelector=selector=>kind==='original'||selector.includes('source-evidence-content')?content:null;
const trigger={parentElement:origin,closest:()=>({dataset:{trial:'<untrusted-study>'}}),focus(){focused++;},
  addEventListener(k,fn){events[k]=fn;}};
const dialog={open:false,addEventListener(k,fn){events['dialog:'+k]=fn;},
  showModal(){this.open=true;opened++;},close(){this.open=false;events['dialog:close']();}};
const body={appendChild(n){n.parentElement=this;}};
const title={textContent:''};
const close={addEventListener(k,fn){events['close:'+k]=fn;}};
const elements={'design-evidence-dialog':dialog,'design-evidence-body':body,'design-evidence-title':title,'design-evidence-close':close};
const document={getElementById:id=>elements[id],querySelectorAll:s=>s.includes('design-evidence > summary')?[trigger]:[]};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{addEventListener(k,fn){life[k]=fn;}}});
assert.equal(typeof events.click,'function');
let prevented=false;events.click({preventDefault(){prevented=true;}});
assert.equal(prevented,true);assert.equal(opened,1);assert.equal(content.parentElement,body);
assert.ok(title.textContent.includes('<untrusted-study>'));
events['close:click']();assert.equal(content.parentElement,origin);assert.equal(focused,1);assert.equal(origin.open,false);
events.click({preventDefault(){}});dialog.close();assert.equal(focused,2);assert.equal(content.parentElement,origin);
events.click({preventDefault(){}});life.pagehide();assert.equal(dialog.open,false);assert.equal(content.parentElement,origin);
'''
    result = subprocess.run([node, '-e', script, str(source),evidence_kind], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr

SOURCE = Path(__file__).resolve().parents[1] / 'src/ciw2/render/static/portal.js'


def run_portal(script):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable: production JS behavior not run')
    result = subprocess.run([node, '-e', script, str(SOURCE)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_design_overview_uses_compact_count_bars_and_disambiguates_only_repeated_labels():
    run_portal(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const ids=['CTR00000001','CTR00000002','CTR00000003'];
const identities=ids.map((id,i)=>({registry_id:id,axis_label:i<2?'药物甲 · III 期':'药物乙 · II 期',label:'完整研究 '+id}));
const data={size:{labels:ids,values:[100,200,300],identities},phase:[{name:'III 期',value:2},{name:'II 期',value:1}]};
const rows=ids.map((id,i)=>({dataset:{trial:id,phase:i<2?'III 期':'II 期',phaseStatus:'verified'},style:{},textContent:id}));
const charts={},elements={charts:{textContent:JSON.stringify(data)},'tbl-c':{id:'tbl-c',querySelectorAll:()=>rows}};
for(const id of ['chart-size','chart-phase-pie']){const card={hidden:false};elements[id]={id,style:{},closest:()=>card};}
let input;const filter={value:'',getAttribute:()=>'tbl-c',addEventListener:(_,fn)=>input=fn};
const document={getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[filter]:[]};
const echarts={init(node){const c={options:[],resize(){},dispose(){},setOption(o){this.options.push(o);}};charts[node.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,ResizeObserver:class{observe(){}},Map});
const labels=charts['chart-size'].options[0].yAxis.axisLabel.formatter;
assert.equal(charts['chart-size'].options[0].yAxis.axisLabel.interval,0);
assert.equal(labels(ids[0]),'药物甲 · III 期\n'+ids[0]);
assert.equal(labels(ids[1]),'药物甲 · III 期\n'+ids[1]);
assert.equal(labels(ids[2]),'药物乙 · II 期');
const phase=charts['chart-phase-pie'].options[0];
assert.equal(phase.series[0].type,'bar');assert.equal(phase.xAxis.min,0);assert.equal(phase.xAxis.minInterval,1);
assert.equal(JSON.stringify(phase.yAxis.data),JSON.stringify(['III 期','II 期']));
assert.equal(JSON.stringify(phase.series[0].data),JSON.stringify([2,1]));
filter.value=ids[2];input();
assert.ok(parseInt(elements['chart-phase-pie'].style.height,10)<=80);
assert.equal(JSON.stringify(charts['chart-phase-pie'].options.at(-1).series[0].data),JSON.stringify([1]));
filter.value='';input();
assert.equal(JSON.stringify(charts['chart-phase-pie'].options.at(-1).series[0].data),JSON.stringify([2,1]));
assert.equal(JSON.stringify(charts['chart-size'].options.at(-1).series[0].data),JSON.stringify([100,200,300]));
''')


def test_landscape_unknown_sparse_dense_and_filtered_membership_share_one_query():
    run_portal(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const cards={},elements={},charts={};let input;
for(const id of ['chart-heat','chart-phase']){
  cards[id]={hidden:false};elements[id]={id,style:{},closest:()=>cards[id]};
}
const known={id:'known',name:'Known',targets:['Target X'],phase_global:'phase2',phase_china:'unknown'};
const unknown={id:'unknown',name:'Unknown',targets:[],phase_global:'unknown',phase_china:'unknown'};
const rows=[known,unknown].map(r=>({dataset:{entityId:r.id},style:{},textContent:r.name}));
const table={id:'tbl-a',querySelectorAll:()=>rows};elements['tbl-a']=table;elements['landscape-count']={};
elements.charts={textContent:JSON.stringify({landscape:{rows:[known,unknown],phase_labels:{phase2:'II 期'}}})};
const filter={value:'',getAttribute:k=>k==='data-filter'?'tbl-a':null,addEventListener:(_,fn)=>input=fn};
const document={getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[filter]:[]};
const echarts={init(n){const c={options:[],setOption(o){this.options.push(o);},resize(){},dispose(){}};charts[n.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,
 ResizeObserver:class{observe(){}disconnect(){}},Set,Map,Math,Array,JSON});
assert.deepEqual(JSON.parse(JSON.stringify(charts['chart-heat'].options.at(-1).series[0].data)),[[0,0,1]]);
assert.ok(parseInt(elements['chart-heat'].style.height)<=160);
assert.ok(parseInt(elements['chart-phase'].style.height)<=220);
const phase=charts['chart-phase'].options.at(-1);
assert.equal(phase.legend.top,0);assert.ok(phase.grid.top>=48);
assert.deepEqual(JSON.parse(JSON.stringify(phase.series.map(s=>s.data))),[[1],[0]]);
assert.ok(!JSON.stringify(phase.xAxis.data).includes('未知'));
assert.equal(elements['landscape-count'].textContent,'2 / 2 个药物 · 全球阶段 1 · 中国阶段 0 · 靶点与阶段 1');
filter.value='Unknown';input();assert.ok(cards['chart-heat'].hidden&&cards['chart-phase'].hidden);
assert.ok(elements['landscape-count'].textContent.startsWith('1 / 2'));
assert.equal(rows[1].style.display,'');
filter.value='Known';input();assert.ok(!cards['chart-heat'].hidden&&!cards['chart-phase'].hidden);
filter.value='no-match';input();assert.ok(cards['chart-heat'].hidden&&cards['chart-phase'].hidden);
filter.value='';input();assert.ok(!cards['chart-heat'].hidden&&!cards['chart-phase'].hidden);
''')


def test_endpoint_index_count_tracks_visible_study_membership():
    run_portal(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const rows=['A','B'].map(trial=>({dataset:{trial},style:{},textContent:trial}));
const entries=rows.map(r=>({dataset:{trial:r.dataset.trial},hidden:false}));
const groups=entries.map(e=>({hidden:false,querySelectorAll:()=>[e]}));
entries.forEach((e,i)=>e.closest=()=>groups[i]);
const count={}, table={id:'tbl-c',querySelectorAll:()=>rows};let input;
const filter={value:'',getAttribute:()=>'tbl-c',addEventListener:(_,fn)=>input=fn};
const elements={'tbl-c':table,'endpoint-group-count':count};
const document={getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[filter]:
  s==='.endpoint-entry'?entries:s==='.endpoint-index tbody tr'?groups:[]};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{addEventListener(){}}});
filter.value='A';input();assert.equal(count.textContent,'1 / 2');assert.equal(groups[1].hidden,true);
filter.value='none';input();assert.equal(count.textContent,'0 / 2');assert.ok(groups.every(g=>g.hidden));
filter.value='';input();assert.equal(count.textContent,'2 / 2');assert.ok(groups.every(g=>!g.hidden));
''')


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
assert.equal(initialPie.series[0].type,'bar');
assert.equal(initialPie.series[0].label.show,true);
assert.equal(JSON.stringify(initialPie.yAxis.data),JSON.stringify(phase.map(p=>p.name)));
assert.equal(JSON.stringify(initialPie.series[0].data),JSON.stringify(phase.map(p=>p.value)));
assert.equal(initialPie.yAxis.axisLabel.fontSize,18);
assert.ok(height('chart-phase-pie')<=200 && height('chart-phase-pie')>=72);
rows.forEach((r,i)=>{r.textContent=i===260?'chosen':'other';});
filter.value='chosen';input();
const sparseSize=charts['chart-size'].options.at(-1);
assert.equal(JSON.stringify(sparseSize.series[0].data),JSON.stringify([values[260]]));
assert.ok(height('chart-size')<=144 && height('chart-size')>=100);
assert.equal(height('chart-phase-pie'),72);
const sparsePie=charts['chart-phase-pie'].options.at(-1);
assert.equal(JSON.stringify(sparsePie.series[0].data),JSON.stringify([1]));
assert.equal(JSON.stringify(sparsePie.yAxis.data),JSON.stringify(['I期']));
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
assert.equal(JSON.stringify(restoredPie.series[0].data),JSON.stringify(phase.map(p=>p.value)));
assert.equal(JSON.stringify(restoredPie.yAxis.data),JSON.stringify(phase.map(p=>p.name)));
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
assert.equal(parseInt(elements['chart-phase-pie'].style.height,10),96);
const initial=charts['chart-phase-pie'].options[0];
assert.equal(JSON.stringify(initial.series[0].data),JSON.stringify([1,1]));
assert.equal(JSON.stringify(initial.yAxis.data),JSON.stringify(['III期','II期']));
rows.forEach((r,i)=>{r.textContent=i===0?'alpha':'other';});
filter.value='alpha';input();
assert.equal(JSON.stringify(charts['chart-phase-pie'].options.at(-1).series[0].data),JSON.stringify([1]));
assert.equal(JSON.stringify(charts['chart-phase-pie'].options.at(-1).yAxis.data),JSON.stringify(['III期']));
assert.equal(elements['chart-phase-pie'].style.height,'72px');
filter.value='unverified';rows.forEach((r,i)=>{r.textContent=i===2?'unverified':'other';});input();
assert.equal(card.hidden,true);
filter.value='empty';rows.forEach((r,i)=>{r.textContent=i===3?'empty':'other';});input();
assert.equal(card.hidden,true);
filter.value='';rows.forEach(r=>{r.textContent=r.dataset.trial;});input();
assert.equal(card.hidden,false);
assert.equal(JSON.stringify(charts['chart-phase-pie'].options.at(-1).series[0].data),JSON.stringify([1,1]));
assert.equal(JSON.stringify(charts['chart-phase-pie'].options.at(-1).yAxis.data),JSON.stringify(['III期','II期']));
assert.equal(elements['design-count'].textContent,'4 / 4 项研究');
'''
    run_portal(script)


def test_chart_source_labels_are_safe_text_and_missing_library_has_no_internal_path():
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const attack='<img src=x onerror=alert(1)>';
const heat={id:'chart-heat',innerHTML:'',style:{},closest:()=>({hidden:false})};
const pie={id:'chart-phase-pie',style:{},closest:()=>({hidden:false})};
const payload={landscape:{rows:[{id:'drug',targets:[attack],phase_global:'phase1',phase_china:'unknown'}],
  phase_labels:{phase1:'I期'}},phase:[{name:attack,value:2}]};
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
assert.equal(charts['chart-phase-pie'].options[0].yAxis.data[0],attack);
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{addEventListener(){}}});
assert.ok(heat.innerHTML.includes('数据表')&&!heat.innerHTML.includes('scripts/'));
'''
    run_portal(script)


def test_dense_landscape_keeps_all_target_cells_and_unknown_stage_stays_in_table_query():
    run_portal(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const rows=Array.from({length:18},(_,i)=>({id:'d'+i,targets:['T'+i,'T'+i],phase_global:'phase2',phase_china:'unknown'}));
rows.push({id:'extra',targets:['unresolved'],phase_global:'unknown',phase_china:'unknown'});
rows[0].phase_china='phase1';
const elements={},charts={};
for(const id of ['chart-heat','chart-phase'])elements[id]={id,style:{},closest:()=>({hidden:false})};
elements.charts={textContent:JSON.stringify({landscape:{rows,phase_labels:{phase1:'I期',phase2:'II期'}}})};
elements['landscape-count']={};
const document={getElementById:id=>elements[id],querySelectorAll:()=>[]};
const echarts={init(n){const c={options:[],setOption(o){this.options.push(o);},resize(){},dispose(){}};charts[n.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,
 ResizeObserver:class{observe(){}disconnect(){}},Set,Map,Math,Array,JSON});
const heat=charts['chart-heat'].options[0];
assert.equal(heat.series[0].data.length,18);
assert.ok(heat.series[0].data.every(p=>p[2]===1));
assert.equal(heat.yAxis.data.length,18);assert.ok(!heat.yAxis.data.includes('unresolved'));
assert.deepEqual(JSON.parse(JSON.stringify(heat.xAxis.data)),['II期']);
assert.deepEqual(JSON.parse(JSON.stringify(charts['chart-phase'].options[0].xAxis.data)),['I期','II期']);
assert.equal(heat.dataZoom[0].show,true);assert.equal(heat.dataZoom[0].endValue,5);
assert.equal(elements['chart-heat'].style.height,'328px');
assert.ok(elements['landscape-count'].textContent.startsWith('19 / 19'));
''')
