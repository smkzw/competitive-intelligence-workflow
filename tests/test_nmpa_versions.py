"""Version fresh public certificate observations without overwriting historical captures."""
import copy
import json

import pytest
from test_nmpa import certificate

from ciw.sources.nmpa.capture import capture
from ciw.sources.nmpa.registry import ingest


def save_old(ws, raw):
    folder = ws.root / "captures/nmpa"
    folder.mkdir(parents=True)
    path = folder / f"certificate-{raw['registration_number']}.json"
    path.write_text(json.dumps(raw, ensure_ascii=False))
    return path


def fresh_browser(monkeypatch, raw, status="ok"):
    calls = []

    def browser(name, config, *args, **kwargs):
        calls.append(name)
        if config["category"] != raw["category"]:
            return [], {"status": "ok", "records": 0}
        return [raw], {"status": status, "records": 1}

    monkeypatch.setattr("ciw.sources.nmpa.capture.run_script", browser)
    return calls


def test_changed_complete_row_versions_old_certificate_and_ingests_latest(cfg, resolver, ws, monkeypatch):
    old = certificate()
    path = save_old(ws, old)
    old_bytes = path.read_bytes()
    new = copy.deepcopy(old)
    new["observed_at"] = "2026-10-30T00:00:00+00:00"
    new["rows"][5][1] = "New holder legal entity"
    fresh_browser(monkeypatch, new, status="failed")
    result = capture(ws, cfg, 58)
    assert result["details"] == 1 and result["resumed"] == 0
    assert path.read_bytes() == old_bytes
    versions = list(path.parent.glob("certificate-*.json"))
    assert len(versions) == 2
    events, issues, coverage = ingest(ws, resolver)
    assert not issues and len(events) == 1
    assert "New holder legal entity" in events[0].detail
    assert coverage["adopted"] == 1 and coverage["status"] == "partial"
    assert coverage["failed_queries"]
    assert len(coverage["detail_missing"]) == 0
    assert ws.read_source(events[0].source_id) == next(p.read_bytes() for p in versions if p != path)


def test_same_record_new_observation_reuses_parse_without_overwriting(cfg, ws, monkeypatch):
    old = certificate()
    path = save_old(ws, old)
    before = path.read_bytes()
    new = copy.deepcopy(old)
    new.update(observed_at="2026-10-30T00:00:00+00:00", query="度普利尤单抗", total="共 1 条")
    calls = fresh_browser(monkeypatch, new)
    result = capture(ws, cfg, 58)
    assert result["resumed"] == 1 and result["details"] == 0
    assert set(calls) == {"browser.mjs"}
    assert path.read_bytes() == before and len(list(path.parent.glob("certificate-*.json"))) == 1
    assert any(json.loads(p.read_text())["rows"] == [new] for p in path.parent.glob("list-*.json"))


def test_bad_historical_capture_is_preserved_when_valid_fresh_detail_arrives(cfg, ws, monkeypatch):
    raw = certificate()
    path = save_old(ws, raw)
    path.write_text('{"historical": "incomplete"}')
    before = path.read_bytes()
    fresh_browser(monkeypatch, raw)
    result = capture(ws, cfg, 58)
    assert result["details"] == 1 and path.read_bytes() == before
    assert len(list(path.parent.glob("certificate-*.json"))) == 2


def test_ingestion_chooses_observed_version_not_filename_and_does_not_duplicate(resolver, ws):
    old = certificate()
    path = save_old(ws, old)
    new = copy.deepcopy(old)
    new["observed_at"] = "2026-10-30T00:00:00+00:00"
    new["rows"][5][1] = "New holder"
    (path.parent / "certificate-aaa.json").write_text(json.dumps(new))
    events, issues, coverage = ingest(ws, resolver)
    assert not issues and len(events) == 1 and "New holder" in events[0].detail
    assert coverage["adopted"] == 1 and coverage["status"] == "ok"
    assert path.exists()


def test_same_observation_time_conflicting_records_are_not_arbitrarily_selected(resolver, ws):
    raw = certificate()
    path = save_old(ws, raw)
    changed = copy.deepcopy(raw)
    changed["rows"][5][1] = "Conflicting holder"
    (path.parent / "certificate-other.json").write_text(json.dumps(changed))
    events, issues, coverage = ingest(ws, resolver)
    assert not events and coverage["status"] == "partial"
    assert any(i["kind"] == "nmpa_capture_conflict" for i in issues)


def test_later_record_can_revert_to_historical_content_without_selecting_stale_version(cfg, resolver, ws, monkeypatch):
    original = certificate()
    path = save_old(ws, original)
    changed = copy.deepcopy(original)
    changed["observed_at"] = "2026-10-28T00:00:00+00:00"
    changed["rows"][5][1] = "Interim holder"
    (path.parent / "certificate-interim.json").write_text(json.dumps(changed))
    fresh = copy.deepcopy(original)
    fresh["observed_at"] = "2026-10-30T00:00:00+00:00"
    # Production-generated names must be used for the historical versions under test.
    (path.parent / "certificate-interim.json").rename(
        path.parent / f"certificate-{original['registration_number']}-interim.json")
    fresh_browser(monkeypatch, fresh)
    result = capture(ws, cfg, 58)
    events, issues, _ = ingest(ws, resolver)
    assert result["details"] == 1 and not issues and len(events) == 1
    assert "Interim holder" not in events[0].detail
    assert json.loads(ws.read_source(events[0].source_id))["observed_at"] == fresh["observed_at"]
    assert len(list(path.parent.glob("certificate-*.json"))) == 3


def test_fast_queries_preserve_each_catalogue_observation(cfg, ws, monkeypatch):
    from ciw.sources.nmpa.parser import DOMESTIC, FOREIGN

    monkeypatch.setattr("ciw.sources.nmpa.capture.now_iso", lambda: "2026-10-30T01:00:00+00:00")
    monkeypatch.setattr("ciw.sources.nmpa.capture.run_script", lambda *a, **k: ([], {"status": "ok", "records": 0}))
    cfg = cfg.model_copy(deep=True)
    cfg.china.nmpa_queries = ["one", "two"]
    capture(ws, cfg, 58)
    docs = [json.loads(p.read_text()) for p in (ws.root / "captures/nmpa").glob("list-*.json")]
    assert len(docs) == 4
    assert {(doc["query"], doc["category"]) for doc in docs} == {
        (query, category) for query in cfg.china.nmpa_queries for category in (DOMESTIC, FOREIGN)}


@pytest.mark.parametrize("observed_at", ["2026-10-30T00:00:00", "invalid"])
def test_invalid_observation_cannot_replace_a_valid_certificate(cfg, resolver, ws, monkeypatch, observed_at):
    raw = certificate()
    path = save_old(ws, raw)
    original = path.read_bytes()
    fresh = copy.deepcopy(raw)
    fresh["observed_at"] = observed_at
    fresh["rows"][5][1] = "New holder"
    fresh_browser(monkeypatch, fresh)
    result = capture(ws, cfg, 58)
    assert len(result["failures"]) == 1 and result["details"] == 0
    assert path.read_bytes() == original and len(list(path.parent.glob("certificate-*.json"))) == 1
    events, issues, _ = ingest(ws, resolver)
    assert not issues and len(events) == 1 and "New holder" not in events[0].detail
