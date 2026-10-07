"""Ordinary B source pool does not require fabricated A landscape metadata."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.application.ctgov_b_result_views import project_unassigned_ctgov_results
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from tests.integration.reports.test_b_report_portal import _page_json_assignment
from tests.integration.reports.test_r24_b_related_study_catalog import _payload, _study
from tests.integration.test_r24_b_unassigned_source_results import _source


def _pool_payload() -> dict:
    base = _payload()
    views = project_unassigned_ctgov_results((
        _source('Number of Participants With Clinical Response', 'Participants', '3', '10'),
    ))
    return {
        'schema_version': base['schema_version'], 'report_version': 'source-pool-review',
        'indication': base['indication'], 'data_cutoff': base['data_cutoff'],
        'related_studies': [_study(base, 'unknown')], 'sources': base['sources'],
        'efficacy_views': {'coverage_mode': 'complete', 'facts': views.efficacy},
    }


def test_source_only_b_uses_ordinary_renderer_without_fake_product(tmp_path: Path) -> None:
    data = ReportBPortalData.model_validate(_pool_payload())
    assert not data.products and not data.trials and not data.safety
    assert not data.regulatory and not data.companies and not data.patents and not data.history
    assert data.trial_ids == ('nct00001999',)
    site = tmp_path / 'source-b'
    render_report_b_site(data, site, publication_limitation_zh='固定原源开发候选，尚未独立复核。')
    overview = (site / 'overview.html').read_text()
    assert '1 项研究' in overview and '不能据此认定竞品检索已完整' in overview
    groups = _page_json_assignment(site, 'efficacy.html', '__CHART_GROUPS__')
    rows = {row['row_id']: row for group in groups for row in group['rows']}
    evidence = {view['row']['row_id']: view for view in
                _page_json_assignment(site, 'efficacy.html', '__EVIDENCE_VIEWS__')}
    for row in _pool_payload()['efficacy_views']['facts']:
        assert rows[row['row_id']]['numeric_projection']['unrenderable_reason'] == (
            'group_product_relationship_unresolved'
        )
        assert evidence[row['row_id']]['source_version_id'] == row['source_version_id']
        assert evidence[row['row_id']]['original_text'] == row['source_text']
    assert (site / 'trials/nct00001999.html').exists()
    assert not list((site / 'products').glob('*.html'))
    offline = (site / 'data/report.js').read_text()
    saved = json.loads(offline.removeprefix('window.REPORT_B=').rstrip(';\n'))
    assert saved['products'] == [] and saved['trials'] == []
    assert saved['related_studies'][0]['product_id'] is None


def test_source_only_b_requires_a_real_study_and_a_still_requires_landscape() -> None:
    payload = _pool_payload()
    with pytest.raises(ValueError):
        ReportAPortalData.model_validate(payload)
    payload['related_studies'] = []
    with pytest.raises(ValueError, match='研究|试验'):
        ReportBPortalData.model_validate(payload)


@pytest.mark.parametrize('kind', ('study', 'product'))
def test_source_pool_unknown_reference_cannot_enter_ordinary_b(kind: str) -> None:
    payload = _pool_payload()
    facts = [dict(row) for row in payload['efficacy_views']['facts']]
    facts[0]['trial_id' if kind == 'study' else 'product_id'] = 'invented-reference'
    payload['efficacy_views']['facts'] = facts
    with pytest.raises(ValueError, match='研究|试验|产品'):
        ReportBPortalData.model_validate(payload)
