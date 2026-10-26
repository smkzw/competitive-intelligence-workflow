const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),path=require('path');
const dir=process.argv[1], elements={},charts={};let input;
const drugs=[
 {id:'a',targets:['C5'],molecular_types:['small molecule'],mechanism_classes:['C5 inhibitor']},
 {id:'b',targets:['C5'],molecular_types:['monoclonal antibody'],mechanism_classes:['C5 inhibitor']},
 {id:'c',targets:['C3'],molecular_types:['protein'],mechanism_classes:['C3 inhibitor']},
 {id:'unknown',targets:[],molecular_types:[],mechanism_classes:[]}
].map((r,i)=>({...r,phase_observations:i<3?[{region:'global',phase:'phase2',fact_id:'f'+i,source_id:'s'+i}]:[]}));
const original=JSON.stringify(drugs),rows=drugs.map(r=>({dataset:{entityId:r.id},textContent:r.id,style:{}}));
const filter={value:'',getAttribute:()=>'tbl-a',addEventListener:(_,fn)=>input=fn,dispatchEvent(){input();}};
for(const id of ['molecular-type','mechanism-class','landscape-group']){
 const listeners={};elements[id]={value:id==='landscape-group'?'targets':'all',options:[],
 appendChild(o){this.options.push(o);},addEventListener:(n,fn)=>listeners[n]=fn,change(){listeners.change();}};
}
elements.charts={textContent:JSON.stringify({landscape:{rows:drugs,classification_labels:{molecular_types:{'small molecule':'小分子药物','monoclonal antibody':'单克隆抗体','protein':'蛋白'},mechanism_classes:{'C5 inhibitor':'C5 抑制剂','C3 inhibitor':'C3 抑制剂'}},phase_labels:{phase2:'II期'}}})};
elements['tbl-a']={id:'tbl-a',querySelectorAll:()=>rows};elements['landscape-count']={};elements['landscape-group-title']={};
for(const id of ['chart-heat','chart-phase']) {const card={hidden:false};elements[id]={id,style:{},closest:()=>card};}
const document={getElementById:id=>elements[id],createElement:()=>({}),querySelector:s=>s==='input[data-filter="tbl-a"]'?filter:null,
 querySelectorAll:s=>s==='input[data-filter]'?[filter]:[]};
const echarts={init(n){const c={options:[],setOption(o){this.options.push(o);},resize(){}};charts[n.id]=c;return c;}};
const window={echarts,addEventListener(){}};
const ctx={window,document,echarts,Event:class{},ResizeObserver:class{observe(){}},Map,Set,Math,Array,JSON};
vm.runInNewContext(fs.readFileSync(path.join(dir,'classification.js'),'utf8'),ctx);
vm.runInNewContext(fs.readFileSync(path.join(dir,'portal.js'),'utf8'),ctx);
const count=()=>rows.filter(r=>r.style.display!=='none').length;
assert.equal(count(),4);
assert.deepEqual(elements['molecular-type'].options.map(o=>o.textContent).sort(),['单克隆抗体','小分子药物','蛋白'].sort());
elements['molecular-type'].value='small molecule';elements['molecular-type'].change();assert.equal(count(),1);assert.equal(rows[0].style.display,'');
elements['mechanism-class'].value='C3 inhibitor';elements['mechanism-class'].change();assert.equal(count(),0);
elements['molecular-type'].value='all';elements['mechanism-class'].value='all';elements['mechanism-class'].change();assert.equal(count(),4);
elements['landscape-group'].value='mechanism_classes';elements['landscape-group'].change();
let heat=charts['chart-heat'].options.at(-1);assert.deepEqual(JSON.parse(JSON.stringify(heat.yAxis.data)),['C3 抑制剂','C5 抑制剂']);
assert.deepEqual(heat.series[0].data.map(p=>p.value[2]).sort(),[1,2]);
assert.deepEqual(heat.series[0].data.flatMap(p=>p.fact_ids).sort(),['f0','f1','f2']);
elements['landscape-group'].value='molecular_types';elements['landscape-group'].change();
heat=charts['chart-heat'].options.at(-1);assert.equal(heat.yAxis.data.length,3);assert.ok(!heat.yAxis.data.includes('C5 抑制剂'));
filter.value='unknown';input();assert.ok(elements['chart-heat'].closest().hidden);assert.equal(count(),1);
filter.value='';input();assert.equal(count(),4);assert.equal(JSON.stringify(drugs),original);
