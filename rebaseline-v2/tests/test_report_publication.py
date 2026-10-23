"""Production HTML publication keeps prior bytes on template/write failure."""
import json
from pathlib import Path

import pytest

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline.stages import render
from ciw2.service import Service


def context(settings, reports):
    service=Service(settings,llm_factory=lambda s:(ScriptedLLM([]),None))
    pid=service.create_project('研究',['A','B','C'])
    service.db.execute('UPDATE projects SET reports=? WHERE id=?',(json.dumps(reports),pid))
    rc=service.context(pid,service.db.create_run(pid))
    target=settings.portals_dir/pid
    target.mkdir(parents=True)
    for report in reports:
        (target/f'{report}.html').write_text(f'旧版本 {report}',encoding='utf-8')
    return rc,target


def test_later_template_failure_does_not_overwrite_earlier_report(settings,monkeypatch):
    rc,target=context(settings,['A','B'])
    def template(db,pid,report,**kwargs):
        if report=='B':
            raise ValueError('later template failed')
        return '新版本 A'
    monkeypatch.setattr('ciw2.render.portal.render_report',template)
    with pytest.raises(ValueError,match='later template failed'):
        render(rc)
    assert (target/'A.html').read_text()=='旧版本 A'
    assert (target/'B.html').read_text()=='旧版本 B'


def test_partial_write_failure_keeps_old_html_and_removes_only_owned_temp(settings,monkeypatch):
    rc,target=context(settings,['C'])
    monkeypatch.setattr('ciw2.render.portal.render_report',lambda *a,**kw:'新版本 C')
    original=Path.write_text
    def partial(path,text,**kwargs):
        original(path,text[:1],**kwargs)
        raise OSError('disk write interrupted')
    monkeypatch.setattr(Path,'write_text',partial)
    with pytest.raises(OSError,match='disk write interrupted'):
        render(rc)
    assert (target/'C.html').read_text()=='旧版本 C'
    assert sorted(p.name for p in target.iterdir())==['C.html']


def test_atomic_replace_failure_preserves_single_report_and_clean_retry(settings,monkeypatch):
    rc,target=context(settings,['C'])
    original=Path.replace
    def unavailable(path,destination):
        assert path.parent.parent==target
        assert Path(destination)==target/'C.html'
        raise PermissionError('replace unavailable')
    monkeypatch.setattr(Path,'replace',unavailable)
    with pytest.raises(PermissionError,match='replace unavailable'):
        render(rc)
    assert (target/'C.html').read_text()=='旧版本 C'
    assert sorted(p.name for p in target.iterdir())==['C.html']
    monkeypatch.setattr(Path,'replace',original)
    assert render(rc)=={'files':['C.html']}
    assert (target/'C.html').read_text().startswith('<!doctype html>')


def test_failed_render_stage_resume_skips_completed_upstream(settings,monkeypatch):
    from ciw2.pipeline import runner
    from ciw2.pipeline.stages import Stage
    rc,target=context(settings,['C'])
    visited=[]
    def upstream(_rc):
        visited.append('analysis')
        return {'report':'C','findings':[]}
    monkeypatch.setattr(runner,'stages_for',lambda reports:[Stage('analysis_C',upstream),Stage('render',render)])
    original=Path.replace
    monkeypatch.setattr(Path,'replace',lambda *a:(_ for _ in ()).throw(OSError('replace failed')))
    assert runner.execute(rc)=='failed'
    assert (target/'C.html').read_text()=='旧版本 C'
    monkeypatch.setattr(Path,'replace',original)
    assert runner.execute(rc)=='succeeded'
    assert visited==['analysis']
    assert rc.db.stage_output(rc.run_id,'render')=={'files':['C.html']}


def test_success_returns_only_complete_names_and_keeps_other_artifacts(settings):
    rc,target=context(settings,['A','B','C'])
    (target/'unrelated.txt').write_text('keep',encoding='utf-8')
    assert render(rc)=={'files':['A.html','B.html','C.html']}
    assert all((target/f'{rep}.html').read_text().startswith('<!doctype html>') for rep in ['A','B','C'])
    assert sorted(p.name for p in target.iterdir())==['A.html','B.html','C.html','unrelated.txt']
