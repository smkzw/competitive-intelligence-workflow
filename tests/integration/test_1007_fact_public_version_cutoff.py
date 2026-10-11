"""Per-fact public-version admission, not a claim that synthetic papers are real."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from ci_workflow.application import source_research_service as service
from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator

CUTOFF = datetime(2026, 10, 7, 23, 59, 59, tzinfo=UTC)
URL = "https://publisher.example/version-1"


def _case():
    text = json.dumps({"value": "14 (18.4)", "other": "99", "public_by": "2023-05-04",
                       "version": "Version1 includes this table",
                       "correction": "Correction changes copyright only, not this table"})
    source = service.SourceCapture(
        source_id="paper", route_id="publisher", source_type="journal_publication",
        title="Synthetic dated version", url=URL, query_or_identifier="test",
        language="en", access_method="test", content_text=text,
        acquired_at=datetime(2026, 10, 11, tzinfo=UTC),
        published_at=datetime(2023, 5, 4, tzinfo=UTC), effective_at=None,
        first_disclosed_at=None,
        locator=EvidenceLocator(document_role="synthetic", field_path="$", url=URL),
    )
    fact = service.ResearchFact(
        fact_id="fact-1", row_ref="efficacy:row-1", entity_id="study", entity_type="trial",
        canonical_name="Synthetic study", field_id="efficacy.primary", raw_value="14 (18.4)",
        normalized_value="14 (18.4)", disclosure_state="reported_value", source_id="paper",
        locator=EvidenceLocator(document_role="synthetic", field_path="$.value", url=URL),
        original_text="14 (18.4)",
    )
    def ref(field):
        return {"reference_id": field, "source_id": "paper", "label_zh": "版本证据",
                "locator": {"document_role": "synthetic", "field_path": f"$.{field}",
                            "url": URL}, "original_text": json.loads(text)[field]}
    proof = {
        "fact_id": fact.fact_id,
        "fact_material_sha256": service.fact_version_material_digest(fact),
        "source_content_sha256": {"paper": hashlib.sha256(text.encode()).hexdigest()},
        "public_by": DateEvidence(state="reported", value="2023-05-04T00:00:00Z",
            precision="calendar_day", locator=EvidenceLocator(**ref("public_by")["locator"])),
        "public_by_reference": ref("public_by"), "version_references": [ref("version")],
        "correction_state": "fact_unaffected", "correction_references": [ref("correction")],
    }
    return source, fact, proof


def test_specific_version_proof_accepts_unknown_earliest_date_and_late_acquisition():
    source, fact, proof = _case()
    service.validate_research_historical_availability([source], [fact], [proof], CUTOFF)
    assert source.first_disclosed_at is None and source.acquired_at > CUTOFF
    assert not source.is_available_by(CUTOFF), "Do not backfill legacy source dates"


def test_same_paper_sibling_does_not_inherit_another_facts_proof():
    source, fact, proof = _case()
    sibling = fact.model_copy(update={"fact_id": "fact-2", "raw_value": "99",
        "normalized_value": "99", "original_text": "99", "row_ref": "efficacy:row-2",
        "locator": EvidenceLocator(document_role="synthetic", field_path="$.other", url=URL)})
    with pytest.raises(ValueError, match="fact-2"):
        service.validate_research_historical_availability(
            [source], [fact, sibling], [proof], CUTOFF,
        )


@pytest.mark.parametrize("failure", ["epub_only", "unknown_scope", "changed_scope",
    "fact_change", "source_change", "wrong_fact", "wrong_locator", "wrong_quote",
    "after_cutoff", "day_not_complete", "no_correction_reference", "duplicate"])
def test_version_proof_failure_family(failure):
    source, fact, proof = _case()
    proofs = [proof]
    cutoff = CUTOFF
    if failure == "epub_only":
        proofs = []
    elif failure == "unknown_scope":
        proof["correction_state"] = "unresolved"
    elif failure == "changed_scope":
        proof["correction_state"] = "fact_changed"
    elif failure == "fact_change":
        fact = fact.model_copy(update={"normalized_value": "15"})
    elif failure == "source_change":
        source = source.model_copy(update={"content_text": source.content_text + " "})
    elif failure == "wrong_fact":
        proof["fact_id"] = "another"
    elif failure == "wrong_locator":
        proof["version_references"][0]["locator"]["field_path"] = "$.other"
    elif failure == "wrong_quote":
        proof["version_references"][0]["original_text"] = "guessed"
    elif failure == "after_cutoff":
        proof["public_by"] = proof["public_by"].model_copy(update={
            "value": datetime(2026, 10, 8, tzinfo=UTC)})
    elif failure == "day_not_complete":
        cutoff = datetime(2023, 5, 4, 12, tzinfo=UTC)
    elif failure == "no_correction_reference":
        proof["correction_references"] = []
    elif failure == "duplicate":
        proofs = [proof, proof]
    with pytest.raises(ValueError):
        service.validate_research_historical_availability([source], [fact], proofs, cutoff)


def test_consumer_row_name_change_does_not_change_fact_version_material():
    _, fact, _ = _case()
    assert service.fact_version_material_digest(fact) == service.fact_version_material_digest(
        fact.model_copy(update={"row_ref": "another-report:another-row"}))


def test_partial_holding_verification_does_not_grant_sibling_eligibility():
    source, fact, proof = _case()
    service.verify_fact_public_version_evidence([source], [fact], [proof], CUTOFF)
    assert source.first_disclosed_at is None
