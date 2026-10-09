"""Receipt-backed repair of a stale parser scope, not general conflict approval."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.source_fact_acceptance import SourceFactAcceptanceError
from ci_workflow.application.source_research_service import (
    RegistryDenominatorCandidate,
    ResearchClaim,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
)
from ci_workflow.storage.sqlite import open_database
from tests.integration import test_r24_reviewed_source_fact_acceptance as base


def _world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str = "scope"):
    record = {
        "protocolSection": {"identificationModule": {"nctId": "NCT00000101"}},
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [
                    {
                        "title": "Percent change in itch",
                        "timeFrame": "Baseline, Week12",
                        "unitOfMeasure": "percent change",
                        "paramType": "LEAST_SQUARES_MEAN",
                        "populationDescription": "Number analyzed is available per category.",
                        "groups": [{"id": "OG001", "title": "Study drug"}],
                        "denoms": [
                            {
                                "units": "Participants",
                                "counts": [{"groupId": "OG001", "value": "78"}],
                            }
                        ],
                        "classes": [
                            {
                                "title": "Week12",
                                "denoms": [
                                    {
                                        "units": "Participants",
                                        "counts": [{"groupId": "OG001", "value": "77"}],
                                    }
                                ],
                                "categories": [
                                    {"measurements": [{"groupId": "OG001", "value": "-48.32"}]}
                                ],
                            }
                        ],
                    }
                ]
            }
        },
    }
    capture = base._primary_source().model_copy(
        update={
            "source_type": "clinical_trial_registry",
            "query_or_identifier": "NCT00000101",
            "content_text": json.dumps(record),
            "url": "https://clinicaltrials.gov/study/NCT00000101",
        }
    )
    atoms, _ = extract_ctgov_atomic_results(capture)
    selected = research_facts_from_ctgov_atom(atoms[0], report_row_ref="efficacy:f1")[0]
    claim = ResearchClaim(
        claim_id="scope-claim",
        claim_text="来源报告原始测量值。",
        claim_kind="direct_evidence",
        fact_ids=(selected.fact_id,),
    )
    monkeypatch.setattr(base, "_sources", lambda: (capture,))
    monkeypatch.setattr(base, "_facts", lambda: (selected,))
    monkeypatch.setattr(base, "_claims", lambda: (claim,))
    world = base._build_world(tmp_path)
    context = selected.result_context
    assert context is not None
    candidate = RegistryDenominatorCandidate(
        group_id="OG001",
        raw_value="78",
        raw_value_type="str",
        parsed_value=78,
        unit="Participants",
        value_path="resultsSection.outcomeMeasuresModule.outcomeMeasures[0].denoms[0].counts[0].value",
    )
    old = selected.model_copy(
        update={
            "result_context": context.model_copy(update={"denominator_candidates": (candidate,)})
        }
    )
    if defect == "value":
        old = old.model_copy(update={"raw_value": "-40", "normalized_value": "-40"})
    elif defect == "analysis":
        old = old.model_copy(
            update={
                "result_context": old.result_context.model_copy(
                    update={"analysis_population": "different population"}
                )
            }
        )
    elif defect == "quote":
        old = old.model_copy(
            update={
                "result_context": old.result_context.model_copy(
                    update={
                        "denominator_candidates": (
                            candidate.model_copy(update={"raw_value": "79", "parsed_value": 79}),
                        )
                    }
                )
            }
        )
    elif defect == "group":
        old = old.model_copy(
            update={
                "result_context": old.result_context.model_copy(
                    update={
                        "denominator_candidates": (
                            candidate.model_copy(update={"group_id": "OG000"}),
                        )
                    }
                )
            }
        )
    elif defect == "parsed":
        old = old.model_copy(
            update={
                "result_context": old.result_context.model_copy(
                    update={
                        "denominator_candidates": (
                            candidate.model_copy(update={"parsed_value": 79}),
                        )
                    }
                )
            }
        )
    old_lineage = ingest_research_evidence(
        project_root=world.root,
        project_id=world.project_id,
        contract_version=1,
        report_kind="A",
        data_cutoff=base.DATA_CUTOFF,
        scientific_content_digest=hashlib.sha256(b"old-parser-scope").hexdigest(),
        created_at=base.PRODUCED_AT,
        sources=(capture,),
        route_attempts=(),
        facts=(old,),
        claims=(claim,),
    )
    return world, old_lineage


def test_signed_exact_source_scope_correction_preserves_history_and_replays(tmp_path, monkeypatch):
    world, old = _world(tmp_path, monkeypatch)
    snapshots = base._file_digests(world.root, "snapshots")
    before = base._fact_states(world.root)
    accepted = base._accept(world)
    assert len(accepted.source_scope_corrections) == 1
    assert base._accept(world) == accepted
    after = base._fact_states(world.root)
    assert after[old.fact_version_ids[0]] == before[old.fact_version_ids[0]]
    assert base._file_digests(world.root, "snapshots") == snapshots
    with open_database(world.root / "state/project.sqlite") as db:
        state, note = db.execute(
            "SELECT resolution_state,resolution_note FROM conflict_sets"
        ).fetchone()
    assert state == "open"  # original append-only conflict is never overwritten
    correction = accepted.source_scope_corrections[0]
    assert note == correction.original_resolution_note
    proof = json.loads(correction.resolution_note)
    assert proof["selected_fact_version_id"] == world.lineage.fact_version_ids[0]
    assert proof["receipt_digest"] == world.receipt.receipt_digest
    assert (
        old.fact_version_ids[0] in json.loads(proof["original_resolution_note"])["fact_version_ids"]
    )
    assert not (world.root / "reports/current.json").exists()


@pytest.mark.parametrize("defect", ["value", "analysis", "quote", "group", "parsed"])
def test_real_disagreement_or_false_denominator_proof_stays_open(tmp_path, monkeypatch, defect):
    world, _ = _world(tmp_path, monkeypatch, defect)
    before = base._fact_states(world.root)
    with pytest.raises(SourceFactAcceptanceError, match="冲突"):
        base._accept(world)
    assert base._fact_states(world.root) == before
    with open_database(world.root / "state/project.sqlite") as db:
        assert db.execute("SELECT resolution_state FROM conflict_sets").fetchone() == ("open",)


def test_scope_resolution_rolls_back_with_fact_acceptance(tmp_path, monkeypatch):
    world, _ = _world(tmp_path, monkeypatch)
    before = base._fact_states(world.root)
    with monkeypatch.context() as patch:

        def fail(*args):
            raise OSError("scope rollback probe")

        patch.setattr(base.acceptance_service, "_restore_append_only_guards", fail)
        with pytest.raises(OSError, match="scope rollback probe"):
            base._accept(world)
    assert base._fact_states(world.root) == before
    with open_database(world.root / "state/project.sqlite") as db:
        assert db.execute("SELECT resolution_state FROM conflict_sets").fetchone() == ("open",)
    assert len(base._accept(world).source_scope_corrections) == 1
