"""C uses the existing atom adapter, but binds complete design material.

Synthetic packages are normal typed input, not real publication acceptance.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

import pytest

from ci_workflow.application import fresh_c_research_package as c
from ci_workflow.application.source_research_service import fact_version_material_digest
from ci_workflow.reports.c import DesignFieldFamily, DesignObservation
from tests.integration.test_fresh_c_research_package import (
    _content_payload,
    _observation,
    _review,
)

PAPER_ID = "paper-design"
URL = "https://publisher.example/design-version"


def _paper_payload() -> dict[str, Any]:
    payload = copy.deepcopy(_content_payload())
    paper = copy.deepcopy(payload["sources"][0])
    paper.update(
        source_id=PAPER_ID, source_type="journal_publication", url=URL,
        acquired_at="2026-09-01T00:00:00Z", first_disclosed_at=None,
        locator={"document_role": "paper", "field_path": "$", "url": URL},
    )
    document = {
        "identity": "Design methods for study alpha", "public_by": "2026-07-01",
        "version": "Version one includes this design paragraph",
        "correction": "The correction changes copyright only, not design methods",
    }
    paper["content_text"] = json.dumps(document)
    payload["sources"].append(paper)
    row = _observation(
        "trial-alpha-1", "product-alpha", DesignFieldFamily.TRIAL_IDENTITY,
        "paper_identity", document["identity"],
    ).model_dump(mode="json")
    row.update(
        source_version_id=PAPER_ID, source_role="primary_trial_report",
        source_locator={"document_role": "paper", "field_path": "$.identity", "url": URL},
        period="treatment", assessment_timepoint="第16周",
    )
    payload["report_data"]["observations"].append(row)
    return payload


def _atoms(payload: dict[str, Any]):
    rows = [DesignObservation.model_validate(item)
            for item in payload["report_data"]["observations"]]
    sources = [c.SourceCapture.model_validate(item) for item in payload["sources"]]
    names = {item["id"]: item["name"] for item in payload["report_data"]["trials"]}
    facts = c.research_facts_from_c_observations(rows, sources=sources, trial_names=names)
    row = next(item for item in rows if item.source_version_id == PAPER_ID)
    fact = next(item for item in facts if item.fact_id == row.row_id)
    return row, fact


def _material_digest(row, fact) -> str:
    material = {
        "fact": fact.model_dump(mode="json", exclude={"row_ref", "fact_id"}),
        "design": row.model_dump(mode="json", exclude={
            "row_id", "display_text", "difference_labels_zh",
        }),
    }
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ) + "\n"
    return hashlib.sha256(canonical.encode()).hexdigest()


def _proved_payload() -> dict[str, Any]:
    payload = _paper_payload()
    row, fact = _atoms(payload)
    paper = payload["sources"][-1]
    document = json.loads(paper["content_text"])

    def ref(key):
        return {"reference_id": key, "source_id": PAPER_ID, "label_zh": "版本证据",
                "locator": {"document_role": "paper", "field_path": f"$.{key}", "url": URL},
                "original_text": document[key]}

    payload["fact_public_version_proofs"] = [{
        "fact_id": fact.fact_id, "fact_material_sha256": _material_digest(row, fact),
        "source_content_sha256": {PAPER_ID: hashlib.sha256(paper["content_text"].encode())
                                  .hexdigest()},
        "public_by": {"state": "reported", "value": "2026-07-01T00:00:00Z",
                      "precision": "calendar_day", "locator": ref("public_by")["locator"]},
        "public_by_reference": ref("public_by"), "version_references": [ref("version")],
        "correction_state": "fact_unaffected", "correction_references": [ref("correction")],
    }]
    return payload


def test_c_proved_paper_keeps_registry_gate_and_normal_package_roundtrip():
    payload = _proved_payload()
    content = c.FreshCResearchContent.model_validate(payload)
    row, fact = _atoms(payload)
    assert c.c_fact_version_material_digest(row, fact) == _material_digest(row, fact)
    assert c.evaluate_c_report_gate(content, project_id="project-synthetic",
                                   evidence_snapshot_id="snapshot-synthetic",
                                   contract_version="test").result.decision.value == "passed"
    review = _review(c, content.content_digest)
    review["reviewed_at"] = "2026-09-02T00:00:00Z"
    package = c.FreshCResearchPackage.model_validate({**payload, "scientific_review": review})
    restored = c.FreshCResearchPackage.model_validate(package.model_dump(mode="json"))
    assert restored.research_content_digest == package.research_content_digest
    assert restored.sources[-1].first_disclosed_at is None
    assert not restored.sources[-1].is_available_by(restored.data_cutoff)


@pytest.mark.parametrize("field,value", [
    ("period", "followup"), ("cohort_id", "another-cohort"),
    ("group_id", "another-arm"), ("assessment_timepoint", "第24周"),
    ("scale", "WI-NRS"), ("threshold_value", "4"),
    ("source_field_definition", "another definition"),
    ("source_row_id", "another-source-fact"),
])
def test_c_context_change_cannot_reuse_source_text_proof(field, value):
    payload = _proved_payload()
    payload["report_data"]["observations"][-1][field] = value
    with pytest.raises(ValueError, match="事实版本材料"):
        c.FreshCResearchContent.model_validate(payload)


def test_c_plain_atom_digest_is_not_a_design_material_proof():
    payload = _proved_payload()
    _, fact = _atoms(payload)
    payload["fact_public_version_proofs"][0]["fact_material_sha256"] = (
        fact_version_material_digest(fact)
    )
    with pytest.raises(ValueError, match="事实版本材料"):
        c.FreshCResearchContent.model_validate(payload)


def test_c_source_fact_identity_change_must_invalidate_an_existing_valid_proof():
    payload = _proved_payload()
    row, fact = _atoms(payload)
    payload["fact_public_version_proofs"][0]["fact_material_sha256"] = (
        c.c_fact_version_material_digest(row, fact)
    )
    c.FreshCResearchContent.model_validate(payload)
    payload["report_data"]["observations"][-1]["source_row_id"] = "another-upstream-fact"
    with pytest.raises(ValueError, match="事实版本材料"):
        c.FreshCResearchContent.model_validate(payload)


def test_c_unproved_sibling_stays_rejected():
    payload = _proved_payload()
    sibling = copy.deepcopy(payload["report_data"]["observations"][-1])
    sibling.update(row_id="sibling", source_row_id="sibling-source",
                   observation_id="sibling-observation", field="paper_identity_sibling")
    payload["report_data"]["observations"].append(sibling)
    with pytest.raises(ValueError, match="sibling"):
        c.FreshCResearchContent.model_validate(payload)


def test_c_consumer_row_and_display_changes_do_not_change_scientific_proof_material():
    payload = _proved_payload()
    row, fact = _atoms(payload)
    changed = row.model_copy(update={
        "row_id": "another-row",
        "display_text": "中文阅读名", "difference_labels_zh": ("提示",),
    })
    changed_fact = fact.model_copy(update={"fact_id": "another-row", "row_ref": "another-row"})
    assert c.c_fact_version_material_digest(changed, changed_fact) == _material_digest(row, fact)


@pytest.mark.parametrize("bad_material", ["missing", "extra", "nonhex"])
def test_shared_complete_material_override_cannot_omit_or_add_keys(bad_material):
    from ci_workflow.application.source_research_service import (
        validate_source_or_fact_historical_availability,
    )
    from tests.integration.test_1007_fact_public_version_cutoff import CUTOFF, _case

    source, fact, proof = _case()
    material = {fact.fact_id: fact_version_material_digest(fact)}
    if bad_material == "missing":
        material.clear()
    elif bad_material == "extra":
        material["not-a-fact"] = "a" * 64
    else:
        material[fact.fact_id] = "A" * 64
    with pytest.raises(ValueError, match="完整科学材料摘要"):
        validate_source_or_fact_historical_availability(
            [source], [fact], [proof], CUTOFF, material_digests=material,
        )


def test_c_legacy_content_omits_empty_proof_field():
    payload = _content_payload()
    payload["fact_public_version_proofs"] = []
    content = c.FreshCResearchContent.model_validate(payload)
    assert "fact_public_version_proofs" not in content.model_dump(mode="json")
    assert content.content_digest == c.FreshCResearchContent.model_validate(
        _content_payload(),
    ).content_digest


def test_c_changed_proof_invalidates_whole_content_review():
    payload = _proved_payload()
    content = c.FreshCResearchContent.model_validate(payload)
    review = _review(c, content.content_digest)
    review["reviewed_at"] = "2026-09-02T00:00:00Z"
    payload["fact_public_version_proofs"][0]["version_references"][0]["label_zh"] = "新标签"
    with pytest.raises(ValueError, match="摘要"):
        c.FreshCResearchPackage.model_validate({**payload, "scientific_review": review})
