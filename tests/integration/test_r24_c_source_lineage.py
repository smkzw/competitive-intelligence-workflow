"""Real C sections retain scalar originals and replay their deterministic derivation."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application import fresh_c_research_package as module
from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.source_research_service import ResearchClaim
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.snapshot_store import SnapshotStore
from ci_workflow.storage.source_derivation import extract_locator_quote
from tests.integration.test_r24_ctgov_c_design_projection import (
    _CAS_ROOT,
    _fixed_capture,
    _project_fixed,
)


def _facts():
    builder = getattr(module, "research_facts_from_c_observations", None)
    assert callable(builder), "C source projection needs a verified atomic-fact boundary"
    captures = tuple(_fixed_capture(nct) for nct in ("NCT02264639", "NCT03829449"))
    observations = _project_fixed("NCT02264639", "NCT03829449").observations
    facts = builder(observations, sources=captures, trial_names={
        "nct02264639": "NCT02264639", "nct03829449": "NCT03829449",
    })
    return captures, observations, facts


def test_real_sections_keep_full_scalar_original_not_fake_narrow_locator() -> None:
    captures, observations, facts = _facts()
    by_id = {source.source_id: source for source in captures}
    by_row = {row.row_id: row for row in observations}
    assert len(facts) == len(observations)
    for fact in facts:
        source = by_id[fact.source_id]
        assert fact.original_text == extract_locator_quote(
            source.content_text, media_type=source.media_type, locator=fact.locator,
        )
        assert fact.raw_value == fact.original_text
        assert fact.normalized_value == by_row[fact.row_ref].source_text
        if by_row[fact.row_ref].field in {"inclusion_criterion", "exclusion_criterion"}:
            assert fact.normalized_value in fact.original_text
            assert fact.normalized_value != fact.original_text
            assert fact.locator.field_path.endswith("eligibilityCriteria")


@pytest.mark.parametrize("variant", ["section_text", "section_rule", "wrong_trial", "wrong_url"])
def test_unproved_c_derivation_or_source_identity_fails_closed(variant: str) -> None:
    builder = getattr(module, "research_facts_from_c_observations", None)
    assert callable(builder), "C atomic-fact boundary missing"
    captures = (_fixed_capture("NCT02264639"),)
    rows = list(_project_fixed("NCT02264639").observations)
    index = next(i for i, row in enumerate(rows) if row.field == "inclusion_criterion")
    row = rows[index]
    if variant == "section_text":
        rows[index] = row.model_copy(update={"source_text": "A fabricated eligibility condition"})
    elif variant == "section_rule":
        rows[index] = row.model_copy(update={"compatibility_rule": "unknown-split"})
    elif variant == "wrong_trial":
        rows[index] = row.model_copy(update={"trial_id": "nct-not-the-source"})
    else:
        rows[index] = row.model_copy(update={"source_locator": row.source_locator.model_copy(
            update={"url": "https://clinicaltrials.gov/study/NCT00000001"},
        )})
    with pytest.raises(module.FreshCPackageError):
        builder(rows, sources=captures, trial_names={
            "nct02264639": "NCT02264639", "nct-not-the-source": "foreign",
        })


def test_c_real_evidence_ingests_with_actual_immutable_versions_idempotently(
    tmp_path: Path,
) -> None:
    captures, observations, facts = _facts()
    contract = create_project_contract(indication="阵发性睡眠性血红蛋白尿症",
        reports=["C"], outputs=["html"], cutoff="2026-09-26",
        created_at=datetime(2026, 10, 3, tzinfo=UTC))
    root = tmp_path / "c-source-project"
    create_project_workspace(root, contract)
    for source in captures:
        assert source.text_derivation is not None
        raw = source.text_derivation.raw_asset
        original = ContentAddressedStore(_CAS_ROOT).read_bytes(raw)
        assert ContentAddressedStore(root).put_bytes(original, media_type=raw.media_type) == raw
    claims = tuple(ResearchClaim(claim_id="claim-" + fact.fact_id,
        claim_text=fact.normalized_value or fact.original_text, claim_kind="direct_evidence",
        fact_ids=(fact.fact_id,)) for fact in facts)
    arguments = dict(project_root=root, project_id=contract.project_id,
        contract_version=contract.contract_version, report_kind="C",
        data_cutoff=contract.data_cutoff, scientific_content_digest=hashlib.sha256(
            "".join(row.model_dump_json() for row in observations).encode()).hexdigest(),
        created_at=datetime(2026, 10, 3, tzinfo=UTC), sources=captures,
        route_attempts=(), facts=facts, claims=claims)
    first = ingest_research_evidence(**arguments)
    second = ingest_research_evidence(**arguments)
    assert second == first
    assert len(first.source_version_ids) == 2
    assert all(version.startswith("source-version_") for version in first.source_version_ids)
    assert set(first.fact_version_by_ref) == {row.row_id for row in observations}
    snapshot = SnapshotStore(root).read(first.evidence_snapshot)
    assert len(snapshot["closure"]["facts"]) == len(observations)
    assert not (root / "current.json").exists()
