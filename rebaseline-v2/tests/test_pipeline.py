from conftest import PAPER_TEXT, PAPER_URL, fake_llm_responder

from ciw2.harness.llm import LLMReply, ScriptedLLM, ToolCall
from ciw2.render.portal import report_data
from ciw2.service import Service
from ciw2.sources.http import register_text


def _svc(settings):
    return Service(settings, llm_factory=lambda s: (ScriptedLLM(fake_llm_responder), None))


def test_end_to_end_abc(settings, offline_ctgov, monkeypatch):
    from ciw2.sources import websearch
    from ciw2.sources.http import Fetched

    def fetch_paper(ctx, url, **kwargs):
        assert url == PAPER_URL
        sid = register_text(ctx, kind='pubmed', url=url, text=PAPER_TEXT)
        return Fetched(sid, url, 200, PAPER_TEXT.encode(), PAPER_TEXT, 'text/plain')

    def read_then_submit(messages):
        if '# Skill：extract-results' in messages[0]['content'] and not any(
                m['role'] == 'assistant' for m in messages):
            return LLMReply(tool_calls=[ToolCall(id='read-paper',name='fetch_url',arguments={'url':PAPER_URL})])
        return fake_llm_responder(messages)

    monkeypatch.setattr(websearch,'fetch',fetch_paper)
    svc = Service(settings,llm_factory=lambda s:(ScriptedLLM(read_then_submit),None))
    pid = svc.create_project("特应性皮炎", ["A", "B", "C"], request_text="看 IL-31 通路竞品")
    run_id = svc.db.create_run(pid)
    svc.start_run(pid, resume_run=run_id, background=False)

    run = svc.db.one("SELECT * FROM runs WHERE id=?", (run_id,))
    stages = {r["name"]: r for r in svc.db.query("SELECT * FROM stages WHERE run_id=?", (run_id,))}
    assert run["status"] == "succeeded", (run, {k: v["error"] for k, v in stages.items() if v["error"]})
    assert all(s["status"] == "succeeded" for s in stages.values())

    drugs = svc.db.entities(pid, "drug")
    assert {d["name"]: d["in_scope"] for d in drugs} == {"nemolizumab": 1, "placebo-like-noise": 0}

    # 原文核验：真实片段通过；编造片段与未读取来源不通过
    llm_facts = [f for f in svc.db.current_facts(pid) if f["extracted_by"].startswith("llm:")
                 and f["field"].startswith("result.")]
    by_val = {f["value"]: f["status"] for f in llm_facts}
    assert by_val == {35.6: "verified", 41.2: "unverified", 12.0: "unverified"}

    a = report_data(svc.db, pid, "A")
    assert a["rows"][0]["name"] == "nemolizumab" and a["rows"][0]["n_trials"] == 1
    b = report_data(svc.db, pid, "B")
    assert b["charts"]["groups"] and b["unverified_critical"] >= 2
    assert all(v != 41.2 for g in b["charts"]["groups"] for v in g["values"])   # 未核实不上图
    c = report_data(svc.db, pid, "C")
    assert c["rows"][0]["trial"] == "NCT03985943" and c["rows"][0]["sample_size"] == 941

    out = settings.portals_dir / pid
    assert {p.name for p in out.iterdir()} == {"A.html", "B.html", "C.html"}
    assert "nemolizumab" in (out / "A.html").read_text(encoding="utf-8")

    cov = svc.db.query("SELECT DISTINCT route_id FROM coverage WHERE run_id=?", (run_id,))
    assert {"china:ctgov:condition", "global:ctgov:condition", "trial:ctgov:intervention"} <= {r["route_id"] for r in cov}


def test_resume_skips_succeeded_stages(settings, offline_ctgov):
    calls = {"n": 0}

    def flaky(messages):
        if "# Skill：coverage-review" in messages[0]["content"] and calls["n"] == 0:
            calls["n"] += 1
            raise RuntimeError("模拟 LLM 故障")
        return fake_llm_responder(messages)

    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM(flaky), None))
    pid = svc.create_project("特应性皮炎", ["A"])
    rid = svc.start_run(pid, background=False)
    assert svc.db.one("SELECT status FROM runs WHERE id=?", (rid,))["status"] == "failed"
    svc.start_run(pid, resume_run=rid, background=False)
    assert svc.db.one("SELECT status FROM runs WHERE id=?", (rid,))["status"] == "succeeded"
    intake_steps = svc.db.query("SELECT COUNT(*) n FROM agent_steps WHERE run_id=? AND skill='intake' AND role='task'",
                                (rid,))
    assert intake_steps[0]["n"] == 1   # intake 没有重跑


def test_resume_failed_discovery_invalidates_empty_downstream_results(settings, offline_ctgov):
    unavailable = {'value': True}

    def responder(messages):
        if unavailable['value'] and '# Skill：universe-' in messages[0]['content']:
            raise RuntimeError('discovery temporarily unavailable')
        return fake_llm_responder(messages)

    svc = Service(settings, llm_factory=lambda s: (ScriptedLLM(responder), None))
    pid = svc.create_project('特应性皮炎', ['C'])
    rid = svc.start_run(pid, background=False)
    assert report_data(svc.db, pid, 'C')['rows'] == []
    unavailable['value'] = False
    svc.start_run(pid, resume_run=rid, background=False)
    assert len(report_data(svc.db, pid, 'C')['rows']) == 1
    assert svc.db.one("SELECT COUNT(*) n FROM agent_steps WHERE run_id=? AND skill='intake' AND role='task'",
                      (rid,))['n'] == 1


def test_resumed_run_does_not_display_previous_downstream_success(settings, monkeypatch):
    from ciw2.pipeline import runner
    from ciw2.pipeline.stages import Stage

    svc = _svc(settings)
    pid = svc.create_project('重试', ['C'])
    rid = svc.db.create_run(pid)
    # Fixture represents an ordinary run that already entered this runner.
    assert runner.stage_versions.ensure_pipeline_scope(svc.context(pid, rid))
    svc.db.set_stage(rid, 'upstream', 'failed', error='old failure')
    svc.db.set_stage(rid, 'downstream', 'succeeded', output={'obsolete': True})

    def upstream(rc):
        state = rc.db.one('SELECT status FROM stages WHERE run_id=? AND name=?', (rid, 'downstream'))
        assert state['status'] == 'pending'
        assert rc.db.stage_output(rid, 'downstream') is None
        return {}

    monkeypatch.setattr(runner, 'STAGES', [Stage('upstream', upstream), Stage('downstream', lambda rc: {})])
    assert runner.execute(svc.context(pid, rid)) == 'succeeded'
