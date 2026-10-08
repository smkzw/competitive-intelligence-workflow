"""已复核来源事实的收据授权物化（ci-r24-114）。

背景与边界：新鲜来源摄取（``fresh_research_ingestion``）只持久化
``review_state='candidate'`` 的事实/声明原子；既有 ``source_current_refresh``
与 C 设计门槛只接受 ``review_state='accepted'`` 的来源原子；既有科学复核
回执链（``qc.review_receipt`` + ``review_issuer`` + ``scientific_review_transition``）
把一次真实独立复核绑定到候选报告上下文，但从未把已复核的**来源事实集合**
物化为已接受状态。本模块是缺失的“收据 → 已持久化事实集合”接缝，不是第二套
复核平台，也不是用户保存授权：

1. 公开入口只接受 ``project_root``、``report_kind``、精确的
   ``evidence_snapshot_id`` / ``claim_snapshot_id`` 与 ``checked_at`` 测试时钟；
   不接受调用方布尔、裸事实标识、退回摘要或替换集合。
2. 按序重开既有授权门：``reload_production_context``（运行时物化的权威上下文）、
   ``require_verified_review_receipt``、``bind_receipt_to_production_context``、
   ``verify_receipt_issuance``、``accepted_verdict_from_receipt``；任何缺回执、
   自洽伪回执、无真实签发记录、同会话/生产者自审、结论过期或上下文漂移
   一律失败关闭，且不产生任何物化。
3. 精确快照必须经既有完整性 API 重开（``compute_locked_snapshot`` +
   ``SnapshotStore.read``）；闭包事实/声明按摄取层同一确定性算法重算
   （v3 载荷身份、来源版本身份、片段身份、声明版本身份），并用
   ``derive_scientific_source_refs`` 从快照材料重建来源引用，与权威上下文
   逐字比对；覆盖集合/覆盖摘要由调用方给定的两个快照标识确定性重算后
   必须与上下文一致。调用方重算的“可信摘要”不能替代这些材料核验。
4. 精确绑定集合经 SQLite 真源与内容寻址原文（CAS）重开核验：事实行、主证据
   片段、来源版本、定位重提取与原文引用必须逐字一致；``user_modified``/
   ``rejected``/``superseded`` 行、已有其他已接受版本或无解决的来源冲突
   一律拒绝。新真实复核可以覆盖与既往已接受**完全相同的原子版本**：这些
   行经逐字节核验后原样复用（科学载荷/标识/来源字节与 review_state 不变，
   不产生新版本行、不晋升用户修订、不关闭冲突）；声明只有在精确闭合覆盖
   时才接受，否则保持 candidate 并作为边界报告。
5. 物化只把精确绑定集合中仍为 candidate 的行翻转为 ``accepted``（先前已
   接受的精确复用原子不进入物化事务；科学载荷/标识/来源字节不可变，
   review_state 正交）；既有迁移的 ``fact_versions``/``claim_versions``
   BEFORE UPDATE 只追加守卫在本模块单事务内被**临时挂起并原样恢复**（守卫
   定义必须逐字匹配既有迁移，否则拒绝），事务回滚/崩溃/进程失败会把守卫与
   物化一起回滚，绝不留下被削弱的守卫或部分接受集合。
6. 追加式接受决策记录（``receipts/source_fact_acceptance/...``）先于物化
   落盘，作为持久意向；``idempotency_keys`` 与物化同一 SQLite 事务提交，
   作为物化完成证明；接受事件经既有 ``EventStore`` 追加。事件缺失（物化后
   崩溃）由同一回执重放补齐；同一回执重放幂等且不重复版本、不重复事件。
7. 只读入口（``load_materialized_source_acceptance``）按已验证的 epoch 指针
   链重开**已完成**的精确来源接受：后续报告纪元（未签发或已签发未物化）不
   使历史接受失效，历史材料也不得代表新对象；本模块的写入入口始终只使用
   当前活跃纪元，活跃纪元是产生新接受的唯一通道。

失败关闭边界：任何拒绝都不改变旧 current、既有快照、权威上下文与无关候选；
不重写历史快照 closure 的 review_state（接受是新决策，不是回填）。
``review_state`` 物化是正交内容状态变化，不构成新的科学复核授权，也不替代
报告晋级（``promote_rendered_candidate``）与视觉验收。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Final, Literal, cast

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.application.fresh_research_primitives import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.application.review_issuer import (
    REVIEW_ISSUANCE_RECORD_KIND,
    ReviewIssuanceError,
    review_issuance_record_path,
    verify_receipt_issuance,
)
from ci_workflow.application.scientific_review_transition import (
    PortalArtifactBinding,
    ScientificReviewTransitionError,
    accepted_verdict_from_receipt,
    derive_scientific_source_refs,
    load_scientific_review_receipt,
    production_context_publication_path,
    reload_production_context,
    scientific_review_receipt_path,
    scientific_review_request_path,
)
from ci_workflow.application.user_fact_edit import current_delivery_lock
from ci_workflow.capabilities.scientific_qc import (
    ScientificQcBoundaryError,
    validate_scientific_qc_verdict_payload,
)
from ci_workflow.domain.evidence import (
    EvidenceFragmentRecord,
    source_version_identity,
)
from ci_workflow.domain.ids import stable_id
from ci_workflow.qc.review_receipt import (
    ReviewProductionContext,
    ScientificReviewReceipt,
    ScientificReviewReceiptError,
    bind_receipt_to_production_context,
    require_verified_review_receipt,
    validate_scientific_review_receipt_payload,
)
from ci_workflow.qc.scientific import ScientificQcCurrentContext
from ci_workflow.storage.content_store import (
    ContentAddressedStore,
    ContentIntegrityError,
    EvidenceRepository,
)
from ci_workflow.storage.event_store import EventStore, WorkflowEvent
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.scientific_review_epoch import (
    ScientificReviewEpochPointer,
    ScientificReviewEpochStateError,
    epoch_issuance_record_path,
    epoch_production_context_path,
    epoch_receipt_path,
    epoch_review_request_path,
    load_epoch_entry,
    read_epoch_pointer,
)
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    SnapshotIntegrityError,
    SnapshotStore,
    compute_locked_snapshot,
)
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    extract_locator_quote,
    verify_source_text_derivation,
)
from ci_workflow.storage.sqlite import open_database

ReportCode = Literal["A", "B", "C"]

_OPERATION: Final = "source.fact.acceptance"
_EVENT_TYPE: Final = "source_fact_acceptance.reviewed_facts_accepted"
_EVENT_KIND: Final = "source-fact-acceptance"
_RUN_ID: Final = "source-fact-acceptance"
_DECISION_KIND: Final = "source-fact-acceptance-decision-v1"
_DECISION_DIR: Final = "receipts/source_fact_acceptance"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
# 既有迁移 0012/0006 的只追加守卫：只有逐字匹配才允许在单事务内挂起并恢复。
_APPEND_ONLY_GUARDS: Final = (
    ("fact_versions_no_update", "fact_versions"),
    ("claim_versions_no_update", "claim_versions"),
)


class SourceFactAcceptanceError(ValueError):
    """已复核来源事实物化失败关闭：绑定、快照、物化或重放不通过。"""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SourceFactAcceptanceError(f"{label}缺失或为空")
    return " ".join(value.split())


def _validated_kind(report_kind: str) -> ReportCode:
    if report_kind not in ("A", "B", "C"):
        raise SourceFactAcceptanceError(
            f"已复核来源事实物化只适用于 A/B/C 类报告：{report_kind!r}"
        )
    return cast(ReportCode, report_kind)


def _validated_identifier(value: str, label: str) -> str:
    normalized = _text(value, label)
    if _IDENTIFIER.fullmatch(normalized) is None:
        raise SourceFactAcceptanceError(f"{label}标识不是合法资源标识")
    return normalized


def _validated_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise SourceFactAcceptanceError(f"{label}必须是小写 SHA-256")
    return value


def _validated_time(value: datetime | None) -> datetime:
    moment = datetime.now(UTC) if value is None else value
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise SourceFactAcceptanceError("接受决策时间必须包含明确时区")
    return moment


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _scoped_digest(value: object) -> str:
    """与 ``scientific_review_transition._sha256_hex`` 同一规范化（含结尾换行）。"""

    return hashlib.sha256((_canonical_json(value) + "\n").encode("utf-8")).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_fact_acceptance_decision_path(
    report_kind: str, receipt_digest: str
) -> PurePosixPath:
    """接受决策记录的确定性项目相对路径（按回执摘要内容寻址，只追加）。"""
    kind = _validated_kind(report_kind)
    digest = _validated_digest(receipt_digest, "接受回执摘要")
    return PurePosixPath(_DECISION_DIR) / kind / f"{digest}.json"


# ── 结果与决策记录 ───────────────────────────────────────────────────────────


class ReviewedSourceFactAcceptanceResult(BaseModel):
    """一次收据授权物化的追加式结果回执。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    report_kind: ReportCode
    evidence_snapshot_id: str
    claim_snapshot_id: str
    receipt_digest: str
    verdict_id: str
    reviewer_id: str
    accepted_fact_version_ids: tuple[str, ...]
    accepted_claim_version_ids: tuple[str, ...]
    boundary_claim_version_ids: tuple[str, ...]
    decision_relative_path: str
    decision_digest: str
    accepted_at: datetime

    @field_validator(
        "project_id",
        "evidence_snapshot_id",
        "claim_snapshot_id",
        "verdict_id",
        "reviewer_id",
        "decision_relative_path",
    )
    @classmethod
    def _text_fields_not_blank(cls, value: str) -> str:
        return _text(value, "接受结果字段")

    @field_validator("receipt_digest", "decision_digest")
    @classmethod
    def _digest_fields_are_sha256(cls, value: str) -> str:
        return _validated_digest(value, "接受结果摘要")

    @field_validator("accepted_at")
    @classmethod
    def _accepted_at_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("接受结果时间必须包含明确时区")
        return value


class _AcceptanceDecisionRecord(BaseModel):
    """接受决策的持久意向载荷；结果字段与决策记录逐字一致。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_kind: Literal["source-fact-acceptance-decision-v1"]
    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    report_kind: ReportCode
    evidence_snapshot_id: str
    claim_snapshot_id: str
    receipt_digest: str
    verdict_id: str
    reviewer_id: str
    accepted_fact_version_ids: tuple[str, ...]
    accepted_claim_version_ids: tuple[str, ...]
    boundary_claim_version_ids: tuple[str, ...]
    accepted_at: datetime


# ── 快照闭包重开与材料重建 ───────────────────────────────────────────────────


@dataclass(frozen=True)
class _ClosureFact:
    version_id: str
    fact: ResearchFact
    source_version_id: str
    capture: SourceCapture
    capture_content_digest: str
    fragment_id: str
    fragment: EvidenceFragmentRecord
    fact_content_sha256: str
    scientific_context_json: str


@dataclass(frozen=True)
class _ClosureClaim:
    version_id: str
    claim: ResearchClaim
    fact_version_ids: tuple[str, ...]


@dataclass(frozen=True)
class _Closure:
    captures: tuple[SourceCapture, ...]
    facts: tuple[ResearchFact, ...]
    claims: tuple[ResearchClaim, ...]
    fact_version_by_ref: dict[str, str]
    bound_facts: tuple[_ClosureFact, ...]
    closure_claims: tuple[_ClosureClaim, ...]


def _closure_list(closure: dict[str, Any], key: str) -> list[Any]:
    value = closure.get(key)
    if not isinstance(value, list):
        raise SourceFactAcceptanceError("证据快照传递闭包不完整")
    return value


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceFactAcceptanceError(label)
    return value


def _reopen_evidence_snapshot(root: Path, evidence_snapshot_id: str) -> EvidenceSnapshotManifest:
    path = root / "snapshots" / "evidence" / f"{evidence_snapshot_id}.json"
    if not path.is_file():
        raise SourceFactAcceptanceError("证据快照文件缺失：无法重开精确快照")
    try:
        payload = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourceFactAcceptanceError("证据快照不可读或不是有效 JSON") from error
    if not isinstance(payload, dict):
        raise SourceFactAcceptanceError("证据快照根节点必须是对象")
    try:
        manifest = EvidenceSnapshotManifest.model_validate(payload)
        locked = compute_locked_snapshot(kind="evidence", report=None, manifest=payload)
    except (PydanticValidationError, ValueError) as error:
        raise SourceFactAcceptanceError(f"证据快照合同无效：{error}") from error
    if locked.snapshot_id != evidence_snapshot_id:
        raise SourceFactAcceptanceError(
            "证据快照字节与声明标识不一致：快照被替换或损坏，拒绝接受"
        )
    if manifest.schema_version != "2.0" or manifest.closure is None:
        raise SourceFactAcceptanceError("历史只读证据快照不参与接受物化：缺少传递闭包")
    try:
        SnapshotStore(root).read(locked)
    except (SnapshotIntegrityError, OSError, ValueError) as error:
        raise SourceFactAcceptanceError(f"证据快照完整性核验失败：{error}") from error
    return manifest


def _reconstruct_closure(
    manifest: EvidenceSnapshotManifest, kind: ReportCode
) -> _Closure:
    closure = manifest.closure
    if closure is None:  # _reopen_evidence_snapshot 已拒绝；保留类型收窄
        raise SourceFactAcceptanceError("证据快照缺少传递闭包")

    capture_by_source: dict[str, SourceCapture] = {}
    source_version_by_source: dict[str, str] = {}
    captures: list[SourceCapture] = []
    for raw in _closure_list(closure, "sources"):
        item = _mapping(raw, "来源闭包记录无效")
        try:
            capture = SourceCapture.model_validate(item.get("capture"))
        except (PydanticValidationError, ValueError) as error:
            raise SourceFactAcceptanceError(f"来源闭包捕获无效：{error}") from error
        version_id = _text(item.get("source_version_id"), "来源版本标识")
        if capture.source_id in capture_by_source:
            raise SourceFactAcceptanceError("来源闭包标识重复")
        content_digest = _sha256_text(capture.content_text)
        recomputed = source_version_identity(
            capture.source_id,
            content_digest,
            published_at=capture.date_evidence("published_at"),
            effective_at=capture.date_evidence("effective_at"),
            first_disclosed_at=capture.date_evidence("first_disclosed_at"),
            text_derivation=capture.text_derivation,
        )
        if recomputed != version_id:
            raise SourceFactAcceptanceError("来源版本身份与快照材料不一致：拒绝接受")
        capture_by_source[capture.source_id] = capture
        source_version_by_source[capture.source_id] = version_id
        captures.append(capture)

    fragment_by_id: dict[str, EvidenceFragmentRecord] = {}
    for raw in _closure_list(closure, "fragments"):
        try:
            fragment = EvidenceFragmentRecord.model_validate(raw)
        except (PydanticValidationError, ValueError) as error:
            raise SourceFactAcceptanceError(f"片段闭包记录无效：{error}") from error
        if fragment.fragment_id in fragment_by_id:
            raise SourceFactAcceptanceError("片段闭包标识重复")
        if fragment.content_sha256 != _sha256_text(fragment.original_text):
            raise SourceFactAcceptanceError("片段原文与内容摘要不一致：拒绝接受")
        fragment_by_id[fragment.fragment_id] = fragment

    facts: list[ResearchFact] = []
    bound_facts: list[_ClosureFact] = []
    fact_version_by_ref: dict[str, str] = {}
    version_by_fact_id: dict[str, str] = {}
    seen_versions: set[str] = set()
    for raw in _closure_list(closure, "facts"):
        item = _mapping(raw, "事实闭包记录无效")
        payload = dict(_mapping(item.get("fact"), "事实闭包缺少事实载荷"))
        if "row_ref" not in payload:
            binding = _mapping(item.get("consumer_binding"), "事实闭包缺少消费者绑定")
            if binding.get("report_kind") != kind:
                raise SourceFactAcceptanceError("事实闭包消费者绑定不属于当前报告类型")
            payload["row_ref"] = _text(binding.get("row_ref"), "事实消费行标识")
        try:
            fact = ResearchFact.model_validate(payload)
        except (PydanticValidationError, ValueError) as error:
            raise SourceFactAcceptanceError(f"事实闭包载荷无效：{error}") from error
        version_id = _validated_identifier(
            _text(item.get("fact_version_id"), "事实版本标识"), "事实版本"
        )
        fragment_id = _text(item.get("primary_fragment_id"), "事实主片段标识")
        fact_content_sha256 = _validated_digest(item.get("content_sha256"), "事实内容摘要")
        context_json = item.get("scientific_context_json")
        if not isinstance(context_json, str) or not context_json:
            raise SourceFactAcceptanceError("事实闭包缺少科学语义上下文")
        try:
            context_payload = json.loads(context_json)
        except json.JSONDecodeError as error:
            raise SourceFactAcceptanceError("事实闭包科学语义上下文不是有效 JSON") from error
        if not isinstance(context_payload, dict):
            raise SourceFactAcceptanceError("事实闭包科学语义上下文必须是对象")
        if _sha256_text(_canonical_json(context_payload)) != fact_content_sha256:
            raise SourceFactAcceptanceError("事实闭包科学语义与内容摘要不一致")
        expected_context = fact.model_dump(mode="json", exclude={"row_ref"})
        if context_payload != expected_context:
            raise SourceFactAcceptanceError("事实闭包科学语义与事实载荷不一致")
        if version_id in seen_versions:
            raise SourceFactAcceptanceError("事实闭包版本标识重复")
        seen_versions.add(version_id)
        source_version_id = source_version_by_source.get(fact.source_id)
        if source_version_id is None:
            raise SourceFactAcceptanceError("事实闭包引用了闭包外来源")
        fact_fragment = fragment_by_id.get(fragment_id)
        if fact_fragment is None:
            raise SourceFactAcceptanceError("事实闭包缺少主证据片段记录")
        if fact_fragment.source_version_id != source_version_id:
            raise SourceFactAcceptanceError("事实主片段与来源版本不一致")
        if fact_fragment.original_text != fact.original_text:
            raise SourceFactAcceptanceError("事实原文与主片段原文不一致")
        facts.append(fact)
        bound_facts.append(
            _ClosureFact(
                version_id=version_id,
                fact=fact,
                source_version_id=source_version_id,
                capture=capture_by_source[fact.source_id],
                capture_content_digest=_sha256_text(
                    capture_by_source[fact.source_id].content_text
                ),
                fragment_id=fragment_id,
                fragment=fact_fragment,
                fact_content_sha256=fact_content_sha256,
                scientific_context_json=context_json,
            )
        )
        fact_version_by_ref[fact.fact_id] = version_id
        fact_version_by_ref[fact.row_ref] = version_id
        version_by_fact_id[fact.fact_id] = version_id

    claims: list[ResearchClaim] = []
    closure_claims: list[_ClosureClaim] = []
    seen_claim_versions: set[str] = set()
    for raw in _closure_list(closure, "claims"):
        item = _mapping(raw, "声明闭包记录无效")
        try:
            claim = ResearchClaim.model_validate(item.get("claim"))
        except (PydanticValidationError, ValueError) as error:
            raise SourceFactAcceptanceError(f"声明闭包载荷无效：{error}") from error
        version_id = _validated_identifier(
            _text(item.get("claim_version_id"), "声明版本标识"), "声明版本"
        )
        stored_ids = item.get("fact_version_ids")
        if not isinstance(stored_ids, list) or not all(
            isinstance(entry, str) for entry in stored_ids
        ):
            raise SourceFactAcceptanceError("声明闭包缺少事实版本清单")
        try:
            mapped = [version_by_fact_id[fact_id] for fact_id in claim.fact_ids]
        except KeyError as error:
            raise SourceFactAcceptanceError("声明闭包引用了闭包外事实") from error
        if list(stored_ids) != mapped:
            raise SourceFactAcceptanceError("声明闭包事实版本与事实谱系不一致")
        identity = [claim.claim_id, claim.claim_text, *mapped]
        if claim.calculation is not None:
            identity.append(claim.calculation.model_dump_json())
        if stable_id("claim-version", *identity) != version_id:
            raise SourceFactAcceptanceError("声明版本身份与快照材料不一致：拒绝接受")
        if version_id in seen_claim_versions:
            raise SourceFactAcceptanceError("声明闭包版本标识重复")
        seen_claim_versions.add(version_id)
        claims.append(claim)
        closure_claims.append(
            _ClosureClaim(
                version_id=version_id,
                claim=claim,
                fact_version_ids=tuple(mapped),
            )
        )

    if not bound_facts or not closure_claims:
        raise SourceFactAcceptanceError("证据快照闭包缺少可接受的事实或声明谱系")
    return _Closure(
        captures=tuple(captures),
        facts=tuple(facts),
        claims=tuple(claims),
        fact_version_by_ref=fact_version_by_ref,
        bound_facts=tuple(bound_facts),
        closure_claims=tuple(closure_claims),
    )


def _bind_context(
    *,
    closure: _Closure,
    manifest: EvidenceSnapshotManifest,
    context: ScientificQcCurrentContext,
    kind: ReportCode,
    evidence_snapshot_id: str,
    claim_snapshot_id: str,
) -> None:
    if manifest.project_id != context.project_id:
        raise SourceFactAcceptanceError("证据快照与权威上下文的项目身份不一致")
    if manifest.scientific_content_digest != context.candidate_content_digest:
        raise SourceFactAcceptanceError("证据快照科学内容摘要与权威上下文候选内容不一致")
    try:
        rebuilt = derive_scientific_source_refs(
            sources=closure.captures,
            facts=closure.facts,
            claims=closure.claims,
            fact_version_by_ref=closure.fact_version_by_ref,
        )
    except ScientificReviewTransitionError as error:
        raise SourceFactAcceptanceError(f"从快照材料重建来源引用失败：{error}") from error
    if tuple(rebuilt) != context.source_refs:
        raise SourceFactAcceptanceError(
            "快照重建来源引用与权威生产上下文不一致：拒绝快照替换或漂移"
        )
    expected_coverage_set_id = stable_id(
        "coverage-set", context.project_id, kind, evidence_snapshot_id, claim_snapshot_id
    )
    if expected_coverage_set_id != context.coverage_set_id:
        raise SourceFactAcceptanceError("覆盖集合与权威上下文不一致：拒绝快照替换")
    coverage_digest = _scoped_digest(
        {
            "claim_ids": [claim.claim_id for claim in closure.claims],
            "claim_snapshot_id": claim_snapshot_id,
            "coverage_set_id": context.coverage_set_id,
            "evidence_snapshot_id": evidence_snapshot_id,
        }
    )
    if coverage_digest != context.coverage_digest:
        raise SourceFactAcceptanceError("覆盖摘要与权威上下文不一致：拒绝快照替换")


# ── SQLite 真源与 CAS 重开核验 ───────────────────────────────────────────────


def _verify_bound_facts(
    *,
    root: Path,
    database_path: Path,
    closure: _Closure,
    context: ScientificQcCurrentContext,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """核验精确绑定集合并返回（全部绑定版本, 其中先前已接受的精确复用版本）。

    新真实复核可以覆盖与既往已接受完全相同的原子版本（逐字节核验后原样
    复用，状态与科学载荷不变）；``user_modified``/``rejected``/``superseded``
    行、其他已接受兄弟版本与未解决来源冲突仍然失败关闭。
    """
    context_version_ids = {
        version_id for ref in context.source_refs for version_id in ref.fact_version_ids
    }
    closure_version_ids = {item.version_id for item in closure.bound_facts}
    if closure_version_ids != context_version_ids:
        raise SourceFactAcceptanceError("快照事实集合与权威上下文事实集合不一致")

    repository = EvidenceRepository(database_path, ContentAddressedStore(root))
    reused_version_ids: set[str] = set()
    with open_database(database_path) as database:
        for item in closure.bound_facts:
            fact = item.fact
            row = database.execute(
                "SELECT fact_id,entity_id,field_id,raw_value,normalized_value,"
                "disclosure_state,review_state,primary_fragment_id,"
                "supersedes_fact_version_id,content_sha256,scientific_context_json "
                "FROM fact_versions WHERE fact_version_id=?",
                (item.version_id,),
            ).fetchone()
            if row is None:
                raise SourceFactAcceptanceError("绑定事实版本在项目科学真源中不存在")
            observed = (
                str(row[0]),
                str(row[1]),
                str(row[2]),
                row[3],
                row[4],
                str(row[5]),
            )
            expected = (
                fact.fact_id,
                fact.entity_id,
                fact.field_id,
                fact.raw_value,
                fact.normalized_value,
                fact.disclosure_state,
            )
            if observed != expected:
                raise SourceFactAcceptanceError("事实行科学载荷与快照不一致：拒绝接受")
            review_state = str(row[6])
            if review_state == "accepted":
                # 与既往接受完全相同的版本：逐字节核验后原样复用，不重复物化
                reused_version_ids.add(item.version_id)
            elif review_state != "candidate":
                raise SourceFactAcceptanceError(
                    f"绑定事实状态为{review_state}：用户修订/拒绝/被替代行不得成为来源接受"
                )
            if row[8] is not None:
                raise SourceFactAcceptanceError("绑定事实带有替代谱系：不是来源原子")
            if str(row[7]) != item.fragment_id:
                raise SourceFactAcceptanceError("事实行主证据片段与快照不一致")
            if str(row[9] or "") != item.fact_content_sha256:
                raise SourceFactAcceptanceError("事实行内容摘要与快照不一致：拒绝接受")
            if str(row[10] or "") != item.scientific_context_json:
                raise SourceFactAcceptanceError("事实行科学语义上下文与快照不一致：拒绝接受")
            sibling = database.execute(
                "SELECT 1 FROM fact_versions WHERE fact_id=? AND fact_version_id<>? "
                "AND review_state='accepted'",
                (fact.fact_id, item.version_id),
            ).fetchone()
            if sibling is not None:
                raise SourceFactAcceptanceError("同一逻辑事实已有其他已接受版本：拒绝重复接受")
            conflict = database.execute(
                "SELECT 1 FROM conflict_sets WHERE object_type='fact' AND object_id=? "
                "AND resolution_state='open'",
                (fact.fact_id,),
            ).fetchone()
            if conflict is not None:
                raise SourceFactAcceptanceError("绑定事实存在未解决的来源冲突：不得成为来源接受")
            primary = database.execute(
                "SELECT 1 FROM fact_evidence WHERE fact_version_id=? AND fragment_id=? "
                "AND evidence_role='primary'",
                (item.version_id, item.fragment_id),
            ).fetchone()
            if primary is None:
                raise SourceFactAcceptanceError("绑定事实缺少主证据片段绑定")
            source_row = database.execute(
                "SELECT source_id,content_sha256 FROM source_versions WHERE source_version_id=?",
                (item.source_version_id,),
            ).fetchone()
            if (
                source_row is None
                or str(source_row[0]) != fact.source_id
                or str(source_row[1]) != item.capture_content_digest
            ):
                raise SourceFactAcceptanceError("来源版本与快照来源材料不一致：拒绝接受")

    for item in closure.bound_facts:
        fact = item.fact
        try:
            reopened = repository.read_fragment(item.fragment_id)
        except (KeyError, ValueError) as error:
            raise SourceFactAcceptanceError("绑定事实主片段不存在") from error
        if reopened != item.fragment:
            drifted = [
                field
                for field in EvidenceFragmentRecord.model_fields
                if getattr(reopened, field) != getattr(item.fragment, field)
            ]
            raise SourceFactAcceptanceError(
                "重开片段与快照片段记录不一致"
                f"（{item.fragment_id}：{', '.join(drifted) or '未知字段'}）"
            )
        try:
            record = repository.verify_reopened_fragment_record(
                reopened,
                reopened_original_text=fact.original_text,
                source_version_id=item.source_version_id,
            )
        except (KeyError, ValueError, ContentIntegrityError) as error:
            raise SourceFactAcceptanceError(f"重开来源原文与派生存证失败：{error}") from error
        if (
            record.source_id != fact.source_id
            or record.content_sha256 != item.capture_content_digest
        ):
            raise SourceFactAcceptanceError("重开来源版本与快照来源材料不一致")
        if item.capture.text_derivation is not None:
            try:
                verify_source_text_derivation(
                    root, item.capture.text_derivation, item.capture.content_text
                )
            except SourceDerivationError as error:
                raise SourceFactAcceptanceError(f"来源原文派生链重开失败：{error}") from error
        try:
            extracted = extract_locator_quote(
                item.capture.content_text,
                media_type=item.capture.media_type,
                locator=fact.locator,
            )
        except SourceDerivationError as error:
            raise SourceFactAcceptanceError(f"事实定位不能重提取原文：{error}") from error
        if extracted != fact.original_text:
            raise SourceFactAcceptanceError("事实原文、定位与快照来源不一致：拒绝接受")
        recomputed_version = stable_id(
            "fact-version",
            "scientific-context-v3",
            item.fact_content_sha256,
            item.source_version_id,
            item.fragment_id,
        )
        if recomputed_version != item.version_id:
            raise SourceFactAcceptanceError("事实 v3 身份与快照材料不一致：拒绝接受")
    return tuple(sorted(closure_version_ids)), tuple(sorted(reused_version_ids))


def _verify_bound_claims(
    *,
    database_path: Path,
    closure: _Closure,
    bound_version_ids: set[str],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """核验声明闭包并返回（接受集合, 边界集合, 其中先前已接受的精确复用）。

    与既往接受完全相同的声明版本原样复用；复用行遇到其他已接受兄弟或
    未解决冲突时无法表示为边界（其行已是 accepted），一律失败关闭。
    """
    accepted: list[str] = []
    boundary: list[str] = []
    reused: list[str] = []
    with open_database(database_path) as database:
        for item in closure.closure_claims:
            claim = item.claim
            row = database.execute(
                "SELECT claim_id,claim_text,claim_kind,review_state,"
                "supersedes_claim_version_id FROM claim_versions WHERE claim_version_id=?",
                (item.version_id,),
            ).fetchone()
            if row is None:
                raise SourceFactAcceptanceError("绑定声明版本在项目科学真源中不存在")
            if (str(row[0]), str(row[1]), str(row[2])) != (
                claim.claim_id,
                claim.claim_text,
                claim.claim_kind,
            ):
                raise SourceFactAcceptanceError("声明行内容与快照不一致：拒绝接受")
            review_state = str(row[3])
            if review_state == "accepted":
                reused.append(item.version_id)
            elif review_state != "candidate":
                raise SourceFactAcceptanceError("绑定声明不是候选状态：拒绝接受")
            if row[4] is not None:
                raise SourceFactAcceptanceError("绑定声明带有替代谱系：拒绝接受")
            links = database.execute(
                "SELECT fact_version_id,support_role FROM claim_facts "
                "WHERE claim_version_id=?",
                (item.version_id,),
            ).fetchall()
            expected_links = {(version_id, "supports") for version_id in item.fact_version_ids}
            if {(str(link[0]), str(link[1])) for link in links} != expected_links:
                raise SourceFactAcceptanceError("声明事实谱系与快照不一致：拒绝接受")
            if review_state == "accepted":
                sibling = database.execute(
                    "SELECT 1 FROM claim_versions WHERE claim_id=? AND claim_version_id<>? "
                    "AND review_state='accepted'",
                    (claim.claim_id, item.version_id),
                ).fetchone()
                conflict = database.execute(
                    "SELECT 1 FROM conflict_sets WHERE object_type='claim' AND object_id=? "
                    "AND resolution_state='open'",
                    (claim.claim_id,),
                ).fetchone()
                if sibling is not None or conflict is not None:
                    raise SourceFactAcceptanceError(
                        "复用的已接受声明存在其他已接受兄弟版本或未解决冲突：拒绝接受"
                    )
                accepted.append(item.version_id)
                continue
            if not set(item.fact_version_ids) <= bound_version_ids:
                boundary.append(item.version_id)
                continue
            sibling = database.execute(
                "SELECT 1 FROM claim_versions WHERE claim_id=? AND claim_version_id<>? "
                "AND review_state='accepted'",
                (claim.claim_id, item.version_id),
            ).fetchone()
            conflict = database.execute(
                "SELECT 1 FROM conflict_sets WHERE object_type='claim' AND object_id=? "
                "AND resolution_state='open'",
                (claim.claim_id,),
            ).fetchone()
            if sibling is not None or conflict is not None:
                boundary.append(item.version_id)
                continue
            accepted.append(item.version_id)
    return tuple(sorted(accepted)), tuple(sorted(boundary)), tuple(sorted(reused))


# ── 只追加守卫的单事务挂起与恢复 ─────────────────────────────────────────────


def _expected_guard_sql(name: str, table: str) -> str:
    return (
        f"CREATE TRIGGER {name} BEFORE UPDATE ON {table} "
        f"BEGIN SELECT RAISE(ABORT, 'append-only: {table}'); END"
    )


def _suspend_append_only_guards(
    database: Any,
) -> tuple[tuple[str, str], ...]:
    """只挂起与既有迁移逐字一致的 review_state 守卫；否则失败关闭。"""

    suspended: list[tuple[str, str]] = []
    for name, table in _APPEND_ONLY_GUARDS:
        row = database.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (name,)
        ).fetchone()
        if row is None or not isinstance(row[0], str):
            raise SourceFactAcceptanceError(f"缺少既有只追加守卫触发器：{name}")
        sql = str(row[0])
        if " ".join(sql.split()) != _expected_guard_sql(name, table):
            raise SourceFactAcceptanceError(f"只追加守卫触发器定义不符合既有迁移：{name}")
        database.execute(f'DROP TRIGGER "{name}"')
        suspended.append((name, sql))
    return tuple(suspended)


def _restore_append_only_guards(
    database: Any, suspended: tuple[tuple[str, str], ...]
) -> None:
    for name, sql in suspended:
        existing = database.execute(
            "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?", (name,)
        ).fetchone()
        if existing is None:
            database.execute(sql)


def _materialize(
    *,
    database_path: Path,
    flip_fact_version_ids: tuple[str, ...],
    flip_claim_version_ids: tuple[str, ...],
    claim_key: str,
    result_digest: str,
    accepted_at: datetime,
) -> None:
    """在单事务内把仍是候选的精确子集翻转为 accepted 并记录幂等键。

    只追加守卫在事务内被临时挂起并原样恢复：事务提交后守卫与既有迁移逐字
    一致；任何失败（含守卫恢复失败）都会整体回滚，不留下部分接受集合。
    先前已接受的精确复用原子不进入本事务（字节与状态正交保留）。
    """

    with open_database(database_path) as database:
        database.execute("BEGIN IMMEDIATE")
        suspended = _suspend_append_only_guards(database)
        updated_facts = 0
        for version_id in flip_fact_version_ids:
            cursor = database.execute(
                "UPDATE fact_versions SET review_state='accepted' "
                "WHERE fact_version_id=? AND review_state='candidate'",
                (version_id,),
            )
            updated_facts += int(cursor.rowcount)
        if updated_facts != len(flip_fact_version_ids):
            raise SourceFactAcceptanceError("事实接受物化未覆盖精确绑定集合：事务回滚")
        updated_claims = 0
        for version_id in flip_claim_version_ids:
            cursor = database.execute(
                "UPDATE claim_versions SET review_state='accepted' "
                "WHERE claim_version_id=? AND review_state='candidate'",
                (version_id,),
            )
            updated_claims += int(cursor.rowcount)
        if updated_claims != len(flip_claim_version_ids):
            raise SourceFactAcceptanceError("声明接受物化未覆盖精确绑定集合：事务回滚")
        database.execute(
            "INSERT OR IGNORE INTO idempotency_keys "
            "(idempotency_key,operation,result_digest,created_at) VALUES (?,?,?,?)",
            (claim_key, _OPERATION, result_digest, accepted_at.isoformat()),
        )
        ledger = database.execute(
            "SELECT operation,result_digest FROM idempotency_keys WHERE idempotency_key=?",
            (claim_key,),
        ).fetchone()
        if (
            ledger is None
            or str(ledger[0]) != _OPERATION
            or str(ledger[1]) != result_digest
        ):
            raise SourceFactAcceptanceError("同一接受请求标识对应了不同载荷")
        _restore_append_only_guards(database, suspended)


# ── 追加式决策记录、事件与重放 ───────────────────────────────────────────────


def _write_decision(
    root: Path,
    relative: str,
    record: _AcceptanceDecisionRecord,
    *,
    issued_at: datetime,
) -> tuple[_AcceptanceDecisionRecord, bytes]:
    """Reuse an exact durable intent after rollback; never rewrite its time/bytes.

    The caller has revalidated the issuer, sources and entire target set. Only
    the original bounded decision time may differ from the retry's clock.
    """
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        payload = path.read_bytes()
        try:
            prior = _AcceptanceDecisionRecord.model_validate_json(payload)
        except PydanticValidationError as error:
            raise SourceFactAcceptanceError("接受决策记录不可读或损坏：拒绝覆盖") from error
        if (
            prior.accepted_at.tzinfo is None
            or prior.accepted_at.utcoffset() is None
            or not issued_at <= prior.accepted_at <= record.accepted_at
        ):
            raise SourceFactAcceptanceError("原接受决策时间不在签发与本次核验之间")
        if prior.model_copy(update={"accepted_at": record.accepted_at}) != record:
            raise SourceFactAcceptanceError("接受决策记录已存在且内容不同：拒绝覆盖")
        return prior, payload
    payload = (_canonical_json(record.model_dump(mode="json")) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(
        prefix=".source-fact-acceptance-", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return record, payload


def _append_acceptance_event(root: Path, result: ReviewedSourceFactAcceptanceResult) -> None:
    payload = {
        "request": {
            "report_kind": result.report_kind,
            "evidence_snapshot_id": result.evidence_snapshot_id,
            "claim_snapshot_id": result.claim_snapshot_id,
        },
        "result": result.model_dump(mode="json"),
        "decision_relative_path": result.decision_relative_path,
        "decision_digest": result.decision_digest,
    }
    EventStore(root).append(
        WorkflowEvent(
            schema_version="1.0",
            event_id=stable_id(_EVENT_KIND, result.project_id, result.receipt_digest),
            project_id=result.project_id,
            run_id=_RUN_ID,
            event_type=_EVENT_TYPE,
            occurred_at=result.accepted_at,
            actor_id=result.reviewer_id,
            idempotency_key=f"{_OPERATION}:{result.receipt_digest}",
            payload=payload,
        )
    )


def _ledger_result_digest(root: Path, claim_key: str) -> str | None:
    with open_database(root / "state" / "project.sqlite") as database:
        return _ledger_result_digest_from_database(database, claim_key)


def _ledger_result_digest_from_database(
    database: sqlite3.Connection, claim_key: str,
) -> str | None:
    row = database.execute(
        "SELECT operation,result_digest FROM idempotency_keys WHERE idempotency_key=?",
        (claim_key,),
    ).fetchone()
    if row is None:
        return None
    if str(row[0]) != _OPERATION:
        raise SourceFactAcceptanceError("同一接受请求标识对应了不同操作")
    digest = row[1]
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise SourceFactAcceptanceError("接受幂等键缺少有效结果摘要")
    return digest


def _result_from_decision(
    record: _AcceptanceDecisionRecord, *, relative: str, decision_digest: str
) -> ReviewedSourceFactAcceptanceResult:
    return ReviewedSourceFactAcceptanceResult(
        project_id=record.project_id,
        report_kind=record.report_kind,
        evidence_snapshot_id=record.evidence_snapshot_id,
        claim_snapshot_id=record.claim_snapshot_id,
        receipt_digest=record.receipt_digest,
        verdict_id=record.verdict_id,
        reviewer_id=record.reviewer_id,
        accepted_fact_version_ids=record.accepted_fact_version_ids,
        accepted_claim_version_ids=record.accepted_claim_version_ids,
        boundary_claim_version_ids=record.boundary_claim_version_ids,
        decision_relative_path=relative,
        decision_digest=decision_digest,
        accepted_at=record.accepted_at,
    )


def _verify_materialized(root: Path, result: ReviewedSourceFactAcceptanceResult) -> None:
    with open_database(root / "state" / "project.sqlite") as database:
        _verify_materialized_from_database(database, result)


def _verify_materialized_from_database(
    database: sqlite3.Connection, result: ReviewedSourceFactAcceptanceResult,
) -> None:
    for version_id in result.accepted_fact_version_ids:
        row = database.execute(
            "SELECT review_state FROM fact_versions WHERE fact_version_id=?", (version_id,),
        ).fetchone()
        if row is None or str(row[0]) != "accepted":
            raise SourceFactAcceptanceError("已记录接受未被完整物化：拒绝重放")
    for version_id in result.accepted_claim_version_ids:
        row = database.execute(
            "SELECT review_state FROM claim_versions WHERE claim_version_id=?", (version_id,),
        ).fetchone()
        if row is None or str(row[0]) != "accepted":
            raise SourceFactAcceptanceError("已记录声明接受未被完整物化：拒绝重放")
    for version_id in result.boundary_claim_version_ids:
        row = database.execute(
            "SELECT review_state FROM claim_versions WHERE claim_version_id=?", (version_id,),
        ).fetchone()
        if row is None or str(row[0]) != "candidate":
            raise SourceFactAcceptanceError("边界声明状态与已记录决策不一致：拒绝重放")


def _load_decision_record(
    root: Path, kind: ReportCode, receipt_digest: str
) -> tuple[_AcceptanceDecisionRecord, str, bytes]:
    """只读重开按回执摘要寻址的接受决策记录；缺失/损坏/身份不符一律失败关闭。"""
    relative = source_fact_acceptance_decision_path(kind, receipt_digest).as_posix()
    path = root / relative
    if not path.is_file():
        raise SourceFactAcceptanceError("接受决策记录缺失：已记录接受不能被重放证明")
    try:
        encoded = path.read_bytes()
        record = _AcceptanceDecisionRecord.model_validate(
            json.loads(encoded.decode("utf-8"))
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, PydanticValidationError) as error:
        raise SourceFactAcceptanceError("接受决策记录不可读或损坏") from error
    if record.report_kind != kind or record.receipt_digest != receipt_digest:
        raise SourceFactAcceptanceError("重放请求与已记录接受决策不一致")
    return record, relative, encoded


def _read_replay_decision(
    *,
    root: Path,
    kind: ReportCode,
    receipt_digest: str,
    evidence_snapshot_id: str,
    claim_snapshot_id: str | None,
    ledger_result_digest: str,
) -> ReviewedSourceFactAcceptanceResult:
    record, relative, encoded = _load_decision_record(root, kind, receipt_digest)
    if record.evidence_snapshot_id != evidence_snapshot_id or (
        claim_snapshot_id is not None and record.claim_snapshot_id != claim_snapshot_id
    ):
        raise SourceFactAcceptanceError("重放请求与已记录接受决策不一致")
    result = _result_from_decision(
        record,
        relative=relative,
        decision_digest=_sha256_bytes(encoded),
    )
    if _digest(result.model_dump(mode="json")) != ledger_result_digest:
        raise SourceFactAcceptanceError("重放结果与已记录接受台账摘要不一致")
    return result


def _replay(
    *,
    root: Path,
    kind: ReportCode,
    receipt_digest: str,
    evidence_snapshot_id: str,
    claim_snapshot_id: str,
    ledger_result_digest: str,
) -> ReviewedSourceFactAcceptanceResult:
    result = _read_replay_decision(
        root=root, kind=kind, receipt_digest=receipt_digest,
        evidence_snapshot_id=evidence_snapshot_id, claim_snapshot_id=claim_snapshot_id,
        ledger_result_digest=ledger_result_digest,
    )
    _verify_materialized(root, result)
    _append_acceptance_event(root, result)
    return result


# ── 跨报告纪元的历史精确来源接受（只读重开） ─────────────────────────────────


@dataclass(frozen=True)
class _ReviewScope:
    """一个科学复核作用域的只读材料路径（epoch 0 既有单例或版本化纪元）。"""

    epoch: int
    receipt_relative: str
    request_relative: str
    context_relative: str
    issuance_relative: str


def _scope_for_epoch(kind: ReportCode, epoch: int) -> _ReviewScope:
    if epoch == 0:
        return _ReviewScope(
            epoch=0,
            receipt_relative=scientific_review_receipt_path(kind).as_posix(),
            request_relative=scientific_review_request_path(kind).as_posix(),
            context_relative=production_context_publication_path(kind).as_posix(),
            issuance_relative=review_issuance_record_path(kind).as_posix(),
        )
    return _ReviewScope(
        epoch=epoch,
        receipt_relative=epoch_receipt_path(kind, epoch).as_posix(),
        request_relative=epoch_review_request_path(kind, epoch).as_posix(),
        context_relative=epoch_production_context_path(kind, epoch).as_posix(),
        issuance_relative=epoch_issuance_record_path(kind, epoch).as_posix(),
    )


def _historical_review_scopes(
    root: Path, kind: ReportCode
) -> tuple[ScientificReviewEpochPointer | None, tuple[_ReviewScope, ...]]:
    """按“活跃纪元 → 历史纪元（新到旧）→ 隐式 epoch 0”枚举只读作用域。

    枚举只来自已激活的 epoch 指针链（损坏即失败关闭），不扫描目录、不按
    文件名先后猜测；新纪元优先的确定性顺序保证同一科学事实存在多条合法
    决策时结果唯一。epoch 0 是既有单例布局的隐式纪元，永远最后考察。
    """
    try:
        pointer = read_epoch_pointer(root, kind)
    except ScientificReviewEpochStateError as error:
        raise SourceFactAcceptanceError(f"科学复核 epoch 指针无效：{error}") from error
    epochs = [entry.epoch for entry in reversed(pointer.epochs)] if pointer else []
    epochs.append(0)
    return pointer, tuple(_scope_for_epoch(kind, epoch) for epoch in epochs)


def _read_scope_json(root: Path, relative: str, label: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise SourceFactAcceptanceError(f"{label}缺失：{relative}")
    try:
        raw = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourceFactAcceptanceError(f"{label}不可读或不是有效 JSON") from error
    if not isinstance(raw, dict):
        raise SourceFactAcceptanceError(f"{label}根节点必须是对象")
    return raw


def _load_scope_receipt(
    root: Path, scope: _ReviewScope, kind: ReportCode
) -> ScientificReviewReceipt:
    """重开一个作用域的回执并过既有授权门；任何漂移失败关闭。"""
    raw = _read_scope_json(root, scope.receipt_relative, "独立复核回执")
    try:
        receipt = validate_scientific_review_receipt_payload(raw)
    except ScientificReviewReceiptError as error:
        raise SourceFactAcceptanceError(f"独立复核回执验证失败：{error}") from error
    if receipt.production.report_kind != kind:
        raise SourceFactAcceptanceError("独立复核回执报告类型与其所在作用域不一致")
    try:
        require_verified_review_receipt(receipt, project_root=root)
    except ScientificReviewReceiptError as error:
        raise SourceFactAcceptanceError(f"独立复核回执未通过授权门：{error}") from error
    return receipt


def _verify_scope_lifecycle(
    *,
    root: Path,
    kind: ReportCode,
    scope: _ReviewScope,
    pointer: ScientificReviewEpochPointer | None,
    receipt: ScientificReviewReceipt,
    decision: _AcceptanceDecisionRecord,
) -> None:
    """重开该作用域的签发记录/请求/权威上下文/结论，并绑定到精确快照。

    有效性只在**原始签发与接受时刻**判定：结论有效期必须覆盖回执签发与接受
    物化时间；之后的时间流逝（含有效期已过）不追溯否定已经完成的合法接受。
    请求的门户字节属于报告复核面，不构成精确来源接受的科学权威，因此本只读
    入口不因报告门户随后被合法替换而否定历史来源接受；请求自身字节、生产身份
    与上下文绑定仍逐项重验。
    """
    request_payload = _read_scope_json(root, scope.request_relative, "科学复核请求")
    request_digest = request_payload.pop("request_digest", None)
    if not isinstance(request_digest, str) or request_digest != _scoped_digest(
        request_payload
    ):
        raise SourceFactAcceptanceError("科学复核请求摘要漂移：请求已被篡改或损坏")
    scientific_context = request_payload.get("scientific_context")
    if (
        not isinstance(scientific_context, dict)
        or scientific_context.get("context_digest")
        != receipt.production.production_context_digest
    ):
        raise SourceFactAcceptanceError("科学复核请求不属于该回执的生产上下文")
    try:
        request_production = ReviewProductionContext.model_validate(
            request_payload.get("production")
        )
    except PydanticValidationError as error:
        raise SourceFactAcceptanceError(f"科学复核请求生产身份无效：{error}") from error
    if request_production != receipt.production:
        raise SourceFactAcceptanceError("科学复核请求生产身份与回执不一致")
    review_input_digest = request_payload.get("review_input_digest")
    if (
        not isinstance(review_input_digest, str)
        or _SHA256.fullmatch(review_input_digest) is None
    ):
        raise SourceFactAcceptanceError("科学复核请求缺少有效审阅输入摘要")
    portal_binding = request_payload.get("portal_binding")
    if not isinstance(portal_binding, dict):
        raise SourceFactAcceptanceError("科学复核请求缺少门户产物绑定")
    try:
        PortalArtifactBinding.model_validate(portal_binding)
    except (PydanticValidationError, ValueError) as error:
        raise SourceFactAcceptanceError(f"复核请求门户产物绑定无效：{error}") from error

    issuance_payload = _read_scope_json(root, scope.issuance_relative, "真实签发记录")
    if issuance_payload.get("record_kind") != REVIEW_ISSUANCE_RECORD_KIND:
        raise SourceFactAcceptanceError("真实签发记录类别无效")
    record_digest = issuance_payload.pop("record_digest", None)
    if not isinstance(record_digest, str) or record_digest != _scoped_digest(
        issuance_payload
    ):
        raise SourceFactAcceptanceError("真实签发记录摘要漂移：记录已被篡改或损坏")
    if issuance_payload.get("request_digest") != request_digest:
        raise SourceFactAcceptanceError("签发记录不属于该科学复核请求")
    receipt_payload = receipt.model_dump(mode="json")
    expected: tuple[tuple[str, object], ...] = (
        ("receipt_digest", receipt.receipt_digest),
        ("report_kind", kind),
        ("host", receipt_payload["host"]),
        ("reviewer_id", receipt_payload["review"]["reviewer_id"]),
        ("issued_at", receipt_payload["issued_at"]),
        ("process", receipt_payload["review"]["process"]),
        ("artifact", receipt_payload["artifact"]),
    )
    for field, value in expected:
        if issuance_payload.get(field) != value:
            raise SourceFactAcceptanceError(
                f"真实签发记录与回执的 {field} 不一致：回执可能已被替换"
            )

    context_raw = _read_scope_json(root, scope.context_relative, "权威生产上下文")
    stored_digest = context_raw.get("context_digest")
    payload = {key: value for key, value in context_raw.items() if key != "context_digest"}
    try:
        context = ScientificQcCurrentContext.model_validate(payload)
    except (PydanticValidationError, ValueError) as error:
        raise SourceFactAcceptanceError(f"权威生产上下文重建失败：{error}") from error
    if stored_digest != context.context_digest:
        raise SourceFactAcceptanceError(
            "权威生产上下文摘要与物化内容不一致：文件已被篡改或损坏"
        )
    try:
        bind_receipt_to_production_context(receipt, context)
    except ScientificReviewReceiptError as error:
        raise SourceFactAcceptanceError(
            f"回执与该纪元权威生产上下文不一致：{error}"
        ) from error
    if decision.project_id != context.project_id:
        raise SourceFactAcceptanceError("接受决策项目与该纪元权威上下文不一致")
    expected_coverage_set_id = stable_id(
        "coverage-set",
        context.project_id,
        kind,
        decision.evidence_snapshot_id,
        decision.claim_snapshot_id,
    )
    if context.coverage_set_id != expected_coverage_set_id:
        raise SourceFactAcceptanceError("接受决策快照与该纪元权威上下文覆盖集合不一致")
    if scope.epoch >= 1:
        if pointer is None:
            raise SourceFactAcceptanceError("epoch 指针缺失：版本化纪元材料失去绑定")
        try:
            entry = load_epoch_entry(pointer, scope.epoch)
        except ScientificReviewEpochStateError as error:
            raise SourceFactAcceptanceError(f"epoch 指针缺少该纪元条目：{error}") from error
        if (
            entry.context_digest != context.context_digest
            or pointer.project_id != context.project_id
        ):
            raise SourceFactAcceptanceError("epoch 指针与该纪元权威上下文绑定不一致")

    artifact = receipt.artifact
    if artifact is None:  # require_verified_review_receipt 已拒绝；保留类型收窄
        raise SourceFactAcceptanceError("独立复核回执缺少科学质控结论产物")
    verdict_raw = _read_scope_json(root, artifact.path, "科学质控结论产物")
    try:
        verdict = validate_scientific_qc_verdict_payload(verdict_raw)
    except ScientificQcBoundaryError as error:
        raise SourceFactAcceptanceError(f"科学质控结论产物验证失败：{error}") from error
    agreement: tuple[tuple[object, object, str], ...] = (
        (verdict.project_id, context.project_id, "项目"),
        (verdict.contract_version, context.contract_version, "合同版本"),
        (verdict.report_kind, context.report_kind, "报告类型"),
        (verdict.report_version, context.report_version, "报告版本"),
        (verdict.report_object_id, context.report_object_id, "报告对象"),
        (verdict.candidate_snapshot_id, context.candidate_snapshot_id, "候选快照"),
        (
            verdict.candidate_content_digest,
            context.candidate_content_digest,
            "候选内容摘要",
        ),
        (verdict.criteria_version, context.criteria_version, "标准版本"),
        (verdict.gate_result_key, context.gate_result_key, "门槛结果键"),
        (verdict.coverage_set_id, context.coverage_set_id, "覆盖集"),
        (verdict.coverage_digest, context.coverage_digest, "覆盖摘要"),
        (verdict.source_refs, context.source_refs, "来源引用"),
        (verdict.locators, context.locators, "来源定位"),
        (verdict.review_input_digest, review_input_digest, "审阅输入摘要"),
        (receipt.content.review_input_digest, review_input_digest, "回执审阅输入摘要"),
        (verdict.reviewer_id, receipt.review.reviewer_id, "独立审查者"),
    )
    for verdict_value, current_value, label in agreement:
        if verdict_value != current_value:
            raise SourceFactAcceptanceError(
                f"科学质控结论{label}与该纪元权威材料不一致"
            )
    if verdict.verdict != "accepted" or verdict.has_blocking_issues():
        raise SourceFactAcceptanceError("科学质控结论未接受该纪元候选")
    if not (
        receipt.review.process.started_at
        <= verdict.reviewed_at
        <= receipt.review.process.finished_at
    ):
        raise SourceFactAcceptanceError("科学质控结论时间不在独立复核进程内")
    if verdict.valid_until <= receipt.issued_at:
        raise SourceFactAcceptanceError("科学质控接受结论在回执签发时已失效")
    if decision.accepted_at < receipt.issued_at:
        raise SourceFactAcceptanceError("接受决策时间早于回执签发时间")
    if verdict.valid_until <= decision.accepted_at:
        raise SourceFactAcceptanceError("科学质控接受结论在来源接受物化时已失效")


def _reopen_scope_decision(
    database: sqlite3.Connection,
    *,
    root: Path,
    kind: ReportCode,
    evidence_snapshot_id: str,
    scope: _ReviewScope,
    pointer: ScientificReviewEpochPointer | None,
) -> ReviewedSourceFactAcceptanceResult | None:
    """在一个作用域内重开与请求快照完全一致且已完成物化的接受决策。

    返回 ``None`` 表示该作用域没有针对该精确快照的已完成接受（未签发、已
    签发但未物化或决策属于其他快照）：跳过不改变任何材料，也不构成该纪元
    对其他对象的授权。尚无完成台账的回执仅核验 JSON 和摘要格式后跳过，
    不据此认定其科学性；声明已完成接受的材料须完整核验，漂移失败关闭。
    """
    receipt_path = root / scope.receipt_relative
    if not receipt_path.is_file():
        return None
    claimed = _read_scope_json(root, scope.receipt_relative, "独立复核回执")
    receipt_digest = claimed.get("receipt_digest")
    if not isinstance(receipt_digest, str) or _SHA256.fullmatch(receipt_digest) is None:
        raise SourceFactAcceptanceError("独立复核回执摘要缺失或不是小写 SHA-256")
    ledger = _ledger_result_digest_from_database(database, f"{_OPERATION}:{receipt_digest}")
    if ledger is None:
        # 已签发但未物化：不是候选，也不允许该纪元的材料代表其他快照。
        return None
    receipt = _load_scope_receipt(root, scope, kind)
    if receipt.receipt_digest != receipt_digest:
        raise SourceFactAcceptanceError("独立复核回执摘要与载荷不一致：回执已被替换")
    record, relative, encoded = _load_decision_record(root, kind, receipt_digest)
    if record.evidence_snapshot_id != evidence_snapshot_id:
        return None
    result = _result_from_decision(
        record, relative=relative, decision_digest=_sha256_bytes(encoded)
    )
    if _digest(result.model_dump(mode="json")) != ledger:
        raise SourceFactAcceptanceError("重放结果与已记录接受台账摘要不一致")
    _verify_scope_lifecycle(
        root=root,
        kind=kind,
        scope=scope,
        pointer=pointer,
        receipt=receipt,
        decision=record,
    )
    return result


# ── 公开入口 ─────────────────────────────────────────────────────────────────


def load_materialized_source_acceptance(
    *, project_root: Path, report_kind: str, evidence_snapshot_id: str,
) -> ReviewedSourceFactAcceptanceResult:
    """只读重开与精确证据快照完全一致且已完成物化的来源接受决策。

    活跃 epoch 仍是唯一可写入的作用域，但已经完成的精确来源接受不因后续
    报告纪元（未签发或已签发未物化）而失效：按“活跃纪元 → 历史纪元（新到
    旧）→ 隐式 epoch 0”的确定性顺序，逐作用域重开回执、真实签发记录、复核
    请求、权威生产上下文、独立结论、接受决策、幂等台账与已物化状态，全部
    绑定到请求的精确项目/报告/快照后才返回；同一科学事实存在多条合法决策
    时取最新纪元，结果唯一。未签发、未物化或决策属于其他快照的作用域被
    跳过。未物化作用域仅核验回执 JSON 和摘要格式，不认定该回执有效；已声明
    完成物化的匹配作用域须完整核验，损坏材料与损坏的 epoch 指针失败关闭。

    本入口既不产生新决策，也不加锁写入、不追加事件、不迁移、不改写指针或
    任何既有字节：它只返回既往已完成的授权，不是新的医学复核或整个报告的
    接受。调用者仍须核验自己的精确快照和消费者。
    """
    kind = _validated_kind(report_kind)
    evidence_id = _validated_identifier(evidence_snapshot_id, "证据快照")
    root = project_root.expanduser().resolve()
    database_path = root / "state/project.sqlite"
    if not database_path.is_file():
        raise SourceFactAcceptanceError("项目科学真源缺失：不能读取接受决策")
    pointer, scopes = _historical_review_scopes(root, kind)
    try:
        database = sqlite3.connect(database_path.as_uri() + "?mode=ro", uri=True)
        try:
            database.execute("BEGIN")
            for scope in scopes:
                result = _reopen_scope_decision(
                    database,
                    root=root,
                    kind=kind,
                    evidence_snapshot_id=evidence_id,
                    scope=scope,
                    pointer=pointer,
                )
                if result is None:
                    continue
                _verify_materialized_from_database(database, result)
                return result
            raise SourceFactAcceptanceError("来源事实接受尚未物化：拒绝隐式接受")
        finally:
            database.close()
    except sqlite3.Error as error:
        raise SourceFactAcceptanceError(f"项目科学真源只读核验失败：{error}") from error


def accept_reviewed_source_facts(
    *,
    project_root: Path,
    report_kind: str,
    evidence_snapshot_id: str,
    claim_snapshot_id: str,
    checked_at: datetime | None = None,
) -> ReviewedSourceFactAcceptanceResult:
    """把独立签发的科学复核回执物化为精确绑定来源事实的接受状态。

    只接受项目、报告类型、两个精确快照标识与可选测试时钟；调用方不能传入
    布尔、裸事实标识或自有摘要替代既有授权门。同一回执重放幂等；任何失败
    都不改变旧 current、快照、无关候选与既有权威物化。
    """

    kind = _validated_kind(report_kind)
    root = project_root.expanduser().resolve()
    evidence_id = _validated_identifier(evidence_snapshot_id, "证据快照")
    claim_id = _validated_identifier(claim_snapshot_id, "声明快照")
    decided_at = _validated_time(checked_at)
    database_path = root / "state" / "project.sqlite"
    if not database_path.is_file():
        raise SourceFactAcceptanceError("项目科学真源缺失：不能在未初始化项目上接受来源事实")
    apply_migrations(database_path)

    with current_delivery_lock(root):
        try:
            receipt = load_scientific_review_receipt(root, kind)
        except ScientificReviewTransitionError as error:
            raise SourceFactAcceptanceError(f"独立复核回执不可用：{error}") from error
        claim_key = f"{_OPERATION}:{receipt.receipt_digest}"
        ledger_result_digest = _ledger_result_digest(root, claim_key)
        if ledger_result_digest is not None:
            return _replay(
                root=root,
                kind=kind,
                receipt_digest=receipt.receipt_digest,
                evidence_snapshot_id=evidence_id,
                claim_snapshot_id=claim_id,
                ledger_result_digest=ledger_result_digest,
            )

        try:
            context = reload_production_context(root, kind)
        except ScientificReviewTransitionError as error:
            raise SourceFactAcceptanceError(f"权威生产上下文未就绪：{error}") from error
        try:
            require_verified_review_receipt(receipt, project_root=root)
            bind_receipt_to_production_context(receipt, context)
        except ScientificReviewReceiptError as error:
            raise SourceFactAcceptanceError(f"独立复核回执未通过授权门：{error}") from error
        try:
            issued = verify_receipt_issuance(root, kind, checked_at=decided_at)
        except ReviewIssuanceError as error:
            raise SourceFactAcceptanceError(f"独立复核签发核验失败：{error}") from error
        if issued.receipt_digest != receipt.receipt_digest:
            raise SourceFactAcceptanceError("issuer 记录未签发当前科学复核回执")
        try:
            verdict = accepted_verdict_from_receipt(
                project_root=root, context=context, receipt=receipt
            )
        except ScientificReviewTransitionError as error:
            raise SourceFactAcceptanceError(f"科学质控接受结论未授权当前候选：{error}") from error

        manifest = _reopen_evidence_snapshot(root, evidence_id)
        closure = _reconstruct_closure(manifest, kind)
        _bind_context(
            closure=closure,
            manifest=manifest,
            context=context,
            kind=kind,
            evidence_snapshot_id=evidence_id,
            claim_snapshot_id=claim_id,
        )
        accepted_fact_version_ids, reused_fact_version_ids = _verify_bound_facts(
            root=root,
            database_path=database_path,
            closure=closure,
            context=context,
        )
        accepted_claim_version_ids, boundary_claim_version_ids, reused_claim_version_ids = (
            _verify_bound_claims(
                database_path=database_path,
                closure=closure,
                bound_version_ids=set(accepted_fact_version_ids),
            )
        )
        if not set(reused_fact_version_ids) <= set(accepted_fact_version_ids):
            raise SourceFactAcceptanceError("复用事实集合不是绑定集合子集：拒绝接受")
        if not set(reused_claim_version_ids) <= set(accepted_claim_version_ids):
            raise SourceFactAcceptanceError("复用声明集合不是接受集合子集：拒绝接受")
        flip_fact_version_ids = tuple(
            sorted(set(accepted_fact_version_ids) - set(reused_fact_version_ids))
        )
        flip_claim_version_ids = tuple(
            sorted(set(accepted_claim_version_ids) - set(reused_claim_version_ids))
        )

        relative = source_fact_acceptance_decision_path(kind, receipt.receipt_digest).as_posix()
        record = _AcceptanceDecisionRecord(
            record_kind=_DECISION_KIND,
            project_id=context.project_id,
            report_kind=kind,
            evidence_snapshot_id=evidence_id,
            claim_snapshot_id=claim_id,
            receipt_digest=receipt.receipt_digest,
            verdict_id=verdict.verdict_id,
            reviewer_id=verdict.reviewer_id,
            accepted_fact_version_ids=accepted_fact_version_ids,
            accepted_claim_version_ids=accepted_claim_version_ids,
            boundary_claim_version_ids=boundary_claim_version_ids,
            accepted_at=decided_at,
        )
        record, payload = _write_decision(
            root, relative, record, issued_at=receipt.issued_at
        )
        result = _result_from_decision(
            record,
            relative=relative,
            decision_digest=_sha256_bytes(payload),
        )
        _materialize(
            database_path=database_path,
            flip_fact_version_ids=flip_fact_version_ids,
            flip_claim_version_ids=flip_claim_version_ids,
            claim_key=claim_key,
            result_digest=_digest(result.model_dump(mode="json")),
            accepted_at=record.accepted_at,
        )
        _append_acceptance_event(root, result)
        return result


__all__ = [
    "ReviewedSourceFactAcceptanceResult",
    "SourceFactAcceptanceError",
    "accept_reviewed_source_facts",
    "load_materialized_source_acceptance",
    "source_fact_acceptance_decision_path",
]
