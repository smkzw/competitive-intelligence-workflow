"""One original context should not render the same clinical sentence three times."""
import json
import subprocess
from pathlib import Path


def test_original_details_deduplicate_literal_subsets_but_keep_independent_timeframe():
    asset = Path(__file__).parents[1] / "src/ciw/render/static/c.js"
    script = r"""
const fs=require('fs'),vm=require('vm'),texts=[];
const els=new Proxy({}, {get:(all,id)=>all[id]||(all[id]={id,value:'',checked:false,style:{},
 parentElement:{},querySelectorAll:()=>[],setAttribute(){},addEventListener(){}})});
const full='Relapsed: Meets either condition: Marker ≥3 or dialysis. <script>data</script>';
const row={trial_id:'t',phase:'III',products:[],primary:[],primary_concepts:[],title:'',eligibility:full,
 start:null,enrollment:null,design_excerpts:[{topic_id:'topic',snippets:[{criterion_role:'inclusion',
 cohort_quote:'Relapsed',condition:'Meets either condition:',text:'Marker ≥3',context:full,timeframe:'Week 24',
 reading:{text_zh:'完整中文临床要点',cohort_zh:'复发',condition_zh:'满足其一',timeframe_zh:'第24周'}}]}]};
const esc=s=>String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const window={U:{D:{c:{rows:[row],topic_catalog:[{topic_id:'topic',kind:'eligibility_threshold',label:'指标'}]}},
 esc,annotate:esc,options(){},src(){},drawer(){},chart(){},PAL:[],
 table(el,cols,rows){if(el.id==='matrix')texts.push(cols[1].html(rows[0]))}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document:{getElementById:id=>els[id]}});
process.stdout.write(JSON.stringify(texts[0]));
"""
    html = json.loads(subprocess.run(["node", "-e", script, str(asset)], check=True,
                                    capture_output=True, text=True).stdout)
    assert html.count("Marker ≥3") == 1 and html.count("Relapsed") == 1
    assert html.count("Meets either condition:") == 1
    assert "Week 24" in html and "&lt;script&gt;data&lt;/script&gt;" in html
    assert "<script>" not in html and "完整中文临床要点" in html
