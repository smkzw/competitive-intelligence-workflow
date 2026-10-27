"""D20: focus the requested report, reuse acquired research, and preserve committed history."""

import pytest

from ciw.pipeline import run
from ciw.release import load_release


def test_b_and_c_skip_a_attributes_and_publish_only_requested_views(cfg, seeded_ws, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("unrequested enrichment was called")
    monkeypatch.setattr("ciw.pipeline.enrich_attributes", unexpected)
    monkeypatch.setattr("ciw.pipeline._add_publications", lambda *a: None)
    first = run(cfg, seeded_ws, offline=True, report_scope="B", render_reports=["B"], log=lambda *_: None)
    assert load_release(first.release_path)["rendered_reports"] == ["B"]
    assert (first.site_dir / "B/index.html").exists() and not (first.site_dir / "A").exists()
    monkeypatch.setattr("ciw.pipeline._add_publications", unexpected)
    second = run(cfg, seeded_ws, offline=True, report_scope="C", render_reports=["B", "C"], log=lambda *_: None)
    assert load_release(second.release_path)["rendered_reports"] == ["B", "C"]
    assert (second.site_dir / "C/index.html").exists() and not (second.site_dir / "A").exists()


def test_a_does_not_wait_for_clinical_publications(cfg, seeded_ws, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("A waited for B's publication extraction")
    monkeypatch.setattr("ciw.pipeline._add_publications", unexpected)
    result = run(cfg, seeded_ws, offline=True, report_scope="A", render_reports=["A"], log=lambda *_: None)
    assert (result.site_dir / "A/index.html").exists() and not (result.site_dir / "B").exists()


def test_identical_research_preserves_existing_snapshot_bytes(cfg, seeded_ws):
    first = run(cfg, seeded_ws, offline=True, log=lambda *_: None)
    old = first.release_path.read_bytes()
    # A repeated content-addressed write must not replace generated_at or any site bytes.
    from unittest.mock import patch

    import ciw.release
    with patch.object(ciw.release, "now_iso", return_value="2099-01-01T00:00:00+00:00"):
        second = run(cfg, seeded_ws, offline=True, log=lambda *_: None)
    assert second.release_id == first.release_id and first.release_path.read_bytes() == old


def test_modified_old_portal_is_not_silently_overwritten(cfg, seeded_ws):
    from ciw.render.site import render_release
    result = run(cfg, seeded_ws, offline=True, log=lambda *_: None)
    path = result.site_dir / "B/index.html"
    path.write_text("user-preserved-content")
    with pytest.raises(ValueError, match="不可变|已存在|冲突"):
        render_release(result.release_path)
    assert path.read_text() == "user-preserved-content"


def test_continuation_reuses_closed_source_set_without_query_or_download(cfg, seeded_ws, monkeypatch):
    from types import SimpleNamespace

    import yaml

    from ciw.research import _research
    from ciw.verify.llm import FakeBackend
    directory = seeded_ws.root / "indications"
    directory.mkdir()
    (directory / "saved.yaml").write_text(yaml.safe_dump(cfg.model_dump(mode="json")))
    ids = [s.source_id for s in seeded_ws.sources()]
    seeded_ws.write_stage("research-context", dict(config="indications/saved.yaml", source_ids=ids))
    def unexpected(*a, **kw):
        raise AssertionError("continuation restarted the registry search")
    monkeypatch.setattr("ciw.research.plan_query", unexpected)
    monkeypatch.setattr("ciw.research.ctgov.search_and_store", unexpected)
    monkeypatch.setattr("ciw.research.load_roles", lambda _: {"extractor_a": FakeBackend("deepseek", "a", unexpected),
                                                            "verifier": FakeBackend("glm", "b", unexpected)})
    received = {}
    def execute(*a, **kw):
        received.update(kw)
        return SimpleNamespace(release_id="unit-only")
    monkeypatch.setattr("ciw.research.run", execute)
    _research("same disease", seeded_ws, report="C", reuse_research=True, log=lambda *_: None)
    assert received["report_scope"] == "C" and received["render_reports"] == ["C"]
    assert {src.source_id for src, _ in received["preloaded_studies"].values()} == set(ids)


def test_reused_registry_keeps_original_acquisition_dates(cfg, seeded_ws):
    from ciw.sources.ctgov import load_from_sources
    studies = load_from_sources(seeded_ws)
    original = max(s.fetched_at for s, _ in studies.values())
    result = run(cfg, seeded_ws, preloaded_studies=studies, report_scope="C", render_reports=["C"],
                 log=lambda *_: None)
    assert next(c for c in result.coverage if c["source"] == "ctgov")["fetched_at"] == original
    html = (result.site_dir / "C/index.html").read_text()
    assert '../A/index.html' not in html and '../B/index.html' not in html


def test_presentation_update_creates_new_release_without_modifying_old(cfg, seeded_ws, monkeypatch):
    from ciw.render.site import rerender_current
    first = run(cfg, seeded_ws, offline=True, log=lambda *_: None)
    old = (first.site_dir / "B/data.js").read_bytes()
    monkeypatch.setattr("ciw.render.site.presentation_digest", lambda: "new-presentation-only")
    site = rerender_current(seeded_ws)
    assert site != first.site_dir
    assert (first.site_dir / "B/data.js").read_bytes() == old
    assert seeded_ws.current_release_dir() == site.parent


def test_later_design_keeps_adopted_paper_results_and_verified_attributes(cfg, seeded_ws, monkeypatch):
    from ciw.models import Locator, OutcomeResult
    source = seeded_ws.sources()[0]
    paper = seeded_ws.record_source(kind="europepmc", url="https://example.test/paper", ext="txt", data=b"Value 8")
    def attributes(ws, products, *args, **kwargs):
        products["dupilumab"].target = "source-backed-test-target"
        products["dupilumab"].attribute_status = "verified"
        products["dupilumab"].attribute_locators["target"] = Locator(source_id=source.source_id, quote="fixture")
        return []
    def publications(cfg, ws, resolver, trials, results, roles, offline, issues, coverage):
        row = results[0].model_copy(deep=True)
        row.result_id, row.kind, row.status = "paper-fixture", "publication", "verified"
        row.locator = Locator(source_id=paper.source_id, quote="Value 8")
        results.append(OutcomeResult.model_validate(row.model_dump()))
        coverage.append(dict(source="publications", status="ok"))
    monkeypatch.setattr("ciw.pipeline.enrich_attributes", attributes)
    monkeypatch.setattr("ciw.pipeline._add_publications", publications)
    run(cfg, seeded_ws, offline=True, log=lambda *_: None)
    def unexpected(*a, **kw):
        raise AssertionError("design continuation ran unrelated enrichment")
    monkeypatch.setattr("ciw.pipeline.enrich_attributes", unexpected)
    monkeypatch.setattr("ciw.pipeline._add_publications", unexpected)
    # Simulate naturally discovered product metadata (not prefilled YAML target).
    updated = cfg.model_copy(deep=True)
    next(p for p in updated.products if p.id == "dupilumab").target = ""
    result = run(updated, seeded_ws, offline=True, report_scope="C", render_reports=list("ABC"), log=lambda *_: None)
    doc = load_release(result.release_path)
    assert next(p for p in doc["products"] if p["product_id"] == "dupilumab")["target"] == "source-backed-test-target"
    assert sum(r["result_id"] == "paper-fixture" for r in doc["results"]) == 1
    assert any(s["source_id"] == paper.source_id for s in doc["sources"])


def test_failed_render_leaves_previous_current_unchanged(cfg, seeded_ws, monkeypatch):
    first = run(cfg, seeded_ws, offline=True, report_scope="C", render_reports=["C"], log=lambda *_: None)
    def fail(*a, **kw):
        raise OSError("fixture render failure")
    monkeypatch.setattr("ciw.render.site.render_release", fail)
    with pytest.raises(OSError):
        run(cfg, seeded_ws, offline=True, report_scope="C", render_reports=["B", "C"], log=lambda *_: None)
    assert seeded_ws.current_release_dir().name == first.release_id


def test_interrupted_unpublished_site_recovers_without_rewriting_any_published_history(cfg, seeded_ws, monkeypatch):
    import ciw.render.site as rendering
    first = run(cfg, seeded_ws, offline=True, report_scope="C", render_reports=["C"], log=lambda *_: None)
    old = (first.site_dir / "C/data.js").read_bytes()
    original_write = rendering._write_immutable
    def crash(path, data, *a, **kw):
        if path.name == "data.js" and path.parent.name == "B":
            path.write_bytes(data[:8])
            raise OSError("simulated truncated candidate file")
        return original_write(path, data, *a, **kw)
    monkeypatch.setattr(rendering, "_write_immutable", crash)
    with pytest.raises(OSError):
        run(cfg, seeded_ws, offline=True, report_scope="C", render_reports=["B", "C"], log=lambda *_: None)
    assert seeded_ws.current_release_dir().name == first.release_id
    monkeypatch.setattr(rendering, "_write_immutable", original_write)
    repaired = run(cfg, seeded_ws, offline=True, report_scope="C", render_reports=["B", "C"], log=lambda *_: None)
    assert repaired.release_id != first.release_id
    assert (first.site_dir / "C/data.js").read_bytes() == old
    assert (repaired.site_dir / "B/data.js").read_bytes().startswith(b"window.CIW=")
    # Protection applies to historical completed reports even after current moves on.
    historical = first.site_dir / "C/data.js"
    historical.write_text("user preserved historical bytes")
    with pytest.raises(ValueError):
        rendering.render_release(first.release_path)
    assert historical.read_text() == "user preserved historical bytes"


def test_recording_same_source_returns_the_original_acquisition_metadata(ws):
    first = ws.record_source(kind="ctgov", url="https://example.test", data=b"same", ext="json",
                             title="original", fetched_at="2020-01-02T03:04:05+00:00")
    again = ws.record_source(kind="ctgov", url="https://example.test", data=b"same", ext="json", title="changed")
    assert again == first
    assert ws.sources() == [first]
