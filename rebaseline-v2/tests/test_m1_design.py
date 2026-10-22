import json

import pytest

from ciw2.render.portal import data_c, render_report
from ciw2.sources.ctgov import design_facts, parse_study
from ciw2.store.db import DB


@pytest.fixture
def design_project(settings):
    settings.ensure_dirs()
    db = DB(settings.db_path)
    pid = db.create_project('设计比较', ['C'])
    trial, _ = db.upsert_entity(pid, 'trial', 'trial-one', attrs={'url': 'https://example.org/trial'})
    source = db.add_source(pid, 'ctgov', 'https://example.org/source', 'digest')
    return db, pid, trial, source


def add_fact(project, field, value, status='verified', **context):
    db, pid, trial, source = project
    return db.add_fact({'project_id': pid, 'entity_id': trial, 'field': field, 'value': value,
                        'source_id': source, 'tier': 'critical', 'status': status,
                        'quote': 'Original design evidence', 'context': context, 'extracted_by': 'code:test'})


def test_unverified_size_is_visible_but_never_charted(design_project):
    add_fact(design_project, 'design.sample_size', 100, 'unverified')
    data = data_c(*design_project[:2])
    assert data['rows'][0]['sample_size'] == 100
    assert data['charts']['size']['values'] == []


def test_design_sources_and_enrollment_kind_are_reachable(design_project):
    fid = add_fact(design_project, 'design.sample_size', 0, enrollment_type='ESTIMATED')
    row = data_c(*design_project[:2])['rows'][0]
    assert row['sample_size'] == 0
    assert row['sample_size_type'] == 'ESTIMATED'
    assert row['sources']['sample_size'][0]['fact_id'] == fid
    assert row['sources']['sample_size'][0]['url'] == 'https://example.org/source'
    assert row['sources']['sample_size'][0]['quote'] == 'Original design evidence'


def test_visit_groups_use_exact_equivalence_and_retain_unknowns(design_project):
    for endpoint, visit in [('EASI-75', 'Week 16'), ('EASI-75', 'Day 112'),
                             ('EASI-75', 'Week 24'), ('EASI-75', 'during treatment')]:
        add_fact(design_project, 'design.primary_endpoint', {'measure': endpoint, 'time_frame': visit})
    groups = data_c(*design_project[:2])['endpoint_groups']
    assert sorted(len(g['entries']) for g in groups) == [1, 1, 2]
    assert sum(len(g['entries']) for g in groups) == 4
    assert all(e['fact_id'] for g in groups for e in g['entries'])


def test_registry_eligibility_is_retained_and_thresholds_are_explicit(design_project, study):
    criteria = 'Inclusion Criteria:\n- EASI >= 16\n- IGA >= 3\nExclusion Criteria:\n- active infection'
    study['protocolSection']['eligibilityModule']['eligibilityCriteria'] = criteria
    parsed = design_facts(parse_study(study))
    fact = next(f for f in parsed if f['field'] == 'design.eligibility.criteria')
    assert fact['value'] == criteria and fact['context']['json_path']
    add_fact(design_project, fact['field'], fact['value'])
    row = data_c(*design_project[:2])['rows'][0]
    assert row['eligibility_criteria'] == criteria
    assert {(v['measure'], v['operator'], v['value']) for v in row['eligibility_thresholds']} == {
        ('EASI', '>=', 16.0), ('IGA', '>=', 3.0)}


def test_structured_chart_data_cannot_break_out_of_script(design_project):
    attack = '</script><script>globalThis.INJECTED=true</script>'
    add_fact(design_project, 'design.sample_size', 100)
    add_fact(design_project, 'design.primary_endpoint', {'measure': attack, 'time_frame': 'Week 16'})
    design_project[0].execute('UPDATE entities SET name=? WHERE id=?', (attack, design_project[2]))
    html = render_report(*design_project[:2], 'C')
    assert attack not in html
    payload = html.split('<script id="charts" type="application/json">', 1)[1].split('</script>', 1)[0]
    json.loads(payload)


def test_c_has_comparison_and_inline_original_evidence(design_project):
    add_fact(design_project, 'design.sample_size', 100)
    add_fact(design_project, 'design.primary_endpoint', {'measure': 'EASI-75', 'time_frame': 'Week 16'})
    html = render_report(*design_project[:2], 'C')
    assert '终点与时间点' in html and 'Original design evidence' in html
    assert 'https://example.org/source' in html and 'data-fact-id=' in html


def test_single_visit_and_interval_are_not_merged(design_project):
    for visit in ('Week 16', 'Baseline to Week 16', 'Week 16 and Week 24'):
        add_fact(design_project, 'design.primary_endpoint', {'measure': 'EASI-75', 'time_frame': visit})
    groups = data_c(*design_project[:2])['endpoint_groups']
    assert len(groups) == 3


def test_phase_counts_do_not_use_unverified_phase(design_project):
    add_fact(design_project, 'design.phase', 'phase3', 'unverified')
    data = data_c(*design_project[:2])
    assert data['rows'][0]['phase'] == 'phase3'
    assert data['charts']['phase'] == []


def test_thresholds_keep_inclusion_exclusion_and_whole_rule(design_project):
    text = 'Inclusion Criteria:\nEASI >= 16 and IGA >= 3\nExclusion Criteria:\nBSA > 80%'
    add_fact(design_project, 'design.eligibility.criteria', text)
    terms = data_c(*design_project[:2])['rows'][0]['eligibility_thresholds']
    assert [(t['measure'], t['section']) for t in terms] == [
        ('EASI', 'inclusion'), ('IGA', 'inclusion'), ('BSA', 'exclusion')]
    assert terms[0]['rule_text'] == 'EASI >= 16 and IGA >= 3'


def test_empty_report_does_not_publish_model_process_explanations(design_project):
    findings = {'findings': [{'title': '输入 data.rows 为空', 'bullets': ['本工作单元不能核实，不作为设计依据'], 'fact_refs': []}]}
    html = render_report(*design_project[:2], 'C', findings=findings)
    assert 'data.rows' not in html and '本工作单元' not in html
    assert '尚未取得试验设计资料' in html


def test_summary_requires_current_verified_fact_references(design_project):
    verified = add_fact(design_project, 'design.sample_size', 100)
    unverified = add_fact(design_project, 'design.phase', 'phase3', 'unverified')
    findings = {'findings': [{'title': title, 'bullets': ['描述'], 'fact_refs': refs} for title, refs in (
        ('可追溯的医学要点', [verified]), ('无引用的说明', []), ('引用不存在', ['missing']), ('尚未核实结论', [unverified]))]}
    html = render_report(*design_project[:2], 'C', findings=findings)
    assert '可追溯的医学要点' in html
    assert all(title not in html for title in ('无引用的说明', '引用不存在', '尚未核实结论'))


def test_c_chinese_display_preserves_full_design_and_source_data(design_project):
    from html.parser import HTMLParser

    add_fact(design_project, 'design.sample_size', 0, enrollment_type='ESTIMATED')
    for field, value in [('status.trial', 'COMPLETED'), ('design.allocation', 'RANDOMIZED'),
                         ('design.masking', 'DOUBLE'), ('design.eligibility.age', {'min': '0 Years', 'max': '18.50 Years'}),
                         ('design.arms', [{'label': 'Original arm', 'type': 'EXPERIMENTAL',
                            'description': 'Complete original dose schedule', 'interventions': ['DRUG: Original compound']}])]:
        add_fact(design_project, field, value)
    before = json.dumps(data_c(*design_project[:2]), sort_keys=True)
    html = render_report(*design_project[:2], 'C')

    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []

        def handle_data(self, data):
            self.parts.append(data)

    parser = Text()
    parser.feed(html)
    text = ''.join(parser.parts)
    for expected in ('已完成', '随机分组', '双盲', '试验组', '0岁', '18.50岁', '计划',
                     'Complete original dose schedule', 'DRUG: Original compound'):
        assert expected in text
    assert 'COMPLETED' not in text and 'RANDOMIZED' not in text and 'DOUBLE' not in text
    assert json.dumps(data_c(*design_project[:2]), sort_keys=True) == before


def test_c_comparison_groups_seven_reading_columns_and_keeps_whole_or_clause(design_project):
    import re

    add_fact(design_project, 'design.sample_size', 100)
    add_fact(design_project, 'design.eligibility.criteria', 'Inclusion Criteria:\nEASI >= 16 OR IGA >= 3')
    html = render_report(*design_project[:2], 'C')
    header = html.split('id="tbl-c"', 1)[1].split('</thead>', 1)[0]
    assert len(re.findall(r'<th(?:>|\s)', header)) == 7
    assert 'class="eligibility-key"' in html
    key_rules = html.split('class="eligibility-key"', 1)[1].split('</details>', 1)[0]
    assert key_rules.count('EASI &gt;= 16 OR IGA &gt;= 3') == 1
    assert '完整入排与依据' in html and 'https://example.org/source' in html


def test_report_first_screen_uses_clinical_counts_not_duplicate_engineering_kpis(design_project):
    db, pid = design_project[:2]
    rid = db.create_run(pid)
    db.log_coverage(rid, 'global:test-source', 'global', 'public query', 'ok', hits=5)
    add_fact(design_project, 'design.sample_size', 100)
    html = render_report(db, pid, 'C')
    kpis = html.split('class="kpis"', 1)[1].split('</div>', 1)[0]
    assert '检索路线成功' not in kpis
    assert '试验设计' in kpis and 'global:test-source' in html
    assert '关注点：未指定' not in html


def test_report_reading_roles_do_not_use_tiny_fonts():
    import re
    from pathlib import Path

    css = (Path(__file__).resolve().parents[1] / 'src/ciw2/render/static/kangzhe.css').read_text()
    sizes = [float(x) for x in re.findall(r'font-size:\s*(\d+(?:\.\d+)?)px', css)]
    assert sizes and min(sizes) >= 16
    assert '--report-font-body:16px' in css


def test_c_expanded_definition_is_complete_and_identical_criteria_not_repeated(design_project):
    from markupsafe import escape

    definition = 'Complete endpoint definition: baseline assessment AND threshold, without truncation.'
    add_fact(design_project, 'design.primary_endpoint', {
        'measure': 'Original endpoint', 'description': definition, 'time_frame': 'Week 16'})
    db, pid, trial, source = design_project
    criteria = 'Inclusion Criteria:\nEASI >= 16 OR IGA >= 3'
    fid = db.add_fact({'project_id': pid, 'entity_id': trial, 'field': 'design.eligibility.criteria',
        'value': criteria, 'quote': criteria, 'tier': 'standard', 'status': 'verified',
        'source_id': source, 'extracted_by': 'code:test'})
    html = render_report(db, pid, 'C')
    assert definition in html
    assert html.count(str(escape(criteria))) == 1
    assert f'data-fact-id="{fid}"' in html and 'https://example.org/source' in html


def test_secondary_source_atoms_preserve_each_full_definition_and_locator(study):
    endpoints = [{'measure': 'Same scale', 'timeFrame': 'Week 16', 'description': 'Definition A'},
                 {'measure': 'Same scale', 'timeFrame': 'Week 24', 'description': 'Definition B'}]
    study['protocolSection']['outcomesModule']['secondaryOutcomes'] = endpoints
    facts = [f for f in design_facts(parse_study(study)) if f['field'] == 'design.secondary_endpoint']
    assert [f['value'] for f in facts] == [
        {'measure': e['measure'], 'time_frame': e['timeFrame'], 'description': e['description']} for e in endpoints]
    assert [f['context']['json_path'] for f in facts] == [
        'outcomesModule.secondaryOutcomes[0]', 'outcomesModule.secondaryOutcomes[1]']


def test_all_secondary_instances_survive_report_and_summary_without_last_wins(design_project):
    from ciw2.pipeline.stages import _compact

    ids = [add_fact(design_project, 'design.secondary_endpoint', {
        'measure': 'Secondary scale', 'time_frame': visit, 'description': definition})
        for visit, definition in [('Week 16', 'Exact secondary definition A'),
                                 ('Week 24', 'Exact secondary definition B'),
                                 ('Week 24', 'Exact secondary definition B')]]
    data = data_c(*design_project[:2])
    row = data['rows'][0]
    assert {e['fact_id'] for e in row['secondary_endpoints']} == set(ids)
    assert 'secondary_endpoint' not in row
    compact = _compact(data)['rows'][0]['secondary_endpoints']
    assert {e['fact_id'] for e in compact} == set(ids)
    assert len(compact) == 3 and {e['description'] for e in compact} == {
        'Exact secondary definition A', 'Exact secondary definition B'}
    html = render_report(*design_project[:2], 'C')
    assert '次要终点' in html
    assert all(f'data-fact-id="{fid}"' in html for fid in ids)
    assert all(text in html for text in ('Exact secondary definition A', 'Exact secondary definition B'))


def test_endpoint_groups_keep_role_and_definition_separate(design_project):
    for field, definition in [('design.primary_endpoint', 'Definition A'),
                              ('design.secondary_endpoint', 'Definition A'),
                              ('design.secondary_endpoint', 'Definition B')]:
        add_fact(design_project, field, {'measure': 'Same measure', 'description': definition, 'time_frame': 'Week 16'})
    groups = data_c(*design_project[:2])['endpoint_groups']
    assert len(groups) == 3
    assert sorted(g['kind'] for g in groups) == ['primary', 'secondary', 'secondary']
    assert all(len(g['entries']) == 1 for g in groups)
