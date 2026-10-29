"""Selected clinical frames must not silently inherit another study's trajectory."""

import json
import subprocess
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[1] / "src/ciw/render/static"


@pytest.mark.parametrize("mode", ["point", "axis", "no_match", "different_axis"])
def test_longitudinal_default_is_bound_to_selected_frame_without_hiding_related_options(mode):
    script = r"""
const fs=require('fs'),vm=require('vm'),mode=process.argv[2];
const els=new Proxy({}, {get:(a,k)=>a[k]||(a[k]={id:k,value:'',checked:false,
 querySelectorAll:()=>[],addEventListener(){}})});
const row={result_id:'r-target',trial_id:'T-target',value:3,acronym:'Target',group_title:'Drug',unit:'Points'};
const frame={frame_id:'f',units:['Points'],trial_ids:['T-target'],result_ids:['r-target'],
 measure_label:'均值',rows:[row],comparisons:[],source_statistics:[],axis_id:mode==='axis'?'a1':undefined};
const q={question_id:'q',concept_id:'score',label:'症状评分',units:['Points'],trial_ids:['T-target'],
 frames:[frame],rows:[row],comparisons:[],measure_label:'均值'};
const line=(trial,id)=>({trial_id:trial,acronym:trial,group_title:'Drug',product_label:'Drug',
 points:[{result_id:id,weeks:16,value:3,label:'第16周'},{result_id:id+'-2',weeks:24,value:4,label:'第24周'}]});
const charts=[{chart_id:'unrelated',concept_id:'score',label:'其他研究',unit:'Points',measure_label:'均值',
 lines:[line('T-other','r-other')]}];
if(mode!=='no_match') charts.push({chart_id:'target',concept_id:'score',label:'目标研究',unit:'Points',
 measure_label:'均值',axis_id:mode==='axis'?'a1':mode==='different_axis'?'different':undefined,
 lines:[line('T-target',mode==='axis'?'r-different-time':'r-target')]});
if(mode==='different_axis') frame.axis_id='selected-axis';
const plots={},tables={},window={U:{D:{b:{questions:[q],longitudinal:charts,safety:[],observations:[]}},
 esc:x=>x||'',num:x=>x,nN(){},tag(){},src(){},options(){},matchesQuestion:()=>true,OWN:'orange',PAL:[],
 chart:(id,o)=>plots[id]=o,table:(e,c,r)=>tables[e.id]=r}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document:{getElementById:id=>els[id]}});
const initial={selector:els['long-select'].value,options:els['long-select'].innerHTML,
 hidden:els['long-chart'].hidden,rows:tables['long-table']||[],points:plots['long-chart']?.series[0].data};
// An explicit user choice may view another related study; it must not be selected on their behalf.
els['long-select'].value='0';els['long-select'].onchange();
process.stdout.write(JSON.stringify({initial,explicit:tables['long-table']?.map(r=>r.trial_id)}));
"""
    result = subprocess.run(
        ["node", "-e", script, str(ASSETS / "b.js"), mode], capture_output=True, text=True, check=True
    )
    out = json.loads(result.stdout)
    assert "其他研究" in out["initial"]["options"]
    if mode in {"no_match", "different_axis"}:
        assert out["initial"]["hidden"]
        assert not out["initial"]["rows"]
    else:
        assert {r["trial_id"] for r in out["initial"]["rows"]} == {"T-target"}
        assert not out["initial"]["hidden"]
    assert out["explicit"] == ["T-other", "T-other"]


@pytest.mark.parametrize("width", [456, 642, 900])
def test_numeric_plot_keeps_legible_ticks_and_real_plot_width_in_a_narrow_card(width):
    script = r"""
const fs=require('fs'),vm=require('vm'),window={CIW:{},innerWidth:1920,innerHeight:1080,addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,URL,
 document:{getElementById:()=>null,addEventListener(){}}});
const el={clientWidth:Number(process.argv[2]),style:{}};
const option={grid:{left:300,right:60,top:20,bottom:40},
 xAxis:{type:'value',scale:true},yAxis:{type:'category',data:['长药物名 · 研究A'],axisLabel:{width:280}},
 series:[{type:'scatter',data:[{value:-2.1}]}]};
const out=window.U.present(option,el);
process.stdout.write(JSON.stringify({plot:el.clientWidth-out.grid.left-out.grid.right,
 label:out.yAxis.axisLabel.width,left:out.grid.left,font:out.xAxis.axisLabel.fontSize,
 hide:out.xAxis.axisLabel.hideOverlap,split:out.xAxis.splitNumber,value:out.series[0].data[0].value}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", script, str(ASSETS / "common.js"), str(width)], capture_output=True, text=True, check=True
        ).stdout
    )
    assert out["plot"] >= min(220, width * 0.45)
    assert out["label"] < out["left"]
    assert out["font"] >= 16 and out["hide"]
    assert out["split"] <= out["plot"] // 65
    assert out["value"] == -2.1


def test_container_resize_replans_from_original_geometry_and_restores_wide_layout():
    script = r"""
const fs=require('fs'),vm=require('vm'),seen=[];
const el={id:'plot',clientWidth:900,style:{},getClientRects:()=>[{}]};let observer;
const chart={resize(){},getOption:()=>({}),setOption:o=>seen.push({left:o.grid.left,
 plot:el.clientWidth-o.grid.left-o.grid.right})};
const window={CIW:{},innerWidth:1920,innerHeight:1080,addEventListener(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,URL,
 document:{getElementById:id=>id==='plot'?el:null,addEventListener(){}},
 echarts:{getInstanceByDom:()=>chart},ResizeObserver:class{constructor(fn){observer=fn}observe(){}}});
const original={grid:{left:300,right:60,top:20,bottom:40},xAxis:{type:'value'},
 yAxis:{type:'category',data:['Study'],axisLabel:{width:280}},series:[{type:'scatter',data:[-2.1]}]};
window.U.chart('plot',original);el.clientWidth=456;observer();el.clientWidth=900;observer();
process.stdout.write(JSON.stringify({seen,left:original.grid.left,label:original.yAxis.axisLabel.width}));
"""
    out = json.loads(
        subprocess.run(
            ["node", "-e", script, str(ASSETS / "common.js")], capture_output=True, text=True, check=True
        ).stdout
    )
    assert len(out["seen"]) == 3
    assert out["seen"][1]["plot"] >= 220
    assert out["seen"][0] == out["seen"][2]
    assert out["left"] == 300 and out["label"] == 280
