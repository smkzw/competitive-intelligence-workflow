"""Ordinary C study-only preview and production filter behavior, not pixels."""

from __future__ import annotations

import json
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest

from ci_workflow.reports.c.endpoint_instances import (
    EndpointInstanceError,
    validate_endpoint_timepoint_pairs,
)
from tests.integration.test_r24_c_source_consumers import _AT, _raw
from tests.integration.test_r24_c_study_projection_identities import _instance_obs
from tests.integration.test_r24_ctgov_c_design_projection import _CAS_ROOT, _full_bindings
from tools.materialize_ctgov_c_candidate import materialize, render_review_preview

ROOT = Path(__file__).resolve().parents[2]


def test_missing_timepoints_mixed_product_diagnostics_do_not_crash() -> None:
    # Same axes except explicit product null versus known product: neither may
    # pair, and ordering the error must not raise Python's None/string TypeError.
    rows = [_instance_obs('unknown', family='endpoint', product_id=None),
            _instance_obs('known', family='endpoint', product_id='P1')]
    with pytest.raises(EndpointInstanceError, match='缺评估时间点'):
        validate_endpoint_timepoint_pairs(rows)


@pytest.mark.parametrize('mixed', (False, True))
def test_ordinary_source_preview_preserves_unassigned_studies(tmp_path: Path, mixed: bool) -> None:
    bindings = tuple(binding.model_copy(update={'product_id': None})
                     if not mixed or index == 0 else binding
                     for index, binding in enumerate(_full_bindings()))
    output = tmp_path / 'fresh-c'
    manifest = materialize(
        source_root=_CAS_ROOT, raw_asset=_raw(), output=output, bindings=bindings,
        indication_id='pnh', indication='阵发性睡眠性血红蛋白尿症',
        cutoff='2026-09-26', observed_at=_AT,
    )
    preview = render_review_preview(output, rendered_at=_AT + timedelta(seconds=1))
    data = json.loads((output / 'review-portal-data.json').read_bytes())
    assert (preview['observations'] == preview['registered_consumers']
            == manifest['observations'] == 85)
    assert len(data['trials']) == 2
    assert {row['id'] for row in data['products']} == {
        b.product_id for b in bindings if b.product_id is not None
    }
    assert data['trials'][0]['product_id'] is None
    assert any(row['product_id'] is None for row in data['observations'])
    assert not preview['scientific_acceptance'] and not preview['current_generation_switched']
    site = output / preview['site_relative_path']
    for page in site.rglob('*.html'):
        text = page.read_text()
        assert 'data-review-status="unreviewed_candidate"' in text
        assert 'data-product-id="None"' not in text
        assert 'data-matrix-product="None"' not in text
    assert not (output / 'project/reports/current.json').exists()


@pytest.mark.parametrize('case', ('all-dimensions', 'empty-chart'))
def test_production_c_filters_never_restore_excluded_rows_or_empty_chart(case: str) -> None:
    asset = ROOT / 'src/ci_workflow/renderers/portal/assets/report-c.js'
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const row=(id,pid)=>({style:{},getAttribute(k){return {
 'data-row-id':id,'data-product-id':pid,'data-trial-id':'T1'}[k]??null;}});
const rows=[row('unknown',''),row('known','P1')];
const dims={unknown:{product:null,trial:'T1',element:'exclude'},
 known:{product:'P1',trial:'T1',element:'exclude'}};
const sandbox={URL,URLSearchParams,window:{location:{search:''},setTimeout(){},
 __C_ROW_DIMENSIONS__:dims,__C_FILTER_DIMENSIONS__:['product','trial','element']},
 document:{readyState:'loading',addEventListener(){},querySelector(){return null;},
 querySelectorAll(s){
   if(s==='.kz-chart-table__row[data-row-id]'||s==='[data-product-id], [data-trial-id]')return rows;
   return [];},createElement(){return {className:'',textContent:''};}}};
const original=fs.readFileSync(process.argv[1],'utf8');
const source=original.replace('window.__CHART_SYNC__ = {',
 'window.__CHART_SYNC__ = {testApply:applyState,testUpdate:updateChartFromState,'+
 'testInit:function(rows,chart,host){cChart=chart;'+
 'chartState={rows:rows,kind:"sample-size-bar",chart:host};},');
assert.notEqual(source,original);
vm.runInNewContext(source,sandbox);
const api=sandbox.window.__CHART_SYNC__;api.syncWithFilter=function(){};
if(process.argv[2]==='all-dimensions'){
 api.testApply({product:['P1'],trial:[],element:['include']});
 assert.equal(rows[0].style.display,'none','null product must not reappear');
 assert.equal(rows[1].style.display,'none','product match must not override element mismatch');
 api.testApply({product:[],trial:[],element:[]});
 assert.equal(rows[0].style.display,'');assert.equal(rows[1].style.display,'');
}else{
 let clears=0,sets=0;const notes=[];
 const chart={clear(){clears++;},setOption(){sets++;}};
 const host={innerHTML:'',appendChild(note){notes.push(note.textContent);}};
 api.testInit([{row_id:'known',value:100,trial_display_id:'NCT00000001',product_zh:'P1'}],chart,host);
 api.testUpdate({product:['P1'],element:['include']});
 assert.equal(clears,1,'empty query must clear the former series');
 assert.equal(sets,0,'empty query must not redraw all rows');
 assert.ok(notes.some(x=>x.includes('筛选')&&x.includes('无')));
}
"""
    result = subprocess.run(['node', '-e', probe, str(asset), case],
                            text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
