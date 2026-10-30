"""Real production C script: same filtered records, compact facts, and reversible quantitative views."""

import json
import subprocess
from pathlib import Path

from lxml import html


def test_single_summary_uses_facts_preserves_zero_unknown_and_restores_comparison():
    asset = Path(__file__).parents[1] / "src/ciw/render/static/c.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),els={},callbacks={},saved={},plots={};
const get=id=>els[id]||(els[id]={id,value:'',checked:false,style:{},parentElement:{},
 addEventListener:(event,fn)=>callbacks[id]=fn});
const rows=[{trial_id:'one',acronym:'ALPHA',phase:'III',start:'2027-01-01',enrollment:0,enrollment_type:'计划',
 products:[{label:'已核药物'}],primary:[],primary_concepts:['评分'],title:'',eligibility:''},
 {trial_id:'two',acronym:'BETA',phase:'II',start:'2027-02-01',enrollment:20,enrollment_type:'实际',
 products:[{label:'Drug Y'}],primary:[],primary_concepts:['评分','临床事件'],title:'',eligibility:''},
 {trial_id:'unknown',phase:'III',start:null,enrollment:null,enrollment_type:'',products:[],primary:[],
 primary_concepts:[],title:'',eligibility:''}];
const esc=s=>String(s??'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const window={U:{D:{c:{rows},indication:{name_zh:'目标适应症'}},esc,src:(u,s)=>esc(s),options(){},drawer(){},
 table:(el,cols,rs)=>saved[el.id]={cols,rs},chart:(id,opt)=>plots[id]=opt,OWN:'orange',PAL:['blue']}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document:{getElementById:get}});
const result=[];
for(const q of ['', 'one','unknown','absent','']){get('q').value=q;callbacks.q();
result.push({q,ids:saved.matrix.rs.map(r=>r.trial_id),tableIds:saved['size-data'].rs.map(r=>r.trial_id),
 conceptHidden:!!get('concept-chart').hidden,sizeHidden:!!get('size-chart').hidden,
 conceptCardHidden:!!get('concept-chart').parentElement.hidden,
 sizeCardHidden:!!get('size-chart').parentElement.hidden,
 sizeFacts:get('size-single').innerHTML||'',conceptFacts:get('concept-single').innerHTML||'',
 sizeFactsHidden:!!get('size-single').hidden,sizeHeight:get('size-chart').style.height,
 tooltip:plots['size-chart']?.tooltip.formatter({data:{r:rows[0]}})||'',
 trigger:plots['size-chart']?.tooltip.trigger||'',
 points:(plots['size-chart']?.series||[]).flatMap(s=>s.data.map(d=>({id:d.r.trial_id,value:d.value,
  tip:plots['size-chart'].tooltip.formatter({data:d})}))),
 encode:plots['size-chart']?.series?.[0]?.encode||null,
 labels:saved['size-data'].cols.map(c=>c.label)});}
process.stdout.write(JSON.stringify(result));
"""
    output = json.loads(
        subprocess.run(["node", "-e", script, str(asset)], text=True, capture_output=True, check=True).stdout
    )
    initial, single, unknown, absent, restored = output
    assert initial["ids"] == initial["tableIds"] == ["one", "two", "unknown"]
    assert not initial["sizeHidden"] and not initial["conceptHidden"]
    assert single["sizeHidden"] and single["conceptHidden"] and not single["sizeFactsHidden"]
    assert single["ids"] == single["tableIds"] == ["one"]
    facts = html.fragment_fromstring(single["sizeFacts"], create_parent="div").text_content()
    assert all(value in facts for value in ["已核药物", "III", "ALPHA", "2027-01-01", "0", "计划"])
    assert "首例" not in facts and "登记开始" in facts
    assert unknown["sizeHidden"] and "—" in unknown["sizeFacts"]
    assert absent["conceptCardHidden"] and absent["sizeCardHidden"] and not absent["ids"]
    assert restored == initial
    assert initial["trigger"] == "item"
    assert [point["id"] for point in initial["points"]] == ["one", "two"]
    assert initial["points"][0]["value"] == ["2027-01-01", 0]
    assert "0" in initial["points"][0]["tip"] and "计划" in initial["points"][0]["tip"]
    assert initial["encode"]["x"] == 0 and initial["encode"]["y"] == 1
    assert all(value in initial["tooltip"] for value in ["已核药物", "III", "ALPHA", "登记开始", "计划"])
    assert "登记开始日期" in initial["labels"] and not any("首例" in label for label in initial["labels"])


def test_c_template_has_compact_slots_and_safety_heading_has_no_teaching_text():
    root = Path(__file__).parents[1] / "src/ciw/render/templates"
    c = html.fragment_fromstring((root / "c.html").read_text(), create_parent="div")
    assert c.xpath(".//*[@id='concept-single']") and c.xpath(".//*[@id='size-single']")
    assert "首例" not in c.text_content()
    b = html.fragment_fromstring((root / "b.html").read_text(), create_parent="div")
    assert "比例仅由人数/风险人数计算" not in b.text_content()
    assert "安全概况" in b.text_content()
