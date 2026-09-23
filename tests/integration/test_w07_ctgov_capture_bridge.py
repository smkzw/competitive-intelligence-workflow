"""CT.gov 原始分页切片到现有研究来源合同的最小接缝。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
    extract_ctgov_atomic_results,
    research_facts_from_ctgov_atom,
    source_capture_from_ctgov_study,
)
from ci_workflow.domain.evidence import CtgovRecordSelector
from ci_workflow.sources.connectors.ctgov_fetch import DerivedCtgovStudy
from ci_workflow.storage.source_derivation import capture_source_text
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_research_package_submission import _project


def _derived(tmp_path: Path) -> DerivedCtgovStudy:
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT04558918", "briefTitle": "PNH study"},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-08-01"}},
        },
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": []}},
    }
    raw = json.dumps({"studies": [record]}, ensure_ascii=False).encode()
    text, receipt = capture_source_text(
        tmp_path,
        raw,
        media_type="application/json",
        record_selector=CtgovRecordSelector(study_index=0, nct_id="NCT04558918"),
    )
    return DerivedCtgovStudy(
        nct_id="NCT04558918",
        title="PNH study",
        record_url="https://clinicaltrials.gov/study/NCT04558918",
        registry_posted_version_date="2026-08-01",
        acquired_at=datetime(2026, 8, 3, tzinfo=UTC),
        content_text=text,
        text_derivation=receipt,
    )


def test_ctgov_study_capture_reopens_raw_and_preserves_calendar_day(tmp_path: Path) -> None:
    study = _derived(tmp_path)
    capture = source_capture_from_ctgov_study(tmp_path, study)
    assert capture.source_id == "ctgov-nct04558918"
    assert capture.source_type == "clinical_trial_registry"
    assert capture.text_derivation == study.text_derivation
    assert capture.date_evidence("published_at").precision == "calendar_day"
    assert capture.date_evidence("first_disclosed_at").precision == "calendar_day"
    assert capture.locator.field_path == "$.protocolSection.identificationModule.nctId"


def test_ctgov_study_capture_rejects_identity_date_or_raw_drift(tmp_path: Path) -> None:
    study = _derived(tmp_path)
    for changed in (
        study.model_copy(update={"nct_id": "NCT00000001"}),
        study.model_copy(update={"registry_posted_version_date": "2026-08-02"}),
        study.model_copy(update={"content_text": study.content_text.replace("PNH", "ABC")}),
    ):
        with pytest.raises(ValueError):
            source_capture_from_ctgov_study(tmp_path, changed)


def test_real_registry_atoms_enter_existing_fact_snapshot_with_exact_quotes(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item)
        for item in payload["sources"]
        if item["query_or_identifier"] == "NCT02277743"
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    assert "result_context" not in ResearchFact.model_validate(
        payload["facts"][0]
    ).model_dump(mode="json")
    assert not issues
    reported = next(item for item in atoms if item.category == "outcome")
    zero = next(
        item for item in atoms
        if item.category == "sae" and item.group_id == "EG001"
        and item.value_quote == "0" and item.denominator_quote == "229"
    )
    facts = (
        *research_facts_from_ctgov_atom(reported),
        *research_facts_from_ctgov_atom(zero),
    )
    assert len(facts) == 3
    assert facts[0].raw_value == "10.3"
    assert facts[1].disclosure_state == "reported_zero"
    assert facts[2].raw_value == "229"
    assert facts[1].result_context is not None
    assert facts[1].result_context.group_id == "EG001"
    assert facts[1].result_context.term == zero.term
    assert facts[1].result_context.value_role == "affected_count"
    with pytest.raises(ValueError, match="领域不一致"):
        research_facts_from_ctgov_atom(zero, report_row_ref="efficacy:wrong")

    project = _project(tmp_path)
    contract = verify_project_workspace(project).contract
    claim = ResearchClaim(
        claim_id="direct-registry-atoms", claim_text="登记原始数值和独立分母字段",
        claim_kind="direct_evidence", fact_ids=tuple(item.fact_id for item in facts),
    )
    digest = sha256(b"NCT02277743:three-atomic-facts").hexdigest()
    lineage = ingest_research_evidence(
        project_root=project, project_id=contract.project_id, contract_version=1,
        report_kind="A", data_cutoff=contract.data_cutoff,
        scientific_content_digest=digest, created_at=source.acquired_at,
        sources=(source,), route_attempts=(), facts=facts, claims=(claim,),
    )

    assert len(lineage.source_version_ids) == 1
    assert len(lineage.fact_version_ids) == len(facts)
    with open_database(project / "state/project.sqlite") as database:
        rows = database.execute(
            "SELECT raw_value,disclosure_state,scientific_context_json "
            "FROM fact_versions WHERE fact_id IN (?,?,?) ORDER BY raw_value",
            tuple(item.fact_id for item in facts),
        ).fetchall()
        fragments = database.execute(
            "SELECT content_text,locator FROM evidence_fragments "
            "WHERE fragment_id IN (?,?,?)",
            tuple(lineage.fragment_by_fact_id[item.fact_id] for item in facts),
        ).fetchall()
    assert {row[0] for row in rows} == {"10.3", "0", "229"}
    assert any(row[0] == "0" and row[1] == "reported_zero" for row in rows)
    assert any('"group_id":"EG001"' in row[2] for row in rows)
    assert {row[0] for row in fragments} == {"10.3", "0", "229"}
    assert all('"field_path":"$.' in row[1] for row in fragments)


def test_missing_affected_count_never_becomes_a_zero_atom_or_fact() -> None:
    payload = json.loads(
        Path("fixtures/positive/a-atopic-dermatitis/research-content.json").read_text()
    )
    source = next(
        SourceCapture.model_validate(item)
        for item in payload["sources"]
        if item["query_or_identifier"] == "NCT05131477"
    )
    atoms, issues = extract_ctgov_atomic_results(source)
    missing = next(
        issue for issue in issues
        if issue.source_path.endswith("seriousEvents[16].stats[7].numAffected")
    )
    assert missing.status == "missing"
    assert "未知，待核" in missing.reason_zh
    assert all(
        atom.value_locator.field_path != f"$.{missing.source_path}"
        for atom in atoms
    )
    assert all(
        fact.locator.field_path != f"$.{missing.source_path}"
        for atom in atoms for fact in research_facts_from_ctgov_atom(atom)
    )
