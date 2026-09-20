"""Report-agnostic ingestion of reviewed research evidence.

This boundary persists source bytes, atomic facts, claims, receipts, and one
content-addressed evidence snapshot.  It deliberately does not persist a gate
decision: report gates are recomputed by the deterministic engine afterwards.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from ci_workflow.application.fresh_research_primitives import (
    ResearchClaim,
    ResearchFact,
    RouteAttempt,
    SourceCapture,
)
from ci_workflow.domain.evidence import SourceReceipt
from ci_workflow.domain.ids import stable_id
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    LockedSnapshot,
    SnapshotStore,
)
from ci_workflow.storage.sqlite import open_database

ReportCode = Literal["A", "B", "C"]
_SHA256 = re.compile(r"[0-9a-f]{64}")


class ResearchIngestionError(ValueError):
    """Research evidence cannot be persisted without breaking lineage."""


@dataclass(frozen=True)
class ResearchEvidenceLineage:
    evidence_snapshot: LockedSnapshot
    source_version_ids: tuple[str, ...]
    fragment_ids: tuple[str, ...]
    fact_version_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    fact_version_by_ref: Mapping[str, str]


def _validate_references(
    sources: Sequence[SourceCapture],
    facts: Sequence[ResearchFact],
    claims: Sequence[ResearchClaim],
) -> None:
    source_ids = [item.source_id for item in sources]
    fact_ids = [item.fact_id for item in facts]
    claim_ids = [item.claim_id for item in claims]
    if len(source_ids) != len(set(source_ids)):
        raise ResearchIngestionError("研究来源标识不得重复")
    if len(fact_ids) != len(set(fact_ids)):
        raise ResearchIngestionError("研究事实标识不得重复")
    if len(claim_ids) != len(set(claim_ids)):
        raise ResearchIngestionError("研究声明标识不得重复")
    if set(item.source_id for item in facts) - set(source_ids):
        raise ResearchIngestionError("研究事实引用了包外来源")
    for claim in claims:
        if set(claim.fact_ids) - set(fact_ids):
            raise ResearchIngestionError("研究声明引用了包外事实")


def ingest_research_evidence(
    *,
    project_root: Path,
    project_id: str,
    contract_version: int,
    report_kind: ReportCode,
    data_cutoff: datetime,
    scientific_content_digest: str,
    created_at: datetime,
    sources: Sequence[SourceCapture],
    route_attempts: Sequence[RouteAttempt],
    facts: Sequence[ResearchFact],
    claims: Sequence[ResearchClaim],
) -> ResearchEvidenceLineage:
    """Persist one immutable evidence lineage, idempotently and without a gate."""
    if _SHA256.fullmatch(scientific_content_digest) is None:
        raise ResearchIngestionError("科学内容摘要必须是小写 SHA-256")
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ResearchIngestionError("证据快照时间必须包含明确时区")
    if not sources or not facts or not claims:
        raise ResearchIngestionError("研究证据必须包含来源、事实和声明")
    _validate_references(sources, facts, claims)

    database_path = project_root / "state/project.sqlite"
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    source_versions: dict[str, str] = {}
    fragments: dict[str, str] = {}
    receipts: list[SourceReceipt] = []
    from ci_workflow.storage.source_derivation import verify_source_text_derivation

    for capture in sources:
        if capture.text_derivation is not None:
            verify_source_text_derivation(
                project_root, capture.text_derivation, capture.content_text
            )
    for capture in sources:
        version = repository.add_source_version(
            source_id=capture.source_id,
            content=capture.content_text.encode("utf-8"),
            media_type=(
                "text/plain" if capture.media_type == "application/pdf" else capture.media_type
            ),
            text_derivation=capture.text_derivation,
            acquired_at=capture.acquired_at,
            published_at=capture.date_evidence("published_at"),
            effective_at=capture.date_evidence("effective_at"),
            first_disclosed_at=capture.date_evidence("first_disclosed_at"),
        )
        fragment = repository.add_fragment(
            source_version_id=version.source_version_id,
            locator=capture.locator,
            original_text=capture.content_text,
            created_at=capture.acquired_at,
        )
        source_versions[capture.source_id] = version.source_version_id
        fragments[capture.source_id] = fragment.fragment_id
        receipts.append(
            SourceReceipt(
                schema_version="1.0",
                receipt_id=stable_id("source-receipt", project_id, report_kind, capture.source_id),
                route_id=capture.route_id,
                strategy_unit_id=f"{capture.route_id}:primary",
                entity_id=project_id,
                gap_id=f"{report_kind}_FRESH_SOURCE",
                claim_domain=f"{report_kind}_RESEARCH",
                query_or_identifier=capture.query_or_identifier,
                language=capture.language,
                access_method=capture.access_method,
                attempt_index=1,
                started_at=capture.acquired_at,
                ended_at=capture.acquired_at,
                scheduled_backoff_ms=0,
                actual_backoff_ms=0,
                result_class="content_acquired",
                error_class=None,
                completeness_checks=("身份可定位", "正文已保存", "截止日适格"),
                alternative_paths=("其他官方登记", "主要论文或监管材料"),
                source_version_id=version.source_version_id,
                content_sha256=version.content_sha256,
                diagnostic_confidence="high",
                parent_attempt_id=None,
                recovery_round=0,
            )
        )
    for attempt in route_attempts:
        receipts.append(
            SourceReceipt(
                schema_version="1.0",
                receipt_id=attempt.attempt_id,
                route_id=attempt.route_id,
                strategy_unit_id=attempt.strategy_unit_id,
                entity_id=project_id,
                gap_id=attempt.gap_id,
                claim_domain=f"{report_kind}_RESEARCH",
                query_or_identifier=attempt.query_or_identifier,
                language=attempt.language,
                access_method=attempt.access_method,
                attempt_index=attempt.attempt_index,
                started_at=attempt.started_at,
                ended_at=attempt.ended_at,
                scheduled_backoff_ms=2000 if attempt.attempt_index > 1 else 0,
                actual_backoff_ms=2000 if attempt.attempt_index > 1 else 0,
                result_class=attempt.result_class,
                error_class=attempt.error_class,
                completeness_checks=("未取得可解析正文", "已区分技术失败与未检出"),
                alternative_paths=attempt.alternative_paths,
                source_version_id=None,
                content_sha256=None,
                diagnostic_confidence=attempt.diagnostic_confidence,
                parent_attempt_id=attempt.parent_attempt_id,
                recovery_round=attempt.recovery_round,
            )
        )

    fact_versions: dict[str, str] = {}
    with open_database(database_path) as database:
        for fact in facts:
            database.execute(
                """INSERT OR IGNORE INTO entities
                (entity_id,entity_type,canonical_name,created_at) VALUES (?,?,?,?)""",
                (fact.entity_id, fact.entity_type, fact.canonical_name, created_at.isoformat()),
            )
            fragment_id = fragments[fact.source_id]
            version_id = stable_id(
                "fact-version",
                fact.fact_id,
                fact.field_id,
                fact.normalized_value or fact.disclosure_state,
                fragment_id,
            )
            database.execute(
                """INSERT OR IGNORE INTO fact_versions (
                fact_version_id,fact_id,entity_id,field_id,raw_value,normalized_value,
                disclosure_state,review_state,primary_fragment_id,supersedes_fact_version_id,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,NULL,?)""",
                (
                    version_id,
                    fact.fact_id,
                    fact.entity_id,
                    fact.field_id,
                    fact.raw_value,
                    fact.normalized_value,
                    fact.disclosure_state,
                    "accepted",
                    fragment_id,
                    created_at.isoformat(),
                ),
            )
            database.execute(
                """INSERT OR IGNORE INTO fact_evidence
                (fact_version_id,fragment_id,evidence_role,created_at) VALUES (?,?,?,?)""",
                (version_id, fragment_id, "primary", created_at.isoformat()),
            )
            fact_versions[fact.fact_id] = version_id
        for claim in claims:
            claim_version_id = stable_id(
                "claim-version",
                claim.claim_id,
                claim.claim_text,
                *(fact_versions[item] for item in claim.fact_ids),
            )
            database.execute(
                """INSERT OR IGNORE INTO claim_versions (
                claim_version_id,claim_id,claim_text,claim_kind,review_state,
                supersedes_claim_version_id,created_at) VALUES (?,?,?,?,?,NULL,?)""",
                (
                    claim_version_id,
                    claim.claim_id,
                    claim.claim_text,
                    claim.claim_kind,
                    "accepted",
                    created_at.isoformat(),
                ),
            )
            for fact_id in claim.fact_ids:
                database.execute(
                    """INSERT OR IGNORE INTO claim_facts
                    (claim_version_id,fact_version_id,support_role,created_at)
                    VALUES (?,?,?,?)""",
                    (claim_version_id, fact_versions[fact_id], "supports", created_at.isoformat()),
                )

    manifest = EvidenceSnapshotManifest(
        schema_version="1.0",
        project_id=project_id,
        contract_version=contract_version,
        data_cutoff=data_cutoff,
        source_version_ids=tuple(sorted(source_versions.values())),
        fragment_ids=tuple(fragments[item.source_id] for item in sources),
        fact_version_ids=tuple(sorted(fact_versions.values())),
        scientific_content_digest=scientific_content_digest,
        created_at=created_at,
    )
    evidence_snapshot = SnapshotStore(project_root).lock_evidence_snapshot(
        manifest.model_dump(mode="json")
    )
    receipt_path = project_root / "receipts/source_receipts.jsonl"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        {
            str(json.loads(line)["receipt_id"])
            for line in receipt_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        if receipt_path.is_file()
        else set()
    )
    with receipt_path.open("a", encoding="utf-8") as handle:
        for receipt in receipts:
            if receipt.receipt_id not in existing:
                handle.write(
                    json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )

    return ResearchEvidenceLineage(
        evidence_snapshot=evidence_snapshot,
        source_version_ids=tuple(sorted(source_versions.values())),
        fragment_ids=tuple(sorted(fragments.values())),
        fact_version_ids=tuple(sorted(fact_versions.values())),
        claim_ids=tuple(item.claim_id for item in claims),
        fact_version_by_ref={
            reference: fact_versions[fact.fact_id]
            for fact in facts
            for reference in (fact.fact_id, fact.row_ref)
        },
    )


__all__ = ["ResearchEvidenceLineage", "ResearchIngestionError", "ingest_research_evidence"]
