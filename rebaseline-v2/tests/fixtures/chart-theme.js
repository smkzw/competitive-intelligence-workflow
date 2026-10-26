const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const events={},elements={},charts={};
const points=Array.from({length:SERIES_COUNT},(_,i)=>[0,14].map(x=>({fact_id:`f${i}-${x}`,
  series_key:'s'+i,series_name:'真实组 '+i,drug_label:'药物 '+i,phase_label:'II 期',
  x,value:i===0&&x===0?0:-(i+x),visit:'第'+x+'天'}))).flat();
const original=JSON.stringify(points),rows=points.map(p=>({dataset:{factId:p.fact_id},style:{},textContent:p.series_key}));
const group={id:'g',kind:'line',points,positions:[0,14],axis_unit:'days',title:'同一终点'};
const selector={value:'g',querySelectorAll:()=>[{value:'g'}],addEventListener(){}};
const input={value:'',getAttribute:()=>'tbl-b',addEventListener:(k,f)=>events.input=f};
elements.charts={textContent:JSON.stringify({groups:[group]})};
elements['tbl-b']={id:'tbl-b',querySelectorAll:()=>rows};elements['result-group']=selector;
elements['result-query']=input;
for(const id of ['result-count','result-panel','result-empty','result-definition','result-unit'])elements[id]={};
elements['result-series']={replaceChildren(){},appendChild(){}};
elements['chart-result']={id:'chart-result',style:{}};
const document={getElementById:id=>elements[id],createElement:()=>({}),
  querySelectorAll:s=>s==='input[data-filter]'?[input]:[]};
const echarts={init(n){const c={options:[],setOption(o){this.options.push(o);},resize(){},on(){}};charts[n.id]=c;return c;}};
const window={echarts,addEventListener(){}};
const ctx={document,window,echarts,ResizeObserver:class{observe(){}},Map,Set,Math,Array,JSON};
vm.runInNewContext(fs.readFileSync(process.argv[1].replace('portal.js','kz-tokens.js'),'utf8'),ctx);
const theme=window.KZ_TOKENS.charts;
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const option=()=>charts['chart-result'].options.at(-1);
assert.deepEqual(Array.from(option().color),Array.from(theme.categorical));
const axes=x=>Array.isArray(x)?x:[x];
for(const axis of axes(option().yAxis)){
  assert.equal(axis.axisLabel.color,theme.label);
  assert.equal(axis.splitLine.lineStyle.color,theme.grid);
  assert.equal(axis.axisLine.lineStyle.color,theme.axis);
}
assert.equal(option().legend instanceof Array,SERIES_COUNT>5);
const plotted=option().series.flatMap(s=>s.data.filter(p=>p.fact_id).map(p=>p.fact_id)).sort();
assert.equal(JSON.stringify(plotted),JSON.stringify(points.map(p=>p.fact_id).sort()));
assert.equal(JSON.stringify(points),original);
if(SERIES_COUNT>5){
  assert.equal(option().grid.length,2);
  assert.equal(new Set(option().series.map(s=>s.xAxisIndex)).size,2);
  assert.equal(option().yAxis[0].min,option().yAxis[1].min);
  assert.equal(option().yAxis[0].max,option().yAxis[1].max);
  assert.equal(option().yAxis[0].min,-20);assert.equal(option().yAxis[0].max,0);
  assert.ok(option().series.every(s=>s.endLabel.show&&s.data.every(p=>!p.label?.show)));
}
const before=option().series.at(-1).lineStyle.color;
input.value='s'+(SERIES_COUNT-1);events.input();
assert.equal(option().series[0].lineStyle.color,before);
assert.equal(option().series[0].name,String(SERIES_COUNT));
assert.equal(option().series[0].data.filter(p=>p.fact_id).length,2);
input.value='';events.input();
assert.equal(option().series.length,SERIES_COUNT);
assert.equal(JSON.stringify(points),original);
