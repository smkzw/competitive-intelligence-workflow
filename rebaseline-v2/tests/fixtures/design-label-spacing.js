const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const labels=Array.from({length:20},(_,i)=>'NCT'+i);
const identities=labels.map((id,i)=>({registry_id:id,axis_label:i<2?'Long complete intervention label '+('component '.repeat(12))+i:'Short '+i,label:'Original '+i}));
const values=labels.map((_,i)=>i===0?0:i);
const rows=labels.map((id,i)=>({dataset:{trial:id,phase:'II',phaseStatus:'verified'},style:{},textContent:i<2?'long':'short'}));
const elements={charts:{textContent:JSON.stringify({size:{labels,values,identities}})},'tbl-c':{id:'tbl-c',querySelectorAll:()=>rows}};
const options=[];elements['chart-size']={id:'chart-size',style:{},closest:()=>({hidden:false})};
let input;
const filter={value:'',getAttribute:()=>'tbl-c',addEventListener:(_,fn)=>input=fn};
const document={getElementById:id=>elements[id],querySelectorAll:s=>s==='input[data-filter]'?[filter]:[]};
const echarts={graphic:{Text:class{constructor(o){this.text=o.style.text;}getBoundingRect(){return{height:this.text.length>80?110:22};}}},init(){return{setOption:o=>options.push(o),resize(){},dispose(){}};}};
vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,ResizeObserver:class{observe(){}},Map,Set});
function check(long){
 const o=options.at(-1),h=parseInt(elements['chart-size'].style.height);
 const shown=o.dataZoom[0].endValue-o.dataZoom[0].startValue+1;
 const row=(h-o.grid.top-o.grid.bottom)/shown;
 assert.ok(row>=(long?110:22)+8,'visible axis labels need their measured height plus separation');
 return o;
}
let o=check(true);assert.equal(JSON.stringify(o.series[0].data),JSON.stringify(values));assert.equal(o.series[0].data[0],0);
assert.equal(o.yAxis.axisLabel.formatter(labels[0]),identities[0].axis_label);
filter.value='short';input();o=check(false);assert.equal(o.series[0].data.length,18);
filter.value='long';input();o=check(true);assert.equal(o.series[0].data.length,2);
filter.value='';input();o=check(true);assert.equal(o.series[0].data.length,20);
