"""Production dense-cell accessibility/retention family; pixels need Ego QA."""

import subprocess
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets"


def test_dense_cell_exposes_all_observations_count_and_native_full_reading_control() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function createComparisonQuestionOrder(');
const end=source.indexOf('\n  window.__COMPARISON_QUERY__',start),sandbox={};
class Node {
 constructor(){this.children=[];this.attrs={};this.className='';this.checked=false;}
 appendChild(n){this.children.push(n);return n;}
 insertBefore(n,ref){this.children.splice(this.children.indexOf(ref),0,n);return n;}
 setAttribute(k,v){this.attrs[k]=String(v);}
}
vm.runInNewContext(source.slice(start,end),sandbox);
const factory=sandbox.createComparisonQuestionOrder(),doc={createElement(){return new Node();}};
const rows=Array.from({length:32},(_,i)=>({row_id:'fact-'+i,product_zh:'药物原名',
 arm:'300mg Q2W',time:'Week '+(i+1),value:i===0?0:i===1?null:i,
 difference_note:'不同分析人群，不共轴',source_denominator_scope_zh:'来源分析集',
 source_denominator_value:39}));
const before=JSON.stringify(rows),cell=new Node();
rows.forEach(row=>{const button=new Node();button.setAttribute('data-evidence-row-id',row.row_id);
 const value=row.value===null?'用户清除，待重新核实':row.value+' %';
 factory.factCell(doc,cell,button,row,value,'来源条件');});
const list=cell.__comparisonObservations;
assert.ok(list.className.includes('kz-comparison-observations--dense'));
assert.equal(list.attrs.role,'region');assert.equal(list.attrs.tabindex,'0');
assert.ok(list.attrs['aria-label'].includes('32'),'local count must not imply a truncated set');
const control=cell.children.find(n=>n.className==='kz-comparison-window-control');
assert.ok(control,'explicit native full reading control');
assert.equal(cell.children[0],control,'count and expansion precede the scroll region');
assert.equal(control.children[0].type,'checkbox');
assert.equal(control.children[0].checked,false,'dense default does not dominate the whole page');
assert.ok(control.children[1].textContent.includes('32'));
const observations=list.children.filter(n=>n.className.includes('kz-comparison-observation'));
assert.equal(observations.length,32,'all atoms remain rendered, no Top-N or clipping deletion');
assert.deepEqual(observations.map(n=>n.children[0].attrs['data-evidence-row-id']),rows.map(r=>r.row_id));
assert.equal(JSON.stringify(rows),before,'presentation never changes scientific/source data');
function text(n){return[n.textContent||'',...n.children.map(text)].join('|');}
assert.ok(text(list).includes('用户清除，待重新核实'));assert.ok(text(list).includes('0 %'));
assert.ok(text(observations[31]).includes('Week 32'));
assert.ok(text(observations[31]).includes('N=39（来源原值，非当前值）'));
const sparse=new Node();
rows.slice(0,2).forEach(row=>factory.factCell(doc,sparse,new Node(),row,'值','条件'));
assert.equal(sparse.children.length,1,'filter32→2 rebuild has no empty dense-control chrome');
assert.ok(!sparse.__comparisonObservations.className.includes('--dense'));
"""
    result = subprocess.run(["node", "-e", probe, str(ASSETS / "portal.js")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_dense_window_is_scrollable_focusable_and_natively_expands_without_hiding_facts() -> None:
    css = (ASSETS / "kangzhe-site.css").read_text()
    marker = css.index(".kz-comparison-observations--dense {")
    block = css[marker:css.index("}", marker)]
    assert "overflow-y: auto" in block and "max-height:" in block
    assert "overflow: hidden" not in block and "font-size" not in block
    marker = css.index(".kz-comparison-window-control:has(input:checked)")
    full = css[marker:css.index("}", marker)]
    assert "max-height: none" in full and "overflow: visible" in full
    assert ".kz-comparison-observations--dense:focus-visible" in css


def test_dense_values_wrap_as_readable_value_and_visit_units() -> None:
    css = (ASSETS / "kangzhe-site.css").read_text()
    marker = css.index("#full-study-comparison button.kz-comparison-fact {")
    block = css[marker:css.index("}", marker)]
    assert "display: flex" in block and "flex-wrap: wrap" in block
    marker = css.index(".kz-comparison-fact__value {")
    value = css[marker:css.index("}", marker)]
    assert "word-break: keep-all" in value
    assert "font-size: 1.125em" in value and "overflow: hidden" not in value
