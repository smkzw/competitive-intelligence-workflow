"""Candidate-only exact AE definition completion, not an accepted-sibling waiver."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.source_fact_acceptance import SourceFactAcceptanceError
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
)
from ci_workflow.storage.sqlite import open_database
from tests.integration import test_r24_reviewed_source_fact_acceptance as base
from tests.integration.test_1007_reviewed_pk_domain_correction import _synthesize_state


def _world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str = "absent"):
    capture = base._primary_source().model_copy(update={
        "source_type": "clinical_trial_registry",
        "query_or_identifier": "NCT04202679",
        "url": "https://clinicaltrials.gov/study/NCT04202679",
        "content_text": json.dumps({
            "protocolSection": {"identificationModule": {"nctId": "NCT04202679"}},
            "resultsSection": {"adverseEventsModule": {
                "description": "Safety population; events during treatment and follow-up.",
                "timeFrame": "Up to Week 36",
                "eventGroups": [{"id": "EG001", "title": "Drug arm",
                                 "seriousNumAffected": 2, "seriousNumAtRisk": 77}],
            }},
        }),
    })
    atoms, issues = extract_ctgov_atomic_results(capture)
    assert not issues
    selected = research_facts_from_ctgov_atom(atoms[0])[0]
    assert selected.result_context and selected.result_context.value_role == "affected_count"
    claim = ResearchClaim(claim_id="ae-definition-claim", claim_text=selected.original_text,
                          claim_kind="direct_evidence", fact_ids=(selected.fact_id,))
    monkeypatch.setattr(base, "_sources", lambda: (capture,))
    monkeypatch.setattr(base, "_facts", lambda: (selected,))
    monkeypatch.setattr(base, "_claims", lambda: (claim,))
    world = base._build_world(tmp_path)
    old_context = selected.result_context.model_copy(update={
        "source_definition": None, "source_definition_path": None})
    if defect in {"analysis_population", "timepoint", "group_id", "source_unit", "domain"}:
        replacements = {"analysis_population": "Other population", "timepoint": "Week 1",
                        "group_id": "EG999", "source_unit": "events", "domain": "efficacy"}
        old_context = old_context.model_copy(update={defect: replacements[defect]})
    elif defect == "changed_definition":
        old_context = old_context.model_copy(update={
            "source_definition": "Already recorded different event definition."})
    elif defect == "partial_definition":
        old_context = old_context.model_copy(update={
            "source_definition_path": selected.result_context.source_definition_path})
    old = selected.model_copy(update={"result_context": old_context})
    if defect == "normalized_value":
        old = old.model_copy(update={"normalized_value": "3"})
    old_lineage = ingest_research_evidence(
        project_root=world.root, project_id=world.project_id, contract_version=1,
        report_kind="A", data_cutoff=base.DATA_CUTOFF,
        scientific_content_digest=hashlib.sha256(b"old-absent-AE-definition").hexdigest(),
        created_at=base.PRODUCED_AT, sources=(capture,), route_attempts=(),
        facts=(old,), claims=(claim,))
    if defect in {"accepted", "user_modified", "rejected", "superseded"}:
        _synthesize_state(world.root, old_lineage.fact_version_ids[0], defect)
    return world, old_lineage


def test_candidate_definition_completion_preserves_history_and_is_idempotent(
    tmp_path, monkeypatch,
):
    world, old = _world(tmp_path, monkeypatch)
    before = base._fact_states(world.root)
    snapshots = base._file_digests(world.root, "snapshots")
    accepted = base._accept(world)
    assert len(accepted.source_scope_corrections) == 1
    assert base._accept(world) == accepted
    assert base._fact_states(world.root)[old.fact_version_ids[0]] == before[
        old.fact_version_ids[0]]
    assert base._file_digests(world.root, "snapshots") == snapshots
    proof = json.loads(accepted.source_scope_corrections[0].resolution_note)
    assert proof["classification"] == "same_registry_scalar_source_definition_enrichment"
    assert proof["receipt_digest"] == world.receipt.receipt_digest
    with open_database(world.root / "state/project.sqlite") as db:
        assert db.execute("SELECT resolution_state FROM conflict_sets").fetchone() == ("open",)
    assert not (world.root / "reports/current.json").exists()


@pytest.mark.parametrize("defect", [
    "analysis_population", "timepoint", "group_id", "source_unit", "domain",
    "changed_definition", "partial_definition", "normalized_value",
    "accepted", "user_modified", "rejected", "superseded",
])
def test_definition_enrichment_cannot_waive_existing_or_changed_scientific_material(
    tmp_path, monkeypatch, defect,
):
    world, _ = _world(tmp_path, monkeypatch, defect)
    before = base._fact_states(world.root)
    with pytest.raises(SourceFactAcceptanceError, match="冲突"):
        base._accept(world)
    assert base._fact_states(world.root) == before
    assert not (world.root / base.source_fact_acceptance_decision_path(
        "A", world.receipt.receipt_digest)).exists()


def test_definition_correction_rolls_back_with_acceptance_and_retries_once(
    tmp_path, monkeypatch,
):
    world, _ = _world(tmp_path, monkeypatch)
    before = base._fact_states(world.root)
    with monkeypatch.context() as patch:
        def fail(*args):
            raise OSError("definition rollback probe")
        patch.setattr(base.acceptance_service, "_restore_append_only_guards", fail)
        with pytest.raises(OSError, match="definition rollback probe"):
            base._accept(world)
    assert base._fact_states(world.root) == before
    assert len(base._accept(world).source_scope_corrections) == 1
