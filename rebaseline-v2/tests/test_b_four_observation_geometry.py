from test_portal_js import run_portal


def test_four_long_source_arms_fit_without_suppressing_the_second_study():
    run_portal(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const elements={},charts={};
const labels=['Nemolizumab 30 mg','Placebo','Placebo','Nemolizumab 30 mg'];
const points=labels.map((a,i)=>({fact_id:'f'+i,value:i+1,series_key:'s'+i,
 axis_label:'初始治疗期 · '+a+' · III期 · NCT0398934'+(i<2?'9':'3'),visit:'第16周'}));
const rows=points.map(p=>({dataset:{factId:p.fact_id,domain:'clinical'},textContent:p.axis_label,style:{}}));
elements.charts={textContent:JSON.stringify({groups:[{id:'g',kind:'bar',points}]})};
elements['tbl-b']={querySelectorAll:()=>rows};
elements['result-group']={value:'g',querySelectorAll:()=>[{value:'g'}],addEventListener(){}};
elements['result-series']={replaceChildren(){},appendChild(){}};
elements['chart-result']={id:'chart-result',style:{}};
for(const id of ['result-panel','result-empty','result-count','result-definition'])elements[id]={};
const document={getElementById:id=>elements[id],querySelectorAll:()=>[],createElement:()=>({})};
const echarts={init(n){const c={setOption(o){this.option=o;},on(){},resize(){}};charts[n.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,
 ResizeObserver:class{observe(){}},Map,Set,Math,Array,JSON});
const option=charts['chart-result'].option;
assert.equal(option.series[0].data.length,4);assert.equal(option.dataZoom[0].endValue,3);
assert.equal(option.dataZoom[0].show,false);
''')
