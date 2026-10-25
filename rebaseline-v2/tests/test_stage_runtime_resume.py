"""Stage runtime binding: resume compatibility, earliest invalidation, legacy refusal.

The tests use the production runner and a temporary SQLite database. Research
callbacks are stubs: this file proves cache/resume control, not clinical output.
"""
from __future__ import annotations

import json
from dataclasses import replace

from runtime_resume_helpers import plan, receipts, service, status

from ciw2.pipeline import runner, stage_versions
from ciw2.pipeline.runner import stages_for
from ciw2.pipeline.stages import Stage


def test_same_runtime_resume_skips_bound_prefix_and_keeps_failed_stage_pending(settings, monkeypatch):
    calls: list[str] = []

    def one(rc):
        calls.append('one')
        return {'kept': True}

    def two(rc):
        calls.append('two')
        if calls.count('two') == 1:
            raise RuntimeError('temporary source failure')
        return {'completed': True}

    svc = plan(settings, monkeypatch, [Stage('one', one), Stage('two', two)])
    pid = svc.create_project('恢复', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert status(svc, run_id) == 'failed'
    assert calls == ['one', 'two']

    svc.start_run(pid, resume_run=run_id, background=False)
    assert status(svc, run_id) == 'succeeded'
    assert calls == ['one', 'two', 'two']          # the bound prefix was not called again
    assert svc.db.stage_output(run_id, 'one') == {'kept': True}
    assert svc.db.stage_output(run_id, 'two') == {'completed': True}
    assert len(receipts(svc, run_id, 'one')) == 1
    assert len(receipts(svc, run_id, 'two')) == 1
    assert svc.db.query('SELECT * FROM agent_steps') == []   # no model call on either pass


def test_cancelled_continuation_keeps_bound_output_and_runs_only_pending(settings, monkeypatch):
    calls: list[str] = []

    def one(rc):
        calls.append('one')
        return {'kept': True}

    def two(rc):
        calls.append('two')
        svc.cancel_run(rc.project_id, rc.run_id)     # cooperative stop requested after the unit
        return {'kept': 2}

    def three(rc):
        calls.append('three')
        return {'fresh': 3}

    svc = plan(settings, monkeypatch, [Stage('one', one), Stage('two', two), Stage('three', three)])
    pid = svc.create_project('取消恢复', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert status(svc, run_id) == 'cancelled'
    assert calls == ['one', 'two']

    svc.start_run(pid, resume_run=run_id, background=False)
    assert status(svc, run_id) == 'succeeded'
    assert calls == ['one', 'two', 'three']
    assert svc.db.stage_output(run_id, 'two') == {'kept': 2}


def test_changed_coverage_skill_restarts_at_candidate_triage(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [
        Stage('intake', stub('intake')),
        Stage('candidate_triage', stub('candidate_triage')),
        Stage('render', stub('render')),
    ])
    pid = svc.create_project('覆盖复核变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['intake', 'candidate_triage', 'render']

    skill = svc.skills['coverage-review']
    svc.skills['coverage-review'] = replace(skill, body=skill.body + '\n新增复核规则')
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert status(svc, run_id) == 'succeeded'
    assert calls == ['candidate_triage', 'render']    # intake prefix stayed valid


def test_changed_analysis_skill_restarts_at_analysis_c_only(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [
        Stage('analysis_A', stub('analysis_A')),
        Stage('analysis_C', stub('analysis_C')),
        Stage('render', stub('render')),
    ])
    pid = svc.create_project('摘要变更', ['A', 'C'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['analysis_A', 'analysis_C', 'render']

    skill = svc.skills['analysis-c']
    svc.skills['analysis-c'] = replace(skill, body=skill.body + '\n新增摘要规则')
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['analysis_C', 'render']


def test_render_asset_change_reruns_render_without_replaying_research(settings, monkeypatch):
    calls: list[str] = []

    def analysis(rc):
        calls.append('analysis_C')
        return {'findings': []}

    def render(rc):
        calls.append('render')
        return {'files': ['C.html']}

    svc = plan(settings, monkeypatch, [Stage('analysis_C', analysis, frozenset({'C'})),
                                      Stage('render', render)])
    pid = svc.create_project('渲染资产', ['C'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['analysis_C', 'render']
    steps = len(svc.db.query('SELECT * FROM agent_steps'))

    original = stage_versions.assets_digest
    monkeypatch.setattr(stage_versions, 'assets_digest',
                        lambda root, names: original(root, names) + '-changed')
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['render']                       # analysis/model work was not replayed
    assert len(svc.db.query('SELECT * FROM agent_steps')) == steps


def test_assets_digest_tracks_content_and_listing(tmp_path):
    templates = tmp_path / 'templates'
    templates.mkdir()
    page = templates / 'page.html'
    page.write_text('one', encoding='utf-8')
    first = stage_versions.assets_digest(tmp_path, ('templates',))
    page.write_text('two', encoding='utf-8')
    second = stage_versions.assets_digest(tmp_path, ('templates',))
    (templates / 'extra.html').write_text('two', encoding='utf-8')
    third = stage_versions.assets_digest(tmp_path, ('templates',))
    assert first != second != third and first != third


def test_package_file_digest_tracks_source_script_content(tmp_path):
    scripts = tmp_path / 'sources'
    scripts.mkdir()
    script = scripts / 'adapter.mjs'
    script.write_text('first', encoding='utf-8')
    first = stage_versions.package_files_digest(tmp_path, ('sources/adapter.mjs',))
    script.write_text('second', encoding='utf-8')
    second = stage_versions.package_files_digest(tmp_path, ('sources/adapter.mjs',))
    assert first != second


def test_relevant_helper_change_invalidates_from_verify(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [
        Stage('extract_results', stub('extract_results'), frozenset({'B'})),
        Stage('verify', stub('verify')),
        Stage('render', stub('render')),
    ])
    pid = svc.create_project('核验变更', ['B'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['extract_results', 'verify', 'render']

    original = stage_versions.module_digest

    def changed(name: str) -> str:
        return 'changed-verification' if name == 'ciw2.pipeline.verification' else original(name)

    monkeypatch.setattr(stage_versions, 'module_digest', changed)
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['verify', 'render']


def test_trial_evidence_source_parser_change_invalidates_evidence(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [
        Stage('trial_evidence', stub('trial_evidence')),
        Stage('render', stub('render')),
    ])
    pid = svc.create_project('来源解析器变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['trial_evidence', 'render']

    original = stage_versions.module_digest

    def changed(name: str) -> str:
        return 'changed-nmpa-parser' if name == 'ciw2.sources.nmpa_ingest' else original(name)

    monkeypatch.setattr(stage_versions, 'module_digest', changed)
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['trial_evidence', 'render']



def test_source_runtime_change_during_stage_is_not_receipted(settings, monkeypatch):
    original = stage_versions.module_digest

    def stage(rc):
        monkeypatch.setattr(
            stage_versions,
            'module_digest',
            lambda name: 'changed-during-stage'
            if name == 'ciw2.sources.nmpa_ingest' else original(name),
        )
        return {'completed': True}

    svc = plan(settings, monkeypatch, [Stage('trial_evidence', stage)])
    pid = svc.create_project('阶段运行期间源码变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert status(svc, run_id) == 'failed'
    assert svc.db.stage_output(run_id, 'trial_evidence') is None
    assert receipts(svc, run_id, 'trial_evidence') == []
    row = svc.db.one('SELECT error FROM stages WHERE run_id=? AND name=?',
                     (run_id, 'trial_evidence'))
    assert '拒绝记录成功回执' in row['error']


def test_function_digest_uses_loaded_behavior_not_filename_or_line():
    def build(source: str, filename: str):
        namespace: dict = {}
        exec(compile(source, filename, 'exec'), namespace)  # noqa: S102 - local fixture function
        return namespace['f']

    first = build('def f():\n    return 1\n', 'one.py')
    same = build('\n\n# shifted lines\ndef f():\n    return 1\n', 'two.py')
    other = build('def f():\n    return 2\n', 'three.py')
    assert stage_versions.function_digest(first) == stage_versions.function_digest(same)
    assert stage_versions.function_digest(first) != stage_versions.function_digest(other)


def test_changed_stage_default_argument_invalidates(settings, monkeypatch):
    calls: list[str] = []

    def make(default: str):
        def only(rc, result=default):
            calls.append(result)
            return {'value': result}
        return only

    svc = plan(settings, monkeypatch, [Stage('only', make('old'))])
    pid = svc.create_project('阶段默认值变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['old']

    monkeypatch.setattr(runner, 'STAGES', [Stage('only', make('new'))])
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['old', 'new']


def test_factory_callback_behavior_and_config_are_bound(settings, monkeypatch):
    calls: list[str] = []

    def make_callback(value: str):
        def callback():
            return value
        return callback

    def make_stage(callback):
        def run(rc):
            result = callback()
            calls.append(result)
            return {'value': result}
        return run

    svc = plan(settings, monkeypatch, [Stage('only', make_stage(make_callback('old')))])
    pid = svc.create_project('回调身份变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['old']

    monkeypatch.setattr(
        runner, 'STAGES', [Stage('only', make_stage(make_callback('new')))])
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['old', 'new']


def test_actual_stage_factories_bind_primitive_configuration(settings):
    svc = service(settings)
    pid = svc.create_project('工厂配置', ['A', 'B', 'C'])
    run_id = svc.db.create_run(pid)
    rc = svc.context(pid, run_id)
    stages = stages_for(['A', 'B', 'C'])
    bindings = {stage.name: stage_versions.stage_binding(
        rc, stage, [item.name for item in stages[:index]])
        for index, stage in enumerate(stages)}
    assert bindings['universe_china']['callable']['config'] == {'region': 'china'}
    assert bindings['universe_global']['callable']['config'] == {'region': 'global'}
    assert bindings['analysis_A']['callable']['config'] == {'report': 'A'}
    extract_results_config = bindings['extract_results']['callable']['config']
    assert extract_results_config['skill'] == 'extract-results'
    assert extract_results_config['extra']['kind'] == 'function'
    assert extract_results_config['extra']['symbol'] == 'ciw2.pipeline.stages._results_extra'
    assert len(extract_results_config['extra']['code']) == 64
    extract_design_config = bindings['extract_design']['callable']['config']
    assert extract_design_config['skill'] == 'extract-design'
    assert extract_design_config['extra']['kind'] == 'function'
    assert extract_design_config['extra']['symbol'] == 'ciw2.pipeline.stages._design_extra'
    assert len(extract_design_config['extra']['code']) == 64
    assert bindings['universe_china']['code']['digest'] == bindings['universe_global']['code']['digest']
    serialized = json.dumps(bindings, ensure_ascii=False)
    assert str(settings.data_dir) not in serialized
    assert str(settings.skills_dir) not in serialized



def test_changed_universe_expansion_skill_restarts_expansion_and_descendants(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [
        Stage('intake', stub('intake')),
        Stage('universe_expand', stub('universe_expand')),
        Stage('render', stub('render')),
    ])
    pid = svc.create_project('扩展 Skill 变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['intake', 'universe_expand', 'render']

    skill = svc.skills['universe-global']
    svc.skills['universe-global'] = replace(skill, body=skill.body + '\n新增扩展规则')
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['universe_expand', 'render']


def test_changed_skill_tool_order_invalidates_stage(settings, monkeypatch):
    calls: list[str] = []

    def only(rc):
        calls.append('universe_china')
        return {'candidates': []}

    svc = plan(settings, monkeypatch, [Stage('universe_china', only)])
    pid = svc.create_project('Skill 工具顺序变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['universe_china']

    skill = svc.skills['universe-china']
    reordered = replace(skill, tools=list(reversed(skill.tools)))
    assert reordered.tools != skill.tools
    svc.skills['universe-china'] = reordered
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['universe_china']
