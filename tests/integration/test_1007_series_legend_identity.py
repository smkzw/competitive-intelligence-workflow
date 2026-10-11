"""Production series, visible legend and tooltip share source-qualified labels."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHARTS = ROOT / "src/ci_workflow/renderers/portal/assets/charts.js"
REAL = ROOT / ".artifacts/1007-baseline-planner-source-v1.json"

PROBE = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function node(){return {children:[],attributes:{},style:{},
 appendChild(child){this.children.push(child);},
 setAttribute(key,value){this.attributes[key]=value;}};}
const document={readyState:'loading',addEventListener(){},createElement:node,
 createTextNode(text){return {textContent:String(text)};}};
const sandbox={window:{},document};
const source=fs.readFileSync(process.argv[1],'utf8').replace(
 'presentationPlan: presentationPlan,',
 'presentationPlan: presentationPlan, testLegend: renderIdentityLegend,');
vm.runInNewContext(source,sandbox);
const api=sandbox.window.__CHART_SYNC__;
const groups=JSON.parse(process.argv[2]);
const text=n=>n.textContent || (n.children || []).map(text).join('');
for(const group of groups){
 const before=JSON.stringify(group),option=api.buildBarOption(group);
 const names=option.series.map(s=>s.name);
 assert.equal(new Set(names).size,names.length,'distinct series have ambiguous names');
 const visible=api.testLegend(node(),group);
 assert.deepEqual(Array.from(visible.children,text),Array.from(names),
  'visible legend differs from the actual plotted series');
 visible.children.forEach((item,index)=>assert.equal(
  item.children[0].style.backgroundColor,option.series[index].itemStyle.color,
  'visible legend color differs from its plotted source series'));
 const mapping=opt=>Object.fromEntries(opt.series.flatMap(s=>s.data
  .filter(p=>p._row_id).map(p=>[p._row_id,{name:s.name,value:p.value,
   color:s.itemStyle.color}])));
 const full=mapping(option),reordered=mapping(api.buildBarOption(
  {...group,rows:group.rows.slice().reverse()}));
 for(const row of group.rows){
  assert.deepEqual(reordered[row.row_id],full[row.row_id],'input order changed identity');
  assert.equal(full[row.row_id].value,row.renderable===false ? null : row.numeric_value);
  const filtered=mapping(api.buildBarOption({...group,rows:[row],
   _series_palette_rows:group.rows}));
  assert.deepEqual(filtered[row.row_id],full[row.row_id],
   'filter changed a retained series name, color or source value');
  assert.ok(full[row.row_id].name.startsWith(row._chart_series_label));
 }
 assert.equal(Object.keys(full).length,group.rows.length,'source facts dropped');
 assert.equal(JSON.stringify(group),before,'display renamed scientific identity');
 assert.deepEqual(Array.from(option.legend.data),Array.from(names));
}
"""


def _probe(groups: list[dict], *, extra: str = "") -> None:
    probe = PROBE.replace("const names=option.series.map(s=>s.name);",
                          "const names=option.series.map(s=>s.name);" + extra)
    result = subprocess.run(
        ["node", "-e", probe, str(CHARTS), json.dumps(groups)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


def _group() -> dict:
    rows = []
    for study, values in enumerate(((51.1, 49.2), (46.7, 51), (57.6, 57.5), (50.8, 53.7))):
        trial = f"NCT0000000{study}"
        for arm, value in enumerate(values):
            label = "对照组" if arm == 0 else ("药A" if study < 2 else "药B")
            rows.append({
                "row_id": f"{trial}-{arm}", "trial_id": trial, "arm_role": "unknown",
                "group_id": f"BG{arm if study < 2 else 1 - arm}",
                "_chart_series_key": f"BG{arm if study < 2 else 1 - arm}",
                "_chart_series_label": label, "_chart_identity_key": f"::{trial.lower()}",
                "_chart_identity_label": trial, "_chart_comparison_context_key": "age-mean",
                "_chart_comparison_context_label": "基线", "value": value,
                "numeric_value": value, "renderable": True, "unit": "岁",
            })
    return {"chart_type": "bar", "cross_trial": True, "title_zh": "年龄", "rows": rows}


def test_same_named_source_series_have_unique_stable_visible_identities() -> None:
    _probe([_group()])


def test_same_study_duplicate_labels_keep_both_source_groups() -> None:
    group = _group()
    group["rows"] = group["rows"][:2]
    for row in group["rows"]:
        row["_chart_series_label"] = "对照组"
    _probe([group])


def test_qualifiers_keep_zero_and_missing_source_values() -> None:
    group = _group()
    group["rows"][0].update(value=0, numeric_value=0)
    group["rows"][2].update(value=None, numeric_value=None, renderable=False)
    _probe([group])


def test_source_variants_with_same_local_group_id_remain_distinguishable() -> None:
    group = _group()
    group["rows"] = group["rows"][:2]
    for index, row in enumerate(group["rows"]):
        row.update(group_id="BG0", _chart_series_key=f"BG0:variant-{index}",
                   _chart_series_label="对照组")
    _probe([group])


@pytest.mark.skipif(not REAL.is_file(), reason="real normal-preview payload absent")
def test_real_four_study_frames_preserve_each_point_and_qualified_legend() -> None:
    groups = json.loads(REAL.read_bytes())
    assert len(groups) == 4 and sum(len(group["rows"]) for group in groups) == 48
    _probe(groups)
