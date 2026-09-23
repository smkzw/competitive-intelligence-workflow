"""Report-agnostic ingestion of reviewed research evidence.

This boundary persists source bytes, atomic facts, claims, receipts, and one
content-addressed evidence snapshot.  It deliberately does not persist a gate
decision: report gates are recomputed by the deterministic engine afterwards.
"""

from __future__ import annotations

import json
import re
from base64 import b64encode
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
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
    source_fragment_ids: tuple[str, ...]
    fragment_ids: tuple[str, ...]
    fact_version_ids: tuple[str, ...]
    claim_version_ids: tuple[str, ...]
    derivation_ids: tuple[str, ...]
    receipt_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    fact_version_by_ref: Mapping[str, str]
    fragment_by_fact_id: Mapping[str, str]


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
    request_id: str | None = None,
) -> ResearchEvidenceLineage:
    """Persist one immutable evidence lineage, idempotently and without a gate."""
    if _SHA256.fullmatch(scientific_content_digest) is None:
        raise ResearchIngestionError("科学内容摘要必须是小写 SHA-256")
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ResearchIngestionError("证据快照时间必须包含明确时区")
    if not sources or not facts or not claims:
        raise ResearchIngestionError("研究证据必须包含来源、事实和声明")
    _validate_references(sources, facts, claims)
    ingestion_request_id = request_id or stable_id(
        "research-ingestion-request",
        project_id,
        report_kind,
        scientific_content_digest,
    )

    database_path = project_root / "state/project.sqlite"
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    source_versions: dict[str, str] = {}
    fragments: dict[str, str] = {}
    receipts: list[SourceReceipt] = []
    acquisition_attempts: list[dict[str, object]] = []
    from ci_workflow.storage.source_derivation import (
        SourceDerivationError,
        extract_locator_quote,
        verify_source_text_derivation,
    )

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
        with open_database(database_path) as database:
            existing_attempt = database.execute(
                """SELECT attempt_id,source_version_id,receipt_id,attempt_index,
                acquired_at,created_at FROM source_acquisition_attempts
                WHERE request_id=? AND source_id=?""",
                (ingestion_request_id, capture.source_id),
            ).fetchone()
            if existing_attempt is not None:
                if str(existing_attempt[1]) != version.source_version_id:
                    raise ResearchIngestionError(
                        "同一幂等请求绑定了不同来源字节；必须使用新的request_id"
                    )
                acquisition_attempt = {
                    "attempt_id": str(existing_attempt[0]),
                    "request_id": ingestion_request_id,
                    "source_id": capture.source_id,
                    "source_version_id": str(existing_attempt[1]),
                    "receipt_id": str(existing_attempt[2]),
                    "attempt_index": int(existing_attempt[3]),
                    "acquired_at": str(existing_attempt[4]),
                    "created_at": str(existing_attempt[5]),
                }
            else:
                attempt_index = int(
                    database.execute(
                        "SELECT COUNT(*) FROM source_acquisition_attempts WHERE source_id=?",
                        (capture.source_id,),
                    ).fetchone()[0]
                ) + 1
                attempt_id = stable_id(
                    "source-acquisition-attempt",
                    project_id,
                    report_kind,
                    ingestion_request_id,
                    capture.source_id,
                )
                receipt_id = stable_id("source-receipt", attempt_id)
                acquisition_attempt = {
                    "attempt_id": attempt_id,
                    "request_id": ingestion_request_id,
                    "source_id": capture.source_id,
                    "source_version_id": version.source_version_id,
                    "receipt_id": receipt_id,
                    "attempt_index": attempt_index,
                    "acquired_at": capture.acquired_at.isoformat(),
                    "created_at": created_at.isoformat(),
                }
                database.execute(
                    """INSERT INTO source_acquisition_attempts (
                    attempt_id,request_id,source_id,source_version_id,receipt_id,
                    attempt_index,acquired_at,created_at) VALUES (?,?,?,?,?,?,?,?)""",
                    tuple(acquisition_attempt[key] for key in (
                        "attempt_id", "request_id", "source_id", "source_version_id",
                        "receipt_id", "attempt_index", "acquired_at", "created_at",
                    )),
                )
        acquisition_attempts.append(acquisition_attempt)
        receipts.append(
            SourceReceipt(
                schema_version="1.0",
                receipt_id=str(acquisition_attempt["receipt_id"]),
                route_id=capture.route_id,
                strategy_unit_id=f"{capture.route_id}:primary",
                entity_id=project_id,
                gap_id=f"{report_kind}_FRESH_SOURCE",
                claim_domain=f"{report_kind}_RESEARCH",
                query_or_identifier=capture.query_or_identifier,
                language=capture.language,
                access_method=capture.access_method,
                attempt_index=int(str(acquisition_attempt["attempt_index"])),
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

    # Every adopted fact must be re-extracted from the persisted source text.
    # A non-empty or URL-only locator is not an exact quote.
    fact_fragments: dict[str, str] = {}
    captures_by_id = {capture.source_id: capture for capture in sources}
    for fact in facts:
        capture = captures_by_id[fact.source_id]
        try:
            extracted = extract_locator_quote(
                capture.content_text,
                media_type=capture.media_type,
                locator=fact.locator,
            )
        except SourceDerivationError as error:
            raise ResearchIngestionError(f"事实缺少精确可重放定位：{error}") from error
        if extracted != fact.original_text:
            raise ResearchIngestionError("事实原文与来源字节按locator重提取结果不一致")
        fact_fragment = repository.add_fragment(
            source_version_id=source_versions[fact.source_id],
            locator=fact.locator,
            original_text=extracted,
            created_at=created_at,
        )
        fact_fragments[fact.fact_id] = fact_fragment.fragment_id

    fact_versions: dict[str, str] = {}
    fact_closure: list[dict[str, object]] = []
    derivations: list[dict[str, object]] = []
    with open_database(database_path) as database:
        for fact in facts:
            database.execute(
                """INSERT OR IGNORE INTO entities
                (entity_id,entity_type,canonical_name,created_at) VALUES (?,?,?,?)""",
                (fact.entity_id, fact.entity_type, fact.canonical_name, created_at.isoformat()),
            )
            fragment_id = fact_fragments[fact.fact_id]
            scientific_context = fact.model_dump(mode="json")
            scientific_context_json = json.dumps(
                scientific_context,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            content_sha256 = sha256(scientific_context_json.encode("utf-8")).hexdigest()
            version_id = stable_id(
                "fact-version",
                "scientific-context-v2",
                content_sha256,
                source_versions[fact.source_id],
                fragment_id,
            )
            existing_version = database.execute(
                """SELECT content_sha256, scientific_context_json
                FROM fact_versions WHERE fact_version_id=?""",
                (version_id,),
            ).fetchone()
            if existing_version is not None:
                if tuple(existing_version) != (content_sha256, scientific_context_json):
                    raise ResearchIngestionError(
                        f"事实版本冲突：{fact.fact_id} 的同一版本标识携带不同载荷，"
                        "同内容重放应幂等，异载荷必须显式冲突"
                    )
            else:
                database.execute(
                    """INSERT INTO fact_versions (
                    fact_version_id,fact_id,entity_id,field_id,raw_value,normalized_value,
                    disclosure_state,review_state,primary_fragment_id,supersedes_fact_version_id,
                    created_at,content_sha256,scientific_context_json
                    ) VALUES (?,?,?,?,?,?,?,?,?,NULL,?,?,?)""",
                    (
                        version_id,
                        fact.fact_id,
                        fact.entity_id,
                        fact.field_id,
                        fact.raw_value,
                        fact.normalized_value,
                        fact.disclosure_state,
                        "candidate",
                        fragment_id,
                        created_at.isoformat(),
                        content_sha256,
                        scientific_context_json,
                    ),
                )
                previous = [
                    str(row[0])
                    for row in database.execute(
                        "SELECT fact_version_id FROM fact_versions "
                        "WHERE fact_id=? AND fact_version_id<>? ORDER BY created_at",
                        (fact.fact_id, version_id),
                    )
                ]
                if previous:
                    members = tuple((*previous, version_id))
                    database.execute(
                        "INSERT OR IGNORE INTO conflict_sets "
                        "(conflict_set_id,object_type,object_id,resolution_state,"
                        "resolution_note,created_at) VALUES (?,?,?,?,?,?)",
                        (
                            stable_id("fact-content-conflict", fact.fact_id, *members),
                            "fact",
                            fact.fact_id,
                            "open",
                            json.dumps({"fact_version_ids": members}, ensure_ascii=False),
                            created_at.isoformat(),
                        ),
                    )
            database.execute(
                """INSERT OR IGNORE INTO fact_evidence
                (fact_version_id,fragment_id,evidence_role,created_at) VALUES (?,?,?,?)""",
                (version_id, fragment_id, "primary", created_at.isoformat()),
            )
            fact_versions[fact.fact_id] = version_id
            fact_closure.append(
                {
                    "fact": scientific_context,
                    "fact_version_id": version_id,
                    "primary_fragment_id": fragment_id,
                    "review_state": "candidate",
                    "content_sha256": content_sha256,
                    "scientific_context_json": scientific_context_json,
                    "created_at": created_at.isoformat(),
                }
            )
            if fact.normalized_value is not None:
                derivation: dict[str, object] = {
                    "derivation_id": stable_id(
                        "evidence-derivation",
                        "normalization",
                        fragment_id,
                        fact.field_id,
                        str(fact.normalized_value),
                    ),
                    "derivation_kind": "normalization",
                    "input_fragment_ids": [fragment_id],
                    "rule_id": "legacy-declared-normalization",
                    "rule_version": "1",
                    "output": {"normalized_value": fact.normalized_value},
                    "created_at": created_at.isoformat(),
                }
                database.execute(
                    "INSERT OR IGNORE INTO evidence_derivations "
                    "(derivation_id,derivation_kind,input_fragment_ids_json,rule_id,"
                    "rule_version,output_json,created_at) VALUES (?,?,?,?,?,?,?)",
                    (
                        derivation["derivation_id"],
                        derivation["derivation_kind"],
                        json.dumps(derivation["input_fragment_ids"], ensure_ascii=False),
                        derivation["rule_id"],
                        derivation["rule_version"],
                        json.dumps(derivation["output"], ensure_ascii=False, sort_keys=True),
                        derivation["created_at"],
                    ),
                )
                derivations.append(derivation)
        claim_versions: dict[str, str] = {}
        claim_closure: list[dict[str, object]] = []
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
                    "candidate",
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
            claim_versions[claim.claim_id] = claim_version_id
            claim_closure.append(
                {
                    "claim": claim.model_dump(mode="json"),
                    "claim_version_id": claim_version_id,
                    "fact_version_ids": [fact_versions[item] for item in claim.fact_ids],
                    "review_state": "candidate",
                    "created_at": created_at.isoformat(),
                }
            )

    store = ContentAddressedStore(project_root)
    source_closure: list[dict[str, object]] = []
    for capture in sources:
        raw_asset_b64 = None
        if capture.text_derivation is not None:
            raw_asset_b64 = b64encode(
                store.read_bytes(capture.text_derivation.raw_asset)
            ).decode("ascii")
            derivations.append(
                {
                    "derivation_id": stable_id(
                        "evidence-derivation",
                        "source-text",
                        source_versions[capture.source_id],
                        capture.text_derivation.raw_asset.sha256,
                        capture.text_derivation.text_sha256,
                    ),
                    "derivation_kind": "source_text",
                    "input_fragment_ids": [fragments[capture.source_id]],
                    "rule_id": capture.text_derivation.method,
                    "rule_version": capture.text_derivation.extractor_version,
                    "output": capture.text_derivation.model_dump(mode="json"),
                    "created_at": created_at.isoformat(),
                }
            )
        source_closure.append(
            {
                "capture": capture.model_dump(mode="json"),
                "source_version_id": source_versions[capture.source_id],
                "raw_asset_b64": raw_asset_b64,
            }
        )
    source_derivations = [
        item for item in derivations if item["derivation_kind"] == "source_text"
    ]
    if source_derivations:
        with open_database(database_path) as database:
            for source_derivation_entry in source_derivations:
                database.execute(
                    "INSERT OR IGNORE INTO evidence_derivations "
                    "(derivation_id,derivation_kind,input_fragment_ids_json,rule_id,"
                    "rule_version,output_json,created_at) VALUES (?,?,?,?,?,?,?)",
                    (
                        source_derivation_entry["derivation_id"],
                        source_derivation_entry["derivation_kind"],
                        json.dumps(
                            source_derivation_entry["input_fragment_ids"],
                            ensure_ascii=False,
                        ),
                        source_derivation_entry["rule_id"],
                        source_derivation_entry["rule_version"],
                        json.dumps(
                            source_derivation_entry["output"],
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                        source_derivation_entry["created_at"],
                    ),
                )
    derivations = list(
        {
            str(item["derivation_id"]): item
            for item in derivations
        }.values()
    )
    all_fragment_ids = tuple(sorted({*fragments.values(), *fact_fragments.values()}))
    fragment_closure = [
        repository.read_fragment(fragment_id).model_dump(mode="json")
        for fragment_id in all_fragment_ids
    ]
    closure = {
        "sources": source_closure,
        "fragments": fragment_closure,
        "facts": fact_closure,
        "claims": claim_closure,
        "derivations": derivations,
        "acquisition_attempts": acquisition_attempts,
        "receipts": [item.model_dump(mode="json") for item in receipts],
    }

    manifest = EvidenceSnapshotManifest(
        schema_version="2.0",
        project_id=project_id,
        contract_version=contract_version,
        data_cutoff=data_cutoff,
        source_version_ids=tuple(sorted(source_versions.values())),
        fragment_ids=all_fragment_ids,
        fact_version_ids=tuple(sorted(fact_versions.values())),
        claim_version_ids=tuple(sorted(claim_versions.values())),
        derivation_ids=tuple(
            sorted(str(item["derivation_id"]) for item in derivations)
        ),
        receipt_ids=tuple(sorted(item.receipt_id for item in receipts)),
        scientific_content_digest=scientific_content_digest,
        created_at=created_at,
        closure=closure,
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
        source_fragment_ids=tuple(fragments[item.source_id] for item in sources),
        fragment_ids=all_fragment_ids,
        fact_version_ids=tuple(sorted(fact_versions.values())),
        claim_version_ids=tuple(sorted(claim_versions.values())),
        derivation_ids=tuple(
            sorted(str(item["derivation_id"]) for item in derivations)
        ),
        receipt_ids=tuple(sorted(item.receipt_id for item in receipts)),
        claim_ids=tuple(item.claim_id for item in claims),
        fact_version_by_ref={
            reference: fact_versions[fact.fact_id]
            for fact in facts
            for reference in (fact.fact_id, fact.row_ref)
        },
        fragment_by_fact_id=dict(fact_fragments),
    )


__all__ = ["ResearchEvidenceLineage", "ResearchIngestionError", "ingest_research_evidence"]
