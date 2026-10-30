"""Turning off new model calls must not discard source-checked facts already in this workspace."""
import hashlib
import json

import pytest
from test_publications import setup as paper_setup

from ciw.sources.captures import extract_events
from ciw.verify.llm import CachedBackend, FakeBackend
from ciw.verify.publications import extract_publications


def cached_roles(ws, items):
    roles = {}
    for name, family in (("extractor_a", "deepseek"), ("verifier", "glm")):
        backend = FakeBackend(family, family, None)
        def reply(system, user, backend=backend):
            backend.receipt = {"response_id": "synthetic_" + hashlib.sha256((system+user).encode()).hexdigest()}
            return json.dumps({"items": items})
        backend.responder = reply
        roles[name] = CachedBackend(backend, ws)
    return roles


def doc_setup(ws):
    folder = ws.root / "captures/docs"
    folder.mkdir()
    text = "MG-K10获批用于慢性鼻窦炎伴鼻息肉，地区为中国和美国。"
    path = folder / "synthetic.txt"
    path.write_text(text)
    path.with_name(path.name+".meta.json").write_text(json.dumps(dict(kind="company", url="https://example.org/news")))
    items = [dict(product_mention="MG-K10", event_type="approval", region=region,
                  indication="慢性鼻窦炎伴鼻息肉", quote=text) for region in ("中国", "美国")]
    return path, items


def test_model_disabled_reuses_both_regions_of_same_product_from_exact_source(cfg, resolver, ws):
    _, items = doc_setup(ws)
    events, issues, _ = extract_events(ws, cfg, resolver, cached_roles(ws, items))
    assert len(events) == 2 and not issues
    ledger = ws.verifications()
    later, later_issues, coverage = extract_events(ws, cfg, resolver, None)
    assert later == events and not later_issues
    assert coverage[0]["extracted"] == 1 and coverage[0]["events"] == 2
    assert coverage[0]["status"] == "ok" and coverage[0]["extraction_status"] == "cached_only"
    assert ws.verifications() == ledger  # No new approval, model call, or rewritten historical receipt.


def test_model_disabled_reprojects_all_paper_items_with_current_bindings(cfg, resolver, ws):
    paper, trial, item = paper_setup(ws)
    items = [item, dict(item, population="eosinophilic population")]
    before, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, cached_roles(ws, items))
    assert len(before) == 2 and not issues
    ledger = ws.verifications()
    after, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, None)
    assert after == before and not issues and ws.verifications() == ledger
    trial.relevance = "background"
    after, issues = extract_publications(ws, cfg, [paper], {trial.trial_id: trial}, resolver, None)
    assert not after and all(i["kind"] == "publication_unbound" for i in issues)


@pytest.mark.parametrize("fault", ["source", "task", "status", "review_response", "missing_review"])
def test_retained_source_items_need_current_task_and_original_verifier_proof(cfg, resolver, ws, fault):
    path, items = doc_setup(ws)
    before, _, _ = extract_events(ws, cfg, resolver, cached_roles(ws, items))
    assert len(before) == 2
    if fault == "source":
        path.write_text(path.read_text()+" This is a changed source version.")
    else:
        with ws.db() as con:
            if fault == "review_response":
                con.execute("UPDATE llm_cache SET response=? WHERE family='glm'", ('{"items":[]}',))
            else:
                for key, payload in con.execute("SELECT fact_key,payload FROM verifications").fetchall():
                    record = json.loads(payload)
                    if fault == "task":
                        record["task"] = "different-instruction-task"
                    if fault == "missing_review":
                        record["calls"] = [c for c in record["calls"] if c["role"] == "extract"]
                    con.execute("UPDATE verifications SET status=?,payload=? WHERE fact_key=?",
                        ("needs_review" if fault == "status" else "verified", json.dumps(record), key))
    after, issues, coverage = extract_events(ws, cfg, resolver, None)
    if fault == "status":
        assert len(after) == 2 and {e.status for e in after} == {"needs_review"}
        assert any(i["kind"] == "event_needs_review" for i in issues)
    else:
        assert not after and any(i["kind"] == "doc_not_extracted" for i in issues)
    assert coverage[0]["status"] == "partial"


@pytest.mark.parametrize("changed", [False, True])
def test_a_repair_for_another_identity_does_not_revoke_good_items_or_confirm_stale_ones(cfg, resolver, ws, changed):
    from ciw.verify.schemas import EventItem

    _, items = doc_setup(ws)
    before, _, _ = extract_events(ws, cfg, resolver, cached_roles(ws, items))
    assert len(before) == 2
    repaired = EventItem.model_validate(items[0]).model_dump()
    if changed:
        repaired["detail"] = "A later different reviewed item"
    with ws.db() as con:
        con.execute("INSERT INTO llm_cache VALUES (?,?,?,?,?,?,?)", (
            "synthetic-repair", "glm", "glm", "synthetic-prompt", json.dumps({"items": [repaired]}),
            "2026-01-01", json.dumps({"response_id": "synthetic-repair-response"})))
        for key, payload in con.execute("SELECT fact_key,payload FROM verifications").fetchall():
            record = json.loads(payload)
            record["calls"].append(dict(role="verify_repair", family="glm", model="glm", n_items=1,
                                        response_id="synthetic-repair-response"))
            con.execute("UPDATE verifications SET payload=? WHERE fact_key=?", (json.dumps(record), key))
    after, issues, coverage = extract_events(ws, cfg, resolver, None)
    assert {e.region for e in after} == ({"美国"} if changed else {"中国", "美国"})
    assert bool(issues) == changed
    assert coverage[0]["status"] == ("partial" if changed else "ok")
    if changed:
        assert issues[0]["kind"] == "doc_cached_review_incomplete"
