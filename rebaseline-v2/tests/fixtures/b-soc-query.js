const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const events={},elements={},charts={};
const spec=[['fc','clinical','A','EASI',1],['fa','safety','A','Infections and infestations',6],
 ['fb','safety','B','Infections and infestations',9],['fu','safety','A','Infections and infestations',null],
 ['fx','safety','B','Gastrointestinal disorders',0]];
const rows=spec.map(([id,domain,study,text])=>({dataset:{factId:id,domain,studyId:study,searchText:text},style:{},textContent:'different main text'}));
const safety=spec.filter(s=>s[1]==='safety').map(([id,,study,text])=>({dataset:{factId:id,studyId:study},style:{},textContent:text}));
const catalog=['A','B','empty'].map(id=>({dataset:{studyId:id},style:{}}));
const groups=[{id:'clinical',domain:'clinical',kind:'bar',points:[{fact_id:'fc',value:1,series_key:'fc'}]},
 {id:'safety',domain:'safety',kind:'bar',points:spec.filter(s=>s[1]==='safety'&&s[4]!=null).map(s=>({fact_id:s[0],value:s[4],series_key:s[0]}))}];
elements.charts={textContent:JSON.stringify({groups})};
elements['tbl-b']={id:'tbl-b',querySelectorAll:()=>rows};elements['tbl-b-safety']={querySelectorAll:()=>safety};elements['tbl-b-studies']={querySelectorAll:()=>catalog};
const group={value:'clinical',querySelectorAll:()=>[{value:'clinical'},{value:'safety'}],addEventListener:(_,f)=>events.group=f};elements['result-group']=group;
const study={value:'all',addEventListener:(_,f)=>events.study=f};elements['result-study']=study;
const domain={value:'all',addEventListener:(_,f)=>events.domain=f};elements['result-domain']=domain;
const query={value:'',getAttribute:k=>k==='data-filter'?'tbl-b':'tbl-b-safety',addEventListener:(_,f)=>events.query=f};elements['result-query']=query;
const scope={value:'all',addEventListener:(_,f)=>events.scope=f};elements['result-table-scope']=scope;
for(const id of ['result-count','result-panel','result-empty','result-definition','result-unit','result-table-count','result-table-title','study-catalog-count','safety-count'])elements[id]={};
elements['result-series']={replaceChildren(){},appendChild(){}};elements['chart-result']={id:'chart-result',style:{}};
const document={getElementById:id=>elements[id],createElement:()=>({}),querySelectorAll:s=>s==='input[data-filter]'?[query]:[]};
const echarts={init(n){const c={setOption(o){this.option=o;},resize(){},on(){}};charts[n.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,ResizeObserver:class{observe(){}},Map,Set,Math,Array,JSON});
const visible=rs=>rs.filter(r=>r.style.display!=='none').map(r=>r.dataset.factId).join(',');
query.value='Infections and infestations';events.query();
assert.equal(visible(rows),'fa,fb,fu');assert.equal(visible(safety),'fa,fb,fu');
assert.equal(elements['result-count'].textContent,'3 / 5 条结果 · 1 组');assert.ok(!elements['result-panel'].hidden);
assert.deepEqual(charts['chart-result'].option.series[0].data.map(p=>p.fact_id),['fa','fb']);
study.value='B';events.study();assert.equal(visible(rows),'fb');assert.equal(visible(safety),'fb');
domain.value='clinical';events.domain();assert.equal(visible(rows),'');assert.equal(visible(safety),'');assert.ok(elements['result-panel'].hidden);
domain.value='all';events.domain();study.value='all';events.study();scope.value='metric';events.scope();
assert.equal(visible(rows),'fa,fb');assert.equal(visible(safety),'fa,fb,fu');
query.value='absent SOC';events.query();assert.equal(visible(rows),'');assert.equal(visible(safety),'');
assert.ok(elements['result-panel'].hidden);assert.equal(safety.length,4);assert.equal(rows.length,5);
