const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={},charts={};const windowText='Initial treatment: baseline to Week 16; maintenance: Week 16 to Week 48.';
const points=Array.from({length:6},(_,i)=>({fact_id:'f'+i,value:i,series_key:'s'+i,axis_label:'原文组别 '+i,visit:windowText,visit_short:''}));
elements.charts={textContent:JSON.stringify({groups:[{id:'g',kind:'bar',title:'原事件',subtitle:windowText,
 unit_label:'受试者人数',stat_label:'受试者人数',points}]})};
const rows=points.map(p=>({dataset:{factId:p.fact_id,domain:'safety'},style:{},textContent:'原文组别'}));
elements['tbl-b']={querySelectorAll:()=>rows};elements['result-group']={value:'g',querySelectorAll:()=>[{value:'g'}],addEventListener(){}};
for(const id of ['result-panel','result-empty','result-count','result-definition','result-unit'])elements[id]={};
elements['result-series']={replaceChildren(){},appendChild(){}};elements['chart-result']={id:'chart-result',style:{}};
const document={getElementById:id=>elements[id],querySelectorAll:()=>[],createElement:()=>({})};
const echarts={init(n){const c={setOption(o){this.option=o;},resize(){},on(){}};charts[n.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,ResizeObserver:class{observe(){}},Map,Set,Math,Array,JSON});
const option=charts['chart-result'].option;
assert.equal(option.dataZoom[0].show,false);assert.equal(option.dataZoom[0].endValue,5);
assert.ok(option.yAxis.data.every(s=>!s.includes(windowText)));
assert.ok(elements['result-definition'].textContent.includes(windowText));
assert.equal(elements['result-unit'].textContent,'受试者人数');
assert.equal(option.series[0].data.length,6);assert.equal(option.series[0].data[0].value,0);
assert.ok(option.tooltip.formatter({data:points[0]}).includes(windowText));
