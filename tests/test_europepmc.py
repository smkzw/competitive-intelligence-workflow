"""Synthetic API cases; not publication evidence or model acceptance."""

import json
from urllib.error import HTTPError

from ciw.sources.europepmc import discover


def seed(ws, papers, url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=test"):
    ws.record_source(
        kind="europepmc", url=url, data=json.dumps({"resultList": {"result": papers}}).encode(), ext="json"
    )


def paper(title="Synthetic randomized trial", text="Registered as NCT12345678. Mean response was 2.3."):
    return {
        "source": "MED",
        "id": "12345678",
        "title": title,
        "abstractText": text,
        "pubTypeList": {"pubType": ["Journal Article"]},
    }


def test_offline_exact_binding_and_content_deduplication(ws):
    seed(ws, [paper(), paper(text="Background citation only; no registration ID.")])
    seed(ws, [paper()], url="https://example.com/second-lookup")
    rows, cov = discover(ws, ["NCT12345678"], offline=True)
    assert len(rows) == 1 and rows[0]["registry_ids"] == ["NCT12345678"]
    assert rows[0]["path"].endswith("abstractText") and cov["eligible"] == 1


def test_review_and_posthoc_remain_discoverable_but_not_primary_results(ws):
    review = paper()
    review["pubTypeList"]["pubType"] = ["Review"]
    seed(
        ws,
        [
            review,
            paper(title="Synthetic post hoc analysis of a trial"),
            paper(title="Rationale and design of synthetic trial"),
        ],
    )
    rows, cov = discover(ws, ["NCT12345678"], offline=True)
    assert len(rows) == 3 and all(r["excluded_type"] for r in rows) and cov["eligible"] == 0


def test_network_error_preserves_existing_sources_and_is_not_zero_results(ws, monkeypatch):
    seed(ws, [paper()])

    def fail(*args, **kwargs):
        raise HTTPError("https://example.com", 503, "Unavailable", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", fail)
    rows, cov = discover(ws, ["NCT12345678"])
    assert len(rows) == 1 and cov["status"] == "partial" and cov["failures"][0]["http_status"] == 503
    _, offline = discover(ws, ["NCT12345678"], offline=True)
    assert offline["status"] == "partial" and offline["failures"][0]["http_status"] == 503


def test_both_registration_ids_are_preserved_without_assigning_arm_or_numeric_order(ws):
    seed(ws, [paper(text="Trials NCT12345678 and NCT12345679 reported together.")])
    rows, _ = discover(ws, ["NCT12345679", "NCT12345678"], offline=True)
    assert rows[0]["registry_ids"] == ["NCT12345678", "NCT12345679"]
    assert "arm" not in rows[0]


def test_newer_observed_publication_replaces_current_projection_without_rewriting_source(ws):
    original = json.dumps({"resultList": {"result": [paper(text="NCT12345678 mean 2.3.")]}}).encode()
    old = ws.record_source(
        kind="europepmc",
        url="https://example.com/original",
        data=original,
        ext="json",
        fetched_at="2026-01-01T00:00:00Z",
    )
    newer = json.dumps({"resultList": {"result": [paper(text="NCT12345678 corrected mean 2.8.")]}}).encode()
    ws.record_source(
        kind="europepmc",
        url="https://example.com/correction",
        data=newer,
        ext="json",
        fetched_at="2026-02-01T00:00:00Z",
    )
    rows, cov = discover(ws, ["NCT12345678"], offline=True)
    assert len(rows) == 1 and "2.8" in rows[0]["text"] and not cov["version_conflicts"]
    assert ws.read_source(old.source_id) == original and len(ws.sources()) == 2


def test_supplement_fetches_only_unsearched_papers_and_keeps_completed_sources(ws, monkeypatch):
    from ciw.store import now_iso
    completed, missing = "NCT12345678", "NCT12345679"
    seed(ws, [], url=f"https://example.com/search?query=%22{completed}%22")
    ws.write_stage("publication-search", {completed: {"status": "ok", "checked_at": now_iso()}})
    before = [s.model_dump() for s in ws.sources()]
    calls = []

    def fetch(workspace, identifier):
        calls.append(identifier)
        seed(workspace, [], url=f"https://example.com/search?query=%22{identifier}%22")
    monkeypatch.setattr("ciw.sources.europepmc._fetch", fetch)
    _, coverage = discover(ws, [completed, missing], reuse=True)
    assert calls == [missing] and coverage["mode"] == "reuse" and not coverage["pending_ids"]
    assert all(s in [v.model_dump() for v in ws.sources()] for s in before)
    discover(ws, [completed, missing], reuse=True)
    assert calls == [missing]
    _, offline = discover(ws, [completed, missing, "NCT12345680"], offline=True, reuse=True)
    assert calls == [missing] and offline["pending_ids"] == ["NCT12345680"]
    discover(ws, [completed, missing])  # explicit ordinary refresh still checks both
    assert calls == [missing, completed, missing]


def test_reuse_retries_failed_lookup_without_relabelling_cached_hits_as_complete(ws, monkeypatch):
    identifier = "NCT12345678"
    seed(ws, [], url=f"https://example.com/search?query=%22{identifier}%22")
    ws.write_stage("publication-search", {identifier: {"status": "failed", "http_status": 503}})
    calls = []

    def fail(*args):
        calls.append(args[1])
        raise HTTPError("https://example.test", 503, "Unavailable", {}, None)
    monkeypatch.setattr("ciw.sources.europepmc._fetch", fail)
    rows, coverage = discover(ws, [identifier], reuse=True)
    assert calls == [identifier] and not rows
    assert coverage["status"] == "partial" and coverage["failures"][0]["http_status"] == 503
