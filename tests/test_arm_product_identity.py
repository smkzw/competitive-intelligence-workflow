"""Synthetic explicit arm codes with generic ingredient names; no title guessing."""

from copy import deepcopy

from ciw.extract.ctgov import extract_trial
from ciw.models import Source


def study(label="OPN-375 400 mcg BID", arm_type="EXPERIMENTAL"):
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT12345678", "briefTitle": "A nasal polyp study"},
            "conditionsModule": {"conditions": ["nasal polyps"]},
            "armsInterventionsModule": {
                "armGroups": [
                    {"label": label, "type": arm_type, "interventionNames": ["Drug: Fluticasone Propionate"]}
                ],
                "interventions": [{"name": "Fluticasone Propionate", "type": "DRUG"}],
            },
        }
    }


def extract(raw, cfg, resolver):
    src = Source(
        source_id="synthetic",
        kind="ctgov",
        url="https://example.com",
        sha256="0" * 64,
        fetched_at="2026-10-27T00:00:00Z",
    )
    return extract_trial(raw, src, cfg, resolver)


def test_explicit_arm_formulation_code_preserves_product_and_generic_original(cfg, resolver):
    raw = study()
    original = deepcopy(raw)
    t = extract(raw, cfg, resolver)
    assert t.relevance == "core" and t.product_ids == ["opn-375"]
    assert t.arms[0].product_ids == ["opn-375"] and t.arms[0].role == "experimental"
    assert t.arms[0].interventions == ["Fluticasone Propionate"]
    assert t.design.background_therapy == [] and raw == original


def test_title_or_sponsor_alone_does_not_relabel_a_generic_ingredient(cfg, resolver):
    raw = study("Fluticasone arm")
    raw["protocolSection"]["identificationModule"]["briefTitle"] += " (OPN-375 mentioned)"
    t = extract(raw, cfg, resolver)
    assert t.product_ids == [] and t.relevance == "background"
    assert t.design.background_therapy == ["Fluticasone Propionate"]


def test_placebo_code_and_multiple_products_do_not_create_single_product_binding(cfg, resolver):
    assert extract(study("Placebo for OPN-375", "PLACEBO_COMPARATOR"), cfg, resolver).arms[0].product_ids == []
    assert extract(study("OPN-375 + dupilumab"), cfg, resolver).arms[0].product_ids == []


def test_product_identity_does_not_invent_missing_arm_role(cfg, resolver):
    t = extract(study(arm_type=""), cfg, resolver)
    assert t.product_ids == ["opn-375"] and t.arms[0].role == "unknown"
