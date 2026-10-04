"""Production matrix labels disclose zero/unknown and retain aggregated row IDs."""

import subprocess
from pathlib import Path


def test_production_c_matrix_labels_preserve_zero_and_full_detail_mapping() -> None:
    source = Path(__file__).resolve().parents[2] / (
        "src/ci_workflow/renderers/portal/assets/report-c.js"
    )
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={URLSearchParams,URL,window:{location:{search:''},setTimeout(){}},
 document:{readyState:'loading',addEventListener(){}}};
const original=fs.readFileSync(process.argv[1],'utf8');
const text=original.replace('window.__CHART_SYNC__ = {',
 'window.__CHART_SYNC__ = {testMatrix:matrixOption,');
assert.notEqual(text,original,'Test entry instrumentation must hit production API');
vm.runInNewContext(text,sandbox);
function row(id,value,state,element){return {row_id:id,value,disclosure_state:state,
 trial_display_id:'NCT00000001',product_zh:'药物',element_zh:element};}
const option=sandbox.window.__CHART_SYNC__.testMatrix([
 row('zero',0,'reported_zero','样本量'),
 row('unknown',null,'not_publicly_disclosed','分组'),
 row('first','原条款甲','reported_value','入选'),
 row('second','原条款乙','reported_value','入选')],'core-design-matrix',900);
const data=option.series[0].data, formatter=option.series[0].label.formatter;
assert.equal(formatter({data:data[0]}),'0');
assert.equal(formatter({data:data[1]}),'未公开');
assert.equal(data[2].rowCount,2);
assert.deepEqual(Array.from(data[2].rowIds),['first','second']);
assert.ok(formatter({data:data[2]}).includes('2条登记明细'));
assert.ok(formatter({data:data[2]}).includes('原条款甲'));
assert.equal(data.flatMap(x=>Array.from(x.rowIds)).length,4);
"""
    result = subprocess.run(
        ["node", "-e", probe, str(source)], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
