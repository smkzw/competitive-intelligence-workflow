"""C 待确认纯研究内容 → 真实来源复核入口（bootstrap 准备，只发布未复核候选）。

本模块把一份**不含独立复核摘要**的 ``FreshCResearchContent``（全部观察仍是
候选）有界地接成真实项目里的来源复核入口：

- 只接受项目根内的输入文件；校验 C 类合同成员、适应症与数据截止，拒绝任何
  预接受/用户修订观察（``review_state`` 必须全部为 ``candidate``）、携带
  ``scientific_review`` 批准摘要的包与来源原文引用不一致的内容，失败关闭且
  不做任何静默状态翻转；
- 事实由既有 ``derive_c_research_facts`` 派生，原文引用先按既有精确定位
  重放；随后走既有共享谱系摄取（``ingest_research_evidence``）持久化真实
  来源、事实、声明与内容寻址证据快照；
- ``evaluate_c_report_gate`` 只在真实谱系（实际证据快照标识与持久化事实
  版本映射）上评估；门槛结论只能来自同一评估单元结果（``review_result``），
  不接受调用方传入布尔、接受标记或 SQL 翻转——门槛阻断仍可复核，但不可
  晋级；
- 候选门户数据只改写来源谱系元数据（新证据快照标识、实际来源实例→版本
  映射、报告快照标识置空），观察原文/取值/状态逐字节保持；规范化报告数据
  持久化在新的 ``evidence/library/c-source-review/<摘要>/report-data.json``，
  输入文件不变；
- 消费者登记复用既有 ``register_c_source_consumers``，行→事实版本映射只取
  实际报告行；候选站点复用 ``_render_html_c_minimal(review_candidate=True)``
  的真实渲染事务与真实摄取谱系绑定；随后按既有正式合同调用
  ``prepare_rendered_scientific_review``（携带 ``gate_result``），绝不写
  current、绝不冒充宿主签署任何接受；
- 首次入口回执冻结实际输入/来源/谱系/渲染/请求/门槛与后续步骤；精确重放
  先校验首次入口回执、绑定与字节再返回既有输出，不重渲染、不覆盖；回执、
  站点、预览数据或显式时间参数漂移一律失败关闭。中断的首次尝试按既有
  产物（预览报告数据、产物清单、复核请求）恢复，不引入新事务平台。

本模块不提供 CLI、不修改共享文件、不做宿主身份冒充；调用方负责项目合同与
运行输入。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.application.fresh_c_research_package import (
    CReportGateOutcome,
    FreshCPackageError,
    FreshCResearchContent,
    derive_c_research_facts,
    evaluate_c_report_gate,
    validate_fresh_c_content,
)
from ci_workflow.application.fresh_research_ingestion import (
    ResearchEvidenceLineage,
    ResearchIngestionError,
    ingest_research_evidence,
)
from ci_workflow.application.fresh_research_primitives import ResearchFact
from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    verify_project_workspace,
)
from ci_workflow.application.scientific_review_transition import (
    ActiveScientificReviewScope,
    PortalArtifactBinding,
    ScientificReviewTransitionError,
    active_scientific_review_scope,
    build_scientific_review_context,
    capture_portal_artifact_binding,
    prepare_rendered_scientific_review,
)
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.enums import FactReviewState, ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.qc.review_receipt import ReviewProductionContext
from ci_workflow.qc.scientific import ScientificQcCurrentContext
from ci_workflow.renderers.portal.active_fact_projection import ActiveFactBinding
from ci_workflow.renderers.portal.report_c import ReportCPortalData
from ci_workflow.storage.manifest_store import ArtifactManifest
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    LockedSnapshot,
    SnapshotIntegrityError,
    compute_locked_snapshot,
)
from ci_workflow.storage.source_derivation import SourceDerivationError

_SHA256_PATTERN_LENGTH = 64
_ENTRY_ROOT_RELATIVE = PurePosixPath("evidence", "library", "c-source-review")
_REPORT_DATA_NAME = "report-data.json"
_RECEIPT_NAME = "entry-receipt.json"

_NEXT_STEPS: tuple[str, ...] = (
    "本入口只发布待独立复核候选：不代表科学接受、不切换 current、不生成正式发布结果。",
    "下一步由具备资格的独立复核会话按复核请求签发真实回执；回执必须绑定同一候选内容、门槛结果与门户字节。",
    "收到真实回执并通过独立接受与投影链后才可由宿主推进；本入口不替代独立医学、报告或发布验收。",
)


class CSourceReviewEntryError(ValueError):
    """C 来源复核入口输入、谱系、渲染或请求不满足合同（失败关闭）。"""


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CSourceReviewEntryError("C 来源复核入口时间必须包含明确时区")
    return value


def _sha256_field(value: str) -> str:
    if len(value) != _SHA256_PATTERN_LENGTH or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("C 来源复核入口摘要必须是小写 SHA-256")
    return value


def _relative_field(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("C 来源复核入口相对路径不能为空")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("C 来源复核入口只接受安全的项目相对路径")
    return normalized


class CSourceReviewEntryReceipt(BaseModel):
    """冻结的 C 来源复核入口回执：实际输入、来源、谱系、渲染、请求与门槛。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    report_kind: Literal["C"] = "C"
    producer_session_id: str
    produced_at: datetime
    created_at: datetime
    run_id: str
    content_relative: str
    content_file_sha256: str
    content_digest: str
    claim_ids: tuple[str, ...] = Field(min_length=1)
    claim_snapshot_id: str
    coverage_set_id: str
    evidence_snapshot_id: str
    evidence_snapshot_relative: str
    source_version_by_source_id: Mapping[str, str]
    fact_row_count: int = Field(ge=1)
    gate_spec_id: str
    gate_spec_version: str
    gate_result_key: str
    gate_decision: Literal["passed", "blocked"]
    context_digest: str
    site_relative: str
    manifest_relative: str
    portal_binding: PortalArtifactBinding
    review_request_relative: str
    production_context_relative: str
    receipt_relative: str
    report_data_relative: str
    report_data_sha256: str
    next_steps: tuple[str, ...] = Field(min_length=1)

    @field_validator("content_file_sha256", "content_digest", "report_data_sha256")
    @classmethod
    def _digests_are_sha256(cls, value: str) -> str:
        return _sha256_field(value)

    @field_validator(
        "content_relative",
        "site_relative",
        "manifest_relative",
        "review_request_relative",
        "production_context_relative",
        "receipt_relative",
        "report_data_relative",
        "evidence_snapshot_relative",
    )
    @classmethod
    def _paths_are_relative(cls, value: str) -> str:
        return _relative_field(value)

    @field_validator("produced_at", "created_at")
    @classmethod
    def _times_have_offsets(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("C 来源复核入口回执时间必须包含明确时区")
        return value


@dataclass(frozen=True)
class CSourceReviewEntryOutcome:
    """一次（或精确重放的）C 来源复核入口准备结果。"""

    context: ScientificQcCurrentContext
    scope: ActiveScientificReviewScope
    evidence_snapshot_id: str
    claim_snapshot_id: str
    coverage_set_id: str
    report_data_path: Path
    gate: CReportGateOutcome
    consumers: tuple[ActiveFactBinding, ...]
    receipt_path: Path


def prepare_c_source_review(
    *,
    project_root: Path,
    content_path: Path,
    producer_session_id: str,
    produced_at: datetime | None = None,
) -> CSourceReviewEntryOutcome:
    """把待确认 C 纯研究内容接成真实项目内的来源复核入口。

    只发布未复核候选：确定性证据门槛按真实谱系评估（阻断也可复核）；
    不写 current、不产生任何接受、不冒充宿主。同一输入重复调用精确重放：
    校验首次入口回执、绑定与字节后返回既有输出，不重渲染、不覆盖。
    """
    root = Path(project_root).expanduser().resolve()
    try:
        contract = verify_project_workspace(root).contract
    except ProjectWorkspaceError as error:
        raise CSourceReviewEntryError(f"C 来源复核入口需要可核验的项目工作区：{error}") from error
    if ReportKind.C not in contract.reports:
        raise CSourceReviewEntryError("项目合同未包含 C 类报告")
    if not producer_session_id.strip():
        raise CSourceReviewEntryError("C 来源复核入口缺少生产者会话标识")

    content, content_relative, content_file_sha256 = _load_content(root, content_path)
    _require_contract_alignment(content, contract)
    _require_all_candidate(content)
    _require_artifact_version(content)

    content_digest = content.content_digest
    claim_ids = content.claim_ids
    claim_snapshot_id = stable_id(
        "claim-snapshot", contract.project_id, content_digest, *claim_ids
    )
    run_id = stable_id("c-source-review-run", contract.project_id, content_digest)
    entry_directory = root.joinpath(*_ENTRY_ROOT_RELATIVE.parts, content_digest)
    report_data_path = entry_directory / _REPORT_DATA_NAME
    receipt_path = entry_directory / _RECEIPT_NAME

    explicit_produced_at = (
        None if produced_at is None else _offset_datetime(produced_at)
    )
    moment = explicit_produced_at or datetime.now(UTC)

    # One preparation path also handles recovery. The frozen receipt and existing
    # renderer/request contracts reject drift; no second replay implementation.
    if receipt_path.is_file():
        _validate_entry_replay(
            root=root,
            contract=contract,
            content=content,
            content_relative=content_relative,
            content_file_sha256=content_file_sha256,
            claim_ids=claim_ids,
            claim_snapshot_id=claim_snapshot_id,
            run_id=run_id,
            report_data_path=report_data_path,
            receipt_path=receipt_path,
            producer_session_id=producer_session_id,
            explicit_produced_at=explicit_produced_at,
        )

    facts = _derive_facts(content)

    # 中断的首次尝试：既有预览数据把首轮证据快照（及其摄取时间）带回，
    # 复用既有产物而不是新事务平台。
    adopted_snapshot_id: str | None = None
    created_at = moment
    if report_data_path.is_file():
        adopted = _load_portal_data(report_data_path, label="既有 C 预览报告数据")
        if adopted.source_evidence_snapshot_id is None:
            raise CSourceReviewEntryError("既有 C 预览报告数据缺少来源快照绑定")
        adopted_snapshot_id = adopted.source_evidence_snapshot_id
        _snapshot, snapshot_payload = _open_locked_evidence(root, adopted_snapshot_id)
        created_at = _require_snapshot_binding(
            snapshot_payload, contract=contract, content=content
        )

    try:
        lineage = ingest_research_evidence(
            project_root=root,
            project_id=contract.project_id,
            contract_version=contract.contract_version,
            report_kind="C",
            data_cutoff=content.data_cutoff,
            scientific_content_digest=content_digest,
            created_at=created_at,
            sources=content.sources,
            route_attempts=content.route_attempts,
            facts=facts,
            claims=content.claims,
        )
    except (ResearchIngestionError, SourceDerivationError, OSError) as error:
        raise CSourceReviewEntryError(f"C 来源摄取失败关闭：{error}") from error
    if (
        adopted_snapshot_id is not None
        and lineage.evidence_snapshot.snapshot_id != adopted_snapshot_id
    ):
        raise CSourceReviewEntryError(
            "既有 C 预览数据不属于当前内容谱系：拒绝覆盖或混合首次尝试"
        )

    closure = _read_closure(root, lineage.evidence_snapshot)
    version_by_capture = _source_version_by_capture(closure)
    fact_version_by_ref = _fact_version_by_ref(closure)
    row_versions = _row_version_map(content, fact_version_by_ref)

    preview = _preview_portal_data(
        content,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        version_by_capture=version_by_capture,
    )
    encoded_report_data = _canonical_json(preview.model_dump(mode="json"))
    if report_data_path.is_file():
        try:
            existing_report_data = report_data_path.read_bytes()
        except OSError as error:
            raise CSourceReviewEntryError("既有 C 预览报告数据不可读") from error
        if existing_report_data != encoded_report_data:
            raise CSourceReviewEntryError(
                "既有 C 预览报告数据与当前输入不一致：拒绝覆盖或复用"
            )
    else:
        _write_frozen(report_data_path, encoded_report_data, label="C 预览报告数据")

    coverage_set_id = stable_id(
        "coverage-set",
        contract.project_id,
        "C",
        lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id,
    )
    gate_outcome = evaluate_c_report_gate(
        content,
        project_id=contract.project_id,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        contract_version=str(contract.contract_version),
        fact_version_by_ref=lineage.fact_version_by_ref,
    )

    from ci_workflow.application.c_portal_consumer_registry import (
        CPortalConsumerRegistrationError,
        register_c_source_consumers,
    )

    captures_by_id = {capture.source_id: capture for capture in content.sources}
    try:
        consumers = register_c_source_consumers(
            root,
            lineage.evidence_snapshot,
            preview,
            row_versions,
            captures_by_id,
            registered_at=created_at,
        )
    except CPortalConsumerRegistrationError as error:
        raise CSourceReviewEntryError(f"C 报告消费者登记失败关闭：{error}") from error

    site_relative, manifest_relative = _render_or_adopt_candidate(
        root=root,
        contract=contract,
        lineage=lineage,
        preview=preview,
        report_data_path=report_data_path,
        encoded_report_data=encoded_report_data,
        run_id=run_id,
        claim_ids=claim_ids,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
    )
    try:
        portal_binding = capture_portal_artifact_binding(
            root, "C", manifest_relative=manifest_relative, site_relative=site_relative
        )
    except ScientificReviewTransitionError as error:
        raise CSourceReviewEntryError(f"C 门户产物绑定失败关闭：{error}") from error
    _require_site_bytes_match_manifest(
        root=root,
        manifest_relative=manifest_relative,
        portal_binding=portal_binding,
    )

    produced_at = _adopt_or_now_produced_at(
        root=root,
        content_digest=content_digest,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        producer_session_id=producer_session_id,
        explicit_produced_at=explicit_produced_at,
        fallback=moment,
    )
    context = _build_context(
        contract=contract,
        content=content,
        facts=facts,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        gate_outcome=gate_outcome,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        fact_version_by_ref=lineage.fact_version_by_ref,
    )
    try:
        scope = prepare_rendered_scientific_review(
            project_root=root,
            report_kind="C",
            context=context,
            producer_session_id=producer_session_id,
            produced_at=produced_at,
            portal_binding=portal_binding,
            gate_result=gate_outcome.review_result,
        )
    except ScientificReviewTransitionError as error:
        raise CSourceReviewEntryError(f"C 复核请求发布失败关闭：{error}") from error

    receipt = CSourceReviewEntryReceipt(
        project_id=contract.project_id,
        producer_session_id=producer_session_id,
        produced_at=produced_at,
        created_at=created_at,
        run_id=run_id,
        content_relative=content_relative,
        content_file_sha256=content_file_sha256,
        content_digest=content_digest,
        claim_ids=claim_ids,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        evidence_snapshot_relative=lineage.evidence_snapshot.relative_path,
        source_version_by_source_id=version_by_capture,
        fact_row_count=len(row_versions),
        gate_spec_id=gate_outcome.spec_id,
        gate_spec_version=gate_outcome.spec_version,
        gate_result_key=gate_outcome.review_result.result_key,
        gate_decision=gate_outcome.result.decision.value,
        context_digest=context.context_digest,
        site_relative=site_relative,
        manifest_relative=manifest_relative,
        portal_binding=portal_binding,
        review_request_relative=scope.review_request_relative,
        production_context_relative=scope.production_context_relative,
        receipt_relative=scope.receipt_relative,
        report_data_relative=report_data_path.relative_to(root).as_posix(),
        report_data_sha256=_sha256_bytes(encoded_report_data),
        next_steps=_NEXT_STEPS,
    )
    _write_frozen(
        receipt_path,
        _canonical_json(receipt.model_dump(mode="json")),
        label="C 来源复核入口回执",
    )
    return CSourceReviewEntryOutcome(
        context=context,
        scope=scope,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
        report_data_path=report_data_path,
        gate=gate_outcome,
        consumers=consumers,
        receipt_path=receipt_path,
    )


# ─── 输入加载与合同校验 ─────────────────────────────────────────────────────


def _load_content(
    root: Path, content_path: Path,
) -> tuple[FreshCResearchContent, str, str]:
    """读取项目根内的待确认内容；文件或合同失败均失败关闭。"""
    resolved = Path(content_path).expanduser()
    if not resolved.is_absolute():
        resolved = root / resolved
    resolved = resolved.resolve()
    try:
        content_relative = resolved.relative_to(root).as_posix()
    except ValueError as error:
        raise CSourceReviewEntryError("C 来源复核输入必须位于项目根内") from error
    if not resolved.is_file():
        raise CSourceReviewEntryError(f"C 来源复核输入不存在：{content_relative}")
    try:
        encoded = resolved.read_bytes()
    except OSError as error:
        raise CSourceReviewEntryError("C 来源复核输入不可读") from error
    try:
        payload = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CSourceReviewEntryError("C 来源复核输入不是有效 JSON") from error
    if isinstance(payload, dict) and "scientific_review" in payload:
        raise CSourceReviewEntryError(
            "C 来源复核入口只接受无独立复核摘要的待确认内容：不得携带 scientific_review 批准"
        )
    try:
        content = validate_fresh_c_content(payload)
    except (FreshCPackageError, PydanticValidationError) as error:
        raise CSourceReviewEntryError(f"C 来源复核输入不符合合同：{error}") from error
    return content, content_relative, _sha256_bytes(encoded)


def _require_contract_alignment(content: FreshCResearchContent, contract: ProjectContract) -> None:
    if " ".join(content.indication.split()) != contract.indication:
        raise CSourceReviewEntryError("C 来源复核输入的适应症与项目合同不一致")
    # 既有 C 消费者登记要求候选报告头的数据截止与锁定项目合同一致；
    # 上游内容通常正是按合同截止日（当日 23:59:59.999999）生成。
    if content.data_cutoff != contract.data_cutoff:
        raise CSourceReviewEntryError(
            "C 来源复核输入的数据截止必须与项目合同截止一致"
            "（既有 C 消费者登记要求候选报告头与锁定合同逐项一致）"
        )


def _require_all_candidate(content: FreshCResearchContent) -> None:
    """全部观察必须仍是候选：拒绝预接受/用户修订，绝不静默翻转。"""
    states = {row.review_state for row in content.report_data.observations}
    if states != {FactReviewState.CANDIDATE}:
        raise CSourceReviewEntryError(
            "C 来源复核入口只接受全部候选观察（review_state=candidate）："
            "不接受预接受或用户修订状态"
        )
    if content.report_data.user_edits:
        raise CSourceReviewEntryError(
            "C 来源复核入口不接受用户修订披露：用户修订属于既有快照，不得混入待确认输入"
        )


def _require_artifact_version(content: FreshCResearchContent) -> None:
    """报告版本必须构成既有站点产物路径合同；不在此规范化科学内容。"""
    from ci_workflow.storage.paths import ArtifactPathService, ArtifactPathViolation

    try:
        ArtifactPathService().version_root(ReportKind.C, content.report_version)
    except ArtifactPathViolation as error:
        raise CSourceReviewEntryError(
            "C 来源复核输入的 report_version 不能构成站点产物路径合同"
            f"（报告版本必须为 v 开头的安全路径段）：{error}"
        ) from error


def _derive_facts(content: FreshCResearchContent) -> tuple[ResearchFact, ...]:
    try:
        return derive_c_research_facts(content)
    except (FreshCPackageError, ValueError) as error:
        raise CSourceReviewEntryError(f"C 事实派生失败关闭：{error}") from error




# ─── 证据快照、闭包与预览数据 ───────────────────────────────────────────────


def _open_locked_evidence(
    root: Path, snapshot_id: str,
) -> tuple[LockedSnapshot, dict[str, Any]]:
    relative = PurePosixPath("snapshots", "evidence", f"{snapshot_id}.json")
    path = root.joinpath(*relative.parts)
    try:
        encoded = path.read_bytes()
    except OSError as error:
        raise CSourceReviewEntryError(f"C 证据快照缺失或不可读：{snapshot_id}") from error
    try:
        payload = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CSourceReviewEntryError("C 证据快照不是有效 JSON") from error
    if not isinstance(payload, dict):
        raise CSourceReviewEntryError("C 证据快照根节点必须是对象")
    try:
        locked = compute_locked_snapshot(kind="evidence", report=None, manifest=payload)
    except (ValueError, SnapshotIntegrityError) as error:
        raise CSourceReviewEntryError(f"C 证据快照合同或摘要无效：{error}") from error
    if (
        locked.snapshot_id != snapshot_id
        or locked.sha256 != _sha256_bytes(encoded)
        or locked.byte_size != len(encoded)
    ):
        raise CSourceReviewEntryError("C 证据快照身份与内容寻址摘要不一致")
    return locked, payload


def _require_snapshot_binding(
    payload: Mapping[str, Any], *, contract: ProjectContract, content: FreshCResearchContent,
) -> datetime:
    try:
        manifest = EvidenceSnapshotManifest.model_validate(payload)
    except (PydanticValidationError, ValueError) as error:
        raise CSourceReviewEntryError(f"C 证据快照合同无效：{error}") from error
    if (
        manifest.project_id != contract.project_id
        or manifest.contract_version != contract.contract_version
        or manifest.data_cutoff != content.data_cutoff
        or manifest.scientific_content_digest != content.content_digest
    ):
        raise CSourceReviewEntryError("C 证据快照与当前项目、截止或内容摘要不一致")
    return manifest.created_at


def _read_closure(root: Path, snapshot: LockedSnapshot) -> Mapping[str, Any]:
    from ci_workflow.storage.snapshot_store import SnapshotStore

    try:
        payload = SnapshotStore(root).read(snapshot)
    except (OSError, ValueError, SnapshotIntegrityError) as error:
        raise CSourceReviewEntryError(f"C 证据快照不可信：{error}") from error
    closure = payload.get("closure")
    if not isinstance(closure, Mapping) or not isinstance(closure.get("sources"), list):
        raise CSourceReviewEntryError("C 证据快照必须包含锁定传递闭包")
    return closure


def _source_version_by_capture(closure: Mapping[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in closure["sources"]:
        try:
            capture_id = str(entry["capture"]["source_id"])
            version_id = str(entry["source_version_id"])
        except (KeyError, TypeError) as error:
            raise CSourceReviewEntryError("C 锁定闭包来源记录无效") from error
        if not capture_id or not version_id or capture_id in mapping:
            raise CSourceReviewEntryError("C 锁定闭包存在缺失或重复来源实例")
        mapping[capture_id] = version_id
    return mapping


def _fact_version_by_ref(closure: Mapping[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for entry in closure.get("facts", []):
        try:
            fact_id = str(entry["fact"]["fact_id"])
            version_id = str(entry["fact_version_id"])
        except (KeyError, TypeError) as error:
            raise CSourceReviewEntryError("C 锁定闭包事实记录无效") from error
        if fact_id in mapping:
            raise CSourceReviewEntryError("C 锁定闭包事实标识重复")
        mapping[fact_id] = version_id
    if not mapping:
        raise CSourceReviewEntryError("C 锁定闭包缺少事实版本")
    return mapping


def _row_version_map(
    content: FreshCResearchContent, fact_version_by_ref: Mapping[str, str],
) -> dict[str, str]:
    """行→事实版本映射只取实际报告行，缺失即失败关闭。"""
    row_versions: dict[str, str] = {}
    for row in content.report_data.observations:
        version_id = fact_version_by_ref.get(row.row_id)
        if version_id is None:
            raise CSourceReviewEntryError(f"C 报告行没有持久化事实版本：{row.row_id}")
        row_versions[row.row_id] = version_id
    return row_versions


def _preview_portal_data(
    content: FreshCResearchContent,
    *,
    evidence_snapshot_id: str,
    version_by_capture: Mapping[str, str],
) -> ReportCPortalData:
    """只改写来源谱系元数据的候选门户数据；观察与取值逐字节保持。"""
    payload = content.report_data.model_dump(mode="json")
    payload["report_snapshot_id"] = None
    payload["source_evidence_snapshot_id"] = evidence_snapshot_id
    payload["source_version_by_source_id"] = dict(version_by_capture)
    try:
        return ReportCPortalData.model_validate(payload)
    except (PydanticValidationError, ValueError) as error:
        raise CSourceReviewEntryError(f"C 门户来源版本投影不闭合：{error}") from error


def _load_portal_data(path: Path, *, label: str) -> ReportCPortalData:
    try:
        encoded = path.read_bytes()
    except OSError as error:
        raise CSourceReviewEntryError(f"{label}不可读") from error
    try:
        return ReportCPortalData.model_validate_json(encoded)
    except (PydanticValidationError, ValueError) as error:
        raise CSourceReviewEntryError(f"{label}不符合合同：{error}") from error


def _write_frozen(path: Path, encoded: bytes, *, label: str) -> None:
    if path.is_file():
        try:
            existing = path.read_bytes()
        except OSError as error:
            raise CSourceReviewEntryError(f"{label}不可读") from error
        if existing != encoded:
            raise CSourceReviewEntryError(f"{label}已存在不同字节，拒绝覆盖：{path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # Publish without replacing a concurrent first writer's frozen bytes.
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            if path.read_bytes() != encoded:
                raise CSourceReviewEntryError(
                    f"{label}已存在不同字节，拒绝覆盖：{path.name}"
                ) from error
    finally:
        temporary.unlink(missing_ok=True)


# ─── 候选站点渲染（复用既有渲染事务与真实谱系绑定） ─────────────────────────


def _render_or_adopt_candidate(
    *,
    root: Path,
    contract: ProjectContract,
    lineage: ResearchEvidenceLineage,
    preview: ReportCPortalData,
    report_data_path: Path,
    encoded_report_data: bytes,
    run_id: str,
    claim_ids: tuple[str, ...],
    claim_snapshot_id: str,
    coverage_set_id: str,
) -> tuple[str, str]:
    """新渲染或校验复用既有已提交候选站点；拒绝覆盖完成绑定。"""
    version = preview.report_version
    site_relative = f"reports/C/{version}/html"
    manifest_relative = f"reports/C/{version}/html.manifest.json"
    manifest_path = root / manifest_relative
    if not manifest_path.is_file():
        from ci_workflow.application.run_service import (
            ContractConfigError,
            RunContext,
            _render_html_c_minimal,
        )

        context = RunContext(
            project_root=root,
            contract=contract,
            report_data_path=report_data_path,
            research_lineage=lineage,
        )
        try:
            site_relative, manifest_relative = _render_html_c_minimal(
                context, run_id, report_data_path, review_candidate=True
            )
        except ContractConfigError as error:
            raise CSourceReviewEntryError(f"C 候选站点渲染失败关闭：{error}") from error
    _require_manifest_matches_inputs(
        root=root,
        manifest_relative=manifest_relative,
        site_relative=site_relative,
        contract=contract,
        preview=preview,
        evidence_snapshot_id=lineage.evidence_snapshot.snapshot_id,
        encoded_report_data=encoded_report_data,
        run_id=run_id,
        claim_ids=claim_ids,
        claim_snapshot_id=claim_snapshot_id,
        coverage_set_id=coverage_set_id,
    )
    return site_relative, manifest_relative


def _require_manifest_matches_inputs(
    *,
    root: Path,
    manifest_relative: str,
    site_relative: str,
    contract: ProjectContract,
    preview: ReportCPortalData,
    evidence_snapshot_id: str,
    encoded_report_data: bytes,
    run_id: str,
    claim_ids: tuple[str, ...],
    claim_snapshot_id: str,
    coverage_set_id: str,
) -> None:
    """复用已提交产物前的完整绑定核验：清单必须逐项绑定本轮输入。"""
    manifest_path = root / manifest_relative
    try:
        manifest = ArtifactManifest.model_validate_json(manifest_path.read_bytes())
    except (OSError, ValueError) as error:
        raise CSourceReviewEntryError("C 候选站点产物清单不可读或无效") from error
    checks = {
        "project_id": manifest.project_id == contract.project_id,
        "contract_version": manifest.contract_version == contract.contract_version,
        "report": manifest.report == "C",
        "report_version": manifest.report_version == preview.report_version,
        "data_cutoff": manifest.data_cutoff == preview.data_cutoff,
        "producer_run_id": manifest.producer_run_id == run_id,
        "evidence_snapshot_id": manifest.evidence_snapshot_id == evidence_snapshot_id,
        "claim_snapshot_id": manifest.claim_snapshot_id == claim_snapshot_id,
        "coverage_set_id": manifest.coverage_set_id == coverage_set_id,
        "claim_ids": tuple(manifest.claim_ids) == tuple(claim_ids),
        "artifact": manifest.artifact.relative_path == site_relative,
        "data_digest": any(
            check.receipt == _sha256_bytes(encoded_report_data)
            for check in manifest.deterministic_checks
        ),
        "manifest_id": manifest.manifest_id == stable_id(
            "artifact-manifest", contract.project_id, run_id, "C", preview.report_version
        ),
    }
    drifted = [name for name, valid in checks.items() if not valid]
    if drifted:
        raise CSourceReviewEntryError(
            "C 候选站点产物与当前入口输入不一致，拒绝覆盖或复用："
            + "、".join(drifted)
        )


def _require_site_bytes_match_manifest(
    *,
    root: Path,
    manifest_relative: str,
    portal_binding: PortalArtifactBinding,
) -> None:
    """当前站点字节必须与产物清单记录一致；漂移失败关闭。"""
    manifest_path = root / manifest_relative
    try:
        manifest = ArtifactManifest.model_validate_json(manifest_path.read_bytes())
    except (OSError, ValueError) as error:
        raise CSourceReviewEntryError("C 候选站点产物清单不可读或无效") from error
    if (
        portal_binding.manifest_sha256 != _sha256_bytes(manifest_path.read_bytes())
        or portal_binding.site_sha256 != manifest.artifact.sha256
        or portal_binding.site_total_bytes != max(manifest.artifact.byte_size, 1)
    ):
        raise CSourceReviewEntryError("C 候选站点字节与产物清单记录不一致")


# ─── 权威上下文与复核请求 ───────────────────────────────────────────────────


def _adopt_or_now_produced_at(
    *,
    root: Path,
    content_digest: str,
    evidence_snapshot_id: str,
    producer_session_id: str,
    explicit_produced_at: datetime | None,
    fallback: datetime,
) -> datetime:
    """同候选重放复用首次请求的生产时间；显式时间漂移失败关闭。"""
    try:
        scope = active_scientific_review_scope(root, "C")
    except ScientificReviewTransitionError as error:
        raise CSourceReviewEntryError(f"C 复核作用域解析失败关闭：{error}") from error
    request_path = root / scope.review_request_relative
    if not request_path.is_file():
        return explicit_produced_at or fallback
    try:
        raw = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CSourceReviewEntryError("既有 C 复核请求不可读或损坏") from error
    if not isinstance(raw, dict):
        raise CSourceReviewEntryError("既有 C 复核请求必须是 JSON 对象")
    try:
        production = ReviewProductionContext.model_validate(raw.get("production"))
    except (PydanticValidationError, ValueError) as error:
        raise CSourceReviewEntryError("既有 C 复核请求生产身份无效") from error
    if (
        production.candidate_content_digest != content_digest
        or production.candidate_snapshot_id != evidence_snapshot_id
    ):
        # 其他候选的活跃请求：交给既有 epoch/跨候选规则处理，不在此覆盖。
        return explicit_produced_at or fallback
    if production.producer_session_id != producer_session_id:
        raise CSourceReviewEntryError(
            "既有 C 复核请求的生产者会话与本轮不一致：拒绝混合入口"
        )
    if explicit_produced_at is not None and explicit_produced_at != production.produced_at:
        raise CSourceReviewEntryError(
            "显式 produced_at 与首次入口记录不一致：如需精确重放请省略或传入首次值"
        )
    return production.produced_at


def _build_context(
    *,
    contract: ProjectContract,
    content: FreshCResearchContent,
    facts: Sequence[ResearchFact],
    claim_snapshot_id: str,
    coverage_set_id: str,
    gate_outcome: CReportGateOutcome,
    evidence_snapshot_id: str,
    fact_version_by_ref: Mapping[str, str],
) -> ScientificQcCurrentContext:
    try:
        return build_scientific_review_context(
            project_id=contract.project_id,
            report_kind="C",
            report_version=content.report_version,
            producer_id=content.producer_id,
            candidate_snapshot_id=evidence_snapshot_id,
            candidate_content_digest=content.content_digest,
            criteria_version=gate_outcome.spec_version,
            gate_result_key=gate_outcome.review_result.result_key,
            contract_version=str(contract.contract_version),
            coverage_set_id=coverage_set_id,
            evidence_snapshot_id=evidence_snapshot_id,
            claim_snapshot_id=claim_snapshot_id,
            sources=content.sources,
            facts=facts,
            claims=content.claims,
            fact_version_by_ref=fact_version_by_ref,
        )
    except ScientificReviewTransitionError as error:
        raise CSourceReviewEntryError(f"C 权威复核上下文构建失败关闭：{error}") from error


# ─── 精确重放 ───────────────────────────────────────────────────────────────


def _validate_entry_replay(
    *,
    root: Path,
    contract: ProjectContract,
    content: FreshCResearchContent,
    content_relative: str,
    content_file_sha256: str,
    claim_ids: tuple[str, ...],
    claim_snapshot_id: str,
    run_id: str,
    report_data_path: Path,
    receipt_path: Path,
    producer_session_id: str,
    explicit_produced_at: datetime | None,
) -> None:
    """Check the first writer before idempotent preparation; never replace it."""
    try:
        receipt = CSourceReviewEntryReceipt.model_validate_json(receipt_path.read_bytes())
        portal_binding = capture_portal_artifact_binding(
            root, "C", manifest_relative=receipt.manifest_relative,
            site_relative=receipt.site_relative,
        )
        report_data_sha256 = _sha256_bytes(report_data_path.read_bytes())
    except (OSError, ValueError, ScientificReviewTransitionError) as error:
        raise CSourceReviewEntryError(f"C 来源复核入口回执或绑定无效：{error}") from error
    expected = {
        "project_id": contract.project_id,
        "content_digest": content.content_digest,
        "content_file_sha256": content_file_sha256,
        "content_relative": content_relative,
        "run_id": run_id,
        "claim_ids": claim_ids,
        "claim_snapshot_id": claim_snapshot_id,
        "producer_session_id": producer_session_id,
        "report_data_relative": report_data_path.relative_to(root).as_posix(),
        "report_data_sha256": report_data_sha256,
        "portal_binding": portal_binding,
    }
    drifted = [key for key, value in expected.items() if getattr(receipt, key) != value]
    if drifted:
        raise CSourceReviewEntryError("精确重放与首次入口记录不一致：" + "、".join(drifted))
    if explicit_produced_at is not None and explicit_produced_at != receipt.produced_at:
        raise CSourceReviewEntryError("显式 produced_at 与首次入口记录不一致")
    _, payload = _open_locked_evidence(root, receipt.evidence_snapshot_id)
    if _require_snapshot_binding(payload, contract=contract, content=content) != receipt.created_at:
        raise CSourceReviewEntryError("C 证据快照摄取时间与首次入口记录不一致")
    # All remaining receipt fields are recomputed by the common preparation path
    # and compared byte-for-byte by _write_frozen, including the actual gate.


__all__ = [
    "CSourceReviewEntryError",
    "CSourceReviewEntryOutcome",
    "CSourceReviewEntryReceipt",
    "prepare_c_source_review",
]
