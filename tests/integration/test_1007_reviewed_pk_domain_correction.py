"""Receipt-backed repair of a stale efficacy→pk_pd domain, not general conflict approval.

Synthetic OLD fixture: same immutable registry scalar was already source-accepted
with the legacy wrong ``result_context.domain=efficacy``. Current parser replay of
that capture yields ``pk_pd``. Normal issuer authorization must accept the corrected
version while preserving the historical accepted row and failing closed on genuine
scientific disagreement.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import (
    ResearchEvidenceLineage,
    ingest_research_evidence,
)
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.review_issuer import review_issuance_record_path
from ci_workflow.application.source_fact_acceptance import (
    SourceFactAcceptanceError,
    source_fact_acceptance_decision_path,
)
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.sqlite import open_database
from tests.integration import test_r24_reviewed_source_fact_acceptance as base


def _pk_record() -> dict[str, object]:
    return {
        "protocolSection": {"identificationModule": {"nctId": "NCT05405985"}},
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [
                    {
                        "title": "Half-life (t1/2) of Nemolizumab",
                        "timeFrame": "Pre-dose through Day 85",
                        "paramType": "MEAN",
                        "dispersionType": "STANDARD_DEVIATION",
                        "unitOfMeasure": "days",
                        "populationDescription": (
                            "Healthy volunteers with evaluable PK samples"
                        ),
                        "groups": [{"id": "OG000", "title": "AI"}],
                        "denoms": [
                            {
                                "units": "Participants",
                                "counts": [{"groupId": "OG000", "value": "95"}],
                            }
                        ],
                        "classes": [
                            {
                                "categories": [
                                    {
                                        "measurements": [
                                            {
                                                "groupId": "OG000",
                                                "value": "18.0",
                                                "spread": "5.91",
                                            }
                                        ]
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }
        },
    }


def _synthesize_accepted_fact(root: Path, fact_version_id: str) -> None:
    """Mark one already-ingested candidate as historically accepted (fixture only)."""
    with open_database(root / "state/project.sqlite") as database:
        database.execute("BEGIN IMMEDIATE")
        suspended = base.acceptance_service._suspend_append_only_guards(database)
        cursor = database.execute(
            "UPDATE fact_versions SET review_state='accepted' "
            "WHERE fact_version_id=? AND review_state='candidate'",
            (fact_version_id,),
        )
        if int(cursor.rowcount) != 1:
            raise AssertionError("synthetic accepted fixture did not update exactly one row")
        base.acceptance_service._restore_append_only_guards(database, suspended)
        database.execute("COMMIT")


def _world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str = "domain"
) -> tuple[base._World, ResearchEvidenceLineage]:
    capture = base._primary_source().model_copy(
        update={
            "source_type": "clinical_trial_registry",
            "query_or_identifier": "NCT05405985",
            "content_text": json.dumps(_pk_record()),
            "url": "https://clinicaltrials.gov/study/NCT05405985",
        }
    )
    atoms, _ = extract_ctgov_atomic_results(capture)
    selected = research_facts_from_ctgov_atom(atoms[0])[0]
    context = selected.result_context
    assert context is not None
    assert context.domain == "pk_pd"
    claim = ResearchClaim(
        claim_id="pk-domain-claim",
        claim_text="来源报告原始药代测量值。",
        claim_kind="direct_evidence",
        fact_ids=(selected.fact_id,),
    )
    old_context = context.model_copy(update={"domain": "efficacy"})
    old = selected.model_copy(update={"result_context": old_context})
    if defect == "value":
        old = old.model_copy(update={"raw_value": "17.0", "normalized_value": "17.0"})
    elif defect == "analysis":
        old = old.model_copy(
            update={
                "result_context": old_context.model_copy(
                    update={"analysis_population": "different population"}
                )
            }
        )
    elif defect == "timepoint":
        old = old.model_copy(
            update={
                "result_context": old_context.model_copy(
                    update={"timepoint": "Day 1", "observation_timepoint": "Day 1"}
                )
            }
        )
    elif defect == "unit":
        old = old.model_copy(
            update={
                "result_context": old_context.model_copy(update={"source_unit": "hours"})
            }
        )
    elif defect == "group":
        old = old.model_copy(
            update={
                "result_context": old_context.model_copy(
                    update={"group_id": "OG999", "group_title": "Other", "arm": "Other"}
                )
            }
        )
    elif defect == "endpoint":
        old = old.model_copy(
            update={
                "result_context": old_context.model_copy(
                    update={"endpoint": "Different endpoint", "term": "Different endpoint"}
                )
            }
        )
    elif defect == "arbitrary_domain":
        old = old.model_copy(
            update={
                "result_context": old_context.model_copy(update={"domain": "biomarkers"})
            }
        )
    elif defect == "reverse_domain":
        # Selected is pk_pd from the parser; a prior that is already pk_pd with
        # some other equal material is not this repair — force prior domain to
        # pk_pd and change metric so the pair is not an efficacy→pk_pd repair.
        old = selected.model_copy(
            update={
                "result_context": context.model_copy(update={"metric": "other_metric"})
            }
        )
    monkeypatch.setattr(base, "_sources", lambda: (capture,))
    monkeypatch.setattr(base, "_facts", lambda: (selected,))
    monkeypatch.setattr(base, "_claims", lambda: (claim,))
    # Historical wrong-domain version lands first, then becomes accepted.
    project_root = tmp_path / "project"
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["A"],
        outputs=["html"],
        cutoff="2026-07-31",
    )
    root = create_project_workspace(project_root, contract)
    old_lineage = ingest_research_evidence(
        project_root=root,
        project_id=contract.project_id,
        contract_version=1,
        report_kind="A",
        data_cutoff=base.DATA_CUTOFF,
        scientific_content_digest=hashlib.sha256(b"old-parser-pk-domain").hexdigest(),
        created_at=base.PRODUCED_AT,
        sources=(capture,),
        route_attempts=(),
        facts=(old,),
        claims=(claim,),
    )
    if defect == "user_modified":
        _synthesize_state(root, old_lineage.fact_version_ids[0], "user_modified")
    elif defect == "rejected":
        _synthesize_state(root, old_lineage.fact_version_ids[0], "rejected")
    elif defect == "superseded":
        _synthesize_state(root, old_lineage.fact_version_ids[0], "superseded")
    else:
        _synthesize_accepted_fact(root, old_lineage.fact_version_ids[0])
    # Rebuild the normal production world on the corrected parser output.
    content_digest = hashlib.sha256(b"research-content-pk-domain").hexdigest()
    lineage = ingest_research_evidence(
        project_root=root,
        project_id=contract.project_id,
        contract_version=contract.contract_version,
        report_kind="A",
        data_cutoff=base.DATA_CUTOFF,
        scientific_content_digest=content_digest,
        created_at=base.PRODUCED_AT,
        sources=(capture,),
        route_attempts=(),
        facts=(selected,),
        claims=(claim,),
    )
    context, claim_snapshot_id = base._build_context(
        contract.project_id, content_digest, lineage
    )
    base._publish(root, context)
    receipt = base._issue_receipt(root, context)
    world = base._World(
        root=root,
        project_id=contract.project_id,
        content_digest=content_digest,
        lineage=lineage,
        context=context,
        claim_snapshot_id=claim_snapshot_id,
        receipt=receipt,
    )
    return world, old_lineage


def _synthesize_state(root: Path, fact_version_id: str, review_state: str) -> None:
    with open_database(root / "state/project.sqlite") as database:
        database.execute("BEGIN IMMEDIATE")
        suspended = base.acceptance_service._suspend_append_only_guards(database)
        cursor = database.execute(
            "UPDATE fact_versions SET review_state=? "
            "WHERE fact_version_id=? AND review_state='candidate'",
            (review_state, fact_version_id),
        )
        if int(cursor.rowcount) != 1:
            raise AssertionError("synthetic state fixture did not update exactly one row")
        base.acceptance_service._restore_append_only_guards(database, suspended)
        database.execute("COMMIT")


def _append_extra_accepted_sibling(root: Path, anchor_version_id: str, index: int) -> str:
    """Fixture only: append an accepted sibling the ingestion conflict never saw."""
    with open_database(root / "state/project.sqlite") as database:
        row = database.execute(
            "SELECT fact_id,entity_id,field_id,raw_value,normalized_value,disclosure_state,"
            "primary_fragment_id,content_sha256,scientific_context_json "
            "FROM fact_versions WHERE fact_version_id=?",
            (anchor_version_id,),
        ).fetchone()
        assert row is not None
        version_id: str = stable_id(
            "fact-version", "test-extra-accepted-sibling", anchor_version_id, str(index)
        )
        database.execute(
            "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,raw_value,"
            "normalized_value,disclosure_state,review_state,primary_fragment_id,"
            "supersedes_fact_version_id,created_at,content_sha256,scientific_context_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,NULL,?,?,?)",
            (
                version_id,
                str(row[0]),
                str(row[1]),
                str(row[2]),
                str(row[3]),
                row[4],
                str(row[5]),
                "accepted",
                str(row[6]),
                base.CHECKED_AT.isoformat(),
                str(row[7]),
                str(row[8]),
            ),
        )
    return version_id


def test_signed_exact_pk_domain_correction_preserves_history_and_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, old = _world(tmp_path, monkeypatch)
    snapshots = base._file_digests(world.root, "snapshots")
    before = base._fact_states(world.root)
    accepted = base._accept(world)
    assert len(accepted.source_scope_corrections) == 1
    proof = json.loads(accepted.source_scope_corrections[0].resolution_note)
    assert (
        proof["classification"]
        == "same_registry_scalar_parser_domain_correction"
    )
    assert proof["selected_fact_version_id"] == world.lineage.fact_version_ids[0]
    assert proof["receipt_digest"] == world.receipt.receipt_digest
    assert base._accept(world) == accepted
    after = base._fact_states(world.root)
    assert after[old.fact_version_ids[0]] == before[old.fact_version_ids[0]]
    assert after[world.lineage.fact_version_ids[0]][0] == "accepted"
    assert base._file_digests(world.root, "snapshots") == snapshots
    with open_database(world.root / "state/project.sqlite") as db:
        state, note = db.execute(
            "SELECT resolution_state,resolution_note FROM conflict_sets"
        ).fetchone()
    assert state == "open"
    correction = accepted.source_scope_corrections[0]
    assert note == correction.original_resolution_note
    assert (
        old.fact_version_ids[0]
        in json.loads(proof["original_resolution_note"])["fact_version_ids"]
    )
    assert not (world.root / "reports/current.json").exists()


@pytest.mark.parametrize(
    "defect",
    [
        "value",
        "analysis",
        "timepoint",
        "unit",
        "group",
        "endpoint",
        "arbitrary_domain",
        "reverse_domain",
        "user_modified",
        "rejected",
        "superseded",
    ],
)
def test_real_disagreement_or_non_domain_repair_stays_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    world, _ = _world(tmp_path, monkeypatch, defect)
    before = base._fact_states(world.root)
    with pytest.raises(
        SourceFactAcceptanceError,
        match="冲突|已接受|user_modified|rejected|superseded",
    ):
        base._accept(world)
    assert base._fact_states(world.root) == before
    with open_database(world.root / "state/project.sqlite") as db:
        assert db.execute("SELECT resolution_state FROM conflict_sets").fetchone() == ("open",)


@pytest.mark.parametrize("extra_count", [1, 2])
def test_accepted_sibling_outside_validated_membership_stays_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra_count: int
) -> None:
    """Partial/missing membership: any accepted sibling of the same logical fact
    that the validated conflict membership never covered must refuse the repair;
    one covered sibling is not a matching count that authorizes the rest."""
    world, old = _world(tmp_path, monkeypatch)
    extras = [
        _append_extra_accepted_sibling(world.root, old.fact_version_ids[0], index)
        for index in range(extra_count)
    ]
    before = base._fact_states(world.root)
    with pytest.raises(SourceFactAcceptanceError, match="已接受"):
        base._accept(world)
    after = base._fact_states(world.root)
    assert after == before
    for version_id in extras:
        assert after[version_id][0] == "accepted"
    with open_database(world.root / "state/project.sqlite") as db:
        assert db.execute("SELECT resolution_state FROM conflict_sets").fetchone() == ("open",)
        assert (
            db.execute(
                "SELECT 1 FROM idempotency_keys WHERE idempotency_key=?",
                (f"source.fact.acceptance:{world.receipt.receipt_digest}",),
            ).fetchone()
            is None
        )
    assert not (
        world.root / source_fact_acceptance_decision_path("A", world.receipt.receipt_digest)
    ).exists()
    assert base._acceptance_events(world.root, world.receipt.receipt_digest) == []


def test_forged_conflict_membership_row_stays_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forged membership: a fabricated member list never creates repair authority;
    an extra open conflict row cannot be washed over by the genuine one."""
    world, _ = _world(tmp_path, monkeypatch)
    selected_version_id = world.lineage.fact_version_ids[0]
    with open_database(world.root / "state/project.sqlite") as database:
        fact_id = str(
            database.execute(
                "SELECT fact_id FROM fact_versions WHERE fact_version_id=?",
                (selected_version_id,),
            ).fetchone()[0]
        )
        database.execute(
            "INSERT INTO conflict_sets (conflict_set_id,object_type,object_id,"
            "resolution_state,resolution_note,created_at) VALUES (?,?,?,?,?,?)",
            (
                "forged-conflict-1007",
                "fact",
                fact_id,
                "open",
                json.dumps(
                    {"fact_version_ids": [selected_version_id, "forged-member-1007"]},
                    ensure_ascii=False,
                ),
                base.PRODUCED_AT.isoformat(),
            ),
        )
    before = base._fact_states(world.root)
    with pytest.raises(SourceFactAcceptanceError, match="冲突"):
        base._accept(world)
    assert base._fact_states(world.root) == before
    with open_database(world.root / "state/project.sqlite") as database:
        states = database.execute(
            "SELECT resolution_state FROM conflict_sets ORDER BY conflict_set_id"
        ).fetchall()
    assert len(states) == 2
    assert {str(row[0]) for row in states} == {"open"}
    assert not (
        world.root / source_fact_acceptance_decision_path("A", world.receipt.receipt_digest)
    ).exists()
    assert base._acceptance_events(world.root, world.receipt.receipt_digest) == []


def test_unsigned_or_corrupt_receipt_does_not_correct_pk_domain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, _ = _world(tmp_path, monkeypatch)
    before = base._fact_states(world.root)
    (world.root / review_issuance_record_path("A")).unlink()
    with pytest.raises(SourceFactAcceptanceError):
        base._accept(world)
    assert base._fact_states(world.root) == before


def test_domain_resolution_rolls_back_with_fact_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world, _ = _world(tmp_path, monkeypatch)
    before = base._fact_states(world.root)
    with monkeypatch.context() as patch:

        def fail(*_args: object) -> None:
            raise OSError("domain rollback probe")

        patch.setattr(base.acceptance_service, "_restore_append_only_guards", fail)
        with pytest.raises(OSError, match="domain rollback probe"):
            base._accept(world)
    assert base._fact_states(world.root) == before
    with open_database(world.root / "state/project.sqlite") as db:
        assert db.execute("SELECT resolution_state FROM conflict_sets").fetchone() == ("open",)
    assert len(base._accept(world).source_scope_corrections) == 1
