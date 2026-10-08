"""Execute portable query functions, without claiming browser/offline acceptance."""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("report", ["A", "B", "C"])
def test_personal_query_preserves_comparison_and_validates_question_page(report):
    script = (Path(__file__).resolve().parents[2] /
              "src/ci_workflow/renderers/portal/assets/portal.js")
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8'),report=process.argv[2];
const start=source.indexOf('  function safeText(',source.indexOf('(function personalViews()'));
const end=source.indexOf('\n  function validSelection(',start);
assert.ok(start>=0&&end>start);
const button={getAttribute(k){return k==='data-filter-value'?'product-a':null;}};
const group={getAttribute(){return 'product';},matches(){return false;},
 querySelectorAll(){return [button];}};
const columns=Array.from({length:9},()=>({question_id:'easi'})).concat([{question_id:'safety'}]);
columns.forEach(c=>{c.question_known=true;c.cells={s1:['a'],s2:['b']};});
columns.push({question_id:'aa-unknown',question_known:false,cells:{s1:['a']}});
const workspace={columns};
const sandbox={report,URLSearchParams,Object,String,Number,Math,Array,Set,
 window:{location:{search:report==='C'?'?view=comparison&product=product-a':
 '?view=comparison&cmp=easi&cmp_page=3&product=product-a'},
 __A_COMPARISON_WORKSPACE__:workspace,__B_COMPARISON_WORKSPACE__:workspace},
 document:{querySelectorAll(){return [group];},
 getElementById(){return report==='C'?null:{};},querySelector(){return {};}}};
const orderStart=source.indexOf('  function createComparisonQuestionOrder(');
const orderEnd=source.indexOf('\n  window.__COMPARISON_QUERY__',orderStart);
if(orderStart>=0){
 vm.runInNewContext(source.slice(orderStart,orderEnd),sandbox);
 sandbox.window.__COMPARISON_QUERY__=sandbox.createComparisonQuestionOrder();
}
vm.runInNewContext(source.slice(start,end),sandbox);
const known=sandbox.knownValues(),query=sandbox.queryFromPage();
assert.equal(query.view[0],'comparison');assert.equal(query.product[0],'product-a');
assert.ok(sandbox.validQuery(query,known,true));
assert.equal(sandbox.validQuery({view:['comparison','comparison']},known,true),false);
if(report!=='C'){
 assert.equal(query.cmp[0],'easi');assert.equal(query.cmp_page[0],'3');
 assert.equal(sandbox.validQuery({cmp:['safety'],cmp_page:['3']},known,true),false);
 assert.equal(sandbox.validQuery({cmp:['missing']},known,true),false);
 assert.ok(sandbox.validQuery({cmp:['safety'],cmp_page:['1']},known,true));
 assert.ok(sandbox.validQuery({view:['comparison'],cmp_page:['3']},known,true));
 assert.ok(sandbox.validQuery({cmp:['aa-unknown'],cmp_page:['1']},known,true));
}
"""
    result = subprocess.run(["node", "-e", probe, str(script), report],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
