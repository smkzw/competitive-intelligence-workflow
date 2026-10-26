const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const events={},elements={},charts={},fold={open:false};let focused;
const rows=[['fa','clinical','common first'],['fb','clinical','common second'],['fu','unresolved','common unknown']].map(
  ([id,domain,text])=>({dataset:{factId:id,domain},style:{},textContent:text,
    closest:()=>fold,focus(){focused=id;},scrollIntoView(){}}));
const groups=['a','b'].map((id,i)=>({id,kind:'bar',title:id==='a'?'绝对变化':'百分比变化',points:[
  {fact_id:'f'+id,series_key:id,series_name:id,value:i===0?0:2}]}));
const original=JSON.stringify(groups);
elements.charts={textContent:JSON.stringify({groups})};
elements['tbl-b']={id:'tbl-b',querySelectorAll:()=>rows};
const selector={value:'a',options:[{value:'a'},{value:'b'}],querySelectorAll(){return this.options;},
  addEventListener:(_,f)=>events.group=f};elements['result-group']=selector;
const scope={value:'metric',addEventListener:(_,f)=>events.scope=f};elements['result-table-scope']=scope;
const query={value:'',getAttribute:()=>'tbl-b',addEventListener:(_,f)=>events.query=f};elements['result-query']=query;
const domain={value:'all',addEventListener:(_,f)=>events.domain=f};elements['result-domain']=domain;
for(const id of ['result-count','result-panel','result-empty','result-definition','result-unit',
  'result-table-count','result-table-title'])elements[id]={};
elements['result-series']={replaceChildren(){},appendChild(){}};
elements['chart-result']={id:'chart-result',style:{}};
const document={getElementById:id=>elements[id],createElement:()=>({}),
  querySelectorAll:s=>s==='input[data-filter]'?[query]:[]};
const echarts={init(n){const c={options:[],handlers:{},setOption(o){this.options.push(o);},resize(){},
  on(k,f){this.handlers[k]=f;}};charts[n.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,
  ResizeObserver:class{observe(){}},Map,Set,Math,Array,JSON});
const visible=()=>rows.filter(r=>r.style.display!=='none').map(r=>r.dataset.factId).join(',');
const current=()=>charts['chart-result'].options.at(-1).series[0].data[0];
assert.equal(visible(),'fa');assert.equal(current().fact_id,'fa');assert.equal(current().value,0);
assert.equal(elements['result-table-count'].textContent,'1');
assert.equal(elements['result-table-title'].textContent,'当前指标完整数据表');
assert.equal(elements['result-count'].textContent,'3 / 3 条结果 · 2 组');
scope.value='all';events.scope();assert.equal(visible(),'fa,fb,fu');assert.equal(current().fact_id,'fa');
assert.equal(elements['result-table-count'].textContent,'3');
selector.value='b';events.group.call(selector);assert.equal(visible(),'fa,fb,fu');assert.equal(current().fact_id,'fb');
scope.value='metric';events.scope();assert.equal(visible(),'fb');assert.equal(selector.value,'b');
query.value='first';events.query();assert.equal(visible(),'fa');assert.equal(selector.value,'a');
query.value='';events.query();assert.equal(visible(),'fb');assert.equal(selector.value,'b');
domain.value='unresolved';events.domain();assert.equal(visible(),'fu');
assert.ok(elements['result-panel'].hidden);assert.equal(elements['result-table-count'].textContent,'1');
assert.equal(elements['result-table-title'].textContent,'匹配结果完整数据表');
domain.value='clinical';events.domain();assert.equal(visible(),'fb');
charts['chart-result'].handlers.click({data:{fact_id:'fb'}});assert.ok(fold.open);assert.equal(focused,'fb');
scope.value='all';events.scope();assert.equal(visible(),'fa,fb');
domain.value='all';events.domain();assert.equal(visible(),'fa,fb,fu');
assert.equal(rows.length,3);assert.equal(JSON.stringify(groups),original);
