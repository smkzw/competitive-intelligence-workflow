import json

from ciw.models import Locator, Trial
from ciw.pipeline import build_products
from ciw.verify.attributes import enrich_attributes
from ciw.verify.llm import FakeBackend


def roles(item):
    return {
        k: FakeBackend(f, f, lambda *a: json.dumps({"items": [item]}))
        for k, f in (("extractor_a", "deepseek"), ("extractor_b", "qwen"), ("arbiter", "glm"))
    }


def test_only_missing_attributes_are_filled_with_source_backing(cfg, resolver, ws):
    text = "MG-K10 targets IL-4R and is a monoclonal antibody."
    source = ws.record_source(
        kind="ctgov",
        url="https://clinicaltrials.gov/study/NCT12345678",
        data=json.dumps({"protocolSection": {"armsInterventionsModule": {"description": text}}}).encode(),
        ext="json",
    )
    trial = Trial(
        trial_id="NCT12345678", registry="ctgov", product_ids=["mg-k10"], locator=Locator(source_id=source.source_id)
    )
    products = build_products(cfg)
    products["mg-k10"].target = "configured target"
    item = dict(product_mention="MG-K10", target="IL-4R", modality="monoclonal antibody", quote=text)
    assert not enrich_attributes(ws, products, [trial], resolver, roles(item))
    p = products["mg-k10"]
    assert p.target == "configured target" and p.modality == "monoclonal antibody"
    assert p.attribute_status == "dual_agreed"
    assert p.attribute_locators["modality"].source_id == source.source_id
    assert p.attribute_locators["modality"].quote == text


def test_absent_or_conflicting_source_values_do_not_fill_by_first_match(cfg, resolver, ws):
    from ciw.verify.attributes import _apply

    p = build_products(cfg)
    issues = []
    loc = Locator(source_id="source", quote="original")
    _apply(p, {("mg-k10", "target"): [("A", "dual_agreed", loc), ("B", "dual_agreed", loc)]}, issues)
    assert p["mg-k10"].target == "" and issues[0]["kind"] == "attribute_conflict"
    assert not enrich_attributes(ws, p, [], resolver, None)
