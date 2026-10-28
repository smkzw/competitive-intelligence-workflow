"""Synthetic NLM XML, production parsing/audit/cache contracts; no clinical acceptance."""
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

from ciw.audit import _publication, audit
from ciw.sources import pubmed

TEXT = "NCT12345678. At Week 24, mean response was 2.3 in 10 participants."


def article(pmid="123", text=TEXT, kind="Clinical Trial", title="Synthetic trial"):
    return (f"<PubmedArticle><MedlineCitation><PMID>{pmid}</PMID><Article>"
            f"<ArticleTitle>{title}</ArticleTitle><Abstract><AbstractText>{text}</AbstractText></Abstract>"
            f"<PublicationTypeList><PublicationType>{kind}</PublicationType></PublicationTypeList>"
            "</Article></MedlineCitation></PubmedArticle>")


def raw_article(**kwargs):
    return ("<PubmedArticleSet>" + article(**kwargs) + "</PubmedArticleSet>").encode()


def search(ids, count=None):
    return (f"<eSearchResult><Count>{len(ids) if count is None else count}</Count><IdList>" +
            "".join(f"<Id>{i}</Id>" for i in ids) + "</IdList></eSearchResult>").encode()


def seed(ws, **kwargs):
    return ws.record_source(kind="pubmed", url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?id=123",
                            data=raw_article(**kwargs), ext="xml", publisher="NCBI PubMed")


def test_search_pagination_raw_xml_literal_binding_and_successful_reuse(ws, monkeypatch):
    calls = []

    def get(url):
        calls.append(url)
        query = parse_qs(urlparse(url).query)
        if "esearch" in url:
            return search(["123"] if query["retstart"] == ["0"] else ["124"], 2)
        return ("<PubmedArticleSet>" + article("123") +
                article("124", "No registration ID in this abstract.") + "</PubmedArticleSet>").encode()
    monkeypatch.setattr(pubmed, "_get", get)
    records, coverage = pubmed.discover(ws, ["NCT12345678"], reuse=True)
    assert len(records) == 1 and records[0]["registry_ids"] == ["NCT12345678"]
    assert coverage["status"] == "ok" and len(calls) == 3
    source = next(s for s in ws.sources() if s.source_id == records[0]["source_id"])
    assert source.kind == "pubmed" and ws.read_source(source.source_id).startswith(b"<PubmedArticleSet>")
    assert records[0]["path"].startswith("xpath:") and records[0]["text"] == TEXT
    assert pubmed.discover(ws, ["NCT12345678"], reuse=True)[0] == records
    assert len(calls) == 3
    _, offline = pubmed.discover(ws, ["NCT12345678", "NCT12345679"], offline=True, reuse=True)
    assert len(calls) == 3 and offline["pending_ids"] == ["NCT12345679"]


def test_network_failure_is_distinct_from_successful_empty_search(ws, monkeypatch):
    def fail(url):
        raise HTTPError(url, 503, "Unavailable", {}, None)
    monkeypatch.setattr(pubmed, "_get", fail)
    rows, failed = pubmed.discover(ws, ["NCT12345678"])
    assert not rows and failed["status"] == "partial" and failed["failures"][0]["http_status"] == 503
    monkeypatch.setattr(pubmed, "_get", lambda _: search([]))
    rows, empty = pubmed.discover(ws, ["NCT12345678"], reuse=True)
    assert not rows and empty["status"] == "ok" and not empty["failures"]


@pytest.mark.parametrize("payload", [
    search(["123", "123"], 2), search([], 2), search(["123"], 0), b"<html>Maintenance</html>",
    b"<eSearchResult><IdList/></eSearchResult>",
])
def test_bad_search_is_not_silent_complete_zero_or_first_wins(ws, monkeypatch, payload):
    monkeypatch.setattr(pubmed, "_get", lambda _: payload)
    _, coverage = pubmed.discover(ws, ["NCT12345678"])
    assert coverage["status"] == "partial" and coverage["failures"][0]["error"] == "ValueError"


@pytest.mark.parametrize("kind", ["Review", "Retracted Publication", "Published Erratum"])
def test_nonprimary_or_retracted_paper_keeps_source_but_is_not_eligible(ws, kind):
    seed(ws, kind=kind)
    record, = pubmed.records(ws, {"NCT12345678"})
    assert record["excluded_type"] and ws.read_source(record["source_id"]) == raw_article(kind=kind)


def test_abstract_literal_id_required_and_external_xml_entities_never_loaded(ws, tmp_path):
    seed(ws, text="Trial response 2.3, registration is present only in search metadata.")
    assert pubmed.records(ws, {"NCT12345678"}) == []
    private = tmp_path / "dummy-private"
    private.write_text("must-not-be-read")
    raw = (f'<!DOCTYPE PubmedArticleSet [<!ENTITY x SYSTEM "{private.as_uri()}">]>'
           "<PubmedArticleSet>&x;</PubmedArticleSet>").encode()
    with pytest.raises(ValueError):
        pubmed.parse_xml(raw)


def test_xml_audit_uses_exact_pmid_path_original_quote_and_numeric_values(ws):
    source = seed(ws)
    paper, = pubmed.records(ws, {"NCT12345678"})
    locator = dict(source_id=source.source_id, path=paper["path"], quote=TEXT)
    result = dict(result_id="r", kind="publication", locator=locator,
                  groups=[dict(value=2.3, n=10)], analyses=[])
    sample = dict(kind="group_value", result_id="r", source_id=source.source_id,
                  path=paper["path"], value=2.3, n=10)
    doc = pubmed.parse_xml(ws.read_source(source.source_id))
    assert _publication(sample, doc, [result])[0]
    assert not _publication({**sample, "value": 3.2}, doc, [result])[0]
    assert not _publication({**sample, "path": paper["path"].replace("'123'", "'999'")}, doc, [result])[0]
    release = ws.releases_dir / "rel_test"
    release.mkdir()
    row = dict(source_id=source.source_id, path=paper["path"], value=2.3, n=10, result_id="r",
               source_kind="publication", acronym="Trial", group_title="Drug")
    (release / "release.json").write_text(json.dumps(dict(release_id="rel_test", results=[result], b=dict(
        questions=[dict(rows=[row], comparisons=[], label="Response", time_label="Week 24")]))))
    ws.set_current("rel_test")
    report = audit(ws, n=40)
    assert report["sampled"] == 1 and report["errors"] == []


def test_latest_paper_version_and_simultaneous_conflicts_do_not_duplicate_or_pick_first(ws):
    old = seed(ws)
    paper, = pubmed.records(ws, {"NCT12345678"})
    duplicate = {**paper}
    assert len(pubmed.merge_records(ws, [paper, duplicate])) == 1
    changed = {**paper, "text": TEXT.replace("2.3", "3.2")}
    conflicts = pubmed.merge_records(ws, [paper, changed])
    assert len(conflicts) == 2 and all(p["version_conflict"] and p["excluded_type"] for p in conflicts)
    assert ws.read_source(old.source_id) == raw_article()


def test_changing_search_total_and_duplicate_fetched_articles_are_incomplete(ws, monkeypatch):
    calls = []
    def changed(url):
        calls.append(url)
        return search(["123"], 2) if len(calls) == 1 else search(["124"], 3)
    monkeypatch.setattr(pubmed, "_get", changed)
    assert pubmed.discover(ws, ["NCT12345678"])[1]["status"] == "partial"
    def duplicate(url):
        return search(["123"]) if "esearch" in url else (
            "<PubmedArticleSet>" + article() * 2 + "</PubmedArticleSet>").encode()
    monkeypatch.setattr(pubmed, "_get", duplicate)
    assert pubmed.discover(ws, ["NCT12345678"])[1]["status"] == "partial"


def test_pipeline_fallback_keeps_failed_provider_and_projects_auditable_xml(cfg, resolver, ws, monkeypatch):
    from test_publications import TEXT as primary_text
    from test_publications import roles

    from ciw.models import Arm, Locator, Trial
    from ciw.pipeline import _add_publications

    source = ws.record_source(kind="ctgov", url="https://example.test/registry", data=b"{}", ext="json")
    trial = Trial(trial_id="NCT12345678", ids={"nct": "NCT12345678"}, registry="ctgov", phase_rank=4,
        locator=Locator(source_id=source.source_id), product_ids=["stapokibart"], arms=[
            Arm(arm_id="A", label="stapokibart", role="experimental", product_ids=["stapokibart"]),
            Arm(arm_id="B", label="placebo", role="placebo")])
    def unavailable(*args, **kwargs):
        raise HTTPError("https://www.ebi.ac.uk/", 503, "Unavailable", {}, None)
    monkeypatch.setattr("ciw.sources.europepmc.urllib.request.urlopen", unavailable)
    monkeypatch.setattr(pubmed, "_get", lambda url: search(["123"]) if "esearch" in url
                        else raw_article(text=primary_text))
    item = dict(registry_id=trial.trial_id, arm_label="stapokibart", comparator_label="placebo",
        endpoint="least squares mean change in nasal polyp score", timepoint="Week 24",
        population="overall population", stat_type="difference", base_stat_type="ls_mean",
        contrast_direction="arm_minus_comparator", value=-2.5, ci_lower=-2.9, ci_upper=-2.1,
        outcome_type="PRIMARY", quote=primary_text)
    results, issues, coverage = [], [], []
    _add_publications(cfg, ws, resolver, {trial.trial_id: trial}, results, roles([item]),
                      False, issues, coverage, True)
    assert len(results) == 1 and not issues and results[0].analyses[0].value == -2.5
    assert results[0].locator.path.startswith("xpath:")
    by_source = {c["source"]: c for c in coverage}
    assert by_source["publications"]["status"] == "partial"
    assert by_source["publications"]["failures"][0]["http_status"] == 503
    assert by_source["pubmed"]["status"] == "ok" and by_source["pubmed"]["eligible"] == 1
    doc = pubmed.parse_xml(ws.read_source(results[0].locator.source_id))
    sample = dict(kind="analysis", result_id=results[0].result_id, source_id=results[0].locator.source_id,
                  path=results[0].locator.path, value=-2.5, ci=(-2.9, -2.1))
    assert _publication(sample, doc, [r.model_dump() for r in results])[0]
