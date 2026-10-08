"""C 类设计观察到门户消费者的有界登记（append-only，不发布、不接受科学）。

本模块只在既有来源事实与 C 报告行之间登记消费者关系：

- 输入是已验证证据快照、C 门户报告数据、显式行→事实版本映射、可核验来源采集
  与登记时间；不搜索、不按数值、行序或 NCT 子串推断任何身份；
- 每条报告行在整批写入前逐项证明：事实 ID/字段/试验/披露状态、锁定闭包内的
  科学语境与内容摘要、来源实例→来源版本→事实版本的闭包映射、精确 JSON 定位、
  逐字原文标量，或按现行公布的资格分段规则从父级标量重放出的准确段落；
- 请求集必须完整且一一对应；任一值、路径、产品、段落、版本、快照负例或重复/
  缺失映射使整批拒绝，预检全部通过后才 append-only 写入；
- 同一输入重复登记幂等；登记不改写来源事实版本，不提升 review_state，不渲染
  门户、不切换 current，也不构成产品身份批准或科学接受；产品身份仍是调用方
  提案，现有身份局限保持显式。

另提供只读的来源状态投影（``project_reviewed_c_source_states``）：把已经由
独立复核回执**物化**接受的来源事实状态，按精确已登记行绑定映射为新的 C 候选
报告数据；除来源 ``review_state`` 外不改任何字节，也不构成整包接受或 current。
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ci_workflow.application.ctgov_c_design_projection import (
    ELIGIBILITY_SECTION_COMPATIBILITY_RULE,
    replay_ctgov_eligibility_section,
)
from ci_workflow.application.portal_consumer_binding_recovery import (
    PortalConsumerBindingRecoveryError,
    _CPortalClosure,
    _CPortalOriginalProof,
    _entry_from_row,
    _validated_binding,
)
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_fact_acceptance import (
    SourceFactAcceptanceError,
    load_materialized_source_acceptance,
)
from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.enums import FactReviewState, ReportKind
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id
from ci_workflow.gates.models import ConflictDisposition
from ci_workflow.renderers.portal.active_fact_projection import (
    ActiveFactBinding,
    canonical_source_pointer,
)
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
)
from ci_workflow.reports.c import DesignObservation
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.snapshot_store import (
    LockedSnapshot,
    SnapshotIntegrityError,
    SnapshotStore,
)
from ci_workflow.storage.source_derivation import (
    SourceDerivationError,
    extract_locator_quote,
    verify_source_text_derivation,
)
from ci_workflow.storage.sqlite import open_database

_SECTION_FIELDS = frozenset({"inclusion_criterion", "exclusion_criterion"})
_REGISTRY_DOCUMENT_ROLE = "clinical_trial_registry"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")

__all__ = [
    "CPortalConsumerRegistrationError",
    "CPortalReviewedProjectionError",
    "project_reviewed_c_source_states",
    "register_c_source_consumers",
]


class CPortalConsumerRegistrationError(ValueError):
    """C 报告消费者未被锁定来源事实证明。"""


class CPortalReviewedProjectionError(ValueError):
    """C 已复核来源状态只读投影失败关闭：绑定、接受或快照证明不通过。"""


def _closure_index(items: object, key: str, label: str) -> dict[str, dict[str, Any]]:
    """Index one locked-closure collection, rejecting missing or duplicate identities."""
    if not isinstance(items, list) or not items:
        raise CPortalConsumerRegistrationError(f"锁定闭包缺少{label}集合")
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise CPortalConsumerRegistrationError(f"锁定闭包{label}记录无效")
        identity = item.get(key)
        if not isinstance(identity, str) or not identity or identity in index:
            raise CPortalConsumerRegistrationError(f"锁定闭包{label}存在缺失或重复版本标识")
        index[identity] = item
    return index


def _resolve_row_id(row_ref: str, rows: Mapping[str, object]) -> str | None:
    """Accept a raw C row id or the explicit ``observations:<row>`` reference form."""
    if row_ref in rows:
        return row_ref
    if row_ref.startswith("observations:"):
        candidate = row_ref.removeprefix("observations:")
        if candidate in rows:
            return candidate
    return None


def register_c_source_consumers(
    project_root: Path,
    evidence_snapshot: LockedSnapshot,
    report: ReportCPortalData,
    row_versions: Mapping[str, str],
    source_captures: Mapping[str, SourceCapture],
    *,
    registered_at: datetime,
) -> tuple[ActiveFactBinding, ...]:
    """Register explicit C report rows against their immutable source versions.

    ``row_versions`` maps a C design-observation row (raw ``row_id`` or
    ``observations:<row_id>``) to the source fact version it consumes. Each entry
    is proven against the locked evidence snapshot and persisted bytes before any
    append-only insert; wrong value/path/product/section/version/snapshot or a
    duplicate/missing mapping rejects the whole batch. Repeating the identical
    batch is idempotent. A new candidate snapshot may reuse scientific facts
    unchanged: consumers are identified by snapshot-qualified binding ids, the
    same-snapshot conflict preflight never reads another snapshot's rows, and
    already-registered rows in older snapshots keep their ids and payloads.
    Registration alone never accepts science, promotes a review state, renders a
    portal, or switches current.
    """
    if registered_at.tzinfo is None or registered_at.utcoffset() is None:
        raise CPortalConsumerRegistrationError("消费者登记时间缺少时区")
    if evidence_snapshot.kind != "evidence" or evidence_snapshot.report is not None:
        raise CPortalConsumerRegistrationError("消费者只能引用证据快照")
    if not row_versions:
        raise CPortalConsumerRegistrationError("消费者登记缺少明确 C 报告行")
    snapshot = SnapshotStore(project_root).read(evidence_snapshot)
    contract = verify_project_workspace(project_root).contract
    if (
        snapshot["project_id"] != contract.project_id
        or snapshot["contract_version"] != contract.contract_version
        or ReportKind.C not in contract.reports
        or report.indication != contract.indication
        or report.data_cutoff != contract.data_cutoff
        or report.data_cutoff != datetime.fromisoformat(str(snapshot["data_cutoff"]))
    ):
        raise CPortalConsumerRegistrationError("C 候选、来源快照与项目合同不一致")
    closure = snapshot.get("closure")
    if not isinstance(closure, dict):
        raise CPortalConsumerRegistrationError("消费者登记必须引用带锁定闭包的证据快照")
    closure_facts = _closure_index(closure.get("facts"), "fact_version_id", "事实")
    closure_sources = _closure_index(closure.get("sources"), "source_version_id", "来源版本")
    version_by_capture: dict[str, str] = {}
    for source_version_id, entry in closure_sources.items():
        capture_payload = entry.get("capture")
        if not isinstance(capture_payload, dict):
            raise CPortalConsumerRegistrationError("锁定闭包来源版本缺少采集记录")
        capture_id = capture_payload.get("source_id")
        if not isinstance(capture_id, str) or not capture_id or capture_id in version_by_capture:
            raise CPortalConsumerRegistrationError("锁定闭包存在缺失或重复来源实例")
        version_by_capture[capture_id] = source_version_id
    if (report.source_evidence_snapshot_id is not None or report.source_version_by_source_id) and (
        report.source_evidence_snapshot_id != evidence_snapshot.snapshot_id
        or dict(report.source_version_by_source_id) != version_by_capture
    ):
        raise CPortalConsumerRegistrationError("C 公开来源版本投影与锁定快照不一致")
    snapshot_fact_versions = {str(item) for item in snapshot["fact_version_ids"]}
    snapshot_source_versions = {str(item) for item in snapshot["source_version_ids"]}

    rows = {row.row_id: row for row in report.observations}
    if len(rows) != len(report.observations):
        raise CPortalConsumerRegistrationError("C 报告观察行标识不唯一")
    products = {item.id: item for item in report.products}
    trials = {item.id: item for item in report.trials}

    resolved: dict[str, str] = {}
    for row_ref, version_id in row_versions.items():
        row_id = _resolve_row_id(row_ref, rows)
        if row_id is None:
            raise CPortalConsumerRegistrationError(f"C 来源行引用不是本报告设计观察：{row_ref}")
        if row_id in resolved:
            raise CPortalConsumerRegistrationError(f"C 报告行被重复引用：{row_id}")
        if not isinstance(version_id, str) or not version_id.strip():
            raise CPortalConsumerRegistrationError(f"消费者登记缺少明确来源事实版本：{row_id}")
        resolved[row_id] = version_id
    if len(set(resolved.values())) != len(resolved):
        raise CPortalConsumerRegistrationError("同一来源事实版本不得复制为多个 C 报告行")

    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    candidates: list[tuple[str, ActiveFactBinding]] = []
    verified_captures: set[str] = set()
    with open_database(database_path) as database:
        for row_id in sorted(resolved):
            version_id = resolved[row_id]
            row = rows[row_id]
            if version_id not in snapshot_fact_versions:
                raise CPortalConsumerRegistrationError(f"来源事实版本不在锁定快照：{row_id}")
            closure_fact = closure_facts.get(version_id)
            if closure_fact is None:
                raise CPortalConsumerRegistrationError(f"来源事实版本不在锁定闭包：{row_id}")
            product = products.get(row.product_id) if row.product_id is not None else None
            trial = trials.get(row.trial_id)
            if (trial is None or trial.product_id != row.product_id
                    or (row.product_id is not None and product is None)):
                raise CPortalConsumerRegistrationError(f"报告行试验—产品身份不一致：{row_id}")
            if row.relationship_blocking:
                raise CPortalConsumerRegistrationError(
                    f"组别—干预关系未解决的观察不得登记为消费者：{row_id}"
                )
            try:
                binding = active_fact_binding_for_c(report, row_id)
            except ValueError as error:
                raise CPortalConsumerRegistrationError(
                    f"C 报告行身份不能被现行投影证明：{row_id}"
                ) from error
            persisted = database.execute(
                "SELECT v.fact_id,v.entity_id,v.field_id,v.raw_value,v.normalized_value,"
                "v.disclosure_state,v.scientific_context_json,v.primary_fragment_id,"
                "f.source_version_id,f.locator,f.content_text FROM fact_versions v "
                "JOIN evidence_fragments f ON f.fragment_id=v.primary_fragment_id "
                "WHERE v.fact_version_id=?",
                (version_id,),
            ).fetchone()
            if persisted is None:
                raise CPortalConsumerRegistrationError(f"来源事实版本未持久化：{row_id}")
            (
                fact_id,
                entity_id,
                field_id,
                _raw_value,
                _normalized_value,
                disclosure_state,
                scientific_context_json,
                fragment_id,
                source_version_id,
                locator_json,
                content_text,
            ) = persisted
            context_json_text = str(scientific_context_json)
            try:
                context = json.loads(context_json_text)
                locator = json.loads(str(locator_json))
            except json.JSONDecodeError as error:
                raise CPortalConsumerRegistrationError(
                    f"来源事实科学语境或定位不可核验：{row_id}"
                ) from error
            if not isinstance(context, dict) or not isinstance(locator, dict):
                raise CPortalConsumerRegistrationError(
                    f"来源事实科学语境或定位不是对象：{row_id}"
                )
            if (
                closure_fact.get("scientific_context_json") != context_json_text
                or closure_fact.get("primary_fragment_id") != fragment_id
                or hashlib.sha256(context_json_text.encode("utf-8")).hexdigest()
                != closure_fact.get("content_sha256")
            ):
                raise CPortalConsumerRegistrationError(f"来源事实与锁定闭包不一致：{row_id}")
            capture = source_captures.get(row.source_version_id)
            if capture is None or capture.source_id != row.source_version_id:
                raise CPortalConsumerRegistrationError(
                    f"缺少报告行来源实例的可核验采集：{row_id}"
                )
            if version_by_capture.get(row.source_version_id) != str(source_version_id):
                raise CPortalConsumerRegistrationError(
                    f"来源实例与锁定来源版本不一致：{row_id}"
                )
            if str(source_version_id) not in snapshot_source_versions:
                raise CPortalConsumerRegistrationError(f"来源版本不在锁定快照：{row_id}")
            if capture.source_id not in verified_captures:
                if capture.text_derivation is not None:
                    try:
                        verify_source_text_derivation(
                            project_root, capture.text_derivation, capture.content_text
                        )
                    except (SourceDerivationError, OSError) as error:
                        raise CPortalConsumerRegistrationError(
                            f"来源采集字节与原始资产派生回执不一致：{row_id}"
                        ) from error
                verified_captures.add(capture.source_id)
            document_role = locator.get("document_role")
            if document_role == _REGISTRY_DOCUMENT_ROLE:
                if (
                    capture.source_type != "clinical_trial_registry"
                    or capture.text_derivation is None
                ):
                    raise CPortalConsumerRegistrationError(
                        f"登记来源缺少与原始资产绑定的采集：{row_id}"
                    )
                if capture.query_or_identifier.casefold() != row.trial_id.casefold():
                    raise CPortalConsumerRegistrationError(
                        f"采集登记号与报告行试验身份不一致：{row_id}"
                    )
            try:
                parent_scalar = extract_locator_quote(
                    capture.content_text,
                    media_type=capture.media_type,
                    locator=EvidenceLocator.model_validate(locator),
                )
            except (SourceDerivationError, ValueError) as error:
                raise CPortalConsumerRegistrationError(
                    f"来源采集不能按锁定定位重提取原文：{row_id}"
                ) from error
            section_proof = row.field not in _SECTION_FIELDS
            if not section_proof:
                section_proof = row.compatibility_rule == ELIGIBILITY_SECTION_COMPATIBILITY_RULE
                if section_proof:
                    try:
                        section_proof = (
                            replay_ctgov_eligibility_section(parent_scalar, row.field)
                            == row.source_text
                        )
                    except ValueError:
                        section_proof = False
            canonical_locator = canonical_source_pointer(locator)
            checks = {
                "snapshot_fact": (
                    closure_fact.get("fact_version_id") == version_id
                    and str(fact_id) == row_id
                    and context.get("fact_id") == row_id
                ),
                "scientific_context": (
                    str(entity_id) == row.trial_id
                    and context.get("entity_id") == row.trial_id
                    and str(field_id) == f"c.{row.field_family.value}.{row.field}"
                    and context.get("field_id") == str(field_id)
                    and str(disclosure_state) == row.disclosure_state.value
                    and context.get("disclosure_state") == row.disclosure_state.value
                    and context.get("source_clause_context") == (
                        row.source_clause_context.model_dump(mode="json")
                        if row.source_clause_context is not None else None
                    )
                ),
                "trial_product_group": (
                    trial.product_id == row.product_id
                    and (row.product_id is None or product is not None
                         and product.id == row.product_id)
                    and bool(row.group_id.strip())
                    and bool(row.cohort_id.strip())
                ),
                "source_instance": (
                    context.get("source_id") == row.source_version_id
                    and binding.source_version_id == row.source_version_id
                    and version_by_capture.get(row.source_version_id) == str(source_version_id)
                ),
                "locator": (
                    canonical_source_pointer(context.get("locator")) == canonical_locator
                    and canonical_locator
                    == canonical_source_pointer(row.source_locator.model_dump(mode="json"))
                    and canonical_source_pointer(binding.source_pointer) == canonical_locator
                    and capture.url == locator.get("url")
                ),
                "quote": (
                    parent_scalar == str(content_text)
                    and context.get("original_text") == str(content_text)
                ),
                "value": (
                    context.get("normalized_value") == row.source_text
                    and context.get("raw_value") == parent_scalar
                ),
                "section": section_proof,
                "direct_scalar": (
                    row.field in _SECTION_FIELDS or row.source_text == parent_scalar
                ),
            }
            invalid = [scope for scope, valid in checks.items() if not valid]
            if invalid:
                raise CPortalConsumerRegistrationError(
                    f"C 报告行 {row_id} 与锁定来源不一致：{','.join(invalid)}"
                )
            candidates.append((version_id, binding))
        if len(candidates) != len(resolved):
            raise CPortalConsumerRegistrationError("消费者登记未覆盖全部请求行")

        # Preflight the entire requested set before writing any append-only row.
        # The conflict scope is the current evidence snapshot only: the same
        # scientific fact may already be registered under other immutable
        # snapshots, and those rows keep their own identity.
        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            existing = database.execute(
                "SELECT collection,row_id,binding_json FROM "
                "source_portal_consumer_bindings WHERE source_fact_version_id=? "
                "AND report='C' AND evidence_snapshot_id=?",
                (version_id, evidence_snapshot.snapshot_id),
            ).fetchone()
            if existing is not None and tuple(existing) != (
                binding.collection,
                binding.row_id,
                encoded,
            ):
                raise CPortalConsumerRegistrationError("已登记 C 消费者身份与当前候选冲突")
        for version_id, binding in candidates:
            encoded = binding.model_dump_json()
            database.execute(
                "INSERT OR IGNORE INTO source_portal_consumer_bindings "
                "(binding_id,source_fact_version_id,evidence_snapshot_id,report,"
                "collection,row_id,binding_json,binding_sha256,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    stable_id(
                        "source-portal-binding", version_id, "C", binding.collection,
                        binding.row_id, evidence_snapshot.snapshot_id,
                    ),
                    version_id,
                    evidence_snapshot.snapshot_id,
                    "C",
                    binding.collection,
                    binding.row_id,
                    encoded,
                    hashlib.sha256(encoded.encode()).hexdigest(),
                    registered_at.isoformat(),
                ),
            )
    return tuple(binding for _version_id, binding in candidates)


def _reopen_materialized_acceptance(
    project_root: Path,
    *,
    project_id: str,
    evidence_snapshot_id: str,
) -> frozenset[str]:
    """复用来源接受模块的唯一只读证明，不复制接受/重放判定规则。"""
    try:
        result = load_materialized_source_acceptance(
            project_root=project_root, report_kind="C", evidence_snapshot_id=evidence_snapshot_id,
        )
    except SourceFactAcceptanceError as error:
        raise CPortalReviewedProjectionError(str(error)) from error
    if result.project_id != project_id:
        raise CPortalReviewedProjectionError("接受决策与锁定快照项目不一致")
    return frozenset(result.accepted_fact_version_ids)


def _read_pinned_c_report(
    c_report_data_path: Path,
) -> tuple[ReportCPortalData, _CPortalOriginalProof]:
    """按钉固路径的原始字节一次读入并重建既有 C 原始绑定证明。"""

    try:
        encoded = c_report_data_path.read_bytes()
    except OSError as error:
        raise CPortalReviewedProjectionError("原始 C 报告数据不可读") from error
    try:
        report = ReportCPortalData.model_validate_json(encoded)
    except (PydanticValidationError, ValueError) as error:
        raise CPortalReviewedProjectionError(f"原始 C 报告数据不符合合同：{error}") from error
    try:
        proof = _CPortalOriginalProof(report, hashlib.sha256(encoded).hexdigest())
    except PortalConsumerBindingRecoveryError as error:
        raise CPortalReviewedProjectionError(str(error)) from error
    return report, proof


def _validated_projection_closure(
    closure: Mapping[str, Any],
    accepted_versions: frozenset[str],
) -> _CPortalClosure:
    """冻结闭包视图：只把已物化授权版本的 ``candidate`` 对齐为 ``accepted``。

    历史快照闭包字节不因接受决策回填（接受是新决策）；投影把闭包**视图**中
    精确位于已物化接受集合内的候选状态对齐，再交给既有完整 C 原始绑定证明
    逐项复核。任何其他状态或字段差异仍在未修改的闭包字节上失败关闭。
    """

    aligned = copy.deepcopy(dict(closure))
    raw_facts = aligned.get("facts")
    if isinstance(raw_facts, list):
        for item in raw_facts:
            if (
                isinstance(item, dict)
                and item.get("review_state") == "candidate"
                and item.get("fact_version_id") in accepted_versions
            ):
                item["review_state"] = "accepted"
    try:
        return _CPortalClosure({"closure": aligned})
    except PortalConsumerBindingRecoveryError as error:
        raise CPortalReviewedProjectionError(str(error)) from error


def project_reviewed_c_source_states(
    project_root: Path,
    evidence_snapshot: LockedSnapshot,
    c_report_data_path: Path,
) -> ReportCPortalData:
    """把已物化接受的来源事实状态投影为新的 C 候选报告数据（只读）。

    输入是项目根、精确证据快照与钉固的原始 C 报告数据路径；报告从该路径
    字节一次读入，逐行经既有 C 原始绑定证明与已登记消费者绑定核验，调用方
    不能用对象、布尔或自有摘要替代证明。接受集合只来自当前活跃独立复核
    回执**已物化**的接受决策（复用既有决策记录、幂等台账与物化核验，只读
    重开，不追加诊断事件、不物化）；未物化、决策字节与台账不一致或未完整
    物化一律失败关闭，绝不隐式接受候选原子。

    只有已登记绑定的观察行、其精确来源事实版本位于接受集合、行仍为 candidate
    且冲突已解决时，才把该行 ``review_state`` 翻为 accepted；其余取值、语境、
    冲突处置、资格、关系阻断、披露、产品身份提案与来源范围逐字节不变，未解决
    冲突行保持候选。返回值仍是待复核候选投影，不是整包独立接受、宇宙闭包、
    发布接受或已提交 current；本函数不写数据库、不追加事件、不写决策记录、
    不切换 current、不改写原始报告与任何既有站点字节。
    """

    if evidence_snapshot.kind != "evidence" or evidence_snapshot.report is not None:
        raise CPortalReviewedProjectionError("来源状态投影只能引用证据快照")
    try:
        snapshot = SnapshotStore(project_root).read(evidence_snapshot)
    except (SnapshotIntegrityError, OSError, ValueError) as error:
        raise CPortalReviewedProjectionError(f"证据快照完整性核验失败：{error}") from error
    closure = snapshot.get("closure")
    if not isinstance(closure, dict):
        raise CPortalReviewedProjectionError("来源状态投影需要带锁定闭包的证据快照")
    report, proof = _read_pinned_c_report(c_report_data_path)
    database_path = project_root / "state/project.sqlite"
    if not database_path.is_file():
        raise CPortalReviewedProjectionError("项目科学真源缺失：不能投影来源状态")
    bindings: dict[str, tuple[str, ActiveFactBinding]] = {}
    try:
        # 消费者/合同只读连接；接受证明也由唯一接受模块经独立只读连接核验。
        database = sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as error:
        raise CPortalReviewedProjectionError(f"项目科学真源不可读：{error}") from error
    try:
        contract_row = database.execute(
            "SELECT contract_json FROM project_contract_versions "
            "WHERE project_id=? AND contract_version=?",
            (snapshot["project_id"], snapshot["contract_version"]),
        ).fetchone()
        if contract_row is None:
            raise CPortalReviewedProjectionError("锁定快照的项目合同版本缺失")
        try:
            contract = ProjectContract.model_validate_json(str(contract_row[0]))
        except PydanticValidationError as error:
            raise CPortalReviewedProjectionError("锁定项目合同不可读") from error
        if (report.indication != contract.indication
            or report.data_cutoff != contract.data_cutoff
            or ReportKind.C not in contract.reports):
            raise CPortalReviewedProjectionError("报告适应症或截止日与锁定项目合同不一致")
        accepted_versions = _reopen_materialized_acceptance(
            project_root,
            project_id=str(snapshot["project_id"]),
            evidence_snapshot_id=evidence_snapshot.snapshot_id,
        )
        c_closure = _validated_projection_closure(closure, accepted_versions)
        snapshot_versions = frozenset(str(item) for item in snapshot["fact_version_ids"])
        rows: Sequence[Sequence[Any]] = database.execute(
            "SELECT binding_id,source_fact_version_id,report,collection,row_id,"
            "binding_json,binding_sha256,created_at FROM source_portal_consumer_bindings "
            "WHERE evidence_snapshot_id=? AND report='C' "
            "ORDER BY report,collection,row_id,source_fact_version_id",
            (evidence_snapshot.snapshot_id,),
        ).fetchall()
        if not rows:
            raise CPortalReviewedProjectionError("该证据快照没有已核验 C 消费者绑定可投影")
        for row in rows:
            try:
                entry = _entry_from_row(row)
                binding = _validated_binding(
                    database,
                    entry,
                    snapshot_versions,
                    evidence_snapshot_id=evidence_snapshot.snapshot_id,
                    c_proof=proof,
                    c_closure=c_closure,
                )
            except PortalConsumerBindingRecoveryError as error:
                raise CPortalReviewedProjectionError(
                    f"C 消费者绑定未通过原始报告或锁定闭包重开证明：{error}"
                ) from error
            if entry.row_id in bindings:
                # One row cannot carry two conflicting consumer declarations in
                # the same exact snapshot; first/last wins is not honest proof.
                raise CPortalReviewedProjectionError(
                    "同一证据快照存在重复的 C 消费者行声明"
                )
            bindings[entry.row_id] = (entry.source_fact_version_id, binding)
    except sqlite3.Error as error:
        raise CPortalReviewedProjectionError(f"项目科学真源读取失败：{error}") from error
    finally:
        database.close()

    projected: list[DesignObservation] = []
    for observation in report.observations:
        resolved = bindings.get(observation.row_id)
        if resolved is None or resolved[0] not in accepted_versions:
            projected.append(observation)
            continue
        if observation.review_state is not FactReviewState.CANDIDATE:
            projected.append(observation)
            continue
        if observation.conflict_disposition is ConflictDisposition.OPEN_CONFLICT_PRESERVED:
            # 未解决冲突不能成为已接受设计事实：保留候选与显式冲突处置。
            projected.append(observation)
            continue
        payload = observation.model_dump(mode="json")
        payload["review_state"] = FactReviewState.ACCEPTED.value
        try:
            projected.append(DesignObservation.model_validate(payload))
        except (PydanticValidationError, ValueError) as error:
            raise CPortalReviewedProjectionError(
                f"C 报告行 {observation.row_id} 不能持有已接受来源状态：{error}"
            ) from error
    return report.model_copy(update={"observations": tuple(projected)})
