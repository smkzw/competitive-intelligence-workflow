"""Chart identity, forest geometry, and inline-disclosure keyboard behavior."""

import json
import subprocess
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "src/ciw/render/static"


def _node(script, *args):
    run = subprocess.run(["node", "-e", script, *args], capture_output=True, text=True, check=True)
    return json.loads(run.stdout)


def test_forest_point_uses_reported_value_and_axis_keeps_drug_before_registry_id():
    script = r"""
const fs=require('fs'),vm=require('vm');
const els=new Proxy({}, {get:(all,id)=>all[id]||(all[id]={id,value:'',checked:false,style:{},hidden:false,
 classList:{toggle(){}},querySelectorAll:()=>[],addEventListener(){}})});
const rows=[
 {result_id:'placebo',value:-0.5,role:'placebo',group_title:'安慰剂组',product_label:'药物甲',phase:'III',
  acronym:'NCT10000001',trial_id:'NCT10000001',unit:'分'},
 {result_id:'active',value:-1.2,role:'experimental',group_title:'药物甲组',product_label:'药物甲',phase:'III',
  acronym:'STUDY',trial_id:'NCT10000002',unit:'分'}];
const comparisons=[
 {family:'difference',plot_value:-0.7,plot_lower:-1.1,plot_upper:-0.5,value:-0.7,ci_lower:-1.1,ci_upper:-0.5,
  ci_pct:95,product_label:'药物甲',exp_group:'药物甲组',ctrl_group:'安慰剂组',acronym:'STUDY',trial_id:'NCT10000002',
  phase:'III',param_type:'差值',p_value:'<0.001',kind:'reported',is_own:false,h2h:false},
 {family:'difference',plot_value:-0.4,plot_lower:null,plot_upper:null,value:-0.4,ci_lower:null,ci_upper:null,
  product_label:'药物乙',exp_group:'药物乙组',ctrl_group:'安慰剂组',acronym:'NCT10000003',trial_id:'NCT10000003',
  phase:'II',param_type:'差值',kind:'reported',is_own:false,h2h:false}];
const frame={frame_id:'f',units:['分'],trial_ids:['NCT10000002'],result_ids:rows.map(r=>r.result_id),
 measure_label:'均值',rows,comparisons,source_statistics:[]};
const q={question_id:'q',concept_id:'score',label:'症状评分',units:['分'],trial_ids:['NCT10000002'],
 frames:[frame],rows,comparisons,measure_label:'均值'};
const plots={};
const window={U:{D:{b:{questions:[q],longitudinal:[],safety:[],observations:[]}},
 esc:s=>String(s??''),num:v=>v==null?'':String(v),nN(){},tag:()=>'',src:(url,label)=>label||'',
 options(){},matchesQuestion:()=>true,OWN:'#A65000',PAL:['#008F8A'],
 chart:(id,option)=>plots[id]=option,table(){},drawer(){}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document:{getElementById:id=>els[id]}});
const axis=plots['value-chart'].yAxis, forest=plots['diff-chart'];
const draw=(tuple,index)=>{
 const seen=[];
 const api={value:i=>tuple[i],coord(pair){seen.push(pair.slice());return pair.slice();}};
 return {graphic:forest.series[0].renderItem({dataIndex:index},api),seen};
};
process.stdout.write(JSON.stringify({
 labels:[0,1].map(i=>axis.axisLabel.formatter('',i)),
 arms:axis.data.length,
 scatter:forest.series[1].data.map(d=>d.value),
 geometry:forest.series[0].data,
 encode:forest.series[0].encode,
 full:draw([0,-1.1,-0.5,-0.7],0),
 missing:draw([1,null,null,-0.4],1)
}));
"""
    out = _node(script, str(ASSETS / "b.js"))
    assert out["arms"] == 2
    placebo, active = out["labels"]
    assert placebo.index("安慰剂") < placebo.index("III") < placebo.index("NCT10000001")
    assert not placebo.startswith("NCT")
    assert active.index("药物甲") < active.index("III") < active.index("STUDY") < active.index("NCT10000002")
    assert out["scatter"] == [[-0.7, 0], [-0.4, 1]]
    assert out["geometry"] == [[0, -1.1, -0.5], [1, None, None]]
    assert out["encode"] == {"x": [1, 2], "y": 0}
    full_coords = out["full"]["seen"]
    assert [-1.1, 0] in full_coords and [-0.5, 0] in full_coords
    circles = [child for child in out["full"]["graphic"]["children"] if child["type"] == "circle"]
    lines = [child for child in out["full"]["graphic"]["children"]
             if child["type"] == "line" and "x2" in child["shape"]]
    assert not circles  # A single scatter glyph owns the point and its clinical symbol.
    assert lines[0]["shape"]["x1"] == -1.1 and lines[0]["shape"]["x2"] == -0.5
    assert out["missing"]["graphic"] is None
    assert out["missing"]["seen"] == []  # Missing CI leaves the separately mapped scatter point intact.


def test_escape_closes_inline_details_and_leaves_the_outer_dialog_open():
    script = r"""
const fs=require('fs'),vm=require('vm'),listeners=[];
function node(tag, extra){
 const el=Object.assign({tag,children:[],parent:null,open:false,disabled:false,tabIndex:0,hidden:false,
  isConnected:true,focus(){el.focused=true;}}, extra||{});
 (extra&&extra.children||[]).forEach(child=>{child.parent=el;el.children.push(child);});
 el.querySelector=sel=>sel==='summary'?el.children.find(child=>child.tag==='summary'):null;
 el.querySelectorAll=()=>[];
 el.closest=sel=>{
  let cur=el;
  while(cur){if(sel==='details[open]'&&cur.tag==='details'&&cur.open)return cur;cur=cur.parent;}
  return null;
 };
 return el;
}
const summary=node('summary');
const innerSummary=node('summary');
const inner=node('details',{children:[innerSummary],open:true});
inner.children=[innerSummary]; innerSummary.parent=inner;
const details=node('details',{children:[summary,inner],open:true});
summary.parent=details; inner.parent=details;
const dialog={open:true,hidden:false,addEventListener(type,fn){listeners.push({type,fn,capture:false});},
 querySelector(){return null;},querySelectorAll:()=>[],setAttribute(){},showModal(){},close(){this.closed=true;}};
const document={activeElement:innerSummary,
 addEventListener(type,fn,capture){listeners.push({type,fn,capture:!!capture});},
 getElementById:id=>id==='drawer'?dialog:null};
const window={CIW:{coverage:[]},addEventListener(){},name:''};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,URL});
const onKey=listeners.filter(item=>item.type==='keydown'&&item.capture).pop().fn;
let prevented=0;
onKey({key:'Escape',target:innerSummary,preventDefault(){prevented++;},stopPropagation(){}});
const afterInner={inner:inner.open,outer:details.open,dialog:!!dialog.closed,focus:!!innerSummary.focused,prevented};
innerSummary.focused=false;
onKey({key:'Escape',target:summary,preventDefault(){prevented++;},stopPropagation(){}});
const afterOuter={inner:inner.open,outer:details.open,dialog:!!dialog.closed,focus:!!summary.focused};
const cancel=listeners.find(item=>item.type==='cancel').fn;
let cancelPrevented=false;
onKey({key:'Escape',target:{closest(){return null;}},preventDefault(){},stopPropagation(){}});
cancel({preventDefault(){cancelPrevented=true;}});
process.stdout.write(JSON.stringify({afterInner,afterOuter,cancelPrevented,dialog:!!dialog.closed}));
"""
    out = _node(script, str(ASSETS / "common.js"))
    assert out["afterInner"] == {"inner": False, "outer": True, "dialog": False, "focus": True, "prevented": 1}
    assert out["afterOuter"]["outer"] is False and out["afterOuter"]["dialog"] is False
    assert out["afterOuter"]["focus"] is True
    assert out["cancelPrevented"] is True and out["dialog"] is True
