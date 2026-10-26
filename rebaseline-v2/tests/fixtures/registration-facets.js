const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={},charts={};let input;
const drugs=Array.from({length:7},(_,i)=>({id:'d'+i,targets:[],phase_observations:[
  {region:'china',phase:'phase2',indication:'人群'+i,as_of:'2026-10-26',fact_id:'f'+i,source_id:'src'+i}]}));
const original=JSON.stringify(drugs),rows=drugs.map(r=>({dataset:{entityId:r.id,competitionClass:['innovative','biosimilar','modified','unknown'][Number(r.id.slice(1))%4]},textContent:r.id,style:{},competition:'unused'}));
let change;const category={value:'all',addEventListener:(_,fn)=>change=fn};elements['competition-class']=category;
const filter={value:'',getAttribute:()=>'tbl-a',addEventListener:(_,fn)=>input=fn};
elements.charts={textContent:JSON.stringify({landscape:{rows:drugs,phase_labels:{phase2:'II 期'}}})};
elements['tbl-a']={id:'tbl-a',querySelectorAll:()=>rows};elements['landscape-count']={};
for(const id of ['chart-heat','chart-phase']){const card={hidden:false};elements[id]={id,style:{},closest:()=>card};}
const document={getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[filter]:[]};
const echarts={init(n){const c={options:[],setOption(o){this.options.push(o);},resize(){}};charts[n.id]=c;return c;}};
const window={echarts,addEventListener(){}};
const ctx={window,document,echarts,ResizeObserver:class{observe(){}},Map,Set,Math,Array,JSON};
vm.runInNewContext(fs.readFileSync(process.argv[1].replace('portal.js','kz-tokens.js'),'utf8'),ctx);
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const option=()=>charts['chart-phase'].options.at(-1);
assert.equal(option().grid.length,2);assert.equal(option().series.length,7);
assert.ok(option().yAxis.every(a=>a.min===0&&a.max===1));
assert.equal(option().legend.length,2);
assert.equal(option().series[0].itemStyle.color,window.KZ_TOKENS.charts.categorical[0]);
assert.equal(new Set(option().series.slice(0,5).map(s=>s.itemStyle.color)).size,5);
assert.equal(JSON.stringify(option().series.flatMap(s=>s.data.flatMap(p=>p.fact_ids)).sort()),
  JSON.stringify(drugs.map((_,i)=>'f'+i).sort()));
assert.equal(JSON.stringify(option().series.flatMap(s=>s.data.flatMap(p=>p.source_ids)).sort()),
  JSON.stringify(drugs.map((_,i)=>'src'+i).sort()));
const lastColor=option().series.at(-1).itemStyle.color;
filter.value='d6';input();
assert.equal(option().series.length,1);assert.equal(option().series[0].itemStyle.color,lastColor);
assert.equal(option().series[0].data[0].fact_ids[0],'f6');
filter.value='';input();assert.equal(option().series.length,7);
assert.equal(JSON.stringify(drugs),original);

category.value='biosimilar';change();assert.equal(rows.filter(r=>r.style.display!=='none').length,2);assert.equal(option().series.length,2);assert.equal(JSON.stringify(option().series.flatMap(s=>s.data.flatMap(p=>p.fact_ids)).sort()),JSON.stringify(['f1','f5']));
filter.value='d5';input();assert.equal(option().series.length,1);assert.equal(option().series[0].data[0].fact_ids[0],'f5');category.value='innovative';change();assert.equal(rows.filter(r=>r.style.display!=='none').length,0);assert.equal(elements['chart-phase'].closest().hidden,true);filter.value='';category.value='all';change();assert.equal(rows.filter(r=>r.style.display!=='none').length,7);assert.equal(option().series.length,7);assert.equal(JSON.stringify(drugs),original);
