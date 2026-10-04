"""Supporting observations keep scientific domains; source reachability is not efficacy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ci_workflow.application.ctgov_b_result_views import project_unassigned_ctgov_results
from ci_workflow.renderers.portal import report_b as b
from ci_workflow.reports.b.semantic_grouping import proposed_semantic_buckets
from tests.integration.reports.test_r24_b_study_only_source_pool import _pool_payload
from tests.integration.test_r24_b_unassigned_source_results import _source
from tests.reports.b.test_approved_merge_contract import _approved
from tests.reports.b.test_semantic_grouping_proposals import _proposal, _rows


@pytest.mark.parametrize(('title', 'unit', 'domain'), (
    ('Anti Drug Antibodies', 'Participants', 'immunogenicity'),
    ('Pharmacokinetic Cmax', 'ng/mL', 'pk_pd'),
    ('Biomarker Level', 'ng/mL', 'biomarkers'),
))
def test_ordinary_supporting_page_keeps_domain_and_source_label(
    tmp_path: Path, title: str, unit: str, domain: str,
) -> None:
    source = _source(title, unit, '3', None)
    views = project_unassigned_ctgov_results((source,))
    assert len(views.supporting) == 2 and not views.efficacy and not views.safety
    payload = _pool_payload()
    payload.pop('efficacy_views')
    payload['supporting_evidence_views'] = {
        'coverage_mode': 'complete', 'facts': views.supporting,
    }
    site = tmp_path / 'supporting'
    b.render_report_b_site(b.ReportBPortalData.model_validate(payload), site)
    html = (site / 'subgroups-supporting-evidence.html').read_text(encoding='utf-8')
    groups, _ = json.JSONDecoder().raw_decode(
        html.split('window.__CHART_GROUPS__ = ', 1)[1].lstrip(),
    )
    rows = [row for group in groups for row in group['rows'] if row['_domain'] == 'supporting']
    assert {row['row_id'] for row in rows} == {row['row_id'] for row in views.supporting}
    assert {row['source_domain'] for row in rows} == {domain}
    assert {row['source_metric'] for row in rows} == {row['metric'] for row in views.supporting}
    assert all(row['value'] == 3 and row['unit'] == unit for row in rows)
    assert all(row['clinical_concept_label_zh'] != '临床概念未列示' for row in rows)
    assert all(row['clinical_concept'].startswith('supporting:') for row in rows)
    assert all('临床概念未列示' not in group['title_zh'] for group in groups)
    assert all(not group.get('cross_trial') for group in groups)


def test_supporting_page_never_uses_efficacy_membership_route(monkeypatch: pytest.MonkeyPatch):
    source = _source('Pharmacokinetic Cmax', 'ng/mL', '3', None)
    views = project_unassigned_ctgov_results((source,))
    records = tuple((b._project_record(
        row, domain='supporting', names={}, trial_names={}, fallback=row['row_id'],
    ), row) for row in views.supporting)

    def no_efficacy_route(*args, **kwargs):
        pytest.fail('supporting was incorrectly routed through efficacy membership')

    monkeypatch.setattr(b, 'adjudicate_comparable_membership', no_efficacy_route)
    groups = b._groups_for_page('subgroups-supporting-evidence', records)
    assert len(groups) == 1 and len(groups[0]['rows']) == 2


@pytest.mark.parametrize('axis', ('source_domain', 'source_metric'))
def test_even_approved_wording_cannot_merge_different_supporting_science(axis: str) -> None:
    left, right = _rows()
    for row in (left, right):
        row.update(_domain='supporting', source_domain='pk_pd', source_metric='concentration')
    right[axis] = 'biomarkers' if axis == 'source_domain' else 'area_under_curve'
    merge = _approved(left, right)
    groups = proposed_semantic_buckets(
        (tuple((row, None) for row in (left, right)),), (_proposal(left, right),),
        approved_merges=(merge,),
    )
    assert len(groups) == 2
    assert {row['row_id'] for group in groups for row, _ in group} == {'first', 'second'}


def test_supporting_same_trial_different_measure_instances_remain_separate() -> None:
    views = project_unassigned_ctgov_results((
        _source('Pharmacokinetic Cmax', 'ng/mL', '3', None),
    ))
    first = dict(views.supporting[0])
    second = dict(first, row_id='other-instance', source_measure_path='another-measure-instance')
    records = tuple((b._project_record(
        row, domain='supporting', names={}, trial_names={}, fallback=row['row_id'],
    ), row) for row in (first, second))
    groups = b._groups_for_page('subgroups-supporting-evidence', records)
    assert len(groups) == 2
    assert {row['row_id'] for group in groups for row in group['rows']} == {
        first['row_id'], second['row_id'],
    }
