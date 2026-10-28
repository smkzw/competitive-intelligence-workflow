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


def test_placebo_only_source_type_conflict_is_not_coerced_into_a_comparator(cfg, resolver):
    from ciw.analyze.common import role_label
    from ciw.normalize.arms import match_group

    raw = study("Placebo")
    module = raw["protocolSection"]["armsInterventionsModule"]
    module["armGroups"][0]["interventionNames"] = ["Drug: Placebo"]
    module["interventions"][0]["name"] = "Placebo"
    original = deepcopy(raw)
    trial = extract(raw, cfg, resolver)
    arm = trial.arms[0]
    assert arm.type == "EXPERIMENTAL" and arm.label == "Placebo"
    assert arm.role == "unknown" and arm.role_conflict
    assert match_group("Placebo", trial.arms, resolver) == (arm.arm_id, "unknown", None)
    assert role_label(arm.role, trial, arm.arm_id) == "登记角色信息不一致"
    assert raw == original


def test_explicit_placebo_and_active_plus_placebo_keep_original_roles(cfg, resolver):
    from ciw.normalize.arms import arm_role

    assert arm_role("PLACEBO_COMPARATOR", ["Placebo"]) == ("placebo", False)
    assert arm_role("EXPERIMENTAL", ["Drug A", "Placebo"]) == ("experimental", False)
    assert arm_role("ACTIVE_COMPARATOR", ["Placebos"]) == ("unknown", True)
    assert arm_role("EXPERIMENTAL", ["Placebomab"]) == ("experimental", False)
    assert arm_role("", ["Placebo"]) == ("unknown", False)


def test_explicit_paper_placebo_is_preserved_when_registry_role_conflicts(cfg, resolver):
    from ciw.models import Arm, Locator, Trial
    from ciw.verify.publications import _publication_group

    trial = Trial(trial_id="NCT00000001", registry="ctgov", title="Synthetic", locator=Locator(source_id="s"),
        arms=[Arm(arm_id="A1", label="Placebo", type="EXPERIMENTAL", role="unknown", role_conflict=True,
                  interventions=["Placebo"])])
    paper = {"paper_id": "synthetic-paper", "path": "Abstract"}
    group = _publication_group(trial, "Placebo", paper, resolver, "experimental")
    assert group.role == "placebo" and group.arm_id is None and group.product_id is None
    assert trial.arms[0].type == "EXPERIMENTAL" and trial.arms[0].role == "unknown"


def test_placebo_type_with_explicit_active_title_conflict_keeps_source_fields(cfg, resolver):
    from ciw.analyze.common import role_label
    from ciw.normalize.arms import match_group

    for label, intervention, conflict in [
        ("Open-label OPN-375 During Parts B and C", "Placebo", True),
        ("Placebo matching OPN-375", "Placebo", False),
        ("OPN-375 plus placebo", "OPN-375", False),
        ("Blinded cohort", "Placebo", False),
    ]:
        raw = study(label, "PLACEBO_COMPARATOR")
        module = raw["protocolSection"]["armsInterventionsModule"]
        module["armGroups"][0]["interventionNames"] = ["Drug: " + intervention]
        module["interventions"][0]["name"] = intervention
        before = deepcopy(raw)
        trial = extract(raw, cfg, resolver)
        arm = trial.arms[0]
        assert arm.role_conflict is conflict, label
        assert arm.role == ("unknown" if conflict else "placebo"), label
        assert arm.type == "PLACEBO_COMPARATOR" and raw == before
        if conflict:
            assert match_group(label, trial.arms, resolver) == (arm.arm_id, "unknown", None)
            assert role_label(arm.role, trial, arm.arm_id) == "登记角色信息不一致"
