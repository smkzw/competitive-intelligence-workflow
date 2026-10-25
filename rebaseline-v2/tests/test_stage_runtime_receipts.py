"""Receipt, legacy, plan and transactional recovery cases (offline)."""
from __future__ import annotations

import json

from runtime_resume_helpers import plan, receipts, render_output, service, snapshot, status

from ciw2.pipeline import runner, stage_versions
from ciw2.pipeline.stages import Stage


def test_unverifiable_legacy_receipt_refuses_before_any_callback(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('不可验证旧回执', ['A'])
    run_id = svc.db.create_run(pid)
    svc.db.set_stage(run_id, 'only', 'succeeded', output={'legacy': True})
    svc.db.set_stage(
        run_id,
        f'{stage_versions.RECEIPT_PREFIX}only:old',
        'succeeded',
        output={'schema': 'ciw2-stage-runtime-v0', 'stage': 'only'},
    )
    before = snapshot(svc)
    calls: list[str] = []
    monkeypatch.setattr(runner, 'STAGES', [Stage('only', lambda rc: calls.append('only') or {})])

    assert runner.execute(svc.context(pid, run_id)) == 'failed'
    assert calls == []
    assert snapshot(svc) == before
    run = svc.db.one('SELECT * FROM runs WHERE id=?', (run_id,))
    assert '版本回执' in run['error'] and '恢复候选' in run['error']

def test_changed_factory_config_invalidates_but_mutable_counter_does_not(settings, monkeypatch):
    calls: list[str] = []
    state = {'runs': 0}

    def make(mode: str):
        def run(rc):
            state['runs'] += 1
            calls.append(mode)
            return {'mode': mode}
        return run

    svc = plan(settings, monkeypatch, [Stage('custom', make('a'))])
    pid = svc.create_project('工厂变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['a']

    state['runs'] += 10                              # mutable telemetry, not code identity
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['a']

    monkeypatch.setattr(runner, 'STAGES', [Stage('custom', make('b'))])
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['a', 'b']


def test_changed_stored_output_restarts_at_that_stage(settings, monkeypatch):
    calls: list[str] = []

    def one(rc):
        calls.append('one')
        return {'fresh': 1}

    def two(rc):
        calls.append('two')
        return {'fresh': 2}

    svc = plan(settings, monkeypatch, [Stage('one', one), Stage('two', two)])
    pid = svc.create_project('输出变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    svc.db.set_stage(run_id, 'one', 'succeeded', output={'tampered': True})
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['one', 'two']
    assert svc.db.stage_output(run_id, 'one') == {'fresh': 1}


def test_inserted_middle_stage_marks_old_descendants_pending(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [Stage('one', stub('one')), Stage('two', stub('two'))])
    pid = svc.create_project('插入阶段', ['A'])
    run_id = svc.start_run(pid, background=False)

    monkeypatch.setattr(runner, 'STAGES', [Stage('one', stub('one')),
                                           Stage('middle', stub('middle')),
                                           Stage('two', stub('two'))])
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['middle', 'two']


def test_reordered_predecessor_restarts_at_earliest_affected(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [Stage('one', stub('one')),
                                       Stage('two', stub('two')),
                                       Stage('three', stub('three'))])
    pid = svc.create_project('顺序变更', ['A'])
    run_id = svc.start_run(pid, background=False)

    monkeypatch.setattr(runner, 'STAGES', [Stage('one', stub('one')),
                                           Stage('three', stub('three')),
                                           Stage('two', stub('two'))])
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['three', 'two']


def test_dropped_middle_stage_invalidates_remaining_descendant(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [Stage('one', stub('one')),
                                       Stage('two', stub('two')),
                                       Stage('three', stub('three'))])
    pid = svc.create_project('删除阶段', ['A'])
    run_id = svc.start_run(pid, background=False)

    monkeypatch.setattr(runner, 'STAGES', [Stage('one', stub('one')), Stage('three', stub('three'))])
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['three']


def test_report_filter_change_updates_predecessors_and_reruns_render(settings, monkeypatch):
    calls: list[str] = []

    def stub(name):
        def run(rc):
            calls.append(name)
            return {'stage': name}
        return run

    svc = plan(settings, monkeypatch, [Stage('analysis_A', stub('analysis_A'), frozenset({'A'})),
                                       Stage('analysis_C', stub('analysis_C'), frozenset({'C'})),
                                       Stage('render', stub('render'))])
    pid = svc.create_project('报告类型变更', ['A', 'C'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['analysis_A', 'analysis_C', 'render']

    svc.db.execute("UPDATE projects SET reports=? WHERE id=?", (json.dumps(['A']), pid))
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['render']


def test_stage_metadata_change_is_part_of_the_binding(settings, monkeypatch):
    calls: list[str] = []

    def only(rc):
        calls.append('only')
        return {'ok': True}

    svc = plan(settings, monkeypatch, [Stage('only', only, frozenset({'A', 'B'}))])
    pid = svc.create_project('元数据变更', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['only']

    monkeypatch.setattr(runner, 'STAGES', [Stage('only', only, frozenset({'A'}))])
    calls.clear()
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['only']


def test_legacy_success_prefix_refuses_before_any_callback(settings, monkeypatch):
    svc = service(settings)
    pid = svc.create_project('旧运行', ['A'])
    run_id = svc.db.create_run(pid)
    svc.db.set_stage(run_id, 'one', 'succeeded', output={'legacy': True})
    svc.db.set_stage(run_id, 'two', 'cancelled', error='旧停止')
    before = snapshot(svc)
    calls: list[str] = []

    monkeypatch.setattr(runner, 'STAGES', [
        Stage('one', lambda rc: calls.append('one') or {}),
        Stage('two', lambda rc: calls.append('two') or {})])
    assert runner.execute(svc.context(pid, run_id)) == 'failed'
    assert calls == []
    assert snapshot(svc) == before
    assert receipts(svc, run_id) == []
    row = svc.db.one('SELECT * FROM runs WHERE id=?', (run_id,))
    assert row['status'] == 'failed'
    assert '版本回执' in row['error'] and '恢复候选' in row['error']
    assert svc.db.query('SELECT * FROM agent_steps') == []
    assert svc.db.query('SELECT * FROM sources') == []
    assert svc.db.query('SELECT * FROM facts') == []


def test_legacy_success_after_compatible_prefix_still_refuses(settings, monkeypatch):
    def one(rc):
        return {'kept': 1}

    svc = plan(settings, monkeypatch, [Stage('one', one)])
    pid = svc.create_project('前缀后旧成功', ['A'])
    run_id = svc.start_run(pid, background=False)
    receipt_before = receipts(svc, run_id, 'one')[0]['row']['output_json']

    svc.db.set_stage(run_id, 'two', 'succeeded', output={'legacy': True})
    before = snapshot(svc)
    monkeypatch.setattr(runner, 'STAGES', [Stage('one', one), Stage('two', lambda rc: {'fresh': 2})])
    assert runner.execute(svc.context(pid, run_id)) == 'failed'
    assert snapshot(svc) == before
    assert receipts(svc, run_id, 'one')[0]['row']['output_json'] == receipt_before
    assert receipts(svc, run_id, 'two') == []


def test_receipt_write_failure_rolls_back_stage_success(settings, monkeypatch):
    svc = plan(settings, monkeypatch, [Stage('only', lambda rc: {'ok': True})])
    pid = svc.create_project('回执失败', ['A'])

    def broken(rc, receipt):
        raise RuntimeError('receipt write failed')

    monkeypatch.setattr(stage_versions, 'write_receipt', broken)
    run_id = svc.start_run(pid, background=False)
    assert status(svc, run_id) == 'failed'
    row = svc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?', (run_id, 'only'))
    assert row['status'] == 'failed'
    assert svc.db.stage_output(run_id, 'only') is None
    assert receipts(svc, run_id) == []


def test_failed_stage_is_never_reused(settings, monkeypatch):
    calls: list[str] = []

    def one(rc):
        calls.append('one')
        if calls.count('one') == 1:
            raise RuntimeError('first attempt')
        return {'ok': 1}

    svc = plan(settings, monkeypatch, [Stage('one', one)])
    pid = svc.create_project('失败不复用', ['A'])
    run_id = svc.start_run(pid, background=False)
    assert calls == ['one']
    svc.start_run(pid, resume_run=run_id, background=False)
    assert calls == ['one', 'one']
    assert receipts(svc, run_id, 'one')[0]['receipt']['output_sha256']


def test_unit_cache_and_prior_receipts_survive_stage_rerun(settings, monkeypatch):
    svc = plan(settings, monkeypatch, [Stage('trial_evidence', lambda rc: {'rows': 1}),
                                       Stage('render', render_output)])
    pid = svc.create_project('单元缓存', ['C'])
    run_id = svc.db.create_run(pid)
    assert stage_versions.ensure_pipeline_scope(svc.context(pid, run_id))
    svc.db.set_stage(run_id, 'trial_ingestion:fixture:unit', 'succeeded',
                     output={'result': {'facts_added': 1}, 'sources': []})
    unit_before = svc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?',
                             (run_id, 'trial_ingestion:fixture:unit'))
    assert runner.execute(svc.context(pid, run_id)) == 'succeeded'
    old = receipts(svc, run_id, 'trial_evidence')
    assert len(old) == 1

    original = stage_versions.code_binding

    def changed(name: str):
        return {'components': ['injected-change'], 'digest': 'injected-change'} \
            if name == 'trial_evidence' else original(name)

    monkeypatch.setattr(stage_versions, 'code_binding', changed)
    assert runner.execute(svc.context(pid, run_id)) == 'succeeded'
    assert svc.db.one('SELECT * FROM stages WHERE run_id=? AND name=?',
                      (run_id, 'trial_ingestion:fixture:unit')) == unit_before
    current = receipts(svc, run_id, 'trial_evidence')
    assert len(current) == 2
    assert current[0]['row']['output_json'] == old[0]['row']['output_json']


def test_receipts_are_not_exposed_as_planned_stages(settings, monkeypatch):
    svc = plan(settings, monkeypatch, [Stage('one', lambda rc: {'ok': True})])
    pid = svc.create_project('界面阶段', ['A'])
    run_id = svc.start_run(pid, background=False)
    table = runner.stage_table(svc.db, run_id, ['A'])
    assert [row['name'] for row in table] == ['one']
    assert table[0]['status'] == 'succeeded'
    assert all('stage_version' not in row['name'] for row in table)
