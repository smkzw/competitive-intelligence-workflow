import json
import subprocess
from pathlib import Path


def test_chart_density_resizes_before_render_and_keeps_all_filtered_data_reachable():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/common.js"
    script = r"""
const fs=require('fs'),vm=require('vm');
const el={style:{},getClientRects:()=>[{}]},calls=[];
const window={CIW:{},addEventListener(){}};
const document={getElementById:id=>id==='coverage'?null:el,addEventListener(){}};
let instance;
const echarts={getInstanceByDom:()=>instance,init(){calls.push(['init',el.style.height]);
 return instance={resize(){calls.push(['resize',el.style.height])},setOption(o,replace){
 calls.push(['draw',el.style.height,o.yAxis.data,o.series[0].data,o.dataZoom,replace,o.yAxis.axisLabel.fontSize]);}}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL,echarts});
const opt=(n,inverse)=>({grid:{top:20,bottom:40},xAxis:{type:'value'},
 yAxis:{type:'category',data:Array.from({length:n},(_,i)=>'study'+i),inverse},
 series:[{type:'bar',data:Array.from({length:n},(_,i)=>i)}]});
for(const [n,inverse] of [[20,true],[2,true],[20,false]])window.U.chart('plot',opt(n,inverse));
window.innerHeight=730;window.U.chart('plot',opt(20,true));
process.stdout.write(JSON.stringify(calls));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    calls = json.loads(result.stdout)
    assert calls[0] == ["init", "340px"]
    assert [c for c in calls if c[0] == "resize"] == [
        ["resize", "144px"], ["resize", "340px"], ["resize", "228px"]]
    dense, sparse, restored, short = [c for c in calls if c[0] == "draw"]
    assert dense[2] == [f"study{i}" for i in range(20)]
    assert dense[3] == list(range(20))  # first zero and last study are retained, not truncated
    assert dense[4][0]["startValue"] == 0 and dense[4][0]["endValue"] == 9
    assert sparse[2:5] == [["study0", "study1"], [0, 1], None]
    assert restored[4][0]["startValue"] == 10 and restored[4][0]["endValue"] == 19
    assert short[4][0]["startValue"] == 0 and short[4][0]["endValue"] == 5
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
const row=v=>({value:v,role:'experimental',acronym:'Trial',group_title:'Drug',product_label:'Drug'});
const frames=[{frame_id:'first',trial_ids:['one'],title:'First definition',population:'All participants',
 rows:[row(25)],comparisons:[],source_statistics:[{value:10.3,ci_lower:5.7,ci_upper:14.9,
 param_type:'Adjusted Difference',group_labels:['A','B'],acronym:'Trial',url:'https://example.test'}]},
 {frame_id:'second',trial_ids:['two'],title:'Other definition',
 population:'Responders',rows:[row(10)],comparisons:[]}];
const q={question_id:'q',label:'临床缓解',time_label:'第52周',units:['%'],measure_label:'比例',
 trial_ids:['one','two'],rows:[row(25),row(10)],comparisons:[],frames};
const plots={},tables={};
const window={U:{D:{b:{questions:[q],longitudinal:[],safety:[],observations:[]},stats:{},trials:{}},
 esc:s=>s||'',num:s=>s,nN(){},tag(){},src(){},options(){},OWN:'orange',PAL:[],
 chart:(id,opt)=>plots[id]=opt,table:(el,cols,rows)=>tables[el.id]=rows}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document:{getElementById:id=>elements[id]}});
const read=()=>({values:plots['value-chart'].series[0].data.map(d=>d.value),
 table:tables['row-table'].map(d=>d.value),context:elements['frame-context-text'].textContent,
 rawValues:plots['source-stat-chart']?.series[1].data.map(d=>d.value),rawHidden:elements['source-statistics'].hidden});
const first=read();elements['frame-select'].value='second';elements['frame-select'].onchange();
process.stdout.write(JSON.stringify([first,read()]));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    first, second = json.loads(result.stdout)
    assert first["values"] == first["table"] == [25]
    assert second["values"] == second["table"] == [10]
    assert "Responders" in second["context"] and "All participants" in first["context"]
    assert first["rawValues"] == [10.3] and not first["rawHidden"] and second["rawHidden"]
