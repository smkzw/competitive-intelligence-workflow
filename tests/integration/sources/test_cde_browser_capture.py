"""Exact public browser captures; registry acceptance is not indication approval."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.storage.content_store import ContentAddressedStore
from ci_workflow.storage.source_derivation import (
    extract_locator_quote,
    verify_source_text_derivation,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/cde-browser"
NAMES = (
    "dupilumab-acceptances-page1.json",
    "dupilumab-acceptances-page2.json",
    "dupilumab-review-JYSB2600265.json",
)
CHECKED = datetime(2026, 10, 3, 12, 46, tzinfo=UTC)


def _captures() -> tuple[bytes, ...]:
    return tuple((FIXTURES / name).read_bytes() for name in NAMES)


def _build(root: Path, captures: tuple[bytes, ...] | None = None) -> Any:
    from ci_workflow.application.cde_browser_research import build_cde_browser_candidates

    return build_cde_browser_candidates(
        root,
        captures=_captures() if captures is None else captures,
        checked_at=CHECKED,
    )


def test_complete_real_directory_and_exact_review_row_preserve_originals(tmp_path: Path) -> None:
    batch = _build(tmp_path)
    assert len(batch.acceptance_numbers) == len(set(batch.acceptance_numbers)) == 80
    assert batch.acceptance_directory_complete is True
    assert batch.indication_lock == "unresolved"
    assert batch.scientifically_accepted is False
    assert len(batch.sources) == 3
    assert batch.facts and batch.claims
    assert all("approval" not in fact.field_id for fact in batch.facts)
    statuses = [fact for fact in batch.facts if fact.field_id == "cde.review_status"]
    assert len(statuses) == 1
    assert statuses[0].row_ref == "china-application:JYSB2600265"
    assert statuses[0].raw_value == "排队待审评"
    assert all(fact.row_ref != "china-application:JXSB2600179" for fact in batch.facts)
    for source, raw in zip(batch.sources, _captures(), strict=True):
        assert source.text_derivation is not None
        assert source.text_derivation.raw_asset.sha256 == sha256(raw).hexdigest()
        assert ContentAddressedStore(tmp_path).read_bytes(source.text_derivation.raw_asset) == raw
        verify_source_text_derivation(tmp_path, source.text_derivation, source.content_text)
        assert source.published_at is source.effective_at is source.first_disclosed_at is None
        assert not source.date_evidence("first_disclosed_at").is_known_by(CHECKED)
    by_id = {source.source_id: source for source in batch.sources}
    for fact in batch.facts:
        source = by_id[fact.source_id]
        assert (
            extract_locator_quote(
                source.content_text,
                media_type=source.media_type,
                locator=fact.locator,
            )
            == fact.original_text
            == fact.raw_value
        )


def test_partial_pagination_keeps_known_records_without_claiming_closure(tmp_path: Path) -> None:
    batch = _build(tmp_path, _captures()[:1])
    assert len(batch.acceptance_numbers) == 50
    assert batch.acceptance_directory_complete is False
    assert any(gap.reason == "pagination_incomplete" for gap in batch.gaps)
    assert batch.facts


def test_missing_exact_review_row_does_not_adopt_neighbor_or_assert_no_application(
    tmp_path: Path,
) -> None:
    captures = list(_captures())
    record = json.loads(captures[2])
    record["query"]["acceptance_number"] = "JYSB2999999"
    captures[2] = json.dumps(record, ensure_ascii=False).encode()
    batch = _build(tmp_path, tuple(captures))
    assert not any(fact.field_id == "cde.review_status" for fact in batch.facts)
    assert any(
        gap.subject == "JYSB2999999" and gap.reason == "review_not_located" for gap in batch.gaps
    )
    assert not any("absent" in fact.field_id for fact in batch.facts)


@pytest.mark.parametrize(
    "case",
    [
        "wrong_host",
        "wrong_kind",
        "duplicate_acceptance",
        "wrong_header",
        "truncated_row",
        "different_query",
        "naive_time",
        "future_time",
        "wrong_review_drug_type",
        "wrong_review_application",
    ],
)
def test_malformed_or_misscoped_capture_rejects_before_cas_write(
    tmp_path: Path,
    case: str,
) -> None:
    captures = list(_captures())
    record = json.loads(captures[0])
    if case == "wrong_host":
        record["url"] = "https://cde.org.cn.attacker.invalid/public"
    elif case == "wrong_kind":
        record["kind"] = "source_accepted"
    elif case == "duplicate_acceptance":
        record["tables"][0]["rows"][2][1] = record["tables"][0]["rows"][1][1]
    elif case == "wrong_header":
        record["tables"][0]["rows"][0][7] = "首次公开时间"
    elif case == "truncated_row":
        record["tables"][0]["rows"][1].pop()
    elif case == "different_query":
        record["query"]["drug_name"] = "别的药"
    elif case == "naive_time":
        record["acquired_at"] = "2026-10-03T12:41:34"
    elif case == "future_time":
        record["acquired_at"] = "2026-10-04T12:41:34Z"
    else:
        record = json.loads(captures[2])
        if case == "wrong_review_drug_type":
            record["query"]["drug_type"] = "预防用生物制品"
        else:
            record["query"]["application_type"] = "LCSYSQ"
        captures[2] = json.dumps(record, ensure_ascii=False).encode()
        record = json.loads(captures[0])
    captures[0] = json.dumps(record, ensure_ascii=False).encode()
    root = tmp_path / "must-remain-uncreated"
    with pytest.raises(ValueError):
        _build(root, tuple(captures))
    assert not root.exists()


def test_repeated_review_capture_rejects_before_cas_write(tmp_path: Path) -> None:
    captures = _captures()
    root = tmp_path / "untouched"
    with pytest.raises(ValueError, match="重复"):
        _build(root, (*captures, captures[-1]))
    assert not root.exists()


def test_query_metadata_cannot_smuggle_credentials_into_source_cas(tmp_path: Path) -> None:
    record = json.loads(_captures()[0])
    record["query"]["password"] = "synthetic-not-a-credential"
    root = tmp_path / "untouched"
    with pytest.raises(ValueError, match="字段"):
        _build(root, (json.dumps(record, ensure_ascii=False).encode(),))
    assert not root.exists()


def test_page_arrival_order_changes_neither_scientific_atoms_nor_coverage(tmp_path: Path) -> None:
    first = _build(tmp_path / "one")
    second = _build(tmp_path / "two", tuple(reversed(_captures())))
    assert set(first.acceptance_numbers) == set(second.acceptance_numbers)
    assert first.acceptance_directory_complete is second.acceptance_directory_complete is True
    assert {fact.fact_id: fact.model_dump(mode="json") for fact in first.facts} == {
        fact.fact_id: fact.model_dump(mode="json") for fact in second.facts
    }


def test_capture_duplicate_json_keys_fail_closed(tmp_path: Path) -> None:
    capture = _captures()[0].decode()
    malformed = capture.replace('"kind":', '"kind":"forged", "kind":', 1).encode()
    with pytest.raises(ValueError):
        _build(tmp_path / "untouched", (malformed,))


def test_real_cde_candidate_uses_existing_ingestion_without_acceptance_or_consumers(
    tmp_path: Path,
) -> None:
    from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
    from ci_workflow.application.project_service import create_project_workspace
    from ci_workflow.domain.contracts import create_project_contract
    from ci_workflow.storage.sqlite import open_database

    contract = create_project_contract(
        indication="慢性鼻窦炎伴鼻息肉",
        reports=["A", "B", "C"],
        outputs=["html"],
        cutoff="2026-10-03",
        created_at=CHECKED,
    )
    project = create_project_workspace(tmp_path / "project", contract)
    batch = _build(project)
    digest = sha256(b"".join(_captures())).hexdigest()
    kwargs = dict(
        project_root=project,
        project_id=contract.project_id,
        contract_version=1,
        report_kind="A",
        data_cutoff=CHECKED,
        scientific_content_digest=digest,
        created_at=CHECKED,
        sources=batch.sources,
        route_attempts=(),
        facts=batch.facts,
        claims=batch.claims,
    )
    first = ingest_research_evidence(**kwargs)
    second = ingest_research_evidence(**kwargs)
    assert first.evidence_snapshot == second.evidence_snapshot
    assert len(first.fact_version_ids) == len(batch.facts)
    with open_database(project / "state/project.sqlite") as database:
        states = database.execute("SELECT DISTINCT review_state FROM fact_versions").fetchall()
        assert states == [("candidate",)]
        assert database.execute(
            "SELECT count(*) FROM source_portal_consumer_bindings"
        ).fetchone() == (0,)
        assert database.execute("SELECT count(*) FROM source_versions").fetchone() == (3,)
    assert not (project / "reports/current.json").exists()
