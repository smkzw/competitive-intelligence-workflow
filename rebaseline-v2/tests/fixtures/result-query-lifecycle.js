const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const events={},charts={},tableDetails={open:false};let initCount=0,observerCount=0,focusCount=0;
const rows=['first','other','last'].map((text,i)=>({dataset:{factId:'f'+i},style:{},textContent:text,
  closest:()=>tableDetails,focus(){focusCount++;},scrollIntoView(){}}));
const a={id:'a',title:'Clinical score <script>',population:'ITT',unit:'points',stat_type:'mean',
  kind:'line',display_axis:'weeks',axis_unit:'days',positions:[28,56,84],points:[
    {fact_id:'f0',series_key:'s1',series_name:'<img src=x>',x:28,value:0,visit:'第4周',trial:'NCT01',
      arm_label:'队列1（7–11岁）',dispersion_text:'SD 0'},
    {fact_id:'f2',series_key:'s1',series_name:'<img src=x>',x:84,value:8,visit:'第12周',trial:'NCT01'}]};
const b={id:'b',title:'Separate endpoint',kind:'bar',points:[
  {fact_id:'f1',series_key:'s2',series_name:'Other',axis_label:'奈莫利珠单抗 · II 期',x:null,value:3,
    visit:'Pre-dose at Weeks 4, 8, 12, 16, 32 and 52',trial:'NCT02'}]};
const select={value:'a',disabled:false,options:[{value:'a'},{value:'b'}],
  querySelectorAll(){return this.options;},addEventListener(k,fn){events['select:'+k]=fn;}};
const input={value:'',getAttribute:()=>'tbl-b',addEventListener(k,fn){events['input:'+k]=fn;}};
const table={id:'tbl-b',querySelectorAll:()=>rows};
const elements={charts:{textContent:JSON.stringify({groups:[a,b]})},'result-group':select,'result-query':input,'tbl-b':table,
  'result-panel':{hidden:false},'result-empty':{hidden:true},'result-count':{},'result-definition':{},
  'result-series':{items:[],replaceChildren(){this.items=[];},appendChild(n){this.items.push(n);}},
  'chart-result':{id:'chart-result',style:{}}};
elements['result-study-reference']={};
elements['result-study-list']={items:[],replaceChildren(){this.items=[];},appendChild(n){this.items.push(n);}};
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
assert.equal(option.animation,false); // A clinical value never travels through invented intermediate values.
assert.equal(option.series[0].type,'line');assert.equal(option.series[0].connectNulls,false);
assert.equal(option.series[0].endLabel.formatter,'组1：8');
assert.equal(JSON.stringify(option.series[0].data.map(p=>p.value)),JSON.stringify([[4,0],[8,null],[12,8]]));
assert.equal(option.series[0].data[0].x,28);
assert.ok(option.tooltip.formatter({data:option.series[0].data[0]}).includes('&lt;img'));
assert.ok(option.tooltip.formatter({data:option.series[0].data[0]}).includes('SD 0'));
assert.ok(option.legend.formatter('1').includes('队列1（7–11岁）'));
assert.ok(!option.tooltip.formatter({data:option.series[0].data[0]}).includes('<img'));
assert.equal(option.xAxis.name,'周');
assert.ok(option.grid.top>=2*option.textStyle.fontSize); // Reserve actual marker-label space at axis extrema.
assert.ok(elements['result-study-reference'].textContent.includes('NCT01'));
assert.equal(elements['result-study-list'].items.length,1);
input.value='last';events['input:input']();option=c.options.at(-1);
assert.equal(elements['safety-count'].textContent,'0 / 2');assert.ok(safetyRows.every(r=>r.style.display==='none'));
assert.equal(option.series[0].type,'custom');
assert.equal(option.series[0].coordinateSystem,'none');
assert.equal(option.animation,false);
assert.equal(option.xAxis,undefined);assert.equal(option.yAxis,undefined);
assert.equal(option.series[0].renderItem().children[0].style.text,'8');
assert.equal(JSON.stringify(option.series[0].data.map(p=>p.value)),JSON.stringify([8]));
assert.equal(option.series[0].data[0].fact_id,'f2');
assert.ok(parseInt(elements['chart-result'].style.height)<=144);
input.value='none';events['input:input']();
assert.equal(elements['result-panel'].hidden,true);assert.equal(elements['result-empty'].hidden,false);
assert.equal(select.disabled,true);
input.value='';events['input:input']();
select.value='b';events['select:change'].call(select);assert.equal(c.options.at(-1).series[0].type,'custom');
assert.ok(elements['result-study-reference'].textContent.includes('NCT02'));
assert.ok(!elements['result-study-reference'].textContent.includes('NCT01'));
const single=c.options.at(-1).series[0].renderItem().children;
assert.equal(single[0].style.text,'3');
assert.ok(single[1].style.text.includes('奈莫利珠单抗 · II 期'));
assert.ok(single[1].style.text.includes(b.points[0].visit));
assert.ok(!single[1].style.text.includes('NCT02'));
assert.ok(!single[0].style.text.includes('100'));
assert.ok(single[1].style.font.includes('16px'));
assert.ok(c.options.at(-1).tooltip.formatter({data:c.options.at(-1).series[0].data[0]}).includes(b.points[0].visit));
input.value='first';events['input:input']();assert.equal(select.value,'a');
assert.equal(elements['safety-count'].textContent,'1 / 2');assert.equal(safetyRows[0].style.display,'');
input.value='';events['input:input']();assert.equal(select.value,'b');
assert.equal(elements['result-count'].textContent,'3 / 3 条结果 · 2 组');
assert.equal(initCount,1);assert.equal(observerCount,1);
c.events.click({data:{fact_id:'f1'}});assert.equal(tableDetails.open,true);assert.equal(focusCount,1);
assert.equal(JSON.stringify(b.points.map(p=>p.value)),JSON.stringify([3]));
