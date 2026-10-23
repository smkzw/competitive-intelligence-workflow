from test_portal_js import run_portal


def test_domain_and_text_query_share_visible_fact_set_without_losing_unplottable_rows():
    run_portal(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const events={},elements={},charts={};
const rows=[['c','clinical','Clinical'],['p','pk','Concentration'],['u','unresolved','Unknown']].map(
  ([id,domain,text])=>({dataset:{factId:id,domain},style:{},textContent:text}));
const domain={value:'clinical',addEventListener:(k,f)=>events.domain=f};
const input={value:'',getAttribute:()=>'tbl-b',addEventListener:(k,f)=>events.input=f};
const selector={value:'c',options:[{value:'c'},{value:'p'}],querySelectorAll(){return this.options;},
  addEventListener:(k,f)=>events.select=f};
elements['tbl-b']={id:'tbl-b',querySelectorAll:()=>rows};
elements['result-domain']=domain;elements['result-query']=input;elements['result-group']=selector;
for(const id of ['result-panel','result-empty','result-count','result-definition','result-unit']) elements[id]={};
elements['result-series']={replaceChildren(){},appendChild(){}};
elements['chart-result']={id:'chart-result',style:{}};
elements.charts={textContent:JSON.stringify({groups:['c','p'].map(id=>({id,kind:'bar',points:[
  {fact_id:id,series_key:id,value:id==='c'?0:2}]}))})};
const document={getElementById:id=>elements[id],createElement:()=>({}),
  querySelectorAll:s=>s==='input[data-filter]'?[input]:[]};
const echarts={init(n){const c={options:[],setOption(o){this.options.push(o);},resize(){},dispose(){},on(){}};
  charts[n.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,
  ResizeObserver:class{observe(){}disconnect(){}},Map,Set,Math,Array,JSON});
const visible=()=>rows.filter(r=>r.style.display!=='none').map(r=>r.dataset.factId).join(',');
assert.equal(visible(),'c');assert.equal(selector.value,'c');
domain.value='pk';events.domain();assert.equal(visible(),'p');assert.equal(selector.value,'p');
input.value='Clinical';events.input();assert.equal(visible(),'');assert.ok(elements['result-panel'].hidden);
domain.value='all';events.domain();assert.equal(visible(),'c');
input.value='';events.input();assert.equal(visible(),'c,p,u');
domain.value='unresolved';events.domain();assert.equal(visible(),'u');assert.ok(elements['result-panel'].hidden);
assert.equal(elements['result-count'].textContent,'1 / 3 条结果 · 0 组');
domain.value='all';events.domain();assert.equal(visible(),'c,p,u');
assert.equal(charts['chart-result'].options.at(-1).series[0].data[0].fact_id,'c');
assert.equal(rows.length,3);
''')


def test_production_result_plot_tracks_query_preserves_gaps_and_reuses_one_chart():
    run_portal(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const events={},charts={},tableDetails={open:false};let initCount=0,observerCount=0,focusCount=0;
const rows=['first','other','last'].map((text,i)=>({dataset:{factId:'f'+i},style:{},textContent:text,
  closest:()=>tableDetails,focus(){focusCount++;},scrollIntoView(){}}));
const a={id:'a',title:'Clinical score <script>',population:'ITT',unit:'points',stat_type:'mean',
  kind:'line',display_axis:'weeks',axis_unit:'days',positions:[28,56,84],points:[
    {fact_id:'f0',series_key:'s1',series_name:'<img src=x>',x:28,value:0,visit:'第4周',trial:'NCT01'},
    {fact_id:'f2',series_key:'s1',series_name:'<img src=x>',x:84,value:8,visit:'第12周',trial:'NCT01'}]};
const b={id:'b',title:'Separate endpoint',kind:'bar',points:[
  {fact_id:'f1',series_key:'s2',series_name:'Other',axis_label:'奈莫利珠单抗 · II 期',x:null,value:3,
    visit:'Pre-dose at Weeks 4, 8, 12, 16, 32 and 52',trial:'NCT02'}]};
const select={value:'a',disabled:false,options:[{value:'a'},{value:'b'}],
  querySelectorAll(){return this.options;},addEventListener(k,fn){events['select:'+k]=fn;}};
const input={value:'',getAttribute:()=>'tbl-b',addEventListener(k,fn){events['input:'+k]=fn;}};
const table={id:'tbl-b',querySelectorAll:()=>rows};
const elements={charts:{textContent:JSON.stringify({groups:[a,b]})},'result-group':select,'tbl-b':table,
  'result-panel':{hidden:false},'result-empty':{hidden:true},'result-count':{},'result-definition':{},
  'result-series':{items:[],replaceChildren(){this.items=[];},appendChild(n){this.items.push(n);}},
  'chart-result':{id:'chart-result',style:{}}};
const safetyRows=['first','other'].map(text=>({textContent:text,style:{}}));
elements['tbl-b-safety']={querySelectorAll:()=>safetyRows};elements['safety-count']={};
input.getAttribute=name=>name==='data-filter-extra'?'tbl-b-safety':'tbl-b';
const document={getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[input]:[],
  createElement(){return {};}};
const echarts={init(node){initCount++;const c={options:[],events:{},resize(){},dispose(){},
  setOption(o){this.options.push(o);},on(k,fn){assert.ok(!this.events[k]);this.events[k]=fn;}};charts[node.id]=c;return c;}};
const window={echarts,addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window,echarts,ResizeObserver:class{
  observe(){observerCount++;}disconnect(){}},Map,Set,Math,Array,JSON});
const c=charts['chart-result'];let option=c.options.at(-1);
assert.equal(option.series[0].type,'line');assert.equal(option.series[0].connectNulls,false);
assert.equal(JSON.stringify(option.series[0].data.map(p=>p.value)),JSON.stringify([[4,0],[8,null],[12,8]]));
assert.equal(option.series[0].data[0].x,28);
assert.ok(option.tooltip.formatter({data:option.series[0].data[0]}).includes('&lt;img'));
assert.ok(!option.tooltip.formatter({data:option.series[0].data[0]}).includes('<img'));
assert.equal(option.xAxis.name,'周');
input.value='last';events['input:input']();option=c.options.at(-1);
assert.equal(elements['safety-count'].textContent,'0 / 2');assert.ok(safetyRows.every(r=>r.style.display==='none'));
assert.equal(option.series[0].type,'bar');
assert.equal(option.xAxis.scale,false);
assert.equal(JSON.stringify(option.series[0].data.map(p=>p.value)),JSON.stringify([8]));
assert.equal(option.series[0].data[0].fact_id,'f2');
assert.ok(parseInt(elements['chart-result'].style.height)<=144);
input.value='none';events['input:input']();
assert.equal(elements['result-panel'].hidden,true);assert.equal(elements['result-empty'].hidden,false);
assert.equal(select.disabled,true);
input.value='';events['input:input']();
select.value='b';events['select:change'].call(select);assert.equal(c.options.at(-1).series[0].type,'bar');
assert.ok(c.options.at(-1).yAxis.data[0].includes('奈莫利珠单抗 · II 期'));
assert.ok(!c.options.at(-1).yAxis.data[0].includes('NCT02'));
assert.ok(c.options.at(-1).tooltip.formatter({data:c.options.at(-1).series[0].data[0]}).includes(b.points[0].visit));
input.value='first';events['input:input']();assert.equal(select.value,'a');
assert.equal(elements['safety-count'].textContent,'1 / 2');assert.equal(safetyRows[0].style.display,'');
input.value='';events['input:input']();assert.equal(select.value,'b');
assert.equal(elements['result-count'].textContent,'3 / 3 条结果 · 2 组');
assert.equal(initCount,1);assert.equal(observerCount,1);
c.events.click({data:{fact_id:'f1'}});assert.equal(tableDetails.open,true);assert.equal(focusCount,1);
assert.equal(JSON.stringify(b.points.map(p=>p.value)),JSON.stringify([3]));
''')
