"""Only explicit cross-registry identifiers can collapse research rows."""

import json
from pathlib import Path

from ciw.analyze.design import build_design
from ciw.analyze.landscape import build_landscape
from ciw.extract.ctgov import extract_trial
from ciw.models import Design, Locator, Product, Source, Trial
from ciw.normalize.trials import deduplicate_trials


def records():
    a = Trial(
        trial_id="NCT02898454",
        registry="ctgov",
        ids={"nct": "NCT02898454", "ctr": "CTR20221480"},
        phase="III",
        phase_rank=4,
        product_ids=["dupilumab"],
        locator=Locator(source_id="src_global"),
        design=Design(enrollment=448, enrollment_type="ACTUAL", eligibility_text="global criteria"),
    )
    b = Trial(
        trial_id="CTR20221480",
        registry="cde",
        ids={"ctr": "CTR20221480"},
        china=True,
        phase="II",
        phase_rank=3,
        product_ids=["dupilumab"],
        locator=Locator(source_id="src_china"),
        design=Design(enrollment=240, enrollment_type="ESTIMATED", eligibility_text="完整中国入排"),
    )
    return a, b


def test_explicit_mapping_keeps_both_complete_records_without_inventing_phase(cfg):
    a, b = records()
    merged, issues = deduplicate_trials([b, a])
    assert not issues and len(merged) == 1
    trial = merged[0]
    assert trial.trial_id == a.trial_id and trial.ids["ctr"] == b.trial_id
    assert trial.design.enrollment == 448 and trial.registrations[0].design.enrollment == 240
    assert trial.registrations[0].locator.source_id == "src_china"
    assert not a.registrations  # pure projection, not mutation of source records
    product = Product(product_id="dupilumab", name_en="dupilumab")
    row = build_landscape([product], merged, [], [], None)["products"][0]
    assert (row["trial_count"], row["global_rank"], row["china_rank"]) == (1, 4, 3)
    design = build_design(cfg, merged, {product.product_id: product})["rows"][0]
    assert design["ids"]["ctr"] == b.trial_id
    assert set(design["registration_ids"]) == {a.trial_id, b.trial_id}
    assert design["registrations"][0]["eligibility"] == "完整中国入排"
    assert deduplicate_trials([a, b])[0] == merged


def test_title_drug_or_array_order_never_establish_registration_identity():
    a, b = records()
    a.ids.pop("ctr")
    a.title = b.title = "Same title, same drug"
    merged, issues = deduplicate_trials([a, b])
    assert len(merged) == 2 and not issues


def test_ambiguous_or_contradictory_links_keep_all_records_for_review():
    a, b = records()
    other = a.model_copy(update={"trial_id": "NCT03280550", "ids": {"nct": "NCT03280550", "ctr": b.trial_id}})
    merged, issues = deduplicate_trials([a, b, other])
    assert len(merged) == 3 and issues[0]["kind"] == "registry_link_conflict"
    b.ids["nct"] = "NCT99999999"
    merged, issues = deduplicate_trials([a, b])
    assert len(merged) == 2 and issues


def test_secondary_registration_identifiers_are_extracted_from_production(cfg, resolver):
    path = Path(__file__).parent / "fixtures/ctgov/NCT02898454.json"
    study = json.loads(path.read_text())
    study["protocolSection"]["identificationModule"]["secondaryIdInfos"] = [
        {"id": "CTR20221480", "type": "OTHER"},
        {"id": "notCTR20220000extra"},
    ]
    source = Source(
        source_id="s",
        kind="ctgov",
        url="https://clinicaltrials.gov/study/NCT02898454",
        fetched_at="2026-10-27T00:00:00Z",
        sha256="0" * 64,
    )
    trial = extract_trial(study, source, cfg, resolver)
    assert trial.ids["ctr"] == "CTR20221480"


def test_cde_foreign_ids_only_use_registration_fields():
    from ciw.sources.cde_registry import _foreign_ids

    assert _foreign_ids({"相关登记号": {"value": "NCT02898454"}}) == {"nct": "NCT02898454"}
    assert not _foreign_ids({"入选标准": {"value": "Previous NCT02898454 participation"}})


def test_normal_pipeline_keeps_both_source_versions_in_single_trial(cfg, seeded_ws, monkeypatch):
    from ciw.pipeline import run
    from ciw.release import load_release

    _, cde = records()
    cde.ids["nct"] = "NCT02898454"
    source = seeded_ws.record_source(
        kind="cde",
        url="https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml",
        data=b'{"test":"registry"}',
        ext="json",
    )
    cde.locator.source_id = source.source_id
    monkeypatch.setattr("ciw.pipeline.cde_registry.ingest", lambda *_: ([cde], {"source": "cde", "status": "ok"}))
    doc = load_release(run(cfg, seeded_ws, offline=True, log=lambda *_: None).release_path)
    assert doc["stats"]["trials_total"] == 5
    trial = next(t for t in doc["trials"] if t["trial_id"] == "NCT02898454")
    assert trial["registrations"][0]["trial_id"] == cde.trial_id
    assert source.source_id in {s["source_id"] for s in doc["sources"]}
