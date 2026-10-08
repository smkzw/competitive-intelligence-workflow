"""A/B/C 两阶段科学复核状态迁移：真实回执是唯一科学状态迁移授权。

阶段一：A/B/C 候选完成 format 渲染（门户站点与产物清单落盘）后处于
``rendered_unreviewed``（预览态，不得产生任何科学、视觉或发布接受后继）；
科学晋级只允许发生在 format 完成之后。

阶段二：真实 ``scientific-review-v1`` 回执（``qc.review_receipt``）按序通过

1. ``require_verified_review_receipt``：内容摘要完整、``verified`` 状态、
   复核产物实际文件字节核验；
2. ``bind_receipt_to_production_context``：逐字绑定编排层权威
   ``ScientificQcCurrentContext``（项目/报告/对象/候选快照/候选内容摘要/
   生产者/标准版本/门槛结果键/上下文摘要）；
3. 首次门户 manifest/站点字节绑定核验：review request 在发布时绑定
   format 产物的 ``PortalArtifactBinding``；恢复与晋级前都用当前磁盘
   字节重验，任何漂移失败关闭。请求只在首次发布时绑定；跨候选/跨项目/
   无关历史的既有请求拒绝覆盖。

全部通过后才迁移为 ``scientifically_reviewed_rendered_candidate``。缺回执、
伪回执（结构/摘要漂移/伪造状态）、同会话复核、生产者自审、旧内容（候选
内容或上下文漂移）与宿主不可用（``host_context_unavailable``）全部失败
关闭，绝不产生被接受后继。

权威上下文从当前候选、Gate、coverage 与来源引用重建
（``build_scientific_review_context``）：来源引用经
``derive_scientific_source_refs`` 与共享谱系摄取（``ingest_research_evidence``）
使用同一确定性标识算法重算持久化来源版本/片段标识，杜绝调用方自由伪造
来源谱系。上下文经 ``publish_production_context`` 物化为确定性状态文件供
外部复核会话读取；``reload_production_context`` 重载时校验上下文摘要，
任何篡改失败关闭。

分层边界：回执结构与授权裁决留在 ``qc`` 层真源（``Task 9.4`` 权能边界）；
本模块只做运行时接线（状态迁移与上下文物化），不得绕过或复制授权门。

R24 epoch 生命周期：同项目重复科学复核经由显式 ``advance_scientific_review_epoch``
推进——绑定预期前驱上下文（摘要等于当前活跃上下文）、同项目/同报告、真实
新科学上下文与真实门户字节后，在版本化目录物化新纪元上下文/请求并原子激活
指针（``storage.scientific_review_epoch``）。既有单例路径是隐式 epoch 0：
遗留发布者保持原拒绝语义；活跃 epoch 是发布/重载/回执/请求/晋级作用域的
唯一权威，历史纪元字节只追加、不可变。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Final, Literal, cast

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.application.user_fact_edit import current_delivery_lock
from ci_workflow.capabilities.scientific_qc import (
    ScientificQcBoundaryError,
    validate_scientific_qc_verdict_payload,
)
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.evidence import source_version_identity
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import ReportDecision, ReportGateResult
from ci_workflow.qc.review_receipt import (
    ReviewProductionContext,
    ScientificReviewReceipt,
    ScientificReviewReceiptError,
    bind_receipt_to_production_context,
    require_verified_review_receipt,
    validate_scientific_review_receipt_payload,
)
from ci_workflow.qc.scientific import (
    LocatorDetail,
    LocatorRef,
    ScientificQcCurrentContext,
    ScientificQcReviewBundle,
    ScientificQcVerdict,
    SourceRef,
)
from ci_workflow.storage.scientific_review_epoch import (
    ScientificReviewEpochEntry,
    ScientificReviewEpochPointer,
    ScientificReviewEpochStateError,
    build_scientific_review_epoch_pointer,
    epoch_production_context_path,
    epoch_receipt_path,
    epoch_review_request_path,
    read_epoch_pointer,
    write_epoch_pointer,
)

ReportKindCode = Literal["A", "B", "C"]

RENDERED_UNREVIEWED: Final = "rendered_unreviewed"
SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE: Final = (
    "scientifically_reviewed_rendered_candidate"
)


class ScientificReviewTransitionError(ValueError):
    """两阶段科学复核状态迁移失败关闭。"""


class PortalArtifactBinding(BaseModel):
    """首次门户产物字节绑定：review request 对 format 产物的信任根。

    ``manifest_sha256`` 是 ``html.manifest.json`` 文件字节摘要；
    ``site_sha256``/``site_total_bytes`` 与产物清单 artifact 绑定同一合同
    （``qc.browser.site_directory_digest``）。绑定只在首次发布时写入，
    之后任何字节漂移都失败关闭。
    """

    model_config = ConfigDict(frozen=True)

    manifest_relative: str
    manifest_sha256: str
    site_relative: str
    site_sha256: str
    site_total_bytes: int


def _validated_kind(report_kind: str) -> ReportKindCode:
    if report_kind not in ("A", "B", "C"):
        raise ScientificReviewTransitionError(
            f"两阶段科学复核状态迁移只适用于 A/B/C 类报告：{report_kind!r}"
        )
    return cast(ReportKindCode, report_kind)


def _canonical_json(value: object) -> str:
    # 与 storage.content_store / qc.scientific 同一规范化，保证确定性标识
    # 与摄取层逐字节一致。
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _sha256_hex(value: object) -> str:
    material = (
        (_canonical_json(value) + "\n").encode("utf-8")
        if not isinstance(value, str)
        else value.encode("utf-8")
    )
    return hashlib.sha256(material).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ActiveScientificReviewScope(BaseModel):
    """当前活跃科学复核作用域：epoch 0 为既有单例布局（隐式纪元）。"""

    model_config = ConfigDict(frozen=True)

    epoch: int
    production_context_relative: str
    review_request_relative: str
    receipt_relative: str

    @field_validator("epoch")
    @classmethod
    def _epoch_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("epoch 序号不得为负")
        return value


def active_scientific_review_scope(
    project_root: Path, report_kind: str
) -> ActiveScientificReviewScope:
    """解析当前活跃作用域：有 epoch 指针则版本化目录，否则既有单例路径。

    指针文件损坏或摘要漂移一律失败关闭；本函数是发布、重载、请求与回执
    读取共同的作用域解析点（issuer 经 ``review_issuer`` 复用同一解析）。
    """
    kind = _validated_kind(report_kind)
    try:
        pointer = read_epoch_pointer(project_root, kind)
    except ScientificReviewEpochStateError as error:
        raise ScientificReviewTransitionError(f"科学复核 epoch 指针无效：{error}") from error
    if pointer is None:
        return ActiveScientificReviewScope(
            epoch=0,
            production_context_relative=production_context_publication_path(
                kind
            ).as_posix(),
            review_request_relative=scientific_review_request_path(kind).as_posix(),
            receipt_relative=scientific_review_receipt_path(kind).as_posix(),
        )
    epoch = pointer.active_epoch
    return ActiveScientificReviewScope(
        epoch=epoch,
        production_context_relative=epoch_production_context_path(kind, epoch).as_posix(),
        review_request_relative=epoch_review_request_path(kind, epoch).as_posix(),
        receipt_relative=epoch_receipt_path(kind, epoch).as_posix(),
    )


def capture_portal_artifact_binding(
    project_root: Path,
    report_kind: str,
    *,
    manifest_relative: str,
    site_relative: str,
) -> PortalArtifactBinding:
    """从当前磁盘字节捕获门户产物绑定；缺失或空站点失败关闭。"""
    _validated_kind(report_kind)
    from ci_workflow.qc.browser import site_directory_digest

    manifest_path = project_root / manifest_relative
    site_root = project_root / site_relative
    if not manifest_path.is_file():
        raise ScientificReviewTransitionError(
            f"门户产物清单缺失，无法绑定复核请求：{manifest_relative}"
        )
    if not site_root.is_dir():
        raise ScientificReviewTransitionError(
            f"门户站点目录缺失，无法绑定复核请求：{site_relative}"
        )
    site_sha256, site_total_bytes = site_directory_digest(site_root)
    if site_total_bytes == 0:
        raise ScientificReviewTransitionError(
            f"门户站点目录没有任何文件，拒绝绑定复核请求：{site_relative}"
        )
    return PortalArtifactBinding(
        manifest_relative=PurePosixPath(manifest_relative).as_posix(),
        manifest_sha256=_sha256_bytes(manifest_path.read_bytes()),
        site_relative=PurePosixPath(site_relative).as_posix(),
        site_sha256=site_sha256,
        site_total_bytes=site_total_bytes,
    )


def verify_portal_artifact_binding(
    project_root: Path,
    report_kind: str,
    binding: PortalArtifactBinding,
) -> None:
    """重验当前门户字节与绑定一致；漂移或缺失失败关闭。"""
    current = capture_portal_artifact_binding(
        project_root,
        report_kind,
        manifest_relative=binding.manifest_relative,
        site_relative=binding.site_relative,
    )
    drifted = [
        field
        for field in PortalArtifactBinding.model_fields
        if getattr(current, field) != getattr(binding, field)
    ]
    if drifted:
        raise ScientificReviewTransitionError(
            "门户 manifest/站点字节与复核请求绑定不一致"
            f"（漂移字段：{', '.join(drifted)}）：渲染产物已变化或被篡改"
        )


def scientific_review_receipt_path(report_kind: str) -> PurePosixPath:
    """外部复核会话签发回执的确定性项目相对路径。"""
    kind = _validated_kind(report_kind)
    return PurePosixPath("receipts") / "scientific_review" / kind / "receipt.json"


def production_context_publication_path(report_kind: str) -> PurePosixPath:
    """权威生产上下文物化文件（供外部复核会话绑定）的项目相对路径。"""
    kind = _validated_kind(report_kind)
    return (
        PurePosixPath("state") / "scientific_review" / kind / "production_context.json"
    )


def scientific_review_request_path(report_kind: str) -> PurePosixPath:
    """运行时发布给独立复核会话的权威请求。"""
    kind = _validated_kind(report_kind)
    return PurePosixPath("state") / "scientific_review" / kind / "review_request.json"


def derive_scientific_source_refs(
    *,
    sources: Sequence[SourceCapture],
    facts: Sequence[ResearchFact],
    claims: Sequence[ResearchClaim],
    fact_version_by_ref: Mapping[str, str],
) -> tuple[SourceRef, ...]:
    """从研究包内容重建与持久化摄取一致的已复核来源引用。

    来源版本/片段标识按摄取层同一算法从内容确定性重算；事实版本引用只取
    摄取层返回的持久化映射（缺映射即失败关闭）；声明按事实谱系归属来源。
    没有事实谱系的来源（如只为宇宙闭合采集的登记快照）不能支撑接受结论，
    不进入权威上下文来源集合——它们仍经候选内容摘要间接绑定。
    """
    source_ids = [capture.source_id for capture in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ScientificReviewTransitionError("研究来源标识重复，无法重建来源引用")
    facts_by_source: dict[str, list[ResearchFact]] = {}
    fact_source_by_id: dict[str, str] = {}
    for fact in facts:
        facts_by_source.setdefault(fact.source_id, []).append(fact)
        if fact.fact_id in fact_source_by_id:
            raise ScientificReviewTransitionError("研究事实标识重复，无法重建来源引用")
        fact_source_by_id[fact.fact_id] = fact.source_id

    refs: list[SourceRef] = []
    for capture in sources:
        content_digest = hashlib.sha256(capture.content_text.encode("utf-8")).hexdigest()
        source_version_id = source_version_identity(
            capture.source_id, content_digest,
            text_derivation=capture.text_derivation,
            **{
                role: capture.date_evidence(role)
                for role in ("published_at", "effective_at", "first_disclosed_at")
            },
        )
        source_facts = facts_by_source.get(capture.source_id, ())
        if not source_facts:
            continue
        fact_version_ids: list[str] = []
        fragment_ids: list[str] = []
        locator_refs: list[LocatorRef] = []
        for fact in source_facts:
            version_id = fact_version_by_ref.get(fact.fact_id)
            if version_id is None:
                raise ScientificReviewTransitionError(
                    f"研究事实 {fact.fact_id} 没有持久化事实版本，拒绝重建来源引用"
                )
            if version_id not in fact_version_ids:
                fact_version_ids.append(version_id)
            locator_json = _canonical_json(fact.locator.model_dump(mode="json"))
            fragment_id = stable_id(
                "evidence-fragment",
                source_version_id,
                locator_json,
                hashlib.sha256(fact.original_text.encode("utf-8")).hexdigest(),
            )
            if fragment_id not in fragment_ids:
                fragment_ids.append(fragment_id)
                locator_refs.append(
                    LocatorRef(
                        fragment_id=fragment_id,
                        locator=LocatorDetail(**fact.locator.model_dump()),
                    )
                )
        claim_ids = [
            claim.claim_id
            for claim in claims
            if any(
                fact_source_by_id.get(fact_id) == capture.source_id
                for fact_id in claim.fact_ids
            )
        ]
        if not claim_ids:
            raise ScientificReviewTransitionError(
                f"来源 {capture.source_id} 没有声明谱系，不能支撑接受结论"
            )
        refs.append(
            SourceRef(
                source_version_id=source_version_id,
                fragment_ids=tuple(fragment_ids),
                claim_ids=tuple(claim_ids),
                fact_version_ids=tuple(fact_version_ids),
                locators=tuple(locator_refs),
            )
        )
    return tuple(refs)


def build_scientific_review_context(
    *,
    project_id: str,
    report_kind: str,
    report_version: str,
    producer_id: str,
    candidate_snapshot_id: str,
    candidate_content_digest: str,
    criteria_version: str,
    gate_result_key: str,
    contract_version: str,
    coverage_set_id: str,
    evidence_snapshot_id: str,
    claim_snapshot_id: str,
    sources: Sequence[SourceCapture],
    facts: Sequence[ResearchFact],
    claims: Sequence[ResearchClaim],
    fact_version_by_ref: Mapping[str, str],
) -> ScientificQcCurrentContext:
    """从当前候选、Gate、coverage 与来源引用重建权威科学质控上下文。

    候选/门槛/身份取值只接受运行时已验证的绑定材料；覆盖摘要对覆盖集合
    身份与声明快照材料确定性计算。任何取值问题都在模型层失败关闭。
    """
    kind = _validated_kind(report_kind)
    source_refs = derive_scientific_source_refs(
        sources=sources,
        facts=facts,
        claims=claims,
        fact_version_by_ref=fact_version_by_ref,
    )
    locators = tuple(
        locator for ref in source_refs for locator in ref.locators
    )
    coverage_digest = _sha256_hex(
        {
            "claim_ids": [claim.claim_id for claim in claims],
            "claim_snapshot_id": claim_snapshot_id,
            "coverage_set_id": coverage_set_id,
            "evidence_snapshot_id": evidence_snapshot_id,
        }
    )
    return ScientificQcCurrentContext(
        context_id=stable_id(
            "scientific-qc-context",
            project_id,
            kind,
            candidate_snapshot_id,
            candidate_content_digest,
        ),
        producer_id=producer_id,
        project_id=project_id,
        report_kind=ReportKind[kind],
        report_version=report_version,
        report_object_id=f"report_{kind}",
        candidate_snapshot_id=candidate_snapshot_id,
        candidate_content_digest=candidate_content_digest,
        criteria_version=criteria_version,
        gate_result_key=gate_result_key,
        contract_version=contract_version,
        coverage_set_id=coverage_set_id,
        coverage_digest=coverage_digest,
        source_refs=source_refs,
        locators=locators,
    )


def publish_production_context(
    project_root: Path,
    report_kind: str,
    context: ScientificQcCurrentContext,
) -> Path:
    """把权威生产上下文物化为确定性状态文件，供外部复核会话绑定。

    作用域随活跃 epoch：epoch 0 写既有单例路径（历史行为逐字节兼容）；
    epoch ≥ 1 写活跃纪元版本化路径。既有文件的隐式覆盖拒绝语义不变。
    """
    kind = _validated_kind(report_kind)
    scope = active_scientific_review_scope(project_root, kind)
    path = project_root / scope.production_context_relative
    payload = (_canonical_json(context.model_dump(mode="json")) + "\n").encode("utf-8")
    if path.is_file():
        try:
            existing = path.read_bytes()
        except OSError as error:
            raise ScientificReviewTransitionError("既有科学复核生产上下文不可读") from error
        if existing != payload:
            raise ScientificReviewTransitionError(
                "既有科学复核生产上下文属于其他候选，拒绝覆盖"
            )
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _bound_gate_result(
    context: ScientificQcCurrentContext, payload: object,
) -> ReportGateResult | None:
    """Revalidate the actual evaluated result, not a PASS flag or opaque key.

    Missing results remain readable for historical source receipts. They do
    not authorize a new C report promotion.
    """
    if payload is None:
        return None
    try:
        result = ReportGateResult.model_validate(payload)
    except PydanticValidationError as error:
        raise ScientificReviewTransitionError(f"科学门槛结果无效：{error}") from error
    if (
        result.report_kind != context.report_kind
        or result.result_key != context.gate_result_key
        or result.spec_version != context.criteria_version
        or result.contract_version != context.contract_version
        or result.candidate_snapshot_digest != context.candidate_content_digest
    ):
        raise ScientificReviewTransitionError("科学门槛结果与当前复核上下文绑定不一致")
    return result


def _bound_review_input_digest(
    context: ScientificQcCurrentContext, gate_result: ReportGateResult | None,
) -> str:
    bundle_digest = _review_bundle(context).input_digest
    if gate_result is None:
        return bundle_digest  # Immutable legacy request/receipt compatibility.
    return _sha256_hex({
        "scientific_bundle_digest": bundle_digest,
        "gate_result": gate_result.model_dump(mode="json"),
    })


def _review_request_body(
    context: ScientificQcCurrentContext,
    *,
    report_kind: ReportKindCode,
    producer_session_id: str,
    produced_at: datetime,
    portal_binding: PortalArtifactBinding,
    gate_result: ReportGateResult | None = None,
) -> dict[str, object]:
    """构造复核请求体（发布与 epoch 物化共用同一格式与摘要算法）。"""
    evaluated_gate = _bound_gate_result(context, gate_result)
    production = ReviewProductionContext(
        project_id=context.project_id,
        report_kind=report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=context.candidate_content_digest,
        producer_id=context.producer_id,
        producer_session_id=producer_session_id,
        criteria_version=context.criteria_version,
        gate_result_key=context.gate_result_key,
        produced_at=produced_at,
        production_context_digest=context.context_digest,
    )
    body: dict[str, object] = {
        "scientific_context": context.model_dump(mode="json"),
        "production": production.model_dump(mode="json"),
        "review_input_digest": _bound_review_input_digest(context, evaluated_gate),
        "portal_binding": portal_binding.model_dump(mode="json"),
    }
    if evaluated_gate is not None:
        body["gate_result"] = evaluated_gate.model_dump(mode="json")
    return body



def publish_scientific_review_request(
    project_root: Path,
    report_kind: str,
    context: ScientificQcCurrentContext,
    *,
    producer_session_id: str,
    produced_at: datetime,
    portal_binding: PortalArtifactBinding,
    gate_result: ReportGateResult | None = None,
) -> Path:
    """发布审查输入、生产身份与首次门户字节绑定；同一候选重跑保留首次绑定。

    ``portal_binding`` 必须来自 format 完成后的真实磁盘字节
    （``capture_portal_artifact_binding``）。同一候选重跑时以重新捕获的
    字节重验首次绑定（漂移即失败关闭）；既有请求属于其他候选或项目时
    拒绝覆盖（不接受跨候选/跨项目/无关历史）。作用域随活跃 epoch：
    epoch 0 写既有单例路径，epoch ≥ 1 写活跃纪元版本化路径；隐式发布者
    永远不能越过显式 epoch 推进写入新候选。
    """
    kind = _validated_kind(report_kind)
    scope = active_scientific_review_scope(project_root, kind)
    path = project_root / scope.review_request_relative
    body = _review_request_body(
        context,
        report_kind=kind,
        producer_session_id=producer_session_id,
        produced_at=produced_at,
        portal_binding=portal_binding,
        gate_result=gate_result,
    )
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ScientificReviewTransitionError("既有科学复核请求损坏") from error
        if not isinstance(existing, dict) or not isinstance(
            existing.get("scientific_context"), dict
        ):
            raise ScientificReviewTransitionError("既有科学复核请求损坏")
        existing_context = existing["scientific_context"]
        if existing_context.get("context_digest") == context.context_digest:
            if existing.get("gate_result") != body.get("gate_result"):
                raise ScientificReviewTransitionError(
                    "科学门槛结果与首次复核请求不同：同键决定也不得被覆盖"
                )
            existing_binding = existing.get("portal_binding")
            if existing_binding != portal_binding.model_dump(mode="json"):
                raise ScientificReviewTransitionError(
                    "门户 manifest/站点字节与首次复核请求绑定不一致："
                    "渲染产物已漂移或被篡改（首次绑定不可变更）"
                )
            _load_scientific_review_request(project_root, kind, context)
            return path
        if existing_context.get("project_id") != context.project_id:
            raise ScientificReviewTransitionError(
                "既有科学复核请求属于其他项目，拒绝覆盖：不接受跨项目历史"
            )
        raise ScientificReviewTransitionError(
            "既有科学复核请求属于其他候选，拒绝覆盖：不接受跨候选历史"
        )
    body["request_digest"] = _sha256_hex(body)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((_canonical_json(body) + "\n").encode("utf-8"))
    return path


def _load_scientific_review_request(
    project_root: Path,
    report_kind: str,
    context: ScientificQcCurrentContext,
) -> tuple[ReviewProductionContext, str, PortalArtifactBinding, ReportGateResult | None]:
    kind = _validated_kind(report_kind)
    scope = active_scientific_review_scope(project_root, kind)
    path = project_root / scope.review_request_relative
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ScientificReviewTransitionError("科学复核请求缺失或损坏") from error
    if not isinstance(raw, dict):
        raise ScientificReviewTransitionError("科学复核请求必须是 JSON 对象")
    digest = raw.pop("request_digest", None)
    if digest != _sha256_hex(raw):
        raise ScientificReviewTransitionError("科学复核请求摘要漂移")
    scientific_context = raw.get("scientific_context")
    if not isinstance(scientific_context, dict):
        raise ScientificReviewTransitionError("科学复核请求缺少权威上下文")
    if scientific_context.get("context_digest") != context.context_digest:
        raise ScientificReviewTransitionError("科学复核请求不属于当前候选上下文")
    try:
        production = ReviewProductionContext.model_validate(raw.get("production"))
    except PydanticValidationError as error:
        raise ScientificReviewTransitionError("科学复核生产身份无效") from error
    review_input_digest = raw.get("review_input_digest")
    if not isinstance(review_input_digest, str):
        raise ScientificReviewTransitionError("科学复核请求缺少审阅输入摘要")
    evaluated_gate = _bound_gate_result(context, raw.get("gate_result"))
    if review_input_digest != _bound_review_input_digest(context, evaluated_gate):
        raise ScientificReviewTransitionError("科学复核请求审阅输入摘要与门槛/上下文不一致")
    binding_payload = raw.get("portal_binding")
    if not isinstance(binding_payload, dict):
        raise ScientificReviewTransitionError(
            "科学复核请求缺少门户产物绑定：format 完成后才能发布或晋级"
        )
    try:
        binding = PortalArtifactBinding.model_validate(binding_payload)
    except (PydanticValidationError, ValueError) as error:
        raise ScientificReviewTransitionError(f"门户产物绑定无效：{error}") from error
    # 恢复/晋级前重验门户字节：站点或清单漂移失败关闭
    verify_portal_artifact_binding(project_root, report_kind, binding)
    return production, review_input_digest, binding, evaluated_gate


def reload_production_context(
    project_root: Path,
    report_kind: str,
) -> ScientificQcCurrentContext:
    """重载活跃作用域的物化权威上下文；缺失、损坏或摘要不一致一律失败关闭。

    活跃 epoch 是唯一权威：epoch ≥ 1 读版本化纪元路径，epoch 0 读既有
    单例路径。旧纪元文件即使存在也不再是活跃上下文。
    """
    kind = _validated_kind(report_kind)
    scope = active_scientific_review_scope(project_root, kind)
    path = project_root / scope.production_context_relative
    if not path.is_file():
        raise ScientificReviewTransitionError(
            f"权威生产上下文未发布：{scope.production_context_relative}"
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ScientificReviewTransitionError(
            f"权威生产上下文文件不可读或不是有效 JSON：{path}"
        ) from error
    if not isinstance(raw, dict):
        raise ScientificReviewTransitionError("权威生产上下文文件必须是 JSON 对象")
    stored_digest = raw.get("context_digest")
    payload = {key: value for key, value in raw.items() if key != "context_digest"}
    try:
        context = ScientificQcCurrentContext.model_validate(payload)
    except (PydanticValidationError, ValueError) as error:
        raise ScientificReviewTransitionError(
            f"权威生产上下文重建失败：{error}"
        ) from error
    if stored_digest != context.context_digest:
        raise ScientificReviewTransitionError(
            "权威生产上下文摘要与物化内容不一致：文件已被篡改或损坏"
        )
    pointer = read_epoch_pointer(project_root, kind)
    if pointer is not None and (
        pointer.project_id != context.project_id
        or context.report_kind.value != kind
        or pointer.epochs[-1].context_digest != context.context_digest
    ):
        raise ScientificReviewTransitionError("epoch 指针与活跃生产上下文绑定不一致")
    return context


def load_scientific_review_receipt(
    project_root: Path,
    report_kind: str,
) -> ScientificReviewReceipt:
    """读取并完整验证活跃作用域的独立复核回执；缺回执或伪回执失败关闭。

    旧纪元回执不在活跃作用域内：即使字节完好，也不能授权新活跃 epoch。
    """
    kind = _validated_kind(report_kind)
    scope = active_scientific_review_scope(project_root, kind)
    path = project_root / scope.receipt_relative
    if not path.is_file():
        raise ScientificReviewTransitionError(
            f"独立复核回执缺失：{scope.receipt_relative}"
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ScientificReviewTransitionError(
            f"独立复核回执不可读或不是有效 JSON：{path}"
        ) from error
    try:
        return validate_scientific_review_receipt_payload(raw)
    except ScientificReviewReceiptError as error:
        raise ScientificReviewTransitionError(f"独立复核回执验证失败：{error}") from error


def _review_bundle(context: ScientificQcCurrentContext) -> ScientificQcReviewBundle:
    """从权威上下文构造审阅输入；调用方不能另选覆盖或来源。"""
    return ScientificQcReviewBundle(
        producer_id=context.producer_id,
        project_id=context.project_id,
        report_kind=context.report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=context.candidate_content_digest,
        criteria_version=context.criteria_version,
        gate_result_key=context.gate_result_key,
        coverage_set_id=context.coverage_set_id,
        coverage_digest=context.coverage_digest,
        source_refs=context.source_refs,
        locators=context.locators,
    )


def accepted_verdict_from_receipt(
    *,
    project_root: Path,
    context: ScientificQcCurrentContext,
    receipt: ScientificReviewReceipt,
) -> ScientificQcVerdict:
    """重开回执绑定产物，并验证其确为当前上下文的接受结论。"""
    artifact = receipt.artifact
    if artifact is None:  # require_verified_review_receipt 已失败关闭；保留类型收窄
        raise ScientificReviewTransitionError("独立复核回执缺少科学质控结论产物")
    path = project_root / artifact.path
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ScientificReviewTransitionError(
            "科学质控结论产物不可读或不是有效 JSON"
        ) from error
    if not isinstance(raw, dict):
        raise ScientificReviewTransitionError("科学质控结论产物必须是 JSON 对象")
    try:
        verdict = validate_scientific_qc_verdict_payload(raw)
    except ScientificQcBoundaryError as error:
        raise ScientificReviewTransitionError(
            f"科学质控结论产物验证失败：{error}"
        ) from error

    _production, input_digest, _portal, _gate = _load_scientific_review_request(
        project_root, context.report_kind.value, context,
    )
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
        (verdict.review_input_digest, input_digest, "审阅输入摘要"),
        (
            receipt.content.review_input_digest,
            input_digest,
            "回执审阅输入摘要",
        ),
        (verdict.reviewer_id, receipt.review.reviewer_id, "独立审查者"),
    )
    for verdict_value, current_value, label in agreement:
        if verdict_value != current_value:
            raise ScientificReviewTransitionError(
                f"科学质控结论{label}与当前权威上下文或回执不一致"
            )
    if verdict.verdict != "accepted" or verdict.has_blocking_issues():
        raise ScientificReviewTransitionError("科学质控结论未接受当前候选")
    if not (
        receipt.review.process.started_at
        <= verdict.reviewed_at
        <= receipt.review.process.finished_at
    ):
        raise ScientificReviewTransitionError("科学质控结论时间不在独立复核进程内")
    if verdict.valid_until <= receipt.issued_at:
        raise ScientificReviewTransitionError("科学质控接受结论在回执签发时已失效")
    return verdict


# ── R24 显式 epoch 推进：同项目重复科学复核的唯一通道 ─────────────────────────


class ScientificReviewEpochAdvance(BaseModel):
    """一次成功 epoch 推进（或精确重放）的追加式结果回执。"""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    report_kind: ReportKindCode
    activated_epoch: int
    active_context_digest: str
    predecessor_context_digest: str
    advanced_at: datetime
    production_context_relative: str
    review_request_relative: str
    receipt_relative: str

    @field_validator("project_id", "production_context_relative",
                     "review_request_relative", "receipt_relative")
    @classmethod
    def _text_fields_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("epoch 推进结果字段不能为空")
        return normalized

    @field_validator("active_context_digest", "predecessor_context_digest")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("epoch 推进结果摘要必须是小写 SHA-256")
        return value

    @field_validator("advanced_at")
    @classmethod
    def _advanced_at_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("epoch 推进时间必须包含明确时区")
        return value

    @field_validator("activated_epoch")
    @classmethod
    def _activated_epoch_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("epoch 推进结果纪元必须从 1 开始")
        return value


def _bind_epoch_contexts(
    *,
    pointer: ScientificReviewEpochPointer | None,
    active: ScientificQcCurrentContext,
    expected_predecessor_context: ScientificQcCurrentContext,
    next_context: ScientificQcCurrentContext,
) -> None:
    """绑定前驱/项目/真实新科学上下文；任何不绑定即拒绝推进。"""
    if expected_predecessor_context.context_digest != active.context_digest:
        raise ScientificReviewTransitionError(
            "预期前驱上下文与当前活跃上下文不一致（陈旧前驱或重复推进）："
            "epoch 只能从真实活跃纪元显式推进"
        )
    if (
        next_context.project_id != active.project_id
        or expected_predecessor_context.project_id != active.project_id
    ):
        raise ScientificReviewTransitionError("epoch 推进不接受跨项目上下文")
    known_digests = {active.context_digest}
    if pointer is not None:
        for entry in pointer.epochs:
            known_digests.add(entry.context_digest)
            known_digests.add(entry.predecessor_context_digest)
    if next_context.context_digest in known_digests:
        raise ScientificReviewTransitionError(
            "epoch 推进的新上下文与活跃或历史纪元上下文相同："
            "不是真实新科学复核对象，不得重复占用或回退纪元"
        )


def _stage_epoch_materials(
    *,
    project_root: Path,
    report_kind: str,
    epoch: int,
    context: ScientificQcCurrentContext,
    producer_session_id: str,
    produced_at: datetime,
    portal_binding: PortalArtifactBinding,
    gate_result: ReportGateResult | None = None,
) -> None:
    """在版本化纪元目录物化上下文与请求；指针激活前对外不可见。

    指针最后原子激活：staged 写入或回读失败时旧活跃作用域原样保留；
    同一纪元重试只接受逐字节相同的材料，拒绝混合纪元残留。
    """
    kind = _validated_kind(report_kind)
    context_path = project_root / epoch_production_context_path(kind, epoch)
    context_payload = (
        _canonical_json(context.model_dump(mode="json")) + "\n"
    ).encode("utf-8")
    body = _review_request_body(
        context,
        report_kind=kind,
        producer_session_id=producer_session_id,
        produced_at=produced_at,
        portal_binding=portal_binding,
        gate_result=gate_result,
    )
    body["request_digest"] = _sha256_hex(body)
    request_path = project_root / epoch_review_request_path(kind, epoch)
    request_payload = (_canonical_json(body) + "\n").encode("utf-8")
    for path, payload in (
        (context_path, context_payload),
        (request_path, request_payload),
    ):
        if path.is_file() and path.read_bytes() != payload:
            raise ScientificReviewTransitionError(
                f"epoch 目录已存在不同字节的前次推进残留，拒绝混合纪元材料：{path.name}"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    staged = json.loads(context_path.read_text(encoding="utf-8"))
    if not isinstance(staged, dict) or staged.get("context_digest") != (
        context.context_digest
    ):
        raise ScientificReviewTransitionError("epoch 上下文物化回读失败：拒绝激活")


def _replay_epoch_activation(
    *,
    project_root: Path,
    report_kind: str,
    pointer: ScientificReviewEpochPointer,
    next_context: ScientificQcCurrentContext,
    portal_binding: PortalArtifactBinding,
    producer_session_id: str,
    produced_at: datetime,
    gate_result: ReportGateResult | None = None,
) -> ScientificReviewEpochAdvance:
    """精确重放已激活纪元：逐字节校验后返回已记录结果（幂等）。"""
    kind = _validated_kind(report_kind)
    last = pointer.epochs[-1]
    if pointer.active_epoch != last.epoch:
        raise ScientificReviewTransitionError("epoch 指针活跃纪元与记录链不一致")
    context_path = project_root / epoch_production_context_path(kind, last.epoch)
    expected_context_payload = (
        _canonical_json(next_context.model_dump(mode="json")) + "\n"
    ).encode("utf-8")
    if not context_path.is_file() or context_path.read_bytes() != (
        expected_context_payload
    ):
        raise ScientificReviewTransitionError(
            "epoch 精确重放与已激活上下文字节不一致：拒绝覆盖或混合纪元"
        )
    production, _digest, published_binding, published_gate = _load_scientific_review_request(
        project_root, kind, next_context,
    )
    if (
        published_binding != portal_binding
        or production.producer_session_id != producer_session_id
        or production.produced_at != produced_at
        or published_gate != _bound_gate_result(next_context, gate_result)
    ):
        raise ScientificReviewTransitionError("epoch 精确重放的请求绑定与已记录材料不一致")
    return ScientificReviewEpochAdvance(
        project_id=next_context.project_id,
        report_kind=kind,
        activated_epoch=last.epoch,
        active_context_digest=next_context.context_digest,
        predecessor_context_digest=last.predecessor_context_digest,
        advanced_at=last.advanced_at,
        production_context_relative=epoch_production_context_path(
            kind, last.epoch
        ).as_posix(),
        review_request_relative=epoch_review_request_path(kind, last.epoch).as_posix(),
        receipt_relative=epoch_receipt_path(kind, last.epoch).as_posix(),
    )


def _activate_epoch_pointer(
    project_root: Path, report_kind: str, pointer: ScientificReviewEpochPointer
) -> Path:
    """原子激活 epoch 指针（测试在此注入激活故障；失败保留旧活跃纪元）。"""
    try:
        return write_epoch_pointer(project_root, report_kind, pointer)
    except ScientificReviewEpochStateError as error:
        raise ScientificReviewTransitionError(f"epoch 指针激活失败：{error}") from error


def advance_scientific_review_epoch(
    *,
    project_root: Path,
    report_kind: str,
    expected_predecessor_context: ScientificQcCurrentContext,
    next_context: ScientificQcCurrentContext,
    producer_session_id: str,
    produced_at: datetime,
    portal_binding: PortalArtifactBinding,
    advanced_at: datetime | None = None,
    gate_result: ReportGateResult | None = None,
) -> ScientificReviewEpochAdvance:
    """显式版本化 epoch 推进：同项目重复科学复核的唯一通道。

    按序绑定：预期前驱上下文（摘要必须等于当前活跃上下文，陈旧前驱拒绝）、
    同项目/同报告、真实新科学上下文（摘要不得等于活跃或任何历史纪元，
    同上下文重复与回退拒绝）与真实门户字节（当前磁盘重验，漂移拒绝）。
    新纪元上下文/请求先物化到版本化目录，指针最后原子激活；共享项目锁内
    任何失败都保留旧活跃上下文/回执/请求，精确重试幂等。隐式发布者不能
    经由既有发布入口越过本 API 写入新候选。
    """
    kind = _validated_kind(report_kind)
    _bound_gate_result(next_context, gate_result)
    root = project_root.expanduser().resolve()
    if (
        expected_predecessor_context.report_kind.value != kind
        or next_context.report_kind.value != kind
    ):
        raise ScientificReviewTransitionError(
            "epoch 推进的上下文报告类型与目标报告类型不一致"
        )
    if not producer_session_id.strip():
        raise ScientificReviewTransitionError("epoch 推进缺少生产者会话标识")
    moment = datetime.now(UTC) if advanced_at is None else advanced_at
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ScientificReviewTransitionError("epoch 推进时间必须包含明确时区")
    if produced_at.tzinfo is None or produced_at.utcoffset() is None:
        raise ScientificReviewTransitionError("epoch 生产完成时间必须包含明确时区")

    with current_delivery_lock(root):
        try:
            pointer = read_epoch_pointer(root, kind)
        except ScientificReviewEpochStateError as error:
            raise ScientificReviewTransitionError(
                f"科学复核 epoch 指针无效：{error}"
            ) from error
        if pointer is not None:
            last = pointer.epochs[-1]
            if (
                last.context_digest == next_context.context_digest
                and last.predecessor_context_digest
                == expected_predecessor_context.context_digest
            ):
                return _replay_epoch_activation(
                    project_root=root,
                    report_kind=kind,
                    pointer=pointer,
                    next_context=next_context,
                    portal_binding=portal_binding,
                    producer_session_id=producer_session_id,
                    produced_at=produced_at,
                    gate_result=gate_result,
                )
        try:
            active = reload_production_context(root, kind)
        except ScientificReviewTransitionError as error:
            raise ScientificReviewTransitionError(
                f"epoch 推进需要既有活跃生产上下文：{error}"
            ) from error
        _bind_epoch_contexts(
            pointer=pointer,
            active=active,
            expected_predecessor_context=expected_predecessor_context,
            next_context=next_context,
        )
        verify_portal_artifact_binding(root, kind, portal_binding)
        next_epoch = (pointer.active_epoch if pointer is not None else 0) + 1
        _stage_epoch_materials(
            project_root=root,
            report_kind=kind,
            epoch=next_epoch,
            context=next_context,
            producer_session_id=producer_session_id,
            produced_at=produced_at,
            portal_binding=portal_binding,
            gate_result=gate_result,
        )
        entry = ScientificReviewEpochEntry(
            epoch=next_epoch,
            context_digest=next_context.context_digest,
            predecessor_context_digest=active.context_digest,
            advanced_at=moment,
        )
        new_pointer = build_scientific_review_epoch_pointer(
            project_id=next_context.project_id,
            report_kind=kind,
            epochs=(
                *(pointer.epochs if pointer is not None else ()),
                entry,
            ),
            active_epoch=next_epoch,
        )
        _activate_epoch_pointer(root, kind, new_pointer)
        return ScientificReviewEpochAdvance(
            project_id=next_context.project_id,
            report_kind=kind,
            activated_epoch=next_epoch,
            active_context_digest=next_context.context_digest,
            predecessor_context_digest=active.context_digest,
            advanced_at=moment,
            production_context_relative=epoch_production_context_path(
                kind, next_epoch
            ).as_posix(),
            review_request_relative=epoch_review_request_path(
                kind, next_epoch
            ).as_posix(),
            receipt_relative=epoch_receipt_path(kind, next_epoch).as_posix(),
        )


def prepare_rendered_scientific_review(
    *,
    project_root: Path,
    report_kind: str,
    context: ScientificQcCurrentContext,
    producer_session_id: str,
    produced_at: datetime,
    portal_binding: PortalArtifactBinding,
    gate_result: ReportGateResult | None = None,
) -> ActiveScientificReviewScope:
    """普通手动运行发布本轮请求；新候选推进纪元，同候选保留首次绑定。

    初始化和同候选恢复在共享项目锁内完成。新候选先捕获当前前驱，释放
    非重入锁后交给显式推进 API 再核验前驱，避免竞态或嵌套锁死锁。
    此处只发布未复核候选，绝不复用历史回执作为新候选的科学授权。
    """
    kind = _validated_kind(report_kind)
    root = project_root.expanduser().resolve()
    if context.report_kind.value != kind:
        raise ScientificReviewTransitionError("本轮上下文与目标报告类型不一致")
    _review_request_body(
        context,
        report_kind=kind,
        producer_session_id=producer_session_id,
        produced_at=produced_at,
        portal_binding=portal_binding,
        gate_result=gate_result,
    )
    with current_delivery_lock(root):
        verify_portal_artifact_binding(root, kind, portal_binding)
        scope = active_scientific_review_scope(root, kind)
        context_path = root / scope.production_context_relative
        if context_path.exists() or context_path.is_symlink() or scope.epoch > 0:
            predecessor = reload_production_context(root, kind)
        else:
            predecessor = None
        if predecessor is None or predecessor == context:
            publish_production_context(root, kind, context)
            publish_scientific_review_request(
                root, kind, context,
                producer_session_id=producer_session_id,
                produced_at=produced_at,
                portal_binding=portal_binding,
                gate_result=gate_result,
            )
            return scope
    advanced = advance_scientific_review_epoch(
        project_root=root,
        report_kind=kind,
        expected_predecessor_context=predecessor,
        next_context=context,
        producer_session_id=producer_session_id,
        produced_at=produced_at,
        portal_binding=portal_binding,
        gate_result=gate_result,
    )
    return ActiveScientificReviewScope(
        epoch=advanced.activated_epoch,
        production_context_relative=advanced.production_context_relative,
        review_request_relative=advanced.review_request_relative,
        receipt_relative=advanced.receipt_relative,
    )


def promote_rendered_candidate(
    *,
    project_root: Path,
    current_state: str,
    context: ScientificQcCurrentContext,
    receipt: ScientificReviewReceipt,
    promoted_at: datetime | None = None,
) -> str:
    """两阶段迁移第二阶段：真实回执绑定权威上下文后才产生被接受后继。

    只有 ``rendered_unreviewed`` 候选可进入本迁移（单向、一次性）；回执按序
    通过内容完整性/verified 状态/复核产物实际字节核验与权威上下文逐字绑定。
    任何失败都以 ``ScientificReviewTransitionError``（或回执层错误）失败关闭。
    """
    if current_state != RENDERED_UNREVIEWED:
        raise ScientificReviewTransitionError(
            f"候选状态 {current_state!r} 不是 {RENDERED_UNREVIEWED}："
            "两阶段科学复核迁移只接受渲染后未复核候选"
        )
    require_verified_review_receipt(receipt, project_root=project_root)
    bind_receipt_to_production_context(receipt, context)
    production, review_input_digest, _portal_binding, evaluated_gate = (
        _load_scientific_review_request(
            project_root, context.report_kind.value, context
        )
    )
    if evaluated_gate is None and context.report_kind is ReportKind.C:
        raise ScientificReviewTransitionError("科学门槛结果缺失：历史来源回执不能授权新 C 晋级")
    if evaluated_gate is not None and evaluated_gate.decision is not ReportDecision.PASSED:
        raise ScientificReviewTransitionError("科学门槛尚未通过：来源复核回执不能晋级报告")
    if receipt.production != production:
        raise ScientificReviewTransitionError("回执生产身份与运行时发布请求不一致")
    if receipt.content.review_input_digest != review_input_digest:
        raise ScientificReviewTransitionError("回执审阅输入与运行时发布请求不一致")
    checked_at = datetime.now(UTC) if promoted_at is None else promoted_at
    if checked_at.tzinfo is None or checked_at.utcoffset() is None:
        raise ScientificReviewTransitionError("科学晋级时间必须包含明确时区")
    verdict = accepted_verdict_from_receipt(
        project_root=project_root,
        context=context,
        receipt=receipt,
    )
    if checked_at < receipt.issued_at:
        raise ScientificReviewTransitionError("科学晋级时间早于回执签发时间")
    if verdict.valid_until <= checked_at:
        raise ScientificReviewTransitionError("科学质控接受结论在晋级时已失效")
    # A structurally self-consistent receipt is not authority.  Reopen the
    # issuer-owned append-only record and bind it to the exact receipt bytes.
    from ci_workflow.application.review_issuer import (
        ReviewIssuanceError,
        verify_receipt_issuance,
    )

    try:
        issued = verify_receipt_issuance(
            project_root,
            context.report_kind.value,
            checked_at=checked_at,
        )
    except ReviewIssuanceError as error:
        raise ScientificReviewTransitionError(
            f"候选缺少真实独立issuer签发：{error}"
        ) from error
    if issued.receipt_digest != receipt.receipt_digest:
        raise ScientificReviewTransitionError("issuer记录未签发当前科学复核回执")
    return SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE


__all__ = [
    "RENDERED_UNREVIEWED",
    "SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE",
    "ActiveScientificReviewScope",
    "PortalArtifactBinding",
    "ScientificReviewEpochAdvance",
    "ScientificReviewTransitionError",
    "accepted_verdict_from_receipt",
    "active_scientific_review_scope",
    "advance_scientific_review_epoch",
    "build_scientific_review_context",
    "capture_portal_artifact_binding",
    "derive_scientific_source_refs",
    "load_scientific_review_receipt",
    "production_context_publication_path",
    "prepare_rendered_scientific_review",
    "promote_rendered_candidate",
    "publish_production_context",
    "publish_scientific_review_request",
    "reload_production_context",
    "scientific_review_receipt_path",
    "scientific_review_request_path",
    "verify_portal_artifact_binding",
]
