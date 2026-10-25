from pathlib import Path

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
    run_portal((Path(__file__).parent/'fixtures/result-query-lifecycle.js').read_text())
