import json
from pathlib import Path

import pytest

from ciw.extract.ctgov import extract_trial
from ciw.models import Source


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Chronic rhinosinusitis without nasal polyps (CRSsNP)", False),
        ("慢性鼻窦炎不伴鼻息肉", False),
        ("无鼻息肉患者", False),
        ("Chronic rhinosinusitis with or without nasal polyps", True),
        ("Chronic rhinosinusitis with and without nasal polyps", True),
        ("慢性鼻窦炎伴或不伴鼻息肉", True),
        ("慢性鼻窦炎伴有或不伴有鼻息肉", True),
        ("Chronic rhinosinusitis with nasal polyps", True),
    ],
)
def test_negated_population_does_not_become_target_indication(cfg, text, expected):
    assert cfg.is_relevant_text(text) is expected


def test_production_extractor_keeps_explicitly_different_indication_as_background(cfg, resolver):
    raw = json.loads((Path(__file__).parent / "fixtures/ctgov/NCT02898454.json").read_text())
    p = raw["protocolSection"]
    for field in ("briefTitle", "officialTitle"):
        p["identificationModule"][field] = "Trial in Chronic Rhinosinusitis Without Nasal Polyps (CRSsNP)"
    p["conditionsModule"] = {"conditions": ["Chronic Rhinosinusitis Without Nasal Polyps"], "keywords": ["CRSsNP"]}
    source = Source(
        source_id="test",
        kind="ctgov",
        url="https://clinicaltrials.gov/study/NCT02898454",
        fetched_at="2026-10-27T00:00:00Z",
        sha256="0" * 64,
    )
    t = extract_trial(raw, source, cfg, resolver)
    assert t.relevance == "background" and t.product_ids
