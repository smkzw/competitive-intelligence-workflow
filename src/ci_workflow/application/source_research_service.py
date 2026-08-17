"""宿主 Agent 与确定性执行器之间的 A 类新鲜来源交接合同。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator, SourceReceipt
from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.portal.report_a import ReportAPortalData
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.manifest_store import ArtifactManifest
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    LockedSnapshot,
    SnapshotStore,
)
from ci_workflow.storage.sqlite import open_database


class ResearchPackageError(ValueError):
    """新鲜来源研究包不能形成可审计科学真源。"""


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


class SourceCapture(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    route_id: str
    source_type: str
    title: str
    url: str
    query_or_identifier: str
    language: str
    access_method: str
    media_type: str = "application/json"
    content_text: str
    acquired_at: datetime
    published_at: datetime | None
    effective_at: datetime | None
    first_disclosed_at: datetime
    locator: EvidenceLocator

    @field_validator(
        "source_id", "route_id", "source_type", "title", "url",
        "query_or_identifier", "language", "access_method", "media_type", "content_text",
    )
    @classmethod
    def _text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("来源采集字段不能为空")
        return value.strip()

    @field_validator("acquired_at", "published_at", "effective_at", "first_disclosed_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("来源日期必须包含明确时区")
        return value


class ResearchFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    row_ref: str
    entity_id: str
    entity_type: str
    canonical_name: str
    field_id: str
    raw_value: str | None
    normalized_value: str | None
    disclosure_state: Literal[
        "reported_value", "reported_zero", "not_reported",
        "below_reporting_threshold", "not_publicly_disclosed",
        "not_applicable", "conflicting", "unresolved_due_to_route",
    ]
    source_id: str
    locator: EvidenceLocator
    original_text: str

    @field_validator(
        "fact_id", "row_ref", "entity_id", "entity_type", "canonical_name",
        "field_id", "source_id", "original_text",
    )
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("事实字段不能为空")
        return value.strip()


class ResearchClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    claim_text: str
    claim_kind: Literal["direct_evidence", "deterministic_calculation", "synthesis"]
    fact_ids: tuple[str, ...] = Field(min_length=1)


class RouteAttempt(BaseModel):
    """没有取得内容的真实技术路线尝试；不得改写为没有证据。"""

    model_config = ConfigDict(extra="forbid", frozen=True)
    attempt_id: str
    route_id: str
    strategy_unit_id: str
    gap_id: str
    query_or_identifier: str
    language: str
    access_method: str
    attempt_index: int = Field(ge=1)
    started_at: datetime
    ended_at: datetime
    result_class: Literal[
        "network_error",
        "rate_limited",
        "captcha_required",
        "permission_denied",
        "proxy_error",
        "dns_error",
        "tls_error",
        "http_error",
        "parser_error",
        "tool_unavailable",
        "content_truncated",
    ]
    error_class: str
    alternative_paths: tuple[str, ...] = Field(min_length=2)
    diagnostic_confidence: Literal["low", "medium", "high"]
    parent_attempt_id: str | None = None
    recovery_round: int = Field(ge=0)

    @field_validator("started_at", "ended_at")
    @classmethod
    def _attempt_time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("技术路线尝试时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _attempt_has_forward_time(self) -> Self:
        if self.ended_at < self.started_at:
            raise ValueError("技术路线尝试结束时间不得早于开始时间")
        return self


class ScientificReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reviewer_id: str
    reviewer_role: Literal["independent_scientific_verifier"]
    status: Literal["accepted", "rejected"]
    reviewed_at: datetime
    reviewed_content_digest: str
    observations: tuple[str, ...]

    @field_validator("reviewer_id", "reviewed_content_digest")
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("科学复核字段不能为空")
        return value.strip()

    @field_validator("reviewed_at")
    @classmethod
    def _review_time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("科学复核时间必须包含明确时区")
        return value


class FreshAResearchContent(BaseModel):
    """独立复核前可规范化、可摘要的 A 类科学内容。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    indication: str
    data_cutoff: datetime
    report_version: str
    universe_closed: Literal[True]
    universe_product_ids: tuple[str, ...] = Field(min_length=1)
    report_data: ReportAPortalData
    sources: tuple[SourceCapture, ...] = Field(min_length=1)
    route_attempts: tuple[RouteAttempt, ...] = ()
    facts: tuple[ResearchFact, ...] = Field(min_length=1)
    claims: tuple[ResearchClaim, ...] = Field(min_length=1)
    gate_status: Literal["passed"]

    @model_validator(mode="after")
    def _content_is_closed(self) -> Self:
        if self.indication != self.report_data.indication:
            raise ValueError("研究包与报告数据的适应症不一致")
        if self.data_cutoff != self.report_data.data_cutoff:
            raise ValueError("研究包与报告数据的数据截止不一致")
        if self.report_version != self.report_data.report_version:
            raise ValueError("研究包与报告数据的报告版本不一致")
        if tuple(self.universe_product_ids) != tuple(self.report_data.product_ids):
            raise ValueError("锁定竞品宇宙与报告产品顺序不一致")
        source_ids = [item.source_id for item in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("来源标识重复")
        if any(item.first_disclosed_at > self.data_cutoff for item in self.sources):
            raise ValueError("截止日之后首次披露的来源不得进入当前快照")
        source_set = set(source_ids)
        if any(fact.source_id not in source_set for fact in self.facts):
            raise ValueError("事实引用了研究包外来源")
        fact_ids = [item.fact_id for item in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("事实标识重复")
        fact_set = set(fact_ids)
        if any(not set(claim.fact_ids) <= fact_set for claim in self.claims):
            raise ValueError("声明引用了研究包外事实")
        required_refs = {
            *(f"product:{item.id}" for item in self.report_data.products),
            *(f"trial:{item.id}" for item in self.report_data.trials),
            *(f"efficacy:{item.row_id}" for item in self.report_data.efficacy),
            *(f"safety:{item.row_id}" for item in self.report_data.safety),
        }
        available_refs = {item.row_ref for item in self.facts}
        missing = sorted(required_refs - available_refs)
        if missing:
            raise ValueError("核心受众事实缺少来源绑定：" + "、".join(missing[:5]))
        incomplete_safety = [
            item.row_id
            for item in self.report_data.safety
            if item.disclosure_state == "已公开"
            and (item.trial_id is None or not item.arm.strip())
        ]
        if incomplete_safety:
            raise ValueError(
                "已公开安全性数值缺少试验或组别语境："
                + "、".join(incomplete_safety[:5])
            )
        mature_product_ids = {
            item.id
            for item in self.report_data.products
            if item.result_status == "有公开关键结果"
        }
        efficacy_arms: dict[str, set[str]] = {}
        for efficacy_row in self.report_data.efficacy:
            if efficacy_row.value is not None:
                efficacy_arms.setdefault(efficacy_row.product_id, set()).add(
                    efficacy_row.arm
                )
        efficacy_incomplete = sorted(
            product_id
            for product_id in mature_product_ids
            if not {"治疗组", "对照组"} <= efficacy_arms.get(product_id, set())
        )
        if efficacy_incomplete:
            raise ValueError(
                "已有关键结果的竞品缺少治疗组与对照组疗效："
                + "、".join(efficacy_incomplete[:5])
            )
        safety_arms: dict[str, set[str]] = {}
        for safety_row in self.report_data.safety:
            if (
                safety_row.value is not None
                and safety_row.term in {"任何TEAE", "任何SAE"}
                and safety_row.disclosure_state == "已公开"
            ):
                safety_arms.setdefault(safety_row.product_id, set()).add(safety_row.arm)
        safety_incomplete = sorted(
            product_id
            for product_id in mature_product_ids
            if not {"治疗组", "对照组"} <= safety_arms.get(product_id, set())
        )
        if safety_incomplete:
            raise ValueError(
                "已有关键结果的竞品缺少治疗组与对照组TEAE或SAE："
                + "、".join(safety_incomplete[:5])
            )
        return self


class FreshAResearchPackage(FreshAResearchContent):
    """可由任意宿主 Agent 生成、由本地执行器验真的完整 A 类交接包。"""

    scientific_review: ScientificReview

    @property
    def research_content(self) -> dict[str, object]:
        return FreshAResearchContent.model_validate(
            self.model_dump(mode="json", exclude={"scientific_review"})
        ).model_dump(mode="json")

    @property
    def research_content_digest(self) -> str:
        return _digest(self.research_content)

    @model_validator(mode="after")
    def _package_is_independently_accepted(self) -> Self:
        if self.scientific_review.status != "accepted":
            raise ValueError("独立科学复核未接受，不得生成报告")
        if self.scientific_review.reviewed_content_digest != self.research_content_digest:
            raise ValueError("独立科学复核与当前研究内容摘要不一致")
        return self


@dataclass(frozen=True)
class ResearchLineage:
    package_digest: str
    evidence_snapshot: LockedSnapshot
    claim_snapshot_id: str
    coverage_set_id: str
    coverage_projection_id: str
    claim_ids: tuple[str, ...]
    source_version_ids: tuple[str, ...]
    fact_version_ids: tuple[str, ...]
    fragment_ids: tuple[str, ...]


def compute_research_content_digest(payload: dict[str, object]) -> str:
    """供宿主在提交独立复核前计算与执行器一致的内容摘要。"""
    candidate = dict(payload)
    candidate.pop("scientific_review", None)
    normalized = FreshAResearchContent.model_validate(candidate)
    return _digest(normalized.model_dump(mode="json"))


def load_fresh_a_research_package(path: Path) -> FreshAResearchPackage:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchPackageError("无法读取 A 类新鲜来源研究包") from exc
    try:
        return FreshAResearchPackage.model_validate(value)
    except ValueError as exc:
        raise ResearchPackageError(f"A 类新鲜来源研究包不符合合同：{exc}") from exc


def _date(value: datetime | None, locator: EvidenceLocator) -> DateEvidence:
    return DateEvidence(
        state="reported" if value is not None else "not_publicly_disclosed",
        value=value,
        locator=locator,
    )


def ingest_fresh_a_research_package(
    *, project_root: Path, project_id: str, contract_version: int,
    package: FreshAResearchPackage,
) -> ResearchLineage:
    """幂等摄取来源、事实、声明和真实锁定证据快照。"""
    database_path = project_root / "state/project.sqlite"
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    timestamp = datetime.now(UTC)
    versions: dict[str, str] = {}
    fragments: dict[str, str] = {}
    receipts: list[SourceReceipt] = []
    for capture in package.sources:
        version = repository.add_source_version(
            source_id=capture.source_id,
            content=capture.content_text.encode("utf-8"),
            media_type=capture.media_type,
            acquired_at=capture.acquired_at,
            published_at=_date(capture.published_at, capture.locator),
            effective_at=_date(capture.effective_at, capture.locator),
            first_disclosed_at=_date(capture.first_disclosed_at, capture.locator),
        )
        fragment = repository.add_fragment(
            source_version_id=version.source_version_id,
            locator=capture.locator,
            original_text=capture.content_text,
            created_at=capture.acquired_at,
        )
        versions[capture.source_id] = version.source_version_id
        fragments[capture.source_id] = fragment.fragment_id
        receipts.append(SourceReceipt(
            schema_version="1.0",
            receipt_id=stable_id("source-receipt", project_id, capture.source_id),
            route_id=capture.route_id,
            strategy_unit_id=f"{capture.route_id}:primary",
            entity_id=project_id,
            gap_id="A_FRESH_SOURCE",
            claim_domain="A_PROFILE",
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
        ))
    for attempt in package.route_attempts:
        receipts.append(
            SourceReceipt(
                schema_version="1.0",
                receipt_id=attempt.attempt_id,
                route_id=attempt.route_id,
                strategy_unit_id=attempt.strategy_unit_id,
                entity_id=project_id,
                gap_id=attempt.gap_id,
                claim_domain="A_PROFILE",
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
        for fact in package.facts:
            database.execute(
                """
                INSERT OR IGNORE INTO entities (
                    entity_id,entity_type,canonical_name,created_at
                ) VALUES (?,?,?,?)
                """,
                (fact.entity_id, fact.entity_type, fact.canonical_name, timestamp.isoformat()),
            )
            fragment_id = fragments[fact.source_id]
            version_id = stable_id(
                "fact-version", fact.fact_id, fact.field_id,
                fact.normalized_value or fact.disclosure_state, fragment_id,
            )
            database.execute(
                """
                INSERT OR IGNORE INTO fact_versions (
                    fact_version_id,fact_id,entity_id,field_id,raw_value,normalized_value,
                    disclosure_state,review_state,primary_fragment_id,supersedes_fact_version_id,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,NULL,?)
                """,
                (version_id, fact.fact_id, fact.entity_id, fact.field_id, fact.raw_value,
                 fact.normalized_value, fact.disclosure_state, "accepted", fragment_id,
                 timestamp.isoformat()),
            )
            database.execute(
                """
                INSERT OR IGNORE INTO fact_evidence (
                    fact_version_id,fragment_id,evidence_role,created_at
                ) VALUES (?,?,?,?)
                """,
                (version_id, fragment_id, "primary", timestamp.isoformat()),
            )
            fact_versions[fact.fact_id] = version_id
        for claim in package.claims:
            claim_version_id = stable_id(
                "claim-version", claim.claim_id, claim.claim_text,
                *(fact_versions[item] for item in claim.fact_ids),
            )
            database.execute(
                """
                INSERT OR IGNORE INTO claim_versions (
                    claim_version_id,claim_id,claim_text,claim_kind,review_state,
                    supersedes_claim_version_id,created_at
                ) VALUES (?,?,?,?,?,NULL,?)
                """,
                (claim_version_id, claim.claim_id, claim.claim_text, claim.claim_kind,
                 "accepted", timestamp.isoformat()),
            )
            for fact_id in claim.fact_ids:
                database.execute(
                    """
                    INSERT OR IGNORE INTO claim_facts (
                        claim_version_id,fact_version_id,support_role,created_at
                    ) VALUES (?,?,?,?)
                    """,
                    (claim_version_id, fact_versions[fact_id], "supports", timestamp.isoformat()),
                )

    evidence_manifest = EvidenceSnapshotManifest(
        schema_version="1.0",
        project_id=project_id,
        contract_version=contract_version,
        data_cutoff=package.data_cutoff,
        source_version_ids=tuple(sorted(versions.values())),
        fragment_ids=tuple(fragments[item.source_id] for item in package.sources),
        fact_version_ids=tuple(sorted(fact_versions.values())),
        scientific_content_digest=package.research_content_digest,
        created_at=timestamp,
    )
    evidence_snapshot = SnapshotStore(project_root).lock_evidence_snapshot(
        evidence_manifest.model_dump(mode="json")
    )
    claim_ids = tuple(item.claim_id for item in package.claims)
    claim_snapshot_id = stable_id(
        "claim-snapshot", project_id, package.research_content_digest, *claim_ids
    )
    coverage_set_id = stable_id(
        "coverage-set", project_id, "A", evidence_snapshot.snapshot_id, claim_snapshot_id
    )
    coverage_projection_id = stable_id(
        "coverage-projection", coverage_set_id, "html"
    )
    with open_database(database_path) as database:
        database.execute(
            """
            INSERT OR IGNORE INTO gate_evaluations (
                gate_evaluation_id,project_id,report_kind,gate_id,result,details_json,created_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                stable_id(
                    "gate-evaluation", project_id, "A", package.research_content_digest
                ),
                project_id,
                "A",
                "A_MATURITY_V1",
                "passed",
                json.dumps(
                    {
                        "universe_closed": True,
                        "product_ids": list(package.universe_product_ids),
                        "scientific_reviewer": package.scientific_review.reviewer_id,
                    },
                    ensure_ascii=False,
                ),
                timestamp.isoformat(),
            ),
        )
    receipt_path = project_root / "receipts/source_receipts.jsonl"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if receipt_path.is_file():
        for line in receipt_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_ids.add(str(json.loads(line)["receipt_id"]))
    with receipt_path.open("a", encoding="utf-8") as handle:
        for item in receipts:
            if item.receipt_id not in existing_ids:
                handle.write(
                    json.dumps(
                        item.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
    return ResearchLineage(
        package_digest=package.research_content_digest,
        evidence_snapshot=evidence_snapshot,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        coverage_projection_id=coverage_projection_id,
        claim_ids=claim_ids,
        source_version_ids=tuple(sorted(versions.values())),
        fact_version_ids=tuple(sorted(fact_versions.values())),
        fragment_ids=tuple(sorted(fragments.values())),
    )


def persist_report_a_projection(
    *,
    project_root: Path,
    lineage: ResearchLineage,
    manifest_path: Path,
) -> None:
    """把已生成门户反向绑定到报告快照与格式覆盖记录。"""
    manifest = ArtifactManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if (
        manifest.evidence_snapshot_id != lineage.evidence_snapshot.snapshot_id
        or manifest.claim_snapshot_id != lineage.claim_snapshot_id
        or manifest.coverage_set_id != lineage.coverage_set_id
        or manifest.coverage_projection_id != lineage.coverage_projection_id
    ):
        raise ResearchPackageError("A 类门户清单未绑定当前新鲜来源谱系")
    report_snapshot_path = (
        project_root
        / "snapshots"
        / "reports"
        / "A"
        / f"{manifest.report_snapshot_id}.json"
    )
    report_snapshot = json.loads(report_snapshot_path.read_text(encoding="utf-8"))
    timestamp = manifest.generated_at.isoformat()
    with open_database(project_root / "state/project.sqlite") as database:
        database.execute(
            """
            INSERT OR IGNORE INTO report_snapshots (
                snapshot_id,project_id,report_kind,report_version,evidence_state,
                manifest_json,created_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                manifest.report_snapshot_id,
                manifest.project_id,
                "A",
                manifest.report_version,
                "snapshot_locked",
                json.dumps(report_snapshot, ensure_ascii=False, sort_keys=True),
                timestamp,
            ),
        )
        database.execute(
            """
            INSERT OR IGNORE INTO coverage_sets (
                coverage_set_id,snapshot_id,report_kind,coverage_json,created_at
            ) VALUES (?,?,?,?,?)
            """,
            (
                lineage.coverage_set_id,
                manifest.report_snapshot_id,
                "A",
                json.dumps(
                    {
                        "claim_ids": list(lineage.claim_ids),
                        "source_version_ids": list(lineage.source_version_ids),
                        "status": "complete",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                timestamp,
            ),
        )
        database.execute(
            """
            INSERT OR IGNORE INTO coverage_projections (
                projection_id,coverage_set_id,output_format,projection_json,
                exception_json,created_at
            ) VALUES (?,?,?,?,?,?)
            """,
            (
                lineage.coverage_projection_id,
                lineage.coverage_set_id,
                "html",
                json.dumps(
                    {
                        "artifact": manifest.artifact.relative_path,
                        "artifact_sha256": manifest.artifact.sha256,
                        "status": "generated",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "[]",
                timestamp,
            ),
        )
