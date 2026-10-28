import json
import subprocess
from pathlib import Path


def test_explicit_embedded_reader_deduplicates_navigation_but_preserves_cutoff():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),result=[];
for(const embedded of [false,true]){
 const out=[],meta={textContent:'数据截至 2026-10-27'},status={},heading={
 querySelector:()=>status,insertBefore:(node,before)=>out.push([node.textContent,before===status])};
 const window={CIW:{},name:embedded?'ciw-report':'',self:{},top:{},addEventListener(){}};
 const document={getElementById:()=>null,addEventListener(){},
 querySelector:sel=>sel==='.page-heading'?heading:meta,
 documentElement:{classList:{add:name=>out.push(name)}}};
 vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL});result.push(out);
}process.stdout.write(JSON.stringify(result));
"""
    run = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    standalone, embedded = json.loads(run.stdout)
    assert standalone == []
    assert embedded == [["数据截至 2026-10-27", True], "embedded-reading"]


def test_chart_density_resizes_before_render_and_keeps_all_filtered_data_reachable():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm');
const el={id:'plot',style:{},getClientRects:()=>[{}]},calls=[],listeners={},frames=new Map();let frame=0;
const window={CIW:{},addEventListener:(k,fn)=>listeners[k]=fn,
 visualViewport:{addEventListener:(k,fn)=>listeners['visual-'+k]=fn}};
const document={getElementById:id=>id==='coverage'?null:el,addEventListener(){},querySelectorAll:()=>[el]};
const requestAnimationFrame=fn=>{frames.set(++frame,fn);return frame};
const cancelAnimationFrame=id=>frames.delete(id);
const flush=()=>{for(const fn of frames.values())fn();frames.clear()};
let instance;
const echarts={getInstanceByDom:()=>instance,init(){calls.push(['init',el.style.height]);
 return instance={resize(){calls.push(['resize',el.style.height])},setOption(o,replace){
 calls.push(['draw',el.style.height,o.yAxis.data,o.series[0].data,o.dataZoom,replace,o.yAxis.axisLabel.fontSize]);}}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL,echarts,requestAnimationFrame,cancelAnimationFrame});
const opt=(n,inverse)=>({grid:{top:20,bottom:40},xAxis:{type:'value'},
 yAxis:{type:'category',data:Array.from({length:n},(_,i)=>'study'+i),inverse},
 series:[{type:'bar',data:Array.from({length:n},(_,i)=>i)}]});
for(const [n,inverse] of [[20,true],[2,true],[20,false]])window.U.chart('plot',opt(n,inverse));
window.innerHeight=730;window.U.chart('plot',opt(20,true));
window.innerHeight=900;listeners.resize();flush();
window.innerHeight=730;listeners['visual-resize']();flush();
process.stdout.write(JSON.stringify(calls));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    calls = json.loads(result.stdout)
    assert calls[0] == ["init", "340px"]
    assert [c for c in calls if c[0] == "resize"] == [
        ["resize", "144px"], ["resize", "340px"], ["resize", "228px"],
        ["resize", "340px"], ["resize", "228px"]]
    dense, sparse, restored, short, tall_again, short_again = [c for c in calls if c[0] == "draw"]
    assert dense[2] == [f"study{i}" for i in range(20)]
    assert dense[3] == list(range(20))  # first zero and last study are retained, not truncated
    assert dense[4][0]["startValue"] == 0 and dense[4][0]["endValue"] == 9
    assert sparse[2:5] == [["study0", "study1"], [0, 1], None]
    assert restored[4][0]["startValue"] == 10 and restored[4][0]["endValue"] == 19
    assert short[4][0]["startValue"] == 0 and short[4][0]["endValue"] == 5
    assert tall_again[4][0]["endValue"] == 9 and short_again[4][0]["endValue"] == 5
    assert all(c[5] is True and c[6] == 16 for c in (dense, sparse, restored, short))
    for c in (dense, restored, short):
        zoom = c[4][0]
        assert zoom["zoomLock"] and not zoom["brushSelect"]
        assert zoom["minValueSpan"] == zoom["maxValueSpan"] == zoom["endValue"] - zoom["startValue"]


def test_production_links_and_highlight_use_safe_original_text():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm');
const window={CIW:{},addEventListener(){}};
const document={getElementById(){return null},addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL});
const u=window.U;
process.stdout.write(JSON.stringify({
  safe:u.src('https://example.com/?a=1&b=2','source'),
  unsafe:['javascript:alert(1)','data:text/html,<script>1</script>','file:///private','//example.com/']
    .map(url=>u.src(url,'<value>')),
  original:u.highlight('NPS < 5 & ≥2','< 5'),
  entity:u.highlight('NPS < 5 & ≥2','amp'),
  markup:u.highlight('<script>','<script>')
}));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    out = json.loads(result.stdout)
    assert 'href="https://example.com/?a=1&amp;b=2"' in out["safe"]
    assert out["unsafe"] == ["&lt;value&gt;"] * 4
    assert out["original"] == "NPS <mark>&lt; 5</mark> &amp; ≥2"
    assert out["entity"] == "NPS &lt; 5 &amp; ≥2"
    assert out["markup"] == "<mark>&lt;script&gt;</mark>"


def test_table_controls_do_not_also_activate_their_parent_row():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm');
const window={CIW:{},addEventListener(){}};
const document={getElementById(){return null},addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL});
const tr={dataset:{ri:'0'}};
const el={querySelectorAll(selector){return selector==='th'?[]:[tr]}};
let opened=0;
window.U.table(el,[{key:'label',label:'label'}],[{label:'x'}],{onRow(){opened++}});
tr.onclick({target:{closest(){return {tagName:'SUMMARY'}}}});
const afterControl=opened;
tr.onclick({target:{closest(){return null}}});
process.stdout.write(JSON.stringify({afterControl,afterRow:opened}));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {"afterControl": 0, "afterRow": 1}


def test_hidden_chart_is_initialized_only_when_shown_and_resized_on_reuse():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm');
let visible=false,created=0,resized=0,instance=null;
const el={getClientRects(){return visible?[{}]:[]}};
const window={CIW:{},addEventListener(){}};
const document={getElementById(id){return id==='coverage'?null:el},addEventListener(){}};
const echarts={getInstanceByDom(){return instance},
  init(){created++;return instance={setOption(){},resize(){resized++}}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL,echarts});
window.U.chart('value-chart',{});
const hiddenCreated=created;
visible=true;window.U.chart('value-chart',{});window.U.chart('value-chart',{});
process.stdout.write(JSON.stringify({hiddenCreated,created,resized}));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {"hiddenCreated": 0, "created": 1, "resized": 1}


def test_unconfirmed_events_are_retained_in_release_but_not_presented_as_adopted_milestones():
    from ciw.render.site import _payload
    events = [{"event_id": str(i), "status": s} for i, s in enumerate(
        ["registry", "verified", "dual_agreed", "arbitrated", "needs_review", "rejected"])]
    rel = dict(indication={}, cutoff="2026-10-27", release_id="r", generated_at="now", own_product_id=None,
               coverage=[], a={}, trials=[], stats={}, events=events, sources=[])
    view = _payload(rel, 'A')
    assert [e['status'] for e in view['events']] == ['registry','verified','dual_agreed','arbitrated']
    assert len(rel['events']) == 6 and rel['events'][4]['status'] == 'needs_review'


def test_design_filter_updates_both_charts_and_omits_empty_plot_frames():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/c.js"
    script = r"""
const fs=require('fs'),vm=require('vm');
const inputs={q:{value:''},'f-phase':{value:''},'f-mask':{value:''},'f-concept':{value:''},'f-china':{checked:false}};
for(const e of Object.values(inputs))e.addEventListener=(name,fn)=>e.change=fn;
const els={...inputs,matrix:{addEventListener(){}},count:{},'concept-chart':{parentElement:{},style:{}},
 'size-chart':{parentElement:{},style:{}},'concept-data':{id:'concept'},'size-data':{id:'size'},'size-data-label':{}};
const rows=[{trial_id:'zero',phase:'II',primary_concepts:['NPS'],start:'2026-01-01',enrollment:0,
 products:[],primary:[],title:'',eligibility:''},
 {trial_id:'unknown',phase:'III',primary_concepts:['NCS'],start:'2026-01-02',enrollment:null,products:[],primary:[],title:'',eligibility:''}];
const plots={},out=[],tables={};
const window={U:{D:{c:{rows}},esc:s=>s,OWN:'orange',PAL:['teal'],options(){},table(el,cols,rows){tables[el.id]=rows;},
 chart(id,opt){plots[id]=opt;}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document:{getElementById:id=>els[id]}});
function read(){return {count:els.count.textContent,concepts:plots['concept-chart'].yAxis.data,
 points:plots['size-chart'].series.flatMap(s=>s.data).map(p=>p.value),
 conceptHidden:!!els['concept-chart'].parentElement.hidden,sizeHidden:!!els['size-chart'].hidden,
 tableCount:tables.size.length,tableEnrollment:tables.size.map(r=>r.enrollment)};}
out.push(read());for(const q of ['zero','unknown','absent','']){inputs.q.value=q;inputs.q.change();out.push(read());}
process.stdout.write(JSON.stringify(out));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    initial, zero, unknown, absent, restored = json.loads(result.stdout)
    assert set(initial["concepts"]) == {"NPS", "NCS"}
    assert zero["concepts"] == ["NPS"] and zero["points"] == [["2026-01-01", 0]]
    assert zero["tableCount"] == 1 and zero["tableEnrollment"] == [0]
    assert unknown["concepts"] == ["NCS"] and unknown["sizeHidden"]
    assert absent["conceptHidden"] and absent["sizeHidden"] and absent["count"].startswith("0 /")
    assert restored == initial


def test_result_context_switch_updates_chart_and_tables_together():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/b.js"
    script = r"""
const fs=require('fs'),vm=require('vm');
const elements=new Proxy({}, {get:(all,id)=>all[id]||(all[id]={id,value:'',checked:false,style:{},
 querySelectorAll:()=>[],addEventListener(){}})});
const row=v=>({result_id:'r'+v,value:v,role:'experimental',acronym:'Trial',group_title:'Drug',product_label:'Drug'});
const frames=[{frame_id:'first',trial_ids:['one'],title:'First definition',population:'All participants',
 rows:[row(25)],comparisons:[],source_statistics:[{value:10.3,ci_lower:5.7,ci_upper:14.9,
 param_type:'Adjusted Difference',group_labels:['A','B'],acronym:'Trial',url:'https://example.test'}]},
 {frame_id:'second',trial_ids:['two'],title:'Other definition',
 population:'Responders',rows:[row(10)],comparisons:[]}];
const q={question_id:'q',label:'临床缓解',time_label:'第52周',units:['%'],measure_label:'比例',
 trial_ids:['one','two'],rows:[row(25),row(10)],comparisons:[],frames};
const plots={},tables={},tableOptions={},drawers=[];
const observations=[25,10].map(v=>({result_id:'r'+v,products:['Drug'],acronym:'Trial',
 groups:[],analyses:[],title:'Source '+v}));
const window={U:{D:{b:{questions:[q],longitudinal:[],safety:[],observations},stats:{},trials:{}},
 esc:s=>s||'',num:s=>s,nN(){},tag(){},src(){},options(){},OWN:'orange',PAL:[],
 drawer:html=>drawers.push(html),chart:(id,opt)=>plots[id]=opt,
 table:(el,cols,rows,opts)=>{tables[el.id]=rows;tableOptions[el.id]=opts}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document:{getElementById:id=>elements[id]}});
const read=()=>({values:plots['value-chart'].series[0].data.map(d=>d.value),
 table:tables['row-table'].map(d=>d.value),context:elements['frame-context-text'].textContent,
 rawValues:plots['source-stat-chart']?.series[1].data.map(d=>d.value),rawHidden:elements['source-statistics'].hidden});
const first=read();tableOptions['row-table'].onRow(tables['row-table'][0]);
elements['frame-select'].value='second';elements['frame-select'].onchange();
tableOptions['row-table'].onRow(tables['row-table'][0]);
process.stdout.write(JSON.stringify([first,{...read(),drawers}]));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    first, second = json.loads(result.stdout)
    assert first["values"] == first["table"] == [25]
    assert second["values"] == second["table"] == [10]
    assert "Responders" in second["context"] and "All participants" in first["context"]
    assert first["rawValues"] == [10.3] and not first["rawHidden"] and second["rawHidden"]
    assert "Source 25" in second["drawers"][0] and "Source 10" in second["drawers"][1]


def test_numeric_search_does_not_match_other_weeks_and_tolerates_source_punctuation():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm');
const window={CIW:{},addEventListener(){}};
const document={getElementById:()=>null,addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL});
const match=window.U.matchesSearch;
process.stdout.write(JSON.stringify([
 match('GPPGA at Week 1','at week 1'),match('GPPGA at Week 12','at week 1'),
 match('GPPGA at Week 16','at week 1'),match('GPPGA at Week 128','week 12'),
 match('(GPPGA) Pustulation Sub-score at Week 1','gppga pustulation subscore'),
 match('Week 1.5','week 1'),match('Week 1.5','week 1.5'),
 match('GPPGA at Week1','week 1'),match('登记 NCT03782792','NCT03782792'),
 match('GPPGA ≥ 2','GPPGA < 2'),match('GPPGA ≥ 2','GPPGA ≥ 2'),
 match('At Week 1.','week 1'),match('At Week 1.5.','week 1.5')
]));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == [True,False,False,False,True,False,True,True,True,False,True,True,True]


def test_table_nested_in_details_still_opens_but_its_own_controls_do_not():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),outer={tagName:'DETAILS'},inside={tagName:'DETAILS'};
const tr={dataset:{ri:'0'},contains:node=>node===inside,focus(){}};
const window={CIW:{},addEventListener(){}};
const document={getElementById:()=>null,addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL});
let opened=0;
window.U.table({querySelectorAll:s=>s==='th'?[]:[tr]},[{label:'value',key:'value'}],[{value:0}],{onRow(){opened++}});
tr.onclick({target:{closest:()=>outer}});const first=opened;
tr.onclick({target:{closest:()=>inside}});
tr.onkeydown({target:tr,key:'Enter',preventDefault(){}});
process.stdout.write(JSON.stringify([first,opened]));
"""
    run = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    assert json.loads(run.stdout) == [1, 2]


def test_question_search_uses_actual_slice_not_other_weeks_in_source_title():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),window={CIW:{},addEventListener(){}};
const document={getElementById:()=>null,addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL});
const q={label:'DLQI评分',time_label:'第16周',measure_label:'均值',time_key:'W16',
 frames:[{title:'Change in DLQI at Week 1, Week 4, and Week 16',population:'All participants'}]};
const m=window.U.matchesQuestion;
process.stdout.write(JSON.stringify([m(q,'week 1'),m(q,'week 16'),m(q,'第1周'),m(q,'DLQI'),
 m({...q,time_key:'W1'},'week 1'),m({...q,time_key:'W1.5'},'week 1'),m(q,'week 1.5'),
 m(q,'Week 1, Week 4, and Week 16'),
 m({...q,frames:[{title:'DLQI at Weeks 1-16'}]},'Weeks 1-16'),
 m({...q,frames:[{title:'DLQI at Week 1 to Week 16'}]},'Week 1 to Week 16'),
 m({...q,frames:[{title:'DLQI at Weeks 1, 4, and 16'}]},'Weeks 1, 4, and 16')]));
"""
    run = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    assert json.loads(run.stdout) == [False, True, False, True, True, False, False, True, True, True, True]


def test_family_search_and_chart_selection_use_the_matching_frame_with_complete_study_table():
    assets = Path(__file__).resolve().parents[1] / "src/ciw/render/static"
    script = r"""
const fs=require('fs'),vm=require('vm'),helper={CIW:{},addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window:helper,URL,
 document:{getElementById:()=>null,addEventListener(){}}});
const els=new Proxy({}, {get:(all,id)=>all[id]||(all[id]={id,value:'',checked:false,
 querySelectorAll:()=>[],addEventListener(){}})});
els.qsearch.value='week 1';
const obs=[1,16].map(n=>({result_id:'r'+n,title:'Remission',products:['Drug'+n],phase:'III',acronym:'T'+n,
 unit:n===1?'Percent':'Proportion',groups:[{group_id:'g',title:'Drug'+n,value:n}],analyses:[]}));
const frames=[16,1].map(n=>({frame_id:'f'+n,time_key:'W'+n,time_label:'第'+n+'周',measure_label:'比例',
 units:[n===1?'Percent':'Proportion'],trial_ids:['T'+n],result_ids:['r'+n],population:'All participants',
 title:'Remission at Week 1, Week 16',rows:[{result_id:'r'+n,value:n,acronym:'T'+n,group_title:'Drug'+n}],
 comparisons:[],source_statistics:[]}));
obs.push({...obs[1],result_id:'shared16',groups:[{group_id:'g',title:'Group16',value:16}]});
frames[0].result_ids.push('shared16');
frames[0].rows[0].product_label='Drug16';frames[0].rows[0].group_title='Group16';frames[0].rows[0].phase='III';
frames[0].rows[0].source_records=[{acronym:'T16',phase:'III'},{acronym:'T1',phase:'III'}];
const q={question_id:'family',is_family:true,label:'临床缓解',time_key:'',time_label:'',units:[],
 measure_label:'比例',trial_ids:['T1','T16'],frames};
const plots={},tables={},opts={},cols={},window={U:{D:{b:{questions:[q],longitudinal:[],safety:[],observations:obs}},
 esc:s=>s||'',num:v=>v,nN(){},tag(){},src:(url,label)=>label,options(){},OWN:'orange',PAL:[],
 matchesQuestion:helper.U.matchesQuestion,table:(e,c,r,o)=>{tables[e.id]=r;opts[e.id]=o;cols[e.id]=c},
 chart:(id,o)=>plots[id]=o,drawer(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),{window,document:{getElementById:id=>els[id]}});
const first={values:plots['value-chart'].series[0].data.map(r=>r.value),title:els['q-title'].textContent,
 sub:els['q-sub'].textContent,all:tables['family-table'].map(r=>r.value),count:els['family-count'].textContent};
els['frame-select'].value='f16';els['frame-select'].onchange();
const second={values:plots['value-chart'].series[0].data.map(r=>r.value),sub:els['q-sub'].textContent};
els.qsearch.value='week 1';els.qsearch.oninput();
const live=plots['value-chart'].series[0].data.map(r=>r.value);
const firstCell=cols['family-table'][0].html(tables['family-table'][0]);
process.stdout.write(JSON.stringify({first,second,live,firstCell,hidden:els['family-overview'].hidden,
 mismatch:helper.U.matchesQuestion({...q,frames:[frames[0]]},'week 1')}));
"""
    run = subprocess.run(["node", "-e", script, str(assets / "common.js"), str(assets / "b.js")],
                         capture_output=True, text=True, check=True)
    result = json.loads(run.stdout)
    assert result["first"]["values"] == [1] and "Percent" in result["first"]["sub"]
    assert result["first"]["all"] == [16, 1] and "2 项研究" in result["first"]["count"]
    assert result["second"]["values"] == [16] and "Proportion" in result["second"]["sub"]
    assert not result["hidden"] and not result["mismatch"]
    assert result["live"] == [1]
    assert result["firstCell"].index("Drug16") < result["firstCell"].index("III") < result["firstCell"].index("T16")
