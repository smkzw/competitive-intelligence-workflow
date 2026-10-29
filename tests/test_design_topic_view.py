"""Synthetic UI contract; actual clinical/browser acceptance remains separate."""
import json
import subprocess
from pathlib import Path

from lxml import html


def test_topic_cells_show_real_clauses_and_selection_survives_filters():
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/c.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),els={},saved={},callbacks={};
const get=id=>els[id]||(els[id]={id,value:'',checked:false,style:{setProperty(){}},parentElement:{},
classList:{toggle(){}},setAttribute(k,v){this[k]=v},querySelectorAll(){return []},
addEventListener:(event,fn)=>callbacks[id+event]=fn});
const topics=Array.from({length:6},(_,i)=>({topic_id:'design-topic-'+i,label:'主题'+i,kind:'eligibility_threshold'}));
const snippet={text:'eGFR ≥40 <script>bad()</script>',marks:[],section:'入排标准',criterion_role:'exclusion',
condition:'Only if all apply:',cohort_quote:'Named cohort',context:'Source full context',context_marks:[]};
const rows=['one','two'].map((trial_id,i)=>({trial_id,title:'',eligibility:'',search_text:i?'其他':'肾功能',
products:[{label:'Drug '+i}],primary:[],primary_concepts:[],phase:'III',masking:'',enrollment:i?20:0,
background_therapy:[],arms:[],
start:'2026-01-01',enrollment_type:'实际',design_excerpts:[{topic_id:'design-topic-0',label:'主题0',snippets:[snippet]}]}));
const escape=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;')
.replaceAll('>','&gt;').replaceAll('"','&quot;');
const window={U:{D:{c:{rows,topic_catalog:topics},indication:{}},esc:escape,src:()=>'',options(){},drawer(){},
annotate:escape,chart(){},table:(el,cols,rs)=>saved[el.id]={cols,rs},OWN:'orange',PAL:['blue']}};
const document={getElementById:get};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document,Set});
function state(){const t=saved.matrix;return {labels:t.cols.map(c=>c.label),ids:t.rs.map(r=>r.trial_id),
 cells:t.rs.map(r=>t.cols.map(c=>c.html?c.html(r):r[c.key])),sizeIds:saved['size-data'].rs.map(r=>r.trial_id)}}
const out=[state()];
callbacks['topic-pickerchange']({target:{dataset:{topicId:'design-topic-4'},checked:true}});out.push(state());
get('q').value='肾功能';callbacks.qinput();out.push(state());
get('q').value='';callbacks.qinput();out.push(state());
callbacks['view-comprehensiveclick']();out.push(state());callbacks['view-topicsclick']();out.push(state());
callbacks['topics-clearclick']();out.push(state());callbacks['topics-allclick']();out.push(state());
process.stdout.write(JSON.stringify(out));
"""
    output = json.loads(subprocess.run(["node", "-e", script, str(asset)], text=True,
                                      capture_output=True, check=True).stdout)
    initial, expanded, filtered, restored, comprehensive, resumed, cleared, all_topics = output
    assert initial["labels"] == ["药物 / 研究", "主题0", "主题1", "主题2", "主题3"]
    assert expanded["labels"] == restored["labels"] == resumed["labels"]
    assert filtered["ids"] == filtered["sizeIds"] == ["one"]
    assert restored["ids"] == ["one", "two"] and comprehensive["labels"][1] == "设计 / 组别"
    assert len(cleared["labels"]) == 1 and len(all_topics["labels"]) == 7
    assert all_topics["ids"] == initial["ids"]
    for row in initial["cells"]:
        fragment = html.fragment_fromstring(row[1], create_parent="div")
        assert not fragment.xpath(".//script")
        assert "Only if all apply:" in fragment.text_content() and "排除" in fragment.text_content()
        assert "Named cohort" in fragment.text_content() and "eGFR ≥40" in fragment.text_content()
    assert "N=0" in initial["cells"][0][0]
