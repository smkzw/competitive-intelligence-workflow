import json
import subprocess
from pathlib import Path


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
const els={...inputs,matrix:{},count:{},'concept-chart':{parentElement:{},style:{}},
 'size-chart':{parentElement:{},style:{}}};
const rows=[{trial_id:'zero',phase:'II',primary_concepts:['NPS'],start:'2026-01-01',enrollment:0,
 products:[],primary:[],title:'',eligibility:''},
 {trial_id:'unknown',phase:'III',primary_concepts:['NCS'],start:'2026-01-02',enrollment:null,products:[],primary:[],title:'',eligibility:''}];
const plots={},out=[];
const window={U:{D:{c:{rows}},esc:s=>s,OWN:'orange',PAL:['teal'],options(){},table(){},chart(id,opt){plots[id]=opt;}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document:{getElementById:id=>els[id]}});
function read(){return {count:els.count.textContent,concepts:plots['concept-chart'].yAxis.data,
 points:plots['size-chart'].series.flatMap(s=>s.data).map(p=>p.value),
 conceptHidden:!!els['concept-chart'].parentElement.hidden,sizeHidden:!!els['size-chart'].parentElement.hidden};}
out.push(read());for(const q of ['zero','unknown','absent','']){inputs.q.value=q;inputs.q.change();out.push(read());}
process.stdout.write(JSON.stringify(out));
"""
    result = subprocess.run(["node", "-e", script, str(asset)], capture_output=True, text=True, check=True)
    initial, zero, unknown, absent, restored = json.loads(result.stdout)
    assert set(initial["concepts"]) == {"NPS", "NCS"}
    assert zero["concepts"] == ["NPS"] and zero["points"] == [["2026-01-01", 0]]
    assert unknown["concepts"] == ["NCS"] and unknown["sizeHidden"]
    assert absent["conceptHidden"] and absent["sizeHidden"] and absent["count"].startswith("0 /")
    assert restored == initial
