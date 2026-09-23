"""Task 5.2 A 类只读视图投影层：AV01–AV03 与全视图共享的严格快照输入。

``pages.py`` 是锁定 A 快照到门户页面之间的只读投影层：接收 Task 5.1 已验证
的全宇宙分析、A 项目合同与 Phase 3 锁定快照，只输出不可变、可排序、可筛选
的页面数据；不改变纳排、成熟度、证据状态或报告可生成性，也不生成模板或
产物（页面模板与图形交互属于 Task 5.4）。

严格输入（AV01–AV08 全部视图共享，见 ``_assert_view_inputs_bound``）：
- 视图身份只来自 ``ApplicableUniverseSnapshot``；不接受自由产品清单后补写
  快照身份；
- 产品合同必须与快照产品清单精确一一对应：缺失、重复、多余或顺序漂移均
  失败关闭；整批分析结果必须与产品合同一一对应且顺序一致；未闭合快照
  失败关闭；
- 视图构建器不信任调用方传入的 ``UniverseAnalysisResult``：一律从当前
  projects + snapshot + ``GateEvidenceBinding`` 重新执行 ``analyze_universe``；
- 版本化扩展记录（AV04–AV08）的事实版本与来源定位必须属于当前证据快照：
  复用 ``LockedSnapshot`` / ``EvidenceSnapshotManifest`` /
  ``ScientificLineageRegistry`` 真实合同，拒绝自声明可伪造的
  ``evidence_snapshot_id``；同一业务记录换证据快照后必须失败关闭；
- 页面记录引用的事实必须已接受、绑定本产品、字段属于该记录类型的封闭
  集合，且来源定位与该事实主片段的定位精确一致；
- 证据字段缺失用显式中文状态表达（不适用/尚未公开/来源未列示/技术暂不可用），
  不用空字符串、默认数值、默认期限或推断结论填补；
- 视图模型只保存专业中文标签；后端枚举只在内部映射使用，用户可见文本
  拒绝 prompt/log/后端枚举/下划线后台标识等程序员语言（医学合理英文保留）；
- 完整视图与筛选子视图有明确不同的作用域；渲染边界必须调用
  ``assert_*_view_authoritative`` 重新验证当前项目、快照、证据清单与内容
  摘要，拒绝旧视图与手工 DTO。

本文件实现 AV01 竞争格局、AV02 产品总览、AV03 逐产品档案、AV04 临床组合、
AV05 监管分轨、AV06 企业与交易、AV07 专利与保护及 AV08 历史与边缘八类
只读投影。所有视图的产品 ID 集合必须等于锁定快照；排序只改变展示顺序，
不改变集合。AV04–AV08 的投影在同一输入边界上扩展。
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from enum import StrEnum
from functools import lru_cache
from operator import attrgetter
from typing import Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ci_workflow.capabilities.extraction_normalization import (
    VerifiedEvidenceFragment,
    revalidate_verified_fragment,
)
from ci_workflow.capabilities.lineage_registry import (
    ScientificLineageRegistry,
    compute_scientific_content_digest,
)
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.domain.enums import FactDisclosureState, FactReviewState, ReportKind
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.facts import AtomicFactVersion
from ci_workflow.gates.models import (
    ApplicableUniverseSnapshot,
    DevelopmentMaturity,
    GateEvaluationError,
    GateEvidenceBinding,
    GateObjectType,
    assert_applicable_universe_closed,
)
from ci_workflow.reports.a.analysis import (
    MaturityGateResult,
    UniverseAnalysisResult,
    analyze_universe,
)
from ci_workflow.reports.a.contracts import (
    AProjectContract,
    CoreTrialRole,
    MaturityLevel,
    RegistryResultsPostedEvidence,
    RegulatoryEventKind,
)
from ci_workflow.reports.common.evidence_view import (
    EVIDENCE_FIELD_STATE_LABELS_ZH,
    EvidenceField,
)
from ci_workflow.reports.common.page_registry import PageRegistry, PageRegistryError
from ci_workflow.storage.project_contract_store import (
    ProjectContractStore,
    ProjectContractStoreError,
)
from ci_workflow.storage.snapshot_store import (
    EvidenceSnapshotManifest,
    LockedSnapshot,
    SnapshotStore,
    compute_locked_snapshot,
)

# 与 ``page_registry._SLUG_RE`` 一致：动态详情路由只接受稳定标识 slug。
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# A 合同的地域分轨固定为中国与境外（Phase 3 区域开发双轨）。
_REGIONS_ZH: tuple[str, str] = ("中国", "境外")

# 用户可见中文标签：与 Task 5.1 阻断说明、Phase 3 词表保持一致，后端枚举
# 只在这里映射，绝不直接作为视图标签。
_MATURITY_LIFECYCLE_LABELS_ZH: dict[MaturityLevel, str] = {
    MaturityLevel.ALL_PROJECTS: "处于早期研发阶段",
    MaturityLevel.CLINICAL: "已进入临床开发阶段",
    MaturityLevel.FILING_APPROVAL_TERMINATION: "处于申报、上市或停止开发阶段",
    MaturityLevel.RESULT_BEARING: "已有临床结果公开",
}

_DEVELOPMENT_STATUS_LABELS_ZH: dict[DevelopmentMaturity, str] = {
    DevelopmentMaturity.PRECLINICAL: "临床前",
    DevelopmentMaturity.CLINICAL: "临床",
    DevelopmentMaturity.SUBMISSION: "申报",
    DevelopmentMaturity.APPROVED: "上市",
    DevelopmentMaturity.PAUSED_TERMINATED_WITHDRAWN: "停止开发",
}

_CORE_TRIAL_ROLE_LABELS_ZH: dict[CoreTrialRole, str] = {
    CoreTrialRole.REGISTRATION_OR_PIVOTAL: "注册/关键",
    CoreTrialRole.SUPPORTING: "支持性",
    CoreTrialRole.EARLY_DECISION: "决策相关早期",
}

_REGULATORY_EVENT_KIND_LABELS_ZH: dict[RegulatoryEventKind, str] = {
    RegulatoryEventKind.SUBMISSION: "申报",
    RegulatoryEventKind.APPROVAL: "批准",
    RegulatoryEventKind.WITHDRAWAL: "撤回",
    RegulatoryEventKind.TERMINATION: "终止",
    RegulatoryEventKind.ABANDONMENT: "放弃",
    RegulatoryEventKind.PAUSE: "暂停",
}


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("视图文本字段不能为空")
    return normalized


def _display_label(field: EvidenceField) -> str:
    """证据字段 → 用户可见标签：确定值原样，互斥状态用中文状态名。

    缺失永远不会表现为空字符串、默认值或推断结论。
    """
    if field.value is not None:
        return _text(field.value)
    if field.state is not None:
        return EVIDENCE_FIELD_STATE_LABELS_ZH[field.state]
    raise AssertionError("证据字段必须恰好为确定值或互斥状态之一")


# ── 用户可见文本权威：拒绝程序员/日志语言，保留医学合理英文 ────────────────

# 禁止进入用户视图的后端/日志标识（工程词）：出现即失败关闭。允许药物名、
# 靶点、机构名、登记号等医学合理英文与中文临床表达；不做"所有英文一律拒绝"
# 的粗暴规则，也不做任意子串匹配（避免误伤 aggregate 等正常词）。
_USER_FACING_BANNED_WORDS: frozenset[str] = frozenset(
    {
        "prompt",
        "log",
        "logs",
        "backend",
        "backendstate",
        "enum",
        "snapshot",
        "binding",
        "factversion",
        "evidencesnapshot",
        "researchrole",
        "rowid",
        "locator",
        "schema",
        "config",
        "strategyunit",
        "applicability",
        "predicate",
        "lineage",
        "fragment",
        "reviewstate",
        "disclosurestate",
        "disclosurematurity",
        "modelcopy",
        "copy",
        "dto",
        "payload",
        "manifest",
        "digest",
        "registry",
        "token",
        "unitid",
        "objectid",
        "fieldid",
        "entityid",
        "bindingid",
        "sourcelocation",
        "applicableconditional",
        "gate",
    }
)

# 格式/零宽控制字符类别：从用户可见文本中移除，防止隐藏拼接绕过词表。
_FORMAT_CATEGORIES: frozenset[str] = frozenset({"Cf"})
_ZERO_WIDTH_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u00ad"}


def _user_facing_compare(value: str) -> str:
    """用户可见文本的安全比较串：NFKC + 移除格式/零宽字符 + 空白折叠。

    只用于工程词检测与证据值比较；不用于展示，避免把中文全角标点改成 ASCII。
    """
    normalized = _text(value)
    nfkc = unicodedata.normalize("NFKC", normalized)
    cleaned = "".join(
        ch
        for ch in nfkc
        if unicodedata.category(ch) not in _FORMAT_CATEGORIES and ch not in _ZERO_WIDTH_CHARS
    )
    return " ".join(cleaned.split())


def _user_facing_text(value: str) -> str:
    """用户可见文本：非空规范化 + 移除格式/零宽字符 + 工程词变体拦截。

    展示保留自然中文标点（``，`` 不被 NFKC 改成 ``,``）；医学合理英文与
    原生中文正常通过；只有确属后端/日志工程词（含大小写、camel-case、
    连字符、全角、零宽变体）和含下划线的后台枚举被拒绝。``aggregate`` 等
    含 "gate" 子串的正常词不受影响（按词边界匹配）。
    """
    normalized = _text(value)
    cleaned = "".join(
        ch
        for ch in normalized
        if unicodedata.category(ch) not in _FORMAT_CATEGORIES and ch not in _ZERO_WIDTH_CHARS
    )
    if not cleaned.strip():
        raise ValueError("用户可见文本不能为空")
    compare = _user_facing_compare(cleaned)
    if "_" in compare:
        raise ValueError("用户可见文本不得包含带下划线的后台枚举")
    for whitespace_token in re.split(r"\s+", compare):
        if not whitespace_token:
            continue
        runs = re.findall(r"[0-9A-Za-z]+", whitespace_token)
        if not runs:
            continue
        collapsed = "".join(runs).lower()
        if collapsed in _USER_FACING_BANNED_WORDS:
            raise ValueError(f"用户可见文本包含程序员或日志语言标识：{whitespace_token!r}")
        # camel-case/PascalCase 拆分：BackendState → backend + state。
        parts = re.findall(r"[A-Z][a-z]*|[a-z]+", collapsed)
        if any(part in _USER_FACING_BANNED_WORDS for part in parts):
            raise ValueError(f"用户可见文本包含程序员或日志语言标识：{whitespace_token!r}")
    return " ".join(cleaned.split())


def _normalized_date(value: str) -> str:
    """监管日期：NFKC 后按 ISO 日期解析并规范输出；非法日期失败关闭。"""
    from datetime import datetime

    compare = _user_facing_compare(value)
    try:
        parsed = datetime.strptime(compare, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(f"监管日期必须是 ISO 日期，当前值无法解析：{value!r}") from error
    return parsed.isoformat()


def _display_date(field: EvidenceField) -> str:
    """监管日期显示：确定值统一为规范 ISO 日期，互斥状态用中文状态标签。"""
    if field.value is not None:
        return _normalized_date(field.value)
    if field.state is not None:
        return EVIDENCE_FIELD_STATE_LABELS_ZH[field.state]
    raise AssertionError("证据字段必须恰好为确定值或互斥状态之一")


# ── 证据快照上下文：复用真实合同，拒绝自声明可伪造的 evidence_snapshot_id ──


class AEvidenceContext(BaseModel):
    """当前证据快照的真实合同捆绑：锁定快照 + 清单 + 科学证据注册表 +
    项目合同 + 内容寻址存储。

    只由项目真源库（``SnapshotStore`` + ``EvidenceRepository`` +
    ``ScientificLineageRegistry`` + ``ProjectContractStore``）构造；页面记录
    不得自行声明 ``evidence_snapshot_id`` 冒充验真。``contract_store`` 仅作
    非权威信息保留，绝不参与信任决定——当前合同权威由公共入口外部注入的
    ``authoritative_contract_store`` 提供。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    locked: LockedSnapshot
    manifest: EvidenceSnapshotManifest
    registry: ScientificLineageRegistry
    project_contract: ProjectContract
    store: SnapshotStore
    contract_store: ProjectContractStore


def _assert_evidence_context_bound(
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
) -> None:
    """证据上下文必须与当前锁定快照、外部权威当前合同与内容寻址存储闭合。

    - 锁定快照 kind 必须是 evidence；对 ``LockedSnapshot + Manifest`` 重算
      规范 JSON/sha256/byte_size/snapshot_id/relative_path 逐项比对；
    - 从内容寻址存储重新读取锁定载荷并重验清单；
    - 科学证据内容摘要（``compute_scientific_content_digest``，覆盖每个
      VerifiedEvidenceFragment 的完整 fragment/source_version/reopened 原文
      与每条已接受事实的规范内容）必须与清单一致——同步改写来源版本内容或
      审计字段（保留全部 ID/locator）也必须失败关闭；清单缺少内容摘要时
      失败关闭（不静默补算）；
    - 当前合同权威只能来自外部注入的 ``authoritative_contract_store``：
      重载后 project_id、contract_version、data_cutoff 必须与清单及上下文
      合同完全一致——上下文内部自洽（含替换 context 内 contract_store）但
      版本/截止日被整体伪造仍必须拒绝；
    - 上下文内 ``contract_store``（非权威信息）必须与外部权威存储身份一致，
      不一致即拒绝；
    - 锁定快照 ID 必须等于适用宇宙快照的 ``evidence_snapshot_id``；manifest
      与注册表的 fact/fragment/来源版本 ID 精确一致。
    """
    if evidence.locked.kind != "evidence":
        raise GateEvaluationError("视图证据上下文必须绑定 evidence 类型锁定快照")
    try:
        recomputed = compute_locked_snapshot(
            kind="evidence",
            report=None,
            manifest=evidence.manifest.model_dump(mode="json"),
        )
    except ValidationError as error:
        raise GateEvaluationError(
            "证据清单缺失或携带非法内容摘要，权威视图必须失败关闭"
        ) from error
    if (
        recomputed.snapshot_id,
        recomputed.sha256,
        recomputed.relative_path,
        recomputed.byte_size,
    ) != (
        evidence.locked.snapshot_id,
        evidence.locked.sha256,
        evidence.locked.relative_path,
        evidence.locked.byte_size,
    ):
        raise GateEvaluationError("锁定快照身份与清单内容寻址不一致，篡改锁定元数据必须失败关闭")
    stored = evidence.store.read(evidence.locked)
    if EvidenceSnapshotManifest.model_validate(stored) != evidence.manifest:
        raise GateEvaluationError("证据清单与锁定快照存储内容不一致，必须失败关闭")
    if evidence.locked.snapshot_id != snapshot.evidence_snapshot_id:
        raise GateEvaluationError("视图证据锁定 ID 必须与适用宇宙快照证据快照一致，必须失败关闭")
    if evidence.manifest.project_id != snapshot.project_id:
        raise GateEvaluationError("证据清单项目必须与适用宇宙快照一致")
    registry_digest = compute_scientific_content_digest(evidence.registry)
    if registry_digest != evidence.manifest.scientific_content_digest:
        raise GateEvaluationError(
            "科学证据注册表内容与锁定清单内容摘要不一致，同步伪造注册表必须失败关闭"
        )
    if evidence.contract_store.project_root != authoritative_contract_store.project_root:
        raise GateEvaluationError(
            "上下文合同存储与外部权威合同存储身份不一致，必须失败关闭"
        )
    try:
        authoritative_contract = authoritative_contract_store.load_current(snapshot.project_id)
    except ProjectContractStoreError as error:
        raise GateEvaluationError("无法从外部权威合同存储读取当前项目合同，必须失败关闭") from error
    if authoritative_contract.project_id != snapshot.project_id:
        raise GateEvaluationError("权威当前合同项目必须与适用宇宙快照一致，必须失败关闭")
    if authoritative_contract.contract_version != evidence.manifest.contract_version:
        raise GateEvaluationError(
            "权威当前合同版本必须与证据清单合同版本一致，必须失败关闭"
        )
    if authoritative_contract.data_cutoff != evidence.manifest.data_cutoff:
        raise GateEvaluationError(
            "权威当前合同数据截止日必须与证据清单数据截止日一致，必须失败关闭"
        )
    if evidence.project_contract != authoritative_contract:
        raise GateEvaluationError(
            "上下文项目合同必须与权威当前合同完全一致，伪造当前合同必须失败关闭"
        )
    if evidence.project_contract.contract_version != evidence.manifest.contract_version:
        raise GateEvaluationError("项目合同版本必须与证据清单合同版本一致，必须失败关闭")
    if evidence.project_contract.data_cutoff != evidence.manifest.data_cutoff:
        raise GateEvaluationError("项目合同数据截止日必须与证据清单数据截止日一致，必须失败关闭")
    registry_fact_ids = frozenset(fact.fact_version_id for fact in evidence.registry.accepted_facts)
    if registry_fact_ids != frozenset(evidence.manifest.fact_version_ids):
        raise GateEvaluationError("证据清单事实版本必须与科学证据注册表精确一致，必须失败关闭")
    registry_fragment_ids = frozenset(
        item.fragment.fragment_id for item in evidence.registry.verified_fragments
    )
    if registry_fragment_ids != frozenset(evidence.manifest.fragment_ids):
        raise GateEvaluationError("证据清单片段必须与科学证据注册表精确一致，必须失败关闭")
    registry_source_ids = frozenset(
        item.fragment.source_version_id for item in evidence.registry.verified_fragments
    )
    if registry_source_ids != frozenset(evidence.manifest.source_version_ids):
        raise GateEvaluationError("证据清单来源版本必须与科学证据注册表精确一致，必须失败关闭")


def _render_locator(locator: EvidenceLocator) -> str:
    """证据片段定位 → 稳定可比较字符串；记录来源定位必须与此精确一致。"""
    parts = (
        locator.document_role,
        locator.field_path,
        locator.heading,
        str(locator.page) if locator.page is not None else None,
        locator.table,
        locator.row,
        locator.column,
        locator.paragraph,
        locator.url,
    )
    return "/".join(part for part in parts if part is not None)


def _assert_record_fact_bound(
    evidence: AEvidenceContext,
    *,
    project_id: str,
    fact_version_id: str,
    source_location: str,
    allowed_field_ids: frozenset[str],
    canonical_value: str,
) -> None:
    """版本化记录的事实必须与当前证据快照精确闭合。

    事实必须已接受、绑定本产品（entity_id 等于产品）、字段属于该记录类型
    的封闭集合，主片段已注册、记录来源定位与主片段定位精确一致，且记录的
    用户展示内容（按记录类型唯一、可审计的规范证据值）必须与事实原文
    精确一致；任意一条不满足均失败关闭。
    """
    accepted_by_id = {fact.fact_version_id: fact for fact in evidence.registry.accepted_facts}
    fact = accepted_by_id.get(fact_version_id)
    if fact is None:
        raise GateEvaluationError("页面记录引用未在当前证据快照接受的事实版本，必须失败关闭")
    if fact.entity_id != project_id:
        raise GateEvaluationError("页面记录事实必须绑定本产品，跨产品事实失败关闭")
    if fact.field_id not in allowed_field_ids:
        raise GateEvaluationError("页面记录事实字段不属于该记录允许的封闭集合，必须失败关闭")
    fragment = next(
        (
            item
            for item in evidence.registry.verified_fragments
            if item.fragment.fragment_id == fact.primary_fragment_id
        ),
        None,
    )
    if fragment is None:
        raise GateEvaluationError("页面记录事实的主片段未在当前证据快照注册，必须失败关闭")
    if _render_locator(fragment.fragment.locator) != _text(source_location):
        raise GateEvaluationError("页面记录来源定位必须与事实主片段定位精确一致，必须失败关闭")
    if fact.raw_value is None:
        raise GateEvaluationError("页面记录绑定的事实缺少原文，无法支撑展示值，必须失败关闭")
    fact_text = unicodedata.normalize("NFKC", _text(fact.raw_value))
    canonical_text = unicodedata.normalize("NFKC", _text(canonical_value))
    if fact_text != canonical_text:
        raise GateEvaluationError("页面记录展示内容必须与事实原文精确一致，篡改展示值必须失败关闭")


def _record_canonical(record: object) -> str:
    """每种记录类型唯一、可审计的规范证据值（字段拼接顺序固定）。

    规范值必须与绑定事实的 ``raw_value`` 精确一致（经 ``_text`` 规范化）；
    不做"包含任一词"的弱匹配。
    """
    if isinstance(record, ClinicalTrialRegionRecord):
        return f"{_display_label(record.phase)} {_display_label(record.status)} {record.region}"
    if isinstance(record, RegulatoryEventVersionRecord):
        return (
            f"{_REGULATORY_EVENT_KIND_LABELS_ZH[record.event_kind]} "
            f"{_display_date(record.event_date)} {_display_label(record.jurisdiction)}"
        )
    if isinstance(record, OrganizationRoleRecord):
        return f"{_COMPANY_ROLE_LABELS_ZH[record.role]} {record.organization_zh}"
    if isinstance(record, CompanyRelationshipRecord):
        return f"{_COMPANY_RELATIONSHIP_LABELS_ZH[record.relationship]} {record.counterparty_zh}"
    if isinstance(record, GeographicRightsRecord):
        return f"{record.region} {record.rights_zh}"
    if isinstance(record, TransactionEventRecord):
        return (
            f"{_TRANSACTION_EVENT_KIND_LABELS_ZH[record.event_kind]} "
            f"{_display_label(record.event_date)}"
        )
    if isinstance(record, PublicTermRecord):
        return record.term_zh
    if isinstance(record, PatentFamilyRecord):
        return record.family_label_zh
    if isinstance(record, PatentMemberRecord):
        return f"{record.jurisdiction} {_display_label(record.member_status)}"
    if isinstance(record, PatentScopeRecord):
        return record.scope_zh
    if isinstance(record, PatentTermRecord):
        return f"{record.term_zh} {_display_label(record.expiry)}"
    if isinstance(record, RegulatoryExclusivityRecord):
        return (
            f"{_EXCLUSIVITY_KIND_LABELS_ZH[record.exclusivity_kind]} "
            f"{record.jurisdiction} {_display_label(record.expiry)}"
        )
    if isinstance(record, HistoricalStatusRecord):
        return (
            f"{_HISTORICAL_STATUS_LABELS_ZH[record.status_kind]} "
            f"{_display_date(record.status_date)} {record.jurisdiction}"
        )
    if isinstance(record, AdjacentObservationRecord):
        return record.relation_basis_zh
    raise AssertionError(f"未知记录类型：{type(record).__name__}")


def _assert_binding_facts_registered(
    evidence: AEvidenceContext,
    bindings: Sequence[object],
    *,
    fact_version_attr: str = "fact_version_id",
) -> None:
    """已接受绑定引用的事实版本必须已注册（registry 级闭合，不做字段限制）。"""
    registered = frozenset(fact.fact_version_id for fact in evidence.registry.accepted_facts)
    for binding in bindings:
        version_id = getattr(binding, fact_version_attr)
        if version_id not in registered:
            raise GateEvaluationError("证据绑定引用未在当前证据快照注册的事实版本，必须失败关闭")


def _revalidate_records(
    records: Sequence[BaseModel], model: type[BaseModel]
) -> tuple[BaseModel, ...]:
    """扩展记录重新验证：``Type.model_validate(model_dump)`` 并返回重验证对象。

    拒绝 ``model_copy/model_construct`` 旁路伪造（含嵌套 ``EvidenceField``
    同时携带 value 与 state、地域值越界等模型校验）。
    """
    try:
        return tuple(model.model_validate(record.model_dump(mode="python")) for record in records)
    except ValidationError as error:
        raise GateEvaluationError("扩展记录重新验证失败，伪造或残缺扩展输入必须失败关闭") from error


def _assert_result_binding_matches_fact(
    binding: GateEvidenceBinding,
    fact: AtomicFactVersion,
    *,
    fragment_locator: str,
) -> None:
    """结果型绑定必须与已接受原子事实全部强类型字段及来源血统闭合。

    比较 normalized/raw 数值、unit/normalized_unit、numerator、denominator、
    arm/cohort、population、timepoint/time window；并强制：
    - ``fact.entity_id == binding.object_id``（结果事实实体是产品）；
    - ``binding.source_location`` 精确等于事实主片段 locator 的稳定渲染；
    - ``binding.source_role``、``review_state``、``disclosure_state``、
      ``disclosure_maturity`` 与已接受事实一致。
    事实缺少需要支撑的字段时失败关闭；页面摘要只在校验完全一致后消费 binding。
    """
    if fact.entity_id != binding.object_id:
        raise GateEvaluationError(
            "结果绑定对象必须与已接受事实实体一致，跨产品结果事实必须失败关闭"
        )
    if binding.source_location is None or _text(binding.source_location) != _text(
        fragment_locator
    ):
        raise GateEvaluationError(
            "结果绑定来源定位必须与事实主片段定位精确一致，伪造定位必须失败关闭"
        )
    if binding.source_role.value != fact.source_role:
        raise GateEvaluationError(
            "结果绑定来源角色必须与已接受事实来源角色一致，伪造来源角色必须失败关闭"
        )
    if binding.review_state is not fact.review_state:
        raise GateEvaluationError(
            "结果绑定审查状态必须与已接受事实审查状态一致，必须失败关闭"
        )
    if binding.disclosure_state is not fact.disclosure_state:
        raise GateEvaluationError(
            "结果绑定披露状态必须与已接受事实披露状态一致，必须失败关闭"
        )
    if binding.disclosure_maturity.value != fact.disclosure_maturity:
        raise GateEvaluationError(
            "结果绑定披露成熟度必须与已接受事实披露成熟度一致，必须失败关闭"
        )
    if binding.numeric_value is not None:
        if fact.normalized_value is None:
            raise GateEvaluationError(
                "结果绑定需要事实规范化数值支撑，事实缺少 normalized_value 必须失败关闭"
            )
        if not isinstance(fact.normalized_value, (int, float)):
            raise GateEvaluationError("事实规范化数值必须是数值类型，必须失败关闭")
        if float(fact.normalized_value) != float(binding.numeric_value):
            raise GateEvaluationError(
                "结果绑定数值必须与已接受事实规范化数值一致，伪造摘要必须失败关闭"
            )
    if binding.unit is not None:
        if fact.normalized_unit is None:
            raise GateEvaluationError(
                "结果绑定需要事实规范化单位支撑，事实缺少 normalized_unit 必须失败关闭"
            )
        if _text(fact.normalized_unit) != _text(binding.unit):
            raise GateEvaluationError(
                "结果绑定单位必须与已接受事实规范化单位一致，伪造摘要必须失败关闭"
            )
    if binding.denominator is not None:
        if fact.denominator is None:
            raise GateEvaluationError(
                "结果绑定需要事实分母支撑，事实缺少 denominator 必须失败关闭"
            )
        if fact.denominator != binding.denominator:
            raise GateEvaluationError(
                "结果绑定分母必须与已接受事实分母一致，伪造摘要必须失败关闭"
            )
    if fact.numerator is not None and (
        fact.denominator is None or fact.numerator > fact.denominator
    ):
        raise GateEvaluationError("事实分子不得大于分母，分子错配必须失败关闭")
    if binding.analysis_population is not None and _text(fact.population) != _text(
        binding.analysis_population
    ):
            raise GateEvaluationError(
                "结果绑定分析人群必须与已接受事实人群一致，伪造摘要必须失败关闭"
            )
    if binding.timepoint is not None and (
        fact.timepoint is None or _text(fact.timepoint) != _text(binding.timepoint)
    ):
            raise GateEvaluationError(
                "结果绑定时间点必须与已接受事实时间点一致，伪造摘要必须失败关闭"
            )
    if binding.time_window is not None and (
        fact.time_window is None or _text(fact.time_window) != _text(binding.time_window)
    ):
            raise GateEvaluationError(
                "结果绑定时间窗必须与已接受事实时间窗一致，伪造摘要必须失败关闭"
            )
    if binding.treatment_group is not None and (
        fact.arm_id is None or _text(fact.arm_id) != _text(binding.treatment_group)
    ):
            raise GateEvaluationError(
                "结果绑定治疗组必须与已接受事实臂标识一致，伪造摘要必须失败关闭"
            )
    if binding.control_group is not None and (
        fact.cohort_id is None or _text(fact.cohort_id) != _text(binding.control_group)
    ):
            raise GateEvaluationError(
                "结果绑定对照组必须与已接受事实队列标识一致，伪造摘要必须失败关闭"
            )


def _revalidate_inputs(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence],
) -> tuple[
    tuple[AProjectContract, ...],
    ApplicableUniverseSnapshot,
    tuple[GateEvidenceBinding, ...],
    tuple[RegistryResultsPostedEvidence, ...],
    AEvidenceContext,
]:
    """统一重新验证全部公共输入并返回重验证后的对象，拒绝旁路伪造。

    - 每个 ``AProjectContract`` 重新 ``model_validate``（拒绝 eligibility 被
      model_copy 改成 excluded 等）；
    - ``ApplicableUniverseSnapshot`` 重新 ``model_validate``（拒绝
      schema_version=9.9 等）；
    - 每条 ``GateEvidenceBinding`` 重新 ``model_validate``（拒绝 model_construct
      绕过的"未报告却带数值/零分母"等非法绑定）；
    - 每条 ``RegistryResultsPostedEvidence`` 重新 ``model_validate``；
    - 科学证据注册表逐项重验并重建：每个已验证片段重新验证（内层片段/来源
      版本重新 model_validate）、每个已接受事实重新 ``model_validate`` 且原文
      必须与其主片段原文一致、片段原文摘要重新计算；重建后的注册表返回给
      调用方使用（拒绝 ``ScientificLineageRegistry.model_copy/model_construct``
      的伪造事实成为后续消费对象）；
    - 全部绑定引用的事实版本必须已在当前 registry 接受（所有视图统一执行）。
    """
    try:
        revalidated_projects = tuple(
            AProjectContract.model_validate(project.model_dump(mode="python"))
            for project in projects
        )
        revalidated_snapshot = ApplicableUniverseSnapshot.model_validate(
            snapshot.model_dump(mode="python")
        )
        revalidated_bindings = tuple(
            GateEvidenceBinding.model_validate(binding.model_dump(mode="python"))
            for binding in bindings
        )
        revalidated_flags = tuple(
            RegistryResultsPostedEvidence.model_validate(flag.model_dump(mode="python"))
            for flag in results_posted_evidence
        )
    except ValidationError as error:
        raise GateEvaluationError("视图输入重新验证失败，伪造或残缺输入必须失败关闭") from error
    binding_ids = [binding.binding_id for binding in revalidated_bindings]
    if len(binding_ids) != len(set(binding_ids)):
        raise GateEvaluationError(
            "全部证据绑定 ID 必须全局唯一，重复绑定必须失败关闭"
        )

    registry = evidence.registry
    fragment_by_id = {
        item.fragment.fragment_id: item.fragment for item in registry.verified_fragments
    }
    revalidated_facts: list[AtomicFactVersion] = []
    for fact in registry.accepted_facts:
        revalidated_fact = AtomicFactVersion.model_validate(fact.model_dump(mode="python"))
        fragment = fragment_by_id.get(revalidated_fact.primary_fragment_id)
        if fragment is None:
            raise GateEvaluationError("已接受事实的主片段未注册，伪造注册表必须失败关闭")
        if revalidated_fact.raw_value != fragment.original_text:
            raise GateEvaluationError("已接受事实原文与其主片段原文不一致，篡改事实必须失败关闭")
        if not set(revalidated_fact.source_fragment_ids) <= set(fragment_by_id):
            raise GateEvaluationError("已接受事实引用了未注册的来源片段，必须失败关闭")
        revalidated_facts.append(revalidated_fact)
    revalidated_fragments: list[VerifiedEvidenceFragment] = []
    for item in registry.verified_fragments:
        try:
            revalidated = revalidate_verified_fragment(item)
        except ValidationError as error:
            raise GateEvaluationError(
                "证据片段重新验证失败，篡改片段必须失败关闭"
            ) from error
        record = revalidated.fragment
        digest = hashlib.sha256(record.original_text.encode("utf-8")).hexdigest()
        if digest != record.content_sha256:
            raise GateEvaluationError("证据片段原文与摘要不一致，篡改片段必须失败关闭")
        revalidated_fragments.append(revalidated)

    revalidated_registry = ScientificLineageRegistry.from_state(
        tuple(revalidated_fragments),
        tuple(revalidated_facts),
    )
    revalidated_evidence = AEvidenceContext(
        locked=evidence.locked,
        manifest=evidence.manifest,
        registry=revalidated_registry,
        project_contract=evidence.project_contract,
        store=evidence.store,
        contract_store=evidence.contract_store,
    )
    _assert_binding_facts_registered(revalidated_evidence, revalidated_bindings)
    return (
        revalidated_projects,
        revalidated_snapshot,
        revalidated_bindings,
        revalidated_flags,
        revalidated_evidence,
    )


def _assert_report_ready(
    analysis: UniverseAnalysisResult,
) -> None:
    """关键证据阻断时所有权威门户视图必须拒绝生成。

    任一产品关键证据不足（``report_ready=False``）时抛出失败关闭，不得生成
    含"尚未公开"的草稿视图；阻断说明保留在分析/日志文档层，不进入门户。
    """
    if not analysis.report_ready:
        raise GateEvaluationError(
            "存在关键证据不足的产品，A 类权威门户视图不得生成草稿，必须失败关闭"
        )


# ── 视图内容摘要：拒绝伪造/残缺 DTO ─────────────────────────────────────────


def _canonical(value: object) -> object:
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="json"))
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    return value


def _view_digest(**fields: object) -> str:
    """视图内容摘要：全部字段的规范 JSON 的 SHA-256。

    摘要由视图内容确定性生成；``model_construct`` / ``model_copy`` 或手工
    DTO 无法伪造摘要，渲染边界可用重建比对拒绝旧视图。
    """
    canonical = json.dumps(
        _canonical(fields),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _view_digest_validator(fields: Mapping[str, object]) -> None:
    """视图模型校验器：内容摘要必须等于当前内容重新计算的摘要。"""
    if fields["content_digest"] != _view_digest(
        **{key: value for key, value in fields.items() if key != "content_digest"}
    ):
        raise ValueError("视图内容摘要与当前内容不一致，拒绝伪造或残缺视图")


# ── AV04 试验分层：核心/特殊核心/支持层/其他适格，默认排除项不得进入 ──────


class ClinicalTrialLayer(StrEnum):
    """临床组合试验分层封闭集合。

    - 注册/关键：承担注册或关键决策证据的试验；
    - 特殊核心：罕见病、肿瘤或加速开发中实际承担决策证据的早期试验；
    - 支持性：支撑性试验；
    - 其他适格：经明确规则适格的其他试验层。

    未获得已接受角色证据的试验为默认排除项，不得仅凭自由记录进入组合。
    """

    CORE = "core"
    SPECIAL_CORE = "special_core"
    SUPPORTING = "supporting"
    OTHER_ELIGIBLE = "other_eligible"


_TRIAL_LAYER_LABELS_ZH: dict[ClinicalTrialLayer, str] = {
    ClinicalTrialLayer.CORE: "注册/关键",
    ClinicalTrialLayer.SPECIAL_CORE: "特殊核心",
    ClinicalTrialLayer.SUPPORTING: "支持性",
    ClinicalTrialLayer.OTHER_ELIGIBLE: "其他适格",
}

# 合同核心试验角色 → 允许分层（封闭映射）：非核心试验默认排除。
# EARLY_DECISION 只有独立事实明确支持"特殊核心"时才进入 SPECIAL_CORE，
# 不能无条件映射为"其他适格"；OTHER_ELIGIBLE 必须有单独适格规则事实。
_ALLOWED_LAYERS_BY_CONTRACT_ROLE: dict[CoreTrialRole, frozenset[ClinicalTrialLayer]] = {
    CoreTrialRole.REGISTRATION_OR_PIVOTAL: frozenset(
        {ClinicalTrialLayer.CORE, ClinicalTrialLayer.SPECIAL_CORE}
    ),
    CoreTrialRole.SUPPORTING: frozenset({ClinicalTrialLayer.SUPPORTING}),
    CoreTrialRole.EARLY_DECISION: frozenset({ClinicalTrialLayer.SPECIAL_CORE}),
}

# 试验角色/纳排事实（field_id 封闭集合）：角色事实绑定 trial_id（entity_id
# 为试验，作为明确例外），分层必须由已接受角色事实支撑，无证据默认排除。
_FIELD_STUDY_ROLE: frozenset[str] = frozenset({"study_role"})

# 已接受角色事实原文 → 分层（封闭映射）；OTHER_ELIGIBLE 需要独立适格规则
# 事实（raw_value == "其他适格"），不能从合同角色自动推出。
_TRIAL_ROLE_FACT_TO_LAYER: dict[str, ClinicalTrialLayer] = {
    "注册/关键": ClinicalTrialLayer.CORE,
    "特殊核心": ClinicalTrialLayer.SPECIAL_CORE,
    "支持性": ClinicalTrialLayer.SUPPORTING,
    "其他适格": ClinicalTrialLayer.OTHER_ELIGIBLE,
}

# 历史状态类型 ↔ 监管事件类型封闭映射：历史状态必须引用真实监管事件。
_HISTORICAL_STATUS_TO_EVENT_KIND: dict[str, RegulatoryEventKind] = {
    "suspended": RegulatoryEventKind.PAUSE,
    "terminated": RegulatoryEventKind.TERMINATION,
    "withdrawn": RegulatoryEventKind.WITHDRAWAL,
    "abandoned": RegulatoryEventKind.ABANDONMENT,
}

# 版本化记录事实字段封闭集合（CE1）：记录引用的事实字段必须属于该集合。
_FIELD_CLINICAL_TRIAL_REGION: frozenset[str] = frozenset({"clinical_trial_region"})
_FIELD_REGULATORY_EVENT: frozenset[str] = frozenset({"regulatory_event"})
_FIELD_ORGANIZATION_ROLE: frozenset[str] = frozenset({"organization_role"})
_FIELD_COMPANY_RELATIONSHIP: frozenset[str] = frozenset({"company_relationship"})
_FIELD_GEOGRAPHIC_RIGHTS: frozenset[str] = frozenset({"geographic_rights"})
_FIELD_TRANSACTION_EVENT: frozenset[str] = frozenset({"transaction_event"})
_FIELD_PUBLIC_TERM: frozenset[str] = frozenset({"public_term"})
_FIELD_PATENT_FAMILY: frozenset[str] = frozenset({"patent_family"})
_FIELD_PATENT_MEMBER: frozenset[str] = frozenset({"patent_member_status"})
_FIELD_PATENT_SCOPE: frozenset[str] = frozenset({"patent_scope"})
_FIELD_PATENT_TERM: frozenset[str] = frozenset({"patent_term_expiry"})
_FIELD_REGULATORY_EXCLUSIVITY: frozenset[str] = frozenset({"regulatory_exclusivity_expiry"})
_FIELD_HISTORICAL_STATUS: frozenset[str] = frozenset({"historical_status"})
_FIELD_ADJACENT_OBSERVATION: frozenset[str] = frozenset({"adjacent_mechanism_observation"})
_FIELD_EFFICACY: frozenset[str] = frozenset({"core_efficacy"})
_FIELD_SAFETY: frozenset[str] = frozenset({"safety_summary"})


def _identity_from_snapshot(snapshot: ApplicableUniverseSnapshot) -> AViewSnapshotIdentity:
    return AViewSnapshotIdentity(
        project_id=snapshot.project_id,
        evidence_snapshot_id=snapshot.evidence_snapshot_id,
        research_role_set_id=snapshot.research_role_set_id,
        product_ids=snapshot.product_ids,
    )


def _assert_view_inputs_bound(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    analysis: UniverseAnalysisResult,
) -> None:
    """全视图共享的严格输入边界：快照闭合、产品合同与分析一一对应。

    视图身份只来自锁定快照；产品合同缺失、重复、多余或顺序漂移失败关闭；
    整批分析结果必须与产品合同一一对应且顺序一致。不重算成熟度、纳排、
    证据状态或报告可生成性。
    """
    assert_applicable_universe_closed(snapshot)
    project_ids = tuple(project.project_id for project in projects)
    if len(project_ids) != len(set(project_ids)):
        raise GateEvaluationError("视图输入不得包含重复产品，必须失败关闭")
    if project_ids != snapshot.product_ids:
        raise GateEvaluationError("视图产品集必须与锁定快照精确一一对应且顺序一致，必须失败关闭")
    analysis_ids = tuple(result.project_id for result in analysis.projects)
    if analysis_ids != project_ids:
        raise GateEvaluationError("视图分析结果必须与产品合同一一对应且顺序一致，必须失败关闭")


@lru_cache(maxsize=1)
def _product_detail_route_template() -> str:
    """产品详情动态路由模板：来自冻结目录，不接受自由路径。"""
    registry = PageRegistry.load()
    catalog = registry.catalog(ReportKind.A)
    for spec in catalog.dynamic_routes:
        if spec.route_kind == "product_detail":
            return spec.route_template
    raise PageRegistryError("A 目录缺少产品详情动态路由")


def _product_detail_route(project_id: str) -> str:
    """稳定产品详情路由：目录模板 + 稳定标识 slug，非 slug 失败关闭。"""
    if not _SLUG_RE.fullmatch(project_id):
        raise GateEvaluationError(
            f"产品详情路由要求稳定标识 slug，当前产品标识不可路由：{project_id!r}"
        )
    return _product_detail_route_template().format(product_id=project_id)


class AViewSnapshotIdentity(BaseModel):
    """视图绑定的锁定快照身份；只由快照构造，绝不从产品清单回填。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    evidence_snapshot_id: str
    research_role_set_id: str
    product_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("project_id", "evidence_snapshot_id", "research_role_set_id")
    @classmethod
    def _identity_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _product_ids_are_unique(self) -> Self:
        if len(set(self.product_ids)) != len(self.product_ids):
            raise ValueError("视图快照产品清单不得重复")
        return self


class LandscapeProductRow(BaseModel):
    """AV01 竞争格局中一个产品的完整分组维度行。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    target_mechanism: str
    modality: str
    china_stage: str
    china_status: str
    overseas_stage: str
    overseas_status: str
    lifecycle_zh: str
    development_status_zh: str

    @field_validator("project_id")
    @classmethod
    def _identity_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("canonical_name")
    @classmethod
    def _canonical_name_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)

    @field_validator(
        "target_mechanism",
        "modality",
        "china_stage",
        "china_status",
        "overseas_stage",
        "overseas_status",
        "lifecycle_zh",
        "development_status_zh",
    )
    @classmethod
    def _dimension_label_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class LandscapeView(BaseModel):
    """AV01 竞争格局：全部产品、全部分组维度与维度目录。

    产品 ID 集合必须等于锁定快照且顺序一致；维度目录由行数据闭合生成，
    不得手写预置或按固定数量截断。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: AViewSnapshotIdentity
    products: tuple[LandscapeProductRow, ...] = Field(min_length=1)
    targets: tuple[str, ...]
    modalities: tuple[str, ...]
    stages: tuple[str, ...]
    statuses: tuple[str, ...]
    lifecycles: tuple[str, ...]
    development_statuses: tuple[str, ...]
    regions: tuple[str, ...] = _REGIONS_ZH
    content_digest: str

    @model_validator(mode="after")
    def _content_digest_matches(self) -> Self:
        _view_digest_validator(self.model_dump(mode="json"))
        return self

    @model_validator(mode="after")
    def _products_exactly_match_locked_snapshot(self) -> Self:
        ids = tuple(row.project_id for row in self.products)
        if ids != self.identity.product_ids:
            raise ValueError("竞争格局视图产品集必须等于锁定快照且顺序一致")
        return self

    @model_validator(mode="after")
    def _dimension_catalogs_are_closed(self) -> Self:
        expected_targets = tuple(sorted({row.target_mechanism for row in self.products}))
        expected_modalities = tuple(sorted({row.modality for row in self.products}))
        expected_stages = tuple(
            sorted(
                {value for row in self.products for value in (row.china_stage, row.overseas_stage)}
            )
        )
        expected_statuses = tuple(
            sorted(
                {
                    value
                    for row in self.products
                    for value in (row.china_status, row.overseas_status)
                }
            )
        )
        expected_lifecycles = tuple(sorted({row.lifecycle_zh for row in self.products}))
        expected_development_statuses = tuple(
            sorted({row.development_status_zh for row in self.products})
        )
        if (
            self.targets,
            self.modalities,
            self.stages,
            self.statuses,
            self.lifecycles,
            self.development_statuses,
            self.regions,
        ) != (
            expected_targets,
            expected_modalities,
            expected_stages,
            expected_statuses,
            expected_lifecycles,
            expected_development_statuses,
            _REGIONS_ZH,
        ):
            raise ValueError("竞争格局维度目录必须由行数据闭合生成")
        return self

    @property
    def total_products(self) -> int:
        return len(self.products)


class ProductOverviewRow(BaseModel):
    """AV02 产品总览完整事实行：全部筛选列 + 稳定详情路由。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    target_mechanism: str
    modality: str
    developer: str
    originator: str
    indication_relation: str
    china_stage: str
    china_status: str
    china_date: str
    overseas_stage: str
    overseas_status: str
    overseas_date: str
    lifecycle_zh: str
    development_status_zh: str
    route: str

    @field_validator("project_id", "route")
    @classmethod
    def _identity_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("canonical_name")
    @classmethod
    def _canonical_name_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)

    @field_validator("aliases")
    @classmethod
    def _aliases_are_unique_user_facing(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_user_facing_text(item) for item in values))

    @field_validator(
        "target_mechanism",
        "modality",
        "developer",
        "originator",
        "indication_relation",
        "china_stage",
        "china_status",
        "china_date",
        "overseas_stage",
        "overseas_status",
        "overseas_date",
        "lifecycle_zh",
        "development_status_zh",
    )
    @classmethod
    def _fact_label_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class ProductOverviewFilters(BaseModel):
    """AV02 产品总览筛选选项：全部来自锁定数据，绝不预置固定数量。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    targets: tuple[str, ...]
    modalities: tuple[str, ...]
    lifecycles: tuple[str, ...]
    development_statuses: tuple[str, ...]
    china_stages: tuple[str, ...]
    overseas_stages: tuple[str, ...]
    indication_relations: tuple[str, ...]

    @field_validator(
        "targets",
        "modalities",
        "lifecycles",
        "development_statuses",
        "china_stages",
        "overseas_stages",
        "indication_relations",
    )
    @classmethod
    def _option_catalogs_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(item) for item in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("筛选选项不得重复")
        return normalized


class ProductOverviewSortKey(StrEnum):
    """AV02 稳定排序列；只改变展示顺序，不改变产品集合。"""

    PROJECT_ID = "project_id"
    CANONICAL_NAME = "canonical_name"
    TARGET_MECHANISM = "target_mechanism"
    MODALITY = "modality"
    CHINA_STAGE = "china_stage"
    OVERSEAS_STAGE = "overseas_stage"
    LIFECYCLE = "lifecycle_zh"
    DEVELOPMENT_STATUS = "development_status_zh"


class ViewScope(StrEnum):
    """视图作用域：完整视图与筛选/排序子视图明确不同，禁止冒充。"""

    COMPLETE = "complete"
    FILTERED = "filtered"


class ProductOverviewView(BaseModel):
    """AV02 产品总览：完整可筛选事实表，无 Top-N。

    完整视图的产品集必须等于锁定快照；``filtered``/``sorted_by`` 只派生
    快照子集或重排，身份始终来自锁定快照，未知筛选值失败关闭。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: AViewSnapshotIdentity
    products: tuple[ProductOverviewRow, ...]
    filter_options: ProductOverviewFilters
    view_scope: ViewScope = ViewScope.COMPLETE
    content_digest: str

    @model_validator(mode="after")
    def _content_digest_matches(self) -> Self:
        _view_digest_validator(self.model_dump(mode="json"))
        return self

    @model_validator(mode="after")
    def _products_are_unique_locked_snapshot_subset(self) -> Self:
        ids = tuple(row.project_id for row in self.products)
        if len(ids) != len(set(ids)):
            raise ValueError("产品总览行不得重复")
        if not set(ids) <= set(self.identity.product_ids):
            raise ValueError("产品总览行必须全部属于锁定快照")
        if self.view_scope == ViewScope.COMPLETE and ids != self.identity.product_ids:
            raise ValueError("完整产品总览必须等于锁定快照且顺序一致，空或残缺视图失败关闭")
        return self

    @model_validator(mode="after")
    def _filter_options_cover_rows(self) -> Self:
        values_by_name = {
            "targets": {row.target_mechanism for row in self.products},
            "modalities": {row.modality for row in self.products},
            "lifecycles": {row.lifecycle_zh for row in self.products},
            "development_statuses": {row.development_status_zh for row in self.products},
            "china_stages": {row.china_stage for row in self.products},
            "overseas_stages": {row.overseas_stage for row in self.products},
            "indication_relations": {row.indication_relation for row in self.products},
        }
        for name, values in values_by_name.items():
            catalog = set(getattr(self.filter_options, name))
            if not values <= catalog:
                raise ValueError(f"筛选选项 {name} 必须覆盖视图内全部维度值")
        return self

    @property
    def total_products(self) -> int:
        return len(self.products)

    def filtered(
        self,
        *,
        target: str | None = None,
        modality: str | None = None,
        lifecycle_zh: str | None = None,
        development_status_zh: str | None = None,
        china_stage: str | None = None,
        overseas_stage: str | None = None,
        indication_relation: str | None = None,
    ) -> ProductOverviewView:
        """纯筛选：只接受注册维度值，未知值失败关闭；结果仍绑定锁定快照。"""
        requested = (
            ("靶点", target, self.filter_options.targets),
            ("模态", modality, self.filter_options.modalities),
            ("生命周期", lifecycle_zh, self.filter_options.lifecycles),
            ("开发状态", development_status_zh, self.filter_options.development_statuses),
            ("中国阶段", china_stage, self.filter_options.china_stages),
            ("境外阶段", overseas_stage, self.filter_options.overseas_stages),
            ("适应症关系", indication_relation, self.filter_options.indication_relations),
        )
        for label_zh, value, catalog in requested:
            if value is not None and value not in catalog:
                raise GateEvaluationError(f"产品总览筛选值不在锁定视图内：{label_zh}「{value}」")
        rows = tuple(
            row
            for row in self.products
            if (
                (target is None or row.target_mechanism == target)
                and (modality is None or row.modality == modality)
                and (lifecycle_zh is None or row.lifecycle_zh == lifecycle_zh)
                and (
                    development_status_zh is None
                    or row.development_status_zh == development_status_zh
                )
                and (china_stage is None or row.china_stage == china_stage)
                and (overseas_stage is None or row.overseas_stage == overseas_stage)
                and (indication_relation is None or row.indication_relation == indication_relation)
            )
        )
        return ProductOverviewView(
            identity=self.identity,
            products=rows,
            filter_options=self.filter_options,
            view_scope=ViewScope.FILTERED,
            content_digest=_view_digest(
                identity=self.identity,
                products=rows,
                filter_options=self.filter_options,
                view_scope=ViewScope.FILTERED,
            ),
        )

    def sorted_by(
        self, key: ProductOverviewSortKey, *, descending: bool = False
    ) -> ProductOverviewView:
        """按注册排序列稳定重排；只改变展示顺序，不改变产品集合。"""
        rows = sorted(self.products, key=attrgetter(key.value), reverse=descending)
        return ProductOverviewView(
            identity=self.identity,
            products=tuple(rows),
            filter_options=self.filter_options,
            view_scope=ViewScope.FILTERED,
            content_digest=_view_digest(
                identity=self.identity,
                products=tuple(rows),
                filter_options=self.filter_options,
                view_scope=ViewScope.FILTERED,
            ),
        )


class RegionDossier(BaseModel):
    """AV03 一个区域（中国/境外）档案：最高阶段、状态与日期。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    highest_stage: str
    highest_status: str
    date: str

    @field_validator("highest_stage", "highest_status", "date")
    @classmethod
    def _region_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class DossierCoreTrial(BaseModel):
    """AV03 档案中的一条核心试验：身份、开发角色中文标签与状态。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    role_zh: str
    status: str

    @field_validator("trial_id")
    @classmethod
    def _trial_id_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("role_zh", "status")
    @classmethod
    def _trial_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class DossierRegulatoryEvent(BaseModel):
    """AV03 档案中的一条监管事件：稳定事件 ID、类型中文标签、地域与日期。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    kind_zh: str
    jurisdiction: str
    event_date: str

    @field_validator("event_id")
    @classmethod
    def _event_id_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("kind_zh", "jurisdiction", "event_date")
    @classmethod
    def _event_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class DossierAnchorTrial(BaseModel):
    """AV03 档案中的适格锚定试验：身份与绑定的事实版本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    fact_version_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("trial_id")
    @classmethod
    def _trial_id_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("fact_version_ids")
    @classmethod
    def _fact_versions_are_text(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_text(item) for item in values)


class DossierClinicalRow(BaseModel):
    """AV03 档案中的一条临床组合行：试验—地域—阶段—状态—分层。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    region: str
    phase: str
    status: str
    layer_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("trial_id", "fact_version_id", "source_location")
    @classmethod
    def _row_identity_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("region", "phase", "status", "layer_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class DossierEfficacyRecord(BaseModel):
    """AV03 档案中的核心疗效记录：由第 5.1 步强类型绑定推导，非空解释文本。

    过渡期强类型摘要：原始定义、方向、单位、时间点、分析人群、治疗组、
    适用对照组、分母与报告值；事实版本必须已在当前证据快照注册。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    definition: str
    direction: str
    unit: str
    timepoint: str
    analysis_population: str
    treatment_group: str
    control_group: str | None
    denominator: int | None
    reported_value: str
    disclosure_label_zh: str
    fact_version_id: str

    @field_validator(
        "definition",
        "direction",
        "unit",
        "timepoint",
        "analysis_population",
        "treatment_group",
        "reported_value",
        "disclosure_label_zh",
        "fact_version_id",
    )
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("control_group")
    @classmethod
    def _optional_control_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)


class DossierSafetyRecord(BaseModel):
    """AV03 档案中的 TEAE/SAE 数值摘要：由第 5.1 步强类型绑定推导。

    事件定义、时间窗、分析人群、治疗组、适用对照组、分母与报告值；
    事实版本必须已在当前证据快照注册。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_definition: str
    time_window: str
    analysis_population: str
    treatment_group: str
    control_group: str | None
    denominator: int | None
    reported_value: str
    disclosure_label_zh: str
    fact_version_id: str

    @field_validator(
        "event_definition",
        "time_window",
        "analysis_population",
        "treatment_group",
        "reported_value",
        "disclosure_label_zh",
        "fact_version_id",
    )
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("control_group")
    @classmethod
    def _optional_control_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)


class ProductDossier(BaseModel):
    """AV03 逐产品完整档案：身份、机制、开发、临床组合、监管、组织、交易、
    专利、历史责任与疗效/安全摘要。

    完整档案在已有身份/成熟度基础上纳入：临床项目组合（试验—地域—阶段—
    状态—分层）、国内/全球监管轨道（稳定事件 ID 分轨）、企业角色/合作/
    交易/权益、专利/监管保护、历史暂停/终止/撤回/放弃状态，并保留稳定
    详情路由。疗效/安全使用第 5.1 步强类型绑定推导的摘要记录，不用空解释
    文本假装完成。证据缺失产品不删除：``blocked`` 与
    ``missing_field_labels_zh`` 保留阻断状态与缺失字段中文标签。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    aliases_absence_basis: str | None
    identity_basis: str
    target_mechanism: str
    modality: str
    developer: str
    originator: str
    indication_relation: str
    china: RegionDossier
    overseas: RegionDossier
    lifecycle_zh: str
    development_status_zh: str
    result_bearing: bool
    blocked: bool
    missing_field_labels_zh: tuple[str, ...]
    core_trials: tuple[DossierCoreTrial, ...]
    regulatory_events: tuple[DossierRegulatoryEvent, ...]
    china_regulatory_events: tuple[DossierRegulatoryEvent, ...] = ()
    overseas_regulatory_events: tuple[DossierRegulatoryEvent, ...] = ()
    anchor_trials: tuple[DossierAnchorTrial, ...]
    clinical_rows: tuple[DossierClinicalRow, ...] = ()
    organization_roles: tuple[OrganizationRoleRow, ...] = ()
    relationships: tuple[CompanyRelationshipRow, ...] = ()
    geographic_rights: tuple[GeographicRightsRow, ...] = ()
    transaction_events: tuple[TransactionEventRow, ...] = ()
    public_terms: tuple[PublicTermRow, ...] = ()
    patent_families: tuple[PatentFamilyRow, ...] = ()
    patent_members: tuple[PatentMemberRow, ...] = ()
    patent_scopes: tuple[PatentScopeRow, ...] = ()
    patent_terms: tuple[PatentTermRow, ...] = ()
    exclusivities: tuple[RegulatoryExclusivityRow, ...] = ()
    historical_statuses: tuple[HistoricalStatusRow, ...] = ()
    adjacent_observations: tuple[AdjacentObservationRow, ...] = ()
    core_efficacy_records: tuple[DossierEfficacyRecord, ...] = ()
    safety_summary_records: tuple[DossierSafetyRecord, ...] = ()
    route: str

    @field_validator("project_id", "route")
    @classmethod
    def _identity_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("canonical_name", "identity_basis")
    @classmethod
    def _identity_text_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)

    @field_validator("aliases")
    @classmethod
    def _aliases_are_unique_user_facing(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_user_facing_text(item) for item in values))

    @field_validator("aliases_absence_basis")
    @classmethod
    def _optional_alias_basis_is_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _text(value)

    @field_validator(
        "target_mechanism",
        "modality",
        "developer",
        "originator",
        "indication_relation",
        "lifecycle_zh",
        "development_status_zh",
    )
    @classmethod
    def _dossier_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)

    @field_validator("missing_field_labels_zh")
    @classmethod
    def _missing_labels_are_unique_user_facing(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(_user_facing_text(item) for item in values))

    @model_validator(mode="after")
    def _alias_contract_preserved(self) -> Self:
        if self.aliases and self.aliases_absence_basis is not None:
            raise ValueError("已有别名时不得同时携带无别名依据")
        if not self.aliases and self.aliases_absence_basis is None:
            raise ValueError("无别名档案必须保存明确的无别名检索依据")
        return self

    @model_validator(mode="after")
    def _missing_labels_only_for_blocked(self) -> Self:
        if self.missing_field_labels_zh and not self.blocked:
            raise ValueError("未阻断产品不得携带缺失字段标签")
        return self

    @model_validator(mode="after")
    def _regulatory_tracks_are_split_and_closed(self) -> Self:
        flat_ids = tuple(event.event_id for event in self.regulatory_events)
        track_ids = tuple(
            event.event_id
            for event in (*self.china_regulatory_events, *self.overseas_regulatory_events)
        )
        if flat_ids != track_ids:
            raise ValueError("档案监管轨道必须与中国/境外分轨精确一致")
        china_ids = {event.event_id for event in self.china_regulatory_events}
        overseas_ids = {event.event_id for event in self.overseas_regulatory_events}
        if china_ids & overseas_ids:
            raise ValueError("同一事件不得同时出现在中国与境外两轨")
        return self

    @model_validator(mode="after")
    def _result_bearing_dossier_carries_typed_evidence(self) -> Self:
        if self.result_bearing and not self.core_efficacy_records:
            raise ValueError("结果承载产品档案必须携带核心疗效记录，不得用空解释文本假装完成")
        if self.result_bearing and not self.safety_summary_records:
            raise ValueError("结果承载产品档案必须携带 TEAE/SAE 数值摘要，不得用空解释文本假装完成")
        return self


class ProductDossierView(BaseModel):
    """AV03 产品档案集：逐产品稳定路由与完整档案。

    档案集必须等于锁定快照且顺序一致；``dossier`` 查询未知产品失败关闭。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: AViewSnapshotIdentity
    dossiers: tuple[ProductDossier, ...] = Field(min_length=1)
    content_digest: str

    @model_validator(mode="after")
    def _content_digest_matches(self) -> Self:
        _view_digest_validator(self.model_dump(mode="json"))
        return self

    @model_validator(mode="after")
    def _dossiers_exactly_match_locked_snapshot(self) -> Self:
        ids = tuple(dossier.project_id for dossier in self.dossiers)
        if ids != self.identity.product_ids:
            raise ValueError("产品档案集必须等于锁定快照且顺序一致")
        return self

    @property
    def total_products(self) -> int:
        return len(self.dossiers)

    def dossier(self, project_id: str) -> ProductDossier:
        for dossier in self.dossiers:
            if dossier.project_id == project_id:
                return dossier
        raise KeyError(f"锁定快照内不存在产品：{project_id}")


def view_identity(snapshot: ApplicableUniverseSnapshot) -> AViewSnapshotIdentity:
    """从锁定快照派生视图身份；身份字段绝不接受自由清单回填。"""
    return _identity_from_snapshot(snapshot)


def build_landscape_view(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    *,
    authoritative_contract_store: ProjectContractStore,
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> LandscapeView:
    """AV01 竞争格局投影：全部产品 + 全部分组维度 + 维度目录。

    分析结果由当前 projects + snapshot + bindings 重新执行，不信任调用方
    传入的分析对象；证据上下文必须与当前锁定快照闭合。
    """
    projects, snapshot, bindings, results_posted_evidence, evidence = _revalidate_inputs(
        projects, snapshot, evidence, bindings, results_posted_evidence
    )
    analysis = analyze_universe(projects, snapshot, bindings, results_posted_evidence)
    _assert_report_ready(analysis)
    _assert_view_inputs_bound(projects, snapshot, analysis)
    _assert_evidence_context_bound(snapshot, evidence, authoritative_contract_store)
    gate_by_project = {result.project_id: result.gate for result in analysis.projects}
    contract_by_project = {project.project_id: project for project in projects}
    rows = tuple(
        _landscape_row(contract_by_project[project_id], gate_by_project[project_id])
        for project_id in snapshot.product_ids
    )
    fields = {
        "identity": _identity_from_snapshot(snapshot),
        "products": rows,
        "targets": tuple(sorted({row.target_mechanism for row in rows})),
        "modalities": tuple(sorted({row.modality for row in rows})),
        "stages": tuple(
            sorted({value for row in rows for value in (row.china_stage, row.overseas_stage)})
        ),
        "statuses": tuple(
            sorted({value for row in rows for value in (row.china_status, row.overseas_status)})
        ),
        "lifecycles": tuple(sorted({row.lifecycle_zh for row in rows})),
        "development_statuses": tuple(sorted({row.development_status_zh for row in rows})),
        "regions": _REGIONS_ZH,
    }
    return LandscapeView.model_validate({**fields, "content_digest": _view_digest(**fields)})


def _landscape_row(project: AProjectContract, gate: MaturityGateResult) -> LandscapeProductRow:
    return LandscapeProductRow(
        project_id=project.project_id,
        canonical_name=project.canonical_name,
        target_mechanism=_display_label(project.target_mechanism),
        modality=_display_label(project.modality),
        china_stage=_display_label(project.china.highest_stage),
        china_status=_display_label(project.china.highest_status),
        overseas_stage=_display_label(project.overseas.highest_stage),
        overseas_status=_display_label(project.overseas.highest_status),
        lifecycle_zh=_MATURITY_LIFECYCLE_LABELS_ZH[gate.maturity_level],
        development_status_zh=_DEVELOPMENT_STATUS_LABELS_ZH[gate.development_maturity],
    )


def build_product_overview_view(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    *,
    authoritative_contract_store: ProjectContractStore,
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> ProductOverviewView:
    """AV02 产品总览投影：完整可筛选事实表，无 Top-N。

    分析结果由当前 projects + snapshot + bindings 重新执行；证据上下文
    必须与当前锁定快照闭合；完整视图产品集必须等于锁定快照。
    """
    projects, snapshot, bindings, results_posted_evidence, evidence = _revalidate_inputs(
        projects, snapshot, evidence, bindings, results_posted_evidence
    )
    analysis = analyze_universe(projects, snapshot, bindings, results_posted_evidence)
    _assert_report_ready(analysis)
    _assert_view_inputs_bound(projects, snapshot, analysis)
    _assert_evidence_context_bound(snapshot, evidence, authoritative_contract_store)
    gate_by_project = {result.project_id: result.gate for result in analysis.projects}
    contract_by_project = {project.project_id: project for project in projects}
    rows = tuple(
        _overview_row(
            contract_by_project[project_id],
            gate_by_project[project_id],
            _product_detail_route(project_id),
        )
        for project_id in snapshot.product_ids
    )
    fields = {
        "identity": _identity_from_snapshot(snapshot),
        "products": rows,
        "filter_options": ProductOverviewFilters(
            targets=tuple(sorted({row.target_mechanism for row in rows})),
            modalities=tuple(sorted({row.modality for row in rows})),
            lifecycles=tuple(sorted({row.lifecycle_zh for row in rows})),
            development_statuses=tuple(sorted({row.development_status_zh for row in rows})),
            china_stages=tuple(sorted({row.china_stage for row in rows})),
            overseas_stages=tuple(sorted({row.overseas_stage for row in rows})),
            indication_relations=tuple(sorted({row.indication_relation for row in rows})),
        ),
        "view_scope": ViewScope.COMPLETE,
    }
    return ProductOverviewView.model_validate({**fields, "content_digest": _view_digest(**fields)})


def _overview_row(
    project: AProjectContract, gate: MaturityGateResult, route: str
) -> ProductOverviewRow:
    return ProductOverviewRow(
        project_id=project.project_id,
        canonical_name=project.canonical_name,
        aliases=project.aliases,
        target_mechanism=_display_label(project.target_mechanism),
        modality=_display_label(project.modality),
        developer=_display_label(project.developer),
        originator=_display_label(project.originator),
        indication_relation=_display_label(project.indication_relation),
        china_stage=_display_label(project.china.highest_stage),
        china_status=_display_label(project.china.highest_status),
        china_date=_display_label(project.china.date),
        overseas_stage=_display_label(project.overseas.highest_stage),
        overseas_status=_display_label(project.overseas.highest_status),
        overseas_date=_display_label(project.overseas.date),
        lifecycle_zh=_MATURITY_LIFECYCLE_LABELS_ZH[gate.maturity_level],
        development_status_zh=_DEVELOPMENT_STATUS_LABELS_ZH[gate.development_maturity],
        route=route,
    )


def build_product_dossier_view(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    *,
    authoritative_contract_store: ProjectContractStore,
    trial_region_records: Sequence[ClinicalTrialRegionRecord] = (),
    versioned_events: Sequence[RegulatoryEventVersionRecord] = (),
    organization_roles: Sequence[OrganizationRoleRecord] = (),
    relationships: Sequence[CompanyRelationshipRecord] = (),
    geographic_rights: Sequence[GeographicRightsRecord] = (),
    transaction_events: Sequence[TransactionEventRecord] = (),
    public_terms: Sequence[PublicTermRecord] = (),
    families: Sequence[PatentFamilyRecord] = (),
    members: Sequence[PatentMemberRecord] = (),
    scopes: Sequence[PatentScopeRecord] = (),
    terms: Sequence[PatentTermRecord] = (),
    exclusivities: Sequence[RegulatoryExclusivityRecord] = (),
    historical_statuses: Sequence[HistoricalStatusRecord] = (),
    adjacent_observations: Sequence[AdjacentObservationRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> ProductDossierView:
    """AV03 逐产品完整档案投影：身份/成熟度 + 临床组合 + 监管分轨 + 企业
    交易 + 专利保护 + 历史状态 + 疗效/安全强类型摘要 + 稳定详情路由。

    全部版本化记录与各专项视图共享同一闭合校验；疗效/安全使用第 5.1 步
    强类型绑定推导的摘要记录，不用空解释文本假装完成；档案事实必须属于
    当前证据快照。
    """
    projects, snapshot, bindings, results_posted_evidence, evidence = _revalidate_inputs(
        projects, snapshot, evidence, bindings, results_posted_evidence
    )
    analysis = analyze_universe(projects, snapshot, bindings, results_posted_evidence)
    _assert_report_ready(analysis)
    _assert_view_inputs_bound(projects, snapshot, analysis)
    _assert_evidence_context_bound(snapshot, evidence, authoritative_contract_store)
    _assert_trial_region_records_closed(projects, snapshot, evidence, trial_region_records)
    _assert_versioned_events_closed(projects, snapshot, evidence, versioned_events)
    _assert_company_records_closed(
        snapshot,
        evidence,
        organization_roles=organization_roles,
        relationships=relationships,
        geographic_rights=geographic_rights,
        transaction_events=transaction_events,
        public_terms=public_terms,
    )
    _assert_patent_records_closed(
        snapshot,
        evidence,
        families=families,
        members=members,
        scopes=scopes,
        terms=terms,
        exclusivities=exclusivities,
    )
    maturity_by_project = {
        result.project_id: result.gate.development_maturity for result in analysis.projects
    }
    _assert_history_edge_records_closed(
        projects,
        snapshot,
        evidence,
        maturity_by_project,
        historical_statuses=historical_statuses,
        adjacent_observations=adjacent_observations,
    )
    gate_by_project = {result.project_id: result.gate for result in analysis.projects}
    contract_by_project = {project.project_id: project for project in projects}

    clinical_by_project: dict[str, list[DossierClinicalRow]] = {}
    for record in trial_region_records:
        clinical_by_project.setdefault(record.project_id, []).append(
            DossierClinicalRow(
                trial_id=record.trial_id,
                region=record.region,
                phase=_display_label(record.phase),
                status=_display_label(record.status),
                layer_zh=_TRIAL_LAYER_LABELS_ZH[record.layer],
                fact_version_id=record.fact_version_id,
                source_location=record.source_location,
            )
        )

    events_by_project: dict[str, list[DossierRegulatoryEvent]] = {}
    for event_record in versioned_events:
        events_by_project.setdefault(event_record.project_id, []).append(
            DossierRegulatoryEvent(
                event_id=event_record.event_id,
                kind_zh=_REGULATORY_EVENT_KIND_LABELS_ZH[event_record.event_kind],
                jurisdiction=_display_label(event_record.jurisdiction),
                event_date=_display_date(event_record.event_date),
            )
        )

    roles_by_project: dict[str, list[OrganizationRoleRow]] = {}
    for role_record in organization_roles:
        roles_by_project.setdefault(role_record.project_id, []).append(
            OrganizationRoleRow(
                role_zh=_COMPANY_ROLE_LABELS_ZH[role_record.role],
                organization_zh=role_record.organization_zh,
                fact_version_id=role_record.fact_version_id,
                source_location=role_record.source_location,
            )
        )
    relationships_by_project: dict[str, list[CompanyRelationshipRow]] = {}
    for relationship_record in relationships:
        relationships_by_project.setdefault(relationship_record.project_id, []).append(
            CompanyRelationshipRow(
                relationship_zh=_COMPANY_RELATIONSHIP_LABELS_ZH[relationship_record.relationship],
                counterparty_zh=relationship_record.counterparty_zh,
                fact_version_id=relationship_record.fact_version_id,
                source_location=relationship_record.source_location,
            )
        )
    rights_by_project: dict[str, list[GeographicRightsRow]] = {}
    for rights_record in geographic_rights:
        rights_by_project.setdefault(rights_record.project_id, []).append(
            GeographicRightsRow(
                region=rights_record.region,
                rights_zh=rights_record.rights_zh,
                fact_version_id=rights_record.fact_version_id,
                source_location=rights_record.source_location,
            )
        )
    transactions_by_project: dict[str, list[TransactionEventRow]] = {}
    for transaction_record in transaction_events:
        transactions_by_project.setdefault(transaction_record.project_id, []).append(
            TransactionEventRow(
                event_kind_zh=_TRANSACTION_EVENT_KIND_LABELS_ZH[transaction_record.event_kind],
                event_date=_display_label(transaction_record.event_date),
                fact_version_id=transaction_record.fact_version_id,
                source_location=transaction_record.source_location,
            )
        )
    terms_by_project: dict[str, list[PublicTermRow]] = {}
    for term_record in public_terms:
        terms_by_project.setdefault(term_record.project_id, []).append(
            PublicTermRow(
                term_zh=term_record.term_zh,
                fact_version_id=term_record.fact_version_id,
                source_location=term_record.source_location,
            )
        )

    families_by_project: dict[str, list[PatentFamilyRow]] = {}
    for family_record in families:
        families_by_project.setdefault(family_record.project_id, []).append(
            PatentFamilyRow(
                family_id=family_record.family_id,
                family_label_zh=family_record.family_label_zh,
                fact_version_id=family_record.fact_version_id,
                source_location=family_record.source_location,
            )
        )
    members_by_project: dict[str, list[PatentMemberRow]] = {}
    for member_record in members:
        members_by_project.setdefault(member_record.project_id, []).append(
            PatentMemberRow(
                family_id=member_record.family_id,
                member_id=member_record.member_id,
                jurisdiction=member_record.jurisdiction,
                member_status=_display_label(member_record.member_status),
                fact_version_id=member_record.fact_version_id,
                source_location=member_record.source_location,
            )
        )
    scopes_by_project: dict[str, list[PatentScopeRow]] = {}
    for scope_record in scopes:
        scopes_by_project.setdefault(scope_record.project_id, []).append(
            PatentScopeRow(
                family_id=scope_record.family_id,
                scope_zh=scope_record.scope_zh,
                fact_version_id=scope_record.fact_version_id,
                source_location=scope_record.source_location,
            )
        )
    terms_by_member_project: dict[str, list[PatentTermRow]] = {}
    for patent_term_record in terms:
        terms_by_member_project.setdefault(patent_term_record.project_id, []).append(
            PatentTermRow(
                member_id=patent_term_record.member_id,
                term_zh=patent_term_record.term_zh,
                expiry=_display_label(patent_term_record.expiry),
                fact_version_id=patent_term_record.fact_version_id,
                source_location=patent_term_record.source_location,
            )
        )
    exclusivities_by_project: dict[str, list[RegulatoryExclusivityRow]] = {}
    for exclusivity_record in exclusivities:
        exclusivities_by_project.setdefault(exclusivity_record.project_id, []).append(
            RegulatoryExclusivityRow(
                exclusivity_kind_zh=_EXCLUSIVITY_KIND_LABELS_ZH[
                    exclusivity_record.exclusivity_kind
                ],
                jurisdiction=exclusivity_record.jurisdiction,
                expiry=_display_label(exclusivity_record.expiry),
                fact_version_id=exclusivity_record.fact_version_id,
                source_location=exclusivity_record.source_location,
            )
        )

    statuses_by_project: dict[str, list[HistoricalStatusRow]] = {}
    for status_record in historical_statuses:
        statuses_by_project.setdefault(status_record.project_id, []).append(
            HistoricalStatusRow(
                status_kind_zh=_HISTORICAL_STATUS_LABELS_ZH[status_record.status_kind],
                jurisdiction=status_record.jurisdiction,
                status_date=_display_date(status_record.status_date),
                fact_version_id=status_record.fact_version_id,
                source_location=status_record.source_location,
            )
        )
    observations_by_project: dict[str, list[AdjacentObservationRow]] = {}
    for observation_record in adjacent_observations:
        observations_by_project.setdefault(observation_record.project_id, []).append(
            AdjacentObservationRow(
                relation_basis_zh=observation_record.relation_basis_zh,
                fact_version_id=observation_record.fact_version_id,
                source_location=observation_record.source_location,
            )
        )

    field_by_version = {
        fact.fact_version_id: fact.field_id for fact in evidence.registry.accepted_facts
    }
    accepted_by_id = {fact.fact_version_id: fact for fact in evidence.registry.accepted_facts}
    fragment_by_id = {
        item.fragment.fragment_id: item.fragment for item in evidence.registry.verified_fragments
    }
    seen_result_facts: set[tuple[str, str]] = set()
    efficacy_by_project: dict[str, list[DossierEfficacyRecord]] = {}
    safety_by_project: dict[str, list[DossierSafetyRecord]] = {}
    registered = frozenset(field_by_version)
    for project_id in snapshot.product_ids:
        project = contract_by_project[project_id]
        anchor_ids = frozenset(anchor.trial_id for anchor in project.anchor_trials)
        for anchor in project.anchor_trials:
            if not set(anchor.fact_version_ids) <= registered:
                raise GateEvaluationError(
                    "适格锚定试验的证据版本未在当前证据快照注册，必须失败关闭"
                )
        for binding in bindings:
            if (
                binding.review_state is not FactReviewState.ACCEPTED
                or binding.trial_id is None
                or binding.trial_id not in anchor_ids
                or binding.object_id != project_id
            ):
                continue
            field_id = field_by_version.get(binding.fact_version_id)
            if field_id in _FIELD_EFFICACY or field_id in _FIELD_SAFETY:
                fact = accepted_by_id[binding.fact_version_id]
                fragment = fragment_by_id.get(fact.primary_fragment_id)
                if fragment is None:
                    raise GateEvaluationError(
                        "结果事实的主片段未注册，伪造结果事实必须失败关闭"
                    )
                _assert_result_binding_matches_fact(
                    binding,
                    fact,
                    fragment_locator=_render_locator(fragment.locator),
                )
                fact_key = (project_id, binding.fact_version_id)
                if fact_key in seen_result_facts:
                    raise GateEvaluationError(
                        "同一结果事实版本不得重复渲染，复制绑定必须失败关闭"
                    )
                seen_result_facts.add(fact_key)
                canonical_binding_value = (
                    f"{binding.numeric_value} {binding.unit}".strip()
                    if binding.numeric_value is not None
                    else None
                )
                if (
                    fact.raw_value is None
                    or canonical_binding_value is None
                    or unicodedata.normalize("NFKC", _text(fact.raw_value))
                    != unicodedata.normalize("NFKC", _text(canonical_binding_value))
                ):
                    raise GateEvaluationError(
                        "疗效/安全摘要的数值与单位必须与当前已接受事实原文精确一致，"
                        "伪造摘要必须失败关闭"
                    )
            if field_id in _FIELD_EFFICACY:
                efficacy_by_project.setdefault(project_id, []).append(
                    _dossier_efficacy_record(binding)
                )
            elif field_id in _FIELD_SAFETY:
                safety_by_project.setdefault(project_id, []).append(_dossier_safety_record(binding))

    dossiers = tuple(
        _product_dossier(
            contract_by_project[project_id],
            gate_by_project[project_id],
            _product_detail_route(project_id),
            clinical_rows=tuple(clinical_by_project.get(project_id, ())),
            regulatory_events=tuple(events_by_project.get(project_id, ())),
            organization_roles=tuple(roles_by_project.get(project_id, ())),
            relationships=tuple(relationships_by_project.get(project_id, ())),
            geographic_rights=tuple(rights_by_project.get(project_id, ())),
            transaction_events=tuple(transactions_by_project.get(project_id, ())),
            public_terms=tuple(terms_by_project.get(project_id, ())),
            patent_families=tuple(families_by_project.get(project_id, ())),
            patent_members=tuple(members_by_project.get(project_id, ())),
            patent_scopes=tuple(scopes_by_project.get(project_id, ())),
            patent_terms=tuple(terms_by_member_project.get(project_id, ())),
            exclusivities=tuple(exclusivities_by_project.get(project_id, ())),
            historical_statuses=tuple(statuses_by_project.get(project_id, ())),
            adjacent_observations=tuple(observations_by_project.get(project_id, ())),
            core_efficacy_records=tuple(efficacy_by_project.get(project_id, ())),
            safety_summary_records=tuple(safety_by_project.get(project_id, ())),
        )
        for project_id in snapshot.product_ids
    )
    fields = {
        "identity": _identity_from_snapshot(snapshot),
        "dossiers": dossiers,
    }
    return ProductDossierView.model_validate({**fields, "content_digest": _view_digest(**fields)})


_DISCLOSURE_LABELS_ZH: dict[FactDisclosureState, str] = {
    FactDisclosureState.REPORTED_VALUE: "已报告数值",
    FactDisclosureState.REPORTED_ZERO: "报告为零",
    FactDisclosureState.NOT_REPORTED: "未报告",
    FactDisclosureState.BELOW_REPORTING_THRESHOLD: "低于报告阈值",
    FactDisclosureState.NOT_PUBLICLY_DISCLOSED: "未公开披露",
    FactDisclosureState.NOT_APPLICABLE: "不适用",
    FactDisclosureState.CONFLICTING: "存在冲突",
    FactDisclosureState.UNRESOLVED_DUE_TO_ROUTE: "来源路线未解决",
    FactDisclosureState.USER_CLEARED: "用户清除，待重新核实",
}


def _dossier_efficacy_record(binding: GateEvidenceBinding) -> DossierEfficacyRecord:
    """一条核心疗效记录：由已接受疗效绑定推导的强类型摘要。"""
    if binding.definition is None:
        raise GateEvaluationError("疗效记录绑定缺少强类型字段：定义，不得用空解释文本填补")
    if binding.direction is None:
        raise GateEvaluationError("疗效记录绑定缺少强类型字段：方向，不得用空解释文本填补")
    if binding.unit is None:
        raise GateEvaluationError("疗效记录绑定缺少强类型字段：单位，不得用空解释文本填补")
    if binding.timepoint is None:
        raise GateEvaluationError("疗效记录绑定缺少强类型字段：时间点，不得用空解释文本填补")
    if binding.analysis_population is None:
        raise GateEvaluationError("疗效记录绑定缺少强类型字段：分析人群，不得用空解释文本填补")
    if binding.treatment_group is None:
        raise GateEvaluationError("疗效记录绑定缺少强类型字段：治疗组，不得用空解释文本填补")
    reported = (
        f"{binding.numeric_value} {binding.unit}".strip()
        if binding.numeric_value is not None
        else _DISCLOSURE_LABELS_ZH[binding.disclosure_state]
    )
    return DossierEfficacyRecord(
        definition=binding.definition,
        direction=binding.direction,
        unit=binding.unit,
        timepoint=binding.timepoint,
        analysis_population=binding.analysis_population,
        treatment_group=binding.treatment_group,
        control_group=None if binding.control_group is None else _text(binding.control_group),
        denominator=binding.denominator,
        reported_value=reported,
        disclosure_label_zh=_DISCLOSURE_LABELS_ZH[binding.disclosure_state],
        fact_version_id=binding.fact_version_id,
    )


def _dossier_safety_record(binding: GateEvidenceBinding) -> DossierSafetyRecord:
    """一条 TEAE/SAE 数值摘要：由已接受安全绑定推导的强类型摘要。"""
    if binding.event_definition is None:
        raise GateEvaluationError("安全摘要绑定缺少强类型字段：事件定义，不得用空解释文本填补")
    if binding.time_window is None:
        raise GateEvaluationError("安全摘要绑定缺少强类型字段：时间窗，不得用空解释文本填补")
    if binding.analysis_population is None:
        raise GateEvaluationError("安全摘要绑定缺少强类型字段：分析人群，不得用空解释文本填补")
    if binding.treatment_group is None:
        raise GateEvaluationError("安全摘要绑定缺少强类型字段：治疗组，不得用空解释文本填补")
    reported = (
        f"{binding.numeric_value} {binding.unit}".strip()
        if binding.numeric_value is not None
        else _DISCLOSURE_LABELS_ZH[binding.disclosure_state]
    )
    return DossierSafetyRecord(
        event_definition=binding.event_definition,
        time_window=binding.time_window,
        analysis_population=binding.analysis_population,
        treatment_group=binding.treatment_group,
        control_group=None if binding.control_group is None else _text(binding.control_group),
        denominator=binding.denominator,
        reported_value=reported,
        disclosure_label_zh=_DISCLOSURE_LABELS_ZH[binding.disclosure_state],
        fact_version_id=binding.fact_version_id,
    )


def _product_dossier(
    project: AProjectContract,
    gate: MaturityGateResult,
    route: str,
    *,
    clinical_rows: tuple[DossierClinicalRow, ...],
    regulatory_events: tuple[DossierRegulatoryEvent, ...],
    organization_roles: tuple[OrganizationRoleRow, ...],
    relationships: tuple[CompanyRelationshipRow, ...],
    geographic_rights: tuple[GeographicRightsRow, ...],
    transaction_events: tuple[TransactionEventRow, ...],
    public_terms: tuple[PublicTermRow, ...],
    patent_families: tuple[PatentFamilyRow, ...],
    patent_members: tuple[PatentMemberRow, ...],
    patent_scopes: tuple[PatentScopeRow, ...],
    patent_terms: tuple[PatentTermRow, ...],
    exclusivities: tuple[RegulatoryExclusivityRow, ...],
    historical_statuses: tuple[HistoricalStatusRow, ...],
    adjacent_observations: tuple[AdjacentObservationRow, ...],
    core_efficacy_records: tuple[DossierEfficacyRecord, ...],
    safety_summary_records: tuple[DossierSafetyRecord, ...],
) -> ProductDossier:
    china_events = tuple(event for event in regulatory_events if event.jurisdiction == "中国")
    overseas_events = tuple(event for event in regulatory_events if event.jurisdiction == "境外")
    return ProductDossier(
        project_id=project.project_id,
        canonical_name=project.canonical_name,
        aliases=project.aliases,
        aliases_absence_basis=project.aliases_absence_basis,
        identity_basis=project.identity_basis,
        target_mechanism=_display_label(project.target_mechanism),
        modality=_display_label(project.modality),
        developer=_display_label(project.developer),
        originator=_display_label(project.originator),
        indication_relation=_display_label(project.indication_relation),
        china=RegionDossier(
            highest_stage=_display_label(project.china.highest_stage),
            highest_status=_display_label(project.china.highest_status),
            date=_display_label(project.china.date),
        ),
        overseas=RegionDossier(
            highest_stage=_display_label(project.overseas.highest_stage),
            highest_status=_display_label(project.overseas.highest_status),
            date=_display_label(project.overseas.date),
        ),
        lifecycle_zh=_MATURITY_LIFECYCLE_LABELS_ZH[gate.maturity_level],
        development_status_zh=_DEVELOPMENT_STATUS_LABELS_ZH[gate.development_maturity],
        result_bearing=gate.result_bearing,
        blocked=gate.blocked,
        missing_field_labels_zh=tuple(outcome.label_zh for outcome in gate.missing_fields),
        core_trials=tuple(
            DossierCoreTrial(
                trial_id=record.trial_id,
                role_zh=_CORE_TRIAL_ROLE_LABELS_ZH[record.role],
                status=record.status,
            )
            for record in project.core_trials
        ),
        regulatory_events=regulatory_events,
        china_regulatory_events=china_events,
        overseas_regulatory_events=overseas_events,
        anchor_trials=tuple(
            DossierAnchorTrial(
                trial_id=anchor.trial_id,
                fact_version_ids=anchor.fact_version_ids,
            )
            for anchor in project.anchor_trials
        ),
        clinical_rows=clinical_rows,
        organization_roles=organization_roles,
        relationships=relationships,
        geographic_rights=geographic_rights,
        transaction_events=transaction_events,
        public_terms=public_terms,
        patent_families=patent_families,
        patent_members=patent_members,
        patent_scopes=patent_scopes,
        patent_terms=patent_terms,
        exclusivities=exclusivities,
        historical_statuses=historical_statuses,
        adjacent_observations=adjacent_observations,
        core_efficacy_records=core_efficacy_records,
        safety_summary_records=safety_summary_records,
        route=route,
    )


# ── AV04 临床组合：产品—试验—地域—阶段—状态与核心角色 ──────────────────────


class ClinicalTrialRegionRecord(BaseModel):
    """AV04 版本化扩展记录：一个产品—试验—地域组合的阶段、状态与分层。

    必须绑定产品、试验、不可变事实版本与精确来源定位；未知产品/试验、
    跨产品引用、同组合重复均失败关闭（由构建器校验）。分层必须属于封闭
    集合且由合同核心试验角色的已接受证据支撑；非核心试验为默认排除项，
    不得仅凭自由记录进入临床组合。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    trial_id: str
    region: str
    phase: EvidenceField
    status: EvidenceField
    layer: ClinicalTrialLayer
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "trial_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("region")
    @classmethod
    def _region_is_a_track(cls, value: str) -> str:
        normalized = _text(value)
        if normalized not in _REGIONS_ZH:
            raise ValueError("临床组合地域必须是锁定分轨：中国或境外")
        return normalized


class ClinicalPortfolioTrialRow(BaseModel):
    """AV04 临床组合中的一条产品—试验—地域行。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    trial_id: str
    region: str
    phase: str
    status: str
    layer_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("trial_id", "fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("region", "phase", "status", "layer_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class ClinicalPortfolioProduct(BaseModel):
    """AV04 一个产品的临床组合：身份与产品—试验—地域行。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    trial_rows: tuple[ClinicalPortfolioTrialRow, ...] = ()

    @field_validator("project_id", "canonical_name")
    @classmethod
    def _identity_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _trial_rows_are_unique_per_region(self) -> Self:
        keys = tuple((row.trial_id, row.region) for row in self.trial_rows)
        if len(set(keys)) != len(keys):
            raise ValueError("临床组合行不得重复同一试验—地域组合")
        return self


class ClinicalPortfolioView(BaseModel):
    """AV04 临床组合：全部产品、产品—试验—地域—阶段—状态与核心角色。

    产品 ID 集合必须等于锁定快照且顺序一致；无试验产品保留显式空组合，
    不删除、不失败。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: AViewSnapshotIdentity
    products: tuple[ClinicalPortfolioProduct, ...] = Field(min_length=1)
    content_digest: str

    @model_validator(mode="after")
    def _content_digest_matches(self) -> Self:
        _view_digest_validator(self.model_dump(mode="json"))
        return self

    @model_validator(mode="after")
    def _products_exactly_match_locked_snapshot(self) -> Self:
        ids = tuple(product.project_id for product in self.products)
        if ids != self.identity.product_ids:
            raise ValueError("临床组合产品集必须等于锁定快照且顺序一致")
        return self

    @property
    def total_products(self) -> int:
        return len(self.products)

    def product(self, project_id: str) -> ClinicalPortfolioProduct:
        for product in self.products:
            if product.project_id == project_id:
                return product
        raise KeyError(f"锁定快照内不存在产品：{project_id}")


def _trial_product_map(snapshot: ApplicableUniverseSnapshot) -> dict[str, str]:
    """快照关系图：试验 → 所属产品；产品→试验边由快照闭合保证。"""
    return {
        edge.child_id: edge.parent_id
        for edge in snapshot.relationship_edges
        if edge.parent_type is GateObjectType.PRODUCT and edge.child_type is GateObjectType.TRIAL
    }


def _assert_fact_coverage(
    evidence: AEvidenceContext,
    *,
    field_ids: frozenset[str],
    entity_ids: frozenset[str],
    consumed_fact_ids: set[str],
    type_label_zh: str,
) -> None:
    """当前证据快照中属于指定封闭字段、实体在作用域内的事实，必须全部且
    仅由相应记录消费：漏一条、重复一条均失败关闭。"""
    expected = {
        fact.fact_version_id
        for fact in evidence.registry.accepted_facts
        if fact.field_id in field_ids and fact.entity_id in entity_ids
    }
    if consumed_fact_ids != expected:
        raise GateEvaluationError(
            f"{type_label_zh}记录必须完整消费当前证据快照中的事实，漏一条或多余一条均失败关闭"
        )


def _assert_trial_region_records_closed(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    records: Sequence[ClinicalTrialRegionRecord],
) -> None:
    """临床组合记录必须与锁定快照闭合：全部产品→试验边被记录且仅被记录一次。

    未知产品、未知试验、跨产品引用、同组合重复失败关闭；记录分层必须
    由已接受的试验角色/纳排事实（field_id 封闭 study_role、绑定 trial_id）
    支撑，无证据默认排除；EARLY_DECISION 只有独立事实明确支持"特殊核心"
    时才进入 SPECIAL_CORE，OTHER_ELIGIBLE 必须有单独适格规则事实；
    记录事实必须绑定当前证据快照（封闭字段、定位、展示值精确一致）；
    同一事实版本不得支撑多个记录；当前证据快照中临床组合与试验角色事实
    必须全部被消费。
    """
    trial_product = _trial_product_map(snapshot)
    contract_role_by_trial: dict[str, CoreTrialRole] = {}
    for project in projects:
        for trial in project.core_trials:
            contract_role_by_trial[trial.trial_id] = trial.role

    revalidated = _revalidate_records(records, ClinicalTrialRegionRecord)
    records = tuple(cast(ClinicalTrialRegionRecord, item) for item in revalidated)

    accepted_by_id = {fact.fact_version_id: fact for fact in evidence.registry.accepted_facts}
    study_role_by_trial: dict[str, AtomicFactVersion] = {}
    for fact in evidence.registry.accepted_facts:
        if fact.field_id in _FIELD_STUDY_ROLE:
            study_role_by_trial[fact.entity_id] = fact

    seen: set[tuple[str, str, str]] = set()
    seen_fact_versions: set[str] = set()
    covered: set[tuple[str, str]] = set()
    consumed_fact_ids: set[str] = set()
    for record in records:
        if record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("临床组合记录引用未知产品，必须失败关闭")
        if record.trial_id not in snapshot.trial_ids:
            raise GateEvaluationError("临床组合记录引用未知试验对象，必须失败关闭")
        if trial_product.get(record.trial_id) != record.project_id:
            raise GateEvaluationError("临床组合记录引用其他产品的试验，必须失败关闭")
        contract_role = contract_role_by_trial.get(record.trial_id)
        if contract_role is None:
            raise GateEvaluationError(
                "非核心试验缺少已接受角色证据，默认排除，不得仅凭自由记录进入临床组合"
            )
        study_role_fact = study_role_by_trial.get(record.trial_id)
        if study_role_fact is None:
            raise GateEvaluationError(
                "临床组合记录缺少已接受的试验角色事实，默认排除，必须失败关闭"
            )
        if study_role_fact.raw_value not in _TRIAL_ROLE_FACT_TO_LAYER:
            raise GateEvaluationError("试验角色事实原文必须属于封闭角色词表，必须失败关闭")
        if _TRIAL_ROLE_FACT_TO_LAYER[study_role_fact.raw_value] is not record.layer:
            raise GateEvaluationError("临床组合记录分层必须与已接受试验角色事实一致，必须失败关闭")
        if record.layer is ClinicalTrialLayer.OTHER_ELIGIBLE:
            if study_role_fact.raw_value != "其他适格":
                raise GateEvaluationError(
                    "其他适格分层必须有单独适格规则事实，不能从合同角色自动推出"
                )
        elif record.layer not in _ALLOWED_LAYERS_BY_CONTRACT_ROLE[contract_role]:
            raise GateEvaluationError(
                "临床组合记录分层必须与产品合同核心试验角色一致，必须失败关闭"
            )
        _assert_record_fact_bound(
            evidence,
            project_id=record.project_id,
            fact_version_id=record.fact_version_id,
            source_location=record.source_location,
            allowed_field_ids=_FIELD_CLINICAL_TRIAL_REGION,
            canonical_value=_record_canonical(record),
        )
        fact = accepted_by_id[record.fact_version_id]
        if fact.fact_version_id in seen_fact_versions:
            raise GateEvaluationError("同一事实版本不得支撑多个临床组合记录，必须失败关闭")
        seen_fact_versions.add(fact.fact_version_id)
        consumed_fact_ids.add(record.fact_version_id)
        key = (record.project_id, record.trial_id, record.region)
        if key in seen:
            raise GateEvaluationError("临床组合记录不得重复同一产品—试验—地域组合，必须失败关闭")
        seen.add(key)
        covered.add((record.project_id, record.trial_id))

    expected = {(product, trial) for trial, product in trial_product.items()}
    if covered != expected:
        raise GateEvaluationError(
            "临床组合必须覆盖锁定快照内全部产品—试验关系，缺失或多余均失败关闭"
        )
    consumed_fact_ids.update(fact.fact_version_id for fact in study_role_by_trial.values())
    _assert_fact_coverage(
        evidence,
        field_ids=_FIELD_CLINICAL_TRIAL_REGION | _FIELD_STUDY_ROLE,
        entity_ids=frozenset(snapshot.product_ids) | frozenset(snapshot.trial_ids),
        consumed_fact_ids=consumed_fact_ids,
        type_label_zh="临床组合",
    )


def build_clinical_portfolio_view(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    trial_region_records: Sequence[ClinicalTrialRegionRecord] = (),
    *,
    authoritative_contract_store: ProjectContractStore,
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> ClinicalPortfolioView:
    """AV04 临床组合投影：全部产品 + 产品—试验—地域—阶段—状态—分层。

    记录必须与锁定快照闭合（全部产品→试验边恰好覆盖一次）；非核心试验
    默认排除；记录事实必须属于当前证据快照；无试验产品保留显式空组合。
    """
    projects, snapshot, bindings, results_posted_evidence, evidence = _revalidate_inputs(
        projects, snapshot, evidence, bindings, results_posted_evidence
    )
    analysis = analyze_universe(projects, snapshot, bindings, results_posted_evidence)
    _assert_report_ready(analysis)
    _assert_view_inputs_bound(projects, snapshot, analysis)
    _assert_evidence_context_bound(snapshot, evidence, authoritative_contract_store)
    _assert_trial_region_records_closed(projects, snapshot, evidence, trial_region_records)
    contract_by_project = {project.project_id: project for project in projects}
    rows_by_project: dict[str, list[ClinicalPortfolioTrialRow]] = {}
    for record in trial_region_records:
        rows_by_project.setdefault(record.project_id, []).append(
            ClinicalPortfolioTrialRow(
                trial_id=record.trial_id,
                region=record.region,
                phase=_display_label(record.phase),
                status=_display_label(record.status),
                layer_zh=_TRIAL_LAYER_LABELS_ZH[record.layer],
                fact_version_id=record.fact_version_id,
                source_location=record.source_location,
            )
        )
    products = tuple(
        ClinicalPortfolioProduct(
            project_id=project_id,
            canonical_name=contract_by_project[project_id].canonical_name,
            trial_rows=tuple(rows_by_project.get(project_id, ())),
        )
        for project_id in snapshot.product_ids
    )
    return ClinicalPortfolioView(
        identity=_identity_from_snapshot(snapshot),
        products=products,
        content_digest=_view_digest(
            identity=_identity_from_snapshot(snapshot),
            products=products,
        ),
    )


# ── AV05 中国/境外监管分轨：事件与版本血统 ──────────────────────────────────


class RegulatoryEventVersionRecord(BaseModel):
    """AV05 版本化扩展记录：一个监管事件（事件 ID、类型、地域、日期、版本、定位）。

    必须与产品合同监管事件按稳定不可变 ``event_id`` 精确一一对应；不得用
    「事件类型+司法辖区+日期」的计数配对冒充事件身份；地域必须解析为
    中国/境外确定值，无法分轨失败关闭。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    event_id: str
    event_kind: RegulatoryEventKind
    jurisdiction: EvidenceField
    event_date: EvidenceField
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "event_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _jurisdiction_resolves_to_a_track(self) -> Self:
        if self.jurisdiction.value not in _REGIONS_ZH:
            raise ValueError("监管事件地域必须解析为中国/境外确定值才能分轨")
        return self


class RegulatoryEventRow(BaseModel):
    """AV05 一条监管事件行：稳定事件 ID、类型中文标签、日期与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    kind_zh: str
    event_date: str
    fact_version_id: str
    source_location: str

    @field_validator("event_id", "fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("kind_zh", "event_date")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class RegulatoryProductTracks(BaseModel):
    """AV05 一个产品的监管分轨：中国事件与境外事件分别保留。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    china_events: tuple[RegulatoryEventRow, ...] = ()
    overseas_events: tuple[RegulatoryEventRow, ...] = ()

    @field_validator("project_id", "canonical_name")
    @classmethod
    def _identity_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _tracks_are_separate(self) -> Self:
        if self.china_events and self.overseas_events:
            china_keys = {
                (row.kind_zh, row.event_date, row.fact_version_id) for row in self.china_events
            }
            overseas_keys = {
                (row.kind_zh, row.event_date, row.fact_version_id) for row in self.overseas_events
            }
            if china_keys & overseas_keys:
                raise ValueError("同一事件不得同时出现在中国与境外两轨")
        return self


class RegulatoryView(BaseModel):
    """AV05 监管视图：全部产品、中国/境外分轨、事件与版本血统。

    产品 ID 集合必须等于锁定快照且顺序一致；无监管事件产品保留显式空轨，
    不删除、不失败。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: AViewSnapshotIdentity
    products: tuple[RegulatoryProductTracks, ...] = Field(min_length=1)
    content_digest: str

    @model_validator(mode="after")
    def _content_digest_matches(self) -> Self:
        _view_digest_validator(self.model_dump(mode="json"))
        return self

    @model_validator(mode="after")
    def _products_exactly_match_locked_snapshot(self) -> Self:
        ids = tuple(product.project_id for product in self.products)
        if ids != self.identity.product_ids:
            raise ValueError("监管视图产品集必须等于锁定快照且顺序一致")
        return self

    @property
    def total_products(self) -> int:
        return len(self.products)

    def product(self, project_id: str) -> RegulatoryProductTracks:
        for product in self.products:
            if product.project_id == project_id:
                return product
        raise KeyError(f"锁定快照内不存在产品：{project_id}")


def _assert_versioned_events_closed(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    records: Sequence[RegulatoryEventVersionRecord],
) -> None:
    """版本化事件必须按稳定 ``event_id`` 与产品合同监管事件精确一一对应。

    未知产品、重复事件 ID、记录事件身份与合同事件字段（类型/地域/日期）
    不一致、合同事件缺少版本化记录或记录超出合同均失败关闭；不同监管
    ``event_id`` 不得复用同一事实版本；记录事实必须绑定当前证据快照
    （监管事件封闭字段、定位、展示值精确一致）；当前证据快照中监管事件
    事实必须全部被消费。
    """
    contract_by_project = {project.project_id: project for project in projects}
    revalidated = _revalidate_records(records, RegulatoryEventVersionRecord)
    records = tuple(cast(RegulatoryEventVersionRecord, item) for item in revalidated)
    record_by_project: dict[str, list[RegulatoryEventVersionRecord]] = {}
    for record in records:
        if record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("版本化监管事件引用未知产品，必须失败关闭")
        record_by_project.setdefault(record.project_id, []).append(record)

    consumed_fact_ids: set[str] = set()
    for project_id, project_records in record_by_project.items():
        contract_events = {
            event.event_id: event for event in contract_by_project[project_id].regulatory_events
        }
        seen_ids: set[str] = set()
        seen_fact_versions: set[str] = set()
        for record in project_records:
            contract_event = contract_events.get(record.event_id)
            if contract_event is None:
                raise GateEvaluationError("版本化监管事件引用合同不存在的稳定事件 ID，必须失败关闭")
            if record.event_kind is not contract_event.event_kind:
                raise GateEvaluationError("版本化监管事件类型必须与合同事件精确一致")
            if record.jurisdiction.value != contract_event.jurisdiction.value:
                raise GateEvaluationError("版本化监管事件地域必须与合同事件精确一致")
            record_date = _display_date(record.event_date)
            contract_date = _display_date(contract_event.event_date)
            if record_date != contract_date:
                raise GateEvaluationError(
                    "版本化监管事件日期必须与合同事件精确一致（ISO 规范比较）"
                )
            if record.event_id in seen_ids:
                raise GateEvaluationError("同一产品同一稳定事件 ID 不得重复记录")
            seen_ids.add(record.event_id)
            if record.fact_version_id in seen_fact_versions:
                raise GateEvaluationError("不同监管事件不得复用同一事实版本，必须失败关闭")
            seen_fact_versions.add(record.fact_version_id)
            _assert_record_fact_bound(
                evidence,
                project_id=record.project_id,
                fact_version_id=record.fact_version_id,
                source_location=record.source_location,
                allowed_field_ids=_FIELD_REGULATORY_EVENT,
                canonical_value=_record_canonical(record),
            )
            consumed_fact_ids.add(record.fact_version_id)
        if len(seen_ids) != len(contract_events):
            raise GateEvaluationError(
                "版本化监管事件必须与合同监管事件按事件 ID 精确一一对应，缺失或多余均失败关闭"
            )

    # 合同有事件但完全没有版本化记录的产品也失败关闭（事件无版本血统）。
    for project in projects:
        if project.regulatory_events and project.project_id not in record_by_project:
            raise GateEvaluationError("合同监管事件必须携带版本化记录，缺失版本血统失败关闭")
    _assert_fact_coverage(
        evidence,
        field_ids=_FIELD_REGULATORY_EVENT,
        entity_ids=frozenset(snapshot.product_ids),
        consumed_fact_ids=consumed_fact_ids,
        type_label_zh="监管事件",
    )


def build_regulatory_view(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    versioned_events: Sequence[RegulatoryEventVersionRecord] = (),
    *,
    authoritative_contract_store: ProjectContractStore,
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> RegulatoryView:
    """AV05 监管投影：全部产品 + 中国/境外分轨 + 稳定事件 ID 版本血统。

    事件记录必须与合同监管事件按 ``event_id`` 一一对应；无事件产品保留
    显式空轨。
    """
    projects, snapshot, bindings, results_posted_evidence, evidence = _revalidate_inputs(
        projects, snapshot, evidence, bindings, results_posted_evidence
    )
    analysis = analyze_universe(projects, snapshot, bindings, results_posted_evidence)
    _assert_report_ready(analysis)
    _assert_view_inputs_bound(projects, snapshot, analysis)
    _assert_evidence_context_bound(snapshot, evidence, authoritative_contract_store)
    _assert_versioned_events_closed(projects, snapshot, evidence, versioned_events)
    contract_by_project = {project.project_id: project for project in projects}

    china_by_project: dict[str, list[RegulatoryEventRow]] = {}
    overseas_by_project: dict[str, list[RegulatoryEventRow]] = {}
    for record in versioned_events:
        row = RegulatoryEventRow(
            event_id=record.event_id,
            kind_zh=_REGULATORY_EVENT_KIND_LABELS_ZH[record.event_kind],
            event_date=_display_date(record.event_date),
            fact_version_id=record.fact_version_id,
            source_location=record.source_location,
        )
        if record.jurisdiction.value == "中国":
            china_by_project.setdefault(record.project_id, []).append(row)
        else:
            overseas_by_project.setdefault(record.project_id, []).append(row)

    products = tuple(
        RegulatoryProductTracks(
            project_id=project_id,
            canonical_name=contract_by_project[project_id].canonical_name,
            china_events=tuple(china_by_project.get(project_id, ())),
            overseas_events=tuple(overseas_by_project.get(project_id, ())),
        )
        for project_id in snapshot.product_ids
    )
    return RegulatoryView(
        identity=_identity_from_snapshot(snapshot),
        products=products,
        content_digest=_view_digest(
            identity=_identity_from_snapshot(snapshot),
            products=products,
        ),
    )


# ── AV06 企业与交易：组织角色/关系/地域权益/交易/条款分离 ───────────────────


class CompanyRoleKind(StrEnum):
    """组织角色封闭集合：原研、开发者、许可方、被许可方。"""

    ORIGINATOR = "originator"
    DEVELOPER = "developer"
    LICENSOR = "licensor"
    LICENSEE = "licensee"


class CompanyRelationshipKind(StrEnum):
    """企业关系封闭集合：合作、并购。"""

    COLLABORATION = "collaboration"
    MERGER_ACQUISITION = "merger_acquisition"


class TransactionEventKind(StrEnum):
    """交易事件类型封闭集合：许可交易、合作、并购、股权投资。"""

    LICENSE = "license"
    COLLABORATION = "collaboration"
    MERGER_ACQUISITION = "merger_acquisition"
    EQUITY_INVESTMENT = "equity_investment"


_COMPANY_ROLE_LABELS_ZH: dict[CompanyRoleKind, str] = {
    CompanyRoleKind.ORIGINATOR: "原研",
    CompanyRoleKind.DEVELOPER: "开发者",
    CompanyRoleKind.LICENSOR: "许可方",
    CompanyRoleKind.LICENSEE: "被许可方",
}

_COMPANY_RELATIONSHIP_LABELS_ZH: dict[CompanyRelationshipKind, str] = {
    CompanyRelationshipKind.COLLABORATION: "合作",
    CompanyRelationshipKind.MERGER_ACQUISITION: "并购",
}

_TRANSACTION_EVENT_KIND_LABELS_ZH: dict[TransactionEventKind, str] = {
    TransactionEventKind.LICENSE: "许可交易",
    TransactionEventKind.COLLABORATION: "合作",
    TransactionEventKind.MERGER_ACQUISITION: "并购",
    TransactionEventKind.EQUITY_INVESTMENT: "股权投资",
}


class OrganizationRoleRecord(BaseModel):
    """AV06 版本化记录：一个产品下某组织的角色（原研/开发者/许可方/被许可方）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    organization_zh: str
    role: CompanyRoleKind
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("organization_zh")
    @classmethod
    def _organization_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class CompanyRelationshipRecord(BaseModel):
    """AV06 版本化记录：一个产品与其对手方的合作关系（合作/并购）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    counterparty_zh: str
    relationship: CompanyRelationshipKind
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("counterparty_zh")
    @classmethod
    def _counterparty_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class GeographicRightsRecord(BaseModel):
    """AV06 版本化记录：一个产品在一个地域的权益（中国/境外）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    region: str
    rights_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("rights_zh")
    @classmethod
    def _rights_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)

    @field_validator("region")
    @classmethod
    def _region_is_a_track(cls, value: str) -> str:
        normalized = _text(value)
        if normalized not in _REGIONS_ZH:
            raise ValueError("地域权益地域必须是锁定分轨：中国或境外")
        return normalized


class TransactionEventRecord(BaseModel):
    """AV06 版本化记录：一个交易事件（类型与日期）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    event_kind: TransactionEventKind
    event_date: EvidenceField
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class PublicTermRecord(BaseModel):
    """AV06 版本化记录：一条公开交易条款。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    term_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("term_zh")
    @classmethod
    def _term_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class OrganizationRoleRow(BaseModel):
    """AV06 组织角色行：角色中文标签、组织与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role_zh: str
    organization_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("role_zh", "organization_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class CompanyRelationshipRow(BaseModel):
    """AV06 企业关系行：关系中文标签、对手方与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relationship_zh: str
    counterparty_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("relationship_zh", "counterparty_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class GeographicRightsRow(BaseModel):
    """AV06 地域权益行：地域、权益描述与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    region: str
    rights_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("region", "rights_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)

    @field_validator("region")
    @classmethod
    def _region_is_a_track(cls, value: str) -> str:
        normalized = _text(value)
        if normalized not in _REGIONS_ZH:
            raise ValueError("地域权益地域必须是锁定分轨：中国或境外")
        return normalized


class TransactionEventRow(BaseModel):
    """AV06 交易事件行：类型中文标签、日期与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_kind_zh: str
    event_date: str
    fact_version_id: str
    source_location: str

    @field_validator("fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("event_kind_zh", "event_date")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class PublicTermRow(BaseModel):
    """AV06 公开条款行：条款文本与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    term_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("term_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class CompanyDealProduct(BaseModel):
    """AV06 一个产品的企业与交易档案：五类独立类型化集合。

    无合作/无交易/无条款时保留显式空集合，不失败、不删除、不占位。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    organization_roles: tuple[OrganizationRoleRow, ...] = ()
    relationships: tuple[CompanyRelationshipRow, ...] = ()
    geographic_rights: tuple[GeographicRightsRow, ...] = ()
    transaction_events: tuple[TransactionEventRow, ...] = ()
    public_terms: tuple[PublicTermRow, ...] = ()

    @field_validator("project_id", "canonical_name")
    @classmethod
    def _identity_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class CompanyDealView(BaseModel):
    """AV06 企业与交易视图：全部产品 + 五类独立类型化集合。

    产品 ID 集合必须等于锁定快照且顺序一致；空集合是合法显式状态。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: AViewSnapshotIdentity
    products: tuple[CompanyDealProduct, ...] = Field(min_length=1)
    content_digest: str

    @model_validator(mode="after")
    def _content_digest_matches(self) -> Self:
        _view_digest_validator(self.model_dump(mode="json"))
        return self

    @model_validator(mode="after")
    def _products_exactly_match_locked_snapshot(self) -> Self:
        ids = tuple(product.project_id for product in self.products)
        if ids != self.identity.product_ids:
            raise ValueError("企业与交易视图产品集必须等于锁定快照且顺序一致")
        return self

    @property
    def total_products(self) -> int:
        return len(self.products)

    def product(self, project_id: str) -> CompanyDealProduct:
        for product in self.products:
            if product.project_id == project_id:
                return product
        raise KeyError(f"锁定快照内不存在产品：{project_id}")


def _assert_company_records_closed(
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    *,
    organization_roles: Sequence[OrganizationRoleRecord],
    relationships: Sequence[CompanyRelationshipRecord],
    geographic_rights: Sequence[GeographicRightsRecord],
    transaction_events: Sequence[TransactionEventRecord],
    public_terms: Sequence[PublicTermRecord],
) -> None:
    """企业/交易记录必须绑定锁定快照内产品、当前证据快照且各自唯一。

    未知产品、同类记录重复（同一自然身份键）失败关闭；记录事实必须绑定
    当前证据快照（各自封闭字段集合、定位、展示值精确一致）；五类记录互不
    混写；同一事实版本不得支撑多个记录；当前证据快照中企业/交易事实必须
    全部被消费。
    """
    organization_roles = tuple(
        cast(OrganizationRoleRecord, item)
        for item in _revalidate_records(organization_roles, OrganizationRoleRecord)
    )
    relationships = tuple(
        cast(CompanyRelationshipRecord, item)
        for item in _revalidate_records(relationships, CompanyRelationshipRecord)
    )
    geographic_rights = tuple(
        cast(GeographicRightsRecord, item)
        for item in _revalidate_records(geographic_rights, GeographicRightsRecord)
    )
    transaction_events = tuple(
        cast(TransactionEventRecord, item)
        for item in _revalidate_records(transaction_events, TransactionEventRecord)
    )
    public_terms = tuple(
        cast(PublicTermRecord, item) for item in _revalidate_records(public_terms, PublicTermRecord)
    )
    consumed_fact_ids: set[str] = set()
    seen_fact_versions: set[str] = set()

    def _consume(record: object, fact_version_id: str) -> None:
        if fact_version_id in seen_fact_versions:
            raise GateEvaluationError("同一事实版本不得支撑多个企业/交易记录，必须失败关闭")
        seen_fact_versions.add(fact_version_id)
        consumed_fact_ids.add(fact_version_id)

    seen_org: set[tuple[str, str, CompanyRoleKind]] = set()
    for role_record in organization_roles:
        if role_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("组织角色记录引用未知产品，必须失败关闭")
        org_key = (role_record.project_id, role_record.organization_zh, role_record.role)
        if org_key in seen_org:
            raise GateEvaluationError("同一产品同一组织同一角色不得重复记录")
        seen_org.add(org_key)
        _consume(role_record, role_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=role_record.project_id,
            fact_version_id=role_record.fact_version_id,
            source_location=role_record.source_location,
            allowed_field_ids=_FIELD_ORGANIZATION_ROLE,
            canonical_value=_record_canonical(role_record),
        )

    seen_rel: set[tuple[str, str, CompanyRelationshipKind]] = set()
    for relationship_record in relationships:
        if relationship_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("企业关系记录引用未知产品，必须失败关闭")
        rel_key = (
            relationship_record.project_id,
            relationship_record.counterparty_zh,
            relationship_record.relationship,
        )
        if rel_key in seen_rel:
            raise GateEvaluationError("同一产品同一对手方同一关系不得重复记录")
        seen_rel.add(rel_key)
        _consume(relationship_record, relationship_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=relationship_record.project_id,
            fact_version_id=relationship_record.fact_version_id,
            source_location=relationship_record.source_location,
            allowed_field_ids=_FIELD_COMPANY_RELATIONSHIP,
            canonical_value=_record_canonical(relationship_record),
        )

    seen_rights: set[tuple[str, str, str]] = set()
    for rights_record in geographic_rights:
        if rights_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("地域权益记录引用未知产品，必须失败关闭")
        rights_key = (rights_record.project_id, rights_record.region, rights_record.rights_zh)
        if rights_key in seen_rights:
            raise GateEvaluationError("同一产品同一地域同一权益不得重复记录")
        seen_rights.add(rights_key)
        _consume(rights_record, rights_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=rights_record.project_id,
            fact_version_id=rights_record.fact_version_id,
            source_location=rights_record.source_location,
            allowed_field_ids=_FIELD_GEOGRAPHIC_RIGHTS,
            canonical_value=_record_canonical(rights_record),
        )

    seen_tx: set[tuple[str, TransactionEventKind, tuple[str | None, object | None]]] = set()
    for transaction_record in transaction_events:
        if transaction_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("交易事件记录引用未知产品，必须失败关闭")
        tx_key = (
            transaction_record.project_id,
            transaction_record.event_kind,
            (transaction_record.event_date.value, transaction_record.event_date.state),
        )
        if tx_key in seen_tx:
            raise GateEvaluationError("同一产品同一交易类型同一日期不得重复记录")
        seen_tx.add(tx_key)
        _consume(transaction_record, transaction_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=transaction_record.project_id,
            fact_version_id=transaction_record.fact_version_id,
            source_location=transaction_record.source_location,
            allowed_field_ids=_FIELD_TRANSACTION_EVENT,
            canonical_value=_record_canonical(transaction_record),
        )

    seen_terms: set[tuple[str, str]] = set()
    for term_record in public_terms:
        if term_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("公开条款记录引用未知产品，必须失败关闭")
        term_key = (term_record.project_id, term_record.term_zh)
        if term_key in seen_terms:
            raise GateEvaluationError("同一产品同一公开条款不得重复记录")
        seen_terms.add(term_key)
        _consume(term_record, term_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=term_record.project_id,
            fact_version_id=term_record.fact_version_id,
            source_location=term_record.source_location,
            allowed_field_ids=_FIELD_PUBLIC_TERM,
            canonical_value=_record_canonical(term_record),
        )

    _assert_fact_coverage(
        evidence,
        field_ids=(
            _FIELD_ORGANIZATION_ROLE
            | _FIELD_COMPANY_RELATIONSHIP
            | _FIELD_GEOGRAPHIC_RIGHTS
            | _FIELD_TRANSACTION_EVENT
            | _FIELD_PUBLIC_TERM
        ),
        entity_ids=frozenset(snapshot.product_ids),
        consumed_fact_ids=consumed_fact_ids,
        type_label_zh="企业与交易",
    )


def build_company_deal_view(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    *,
    authoritative_contract_store: ProjectContractStore,
    organization_roles: Sequence[OrganizationRoleRecord] = (),
    relationships: Sequence[CompanyRelationshipRecord] = (),
    geographic_rights: Sequence[GeographicRightsRecord] = (),
    transaction_events: Sequence[TransactionEventRecord] = (),
    public_terms: Sequence[PublicTermRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> CompanyDealView:
    """AV06 企业与交易投影：全部产品 + 五类独立类型化集合。

    空集合是合法显式状态（无合作/无交易/无条款不失败、不占位）；记录
    事实必须属于当前证据快照。
    """
    projects, snapshot, bindings, results_posted_evidence, evidence = _revalidate_inputs(
        projects, snapshot, evidence, bindings, results_posted_evidence
    )
    analysis = analyze_universe(projects, snapshot, bindings, results_posted_evidence)
    _assert_report_ready(analysis)
    _assert_view_inputs_bound(projects, snapshot, analysis)
    _assert_evidence_context_bound(snapshot, evidence, authoritative_contract_store)
    _assert_company_records_closed(
        snapshot,
        evidence,
        organization_roles=organization_roles,
        relationships=relationships,
        geographic_rights=geographic_rights,
        transaction_events=transaction_events,
        public_terms=public_terms,
    )
    contract_by_project = {project.project_id: project for project in projects}

    roles_by_project: dict[str, list[OrganizationRoleRow]] = {}
    for role_record in organization_roles:
        roles_by_project.setdefault(role_record.project_id, []).append(
            OrganizationRoleRow(
                role_zh=_COMPANY_ROLE_LABELS_ZH[role_record.role],
                organization_zh=role_record.organization_zh,
                fact_version_id=role_record.fact_version_id,
                source_location=role_record.source_location,
            )
        )
    relationships_by_project: dict[str, list[CompanyRelationshipRow]] = {}
    for relationship_record in relationships:
        relationships_by_project.setdefault(relationship_record.project_id, []).append(
            CompanyRelationshipRow(
                relationship_zh=_COMPANY_RELATIONSHIP_LABELS_ZH[relationship_record.relationship],
                counterparty_zh=relationship_record.counterparty_zh,
                fact_version_id=relationship_record.fact_version_id,
                source_location=relationship_record.source_location,
            )
        )
    rights_by_project: dict[str, list[GeographicRightsRow]] = {}
    for rights_record in geographic_rights:
        rights_by_project.setdefault(rights_record.project_id, []).append(
            GeographicRightsRow(
                region=rights_record.region,
                rights_zh=rights_record.rights_zh,
                fact_version_id=rights_record.fact_version_id,
                source_location=rights_record.source_location,
            )
        )
    transactions_by_project: dict[str, list[TransactionEventRow]] = {}
    for transaction_record in transaction_events:
        transactions_by_project.setdefault(transaction_record.project_id, []).append(
            TransactionEventRow(
                event_kind_zh=_TRANSACTION_EVENT_KIND_LABELS_ZH[transaction_record.event_kind],
                event_date=_display_label(transaction_record.event_date),
                fact_version_id=transaction_record.fact_version_id,
                source_location=transaction_record.source_location,
            )
        )
    terms_by_project: dict[str, list[PublicTermRow]] = {}
    for term_record in public_terms:
        terms_by_project.setdefault(term_record.project_id, []).append(
            PublicTermRow(
                term_zh=term_record.term_zh,
                fact_version_id=term_record.fact_version_id,
                source_location=term_record.source_location,
            )
        )

    products = tuple(
        CompanyDealProduct(
            project_id=project_id,
            canonical_name=contract_by_project[project_id].canonical_name,
            organization_roles=tuple(roles_by_project.get(project_id, ())),
            relationships=tuple(relationships_by_project.get(project_id, ())),
            geographic_rights=tuple(rights_by_project.get(project_id, ())),
            transaction_events=tuple(transactions_by_project.get(project_id, ())),
            public_terms=tuple(terms_by_project.get(project_id, ())),
        )
        for project_id in snapshot.product_ids
    )
    return CompanyDealView(
        identity=_identity_from_snapshot(snapshot),
        products=products,
        content_digest=_view_digest(
            identity=_identity_from_snapshot(snapshot),
            products=products,
        ),
    )


# ── AV07 专利与保护：专利族/法域成员/保护范围/期限/监管独占分离 ─────────────


class RegulatoryExclusivityKind(StrEnum):
    """监管独占类型封闭集合：数据独占、生物制品独占、孤儿药独占、儿科独占。"""

    DATA_EXCLUSIVITY = "data_exclusivity"
    BIOLOGICS_EXCLUSIVITY = "biologics_exclusivity"
    ORPHAN_DRUG_EXCLUSIVITY = "orphan_drug_exclusivity"
    PEDIATRIC_EXCLUSIVITY = "pediatric_exclusivity"


_EXCLUSIVITY_KIND_LABELS_ZH: dict[RegulatoryExclusivityKind, str] = {
    RegulatoryExclusivityKind.DATA_EXCLUSIVITY: "数据独占",
    RegulatoryExclusivityKind.BIOLOGICS_EXCLUSIVITY: "生物制品独占",
    RegulatoryExclusivityKind.ORPHAN_DRUG_EXCLUSIVITY: "孤儿药独占",
    RegulatoryExclusivityKind.PEDIATRIC_EXCLUSIVITY: "儿科独占",
}


class PatentFamilyRecord(BaseModel):
    """AV07 版本化记录：一个产品的专利族身份与族标题。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    family_id: str
    family_label_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "family_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("family_label_zh")
    @classmethod
    def _family_label_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class PatentMemberRecord(BaseModel):
    """AV07 版本化记录：一个法域成员（单一法域 + 来源可定位的程序状态）。

    一个成员只绑定一个法域；期限/到期绑定成员即绑定单一法域，跨法域
    拼接在结构上不可能。成员状态只保存可定位的程序状态（已授权/审评中
    等事实），不做有效性法律结论。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    family_id: str
    member_id: str
    jurisdiction: str
    member_status: EvidenceField
    fact_version_id: str
    source_location: str

    @field_validator(
        "project_id",
        "family_id",
        "member_id",
        "jurisdiction",
        "fact_version_id",
        "source_location",
    )
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class PatentScopeRecord(BaseModel):
    """AV07 版本化记录：一个专利族的保护范围（权利要求涵盖描述）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    family_id: str
    scope_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "family_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("scope_zh")
    @classmethod
    def _scope_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class PatentTermRecord(BaseModel):
    """AV07 版本化记录：一个法域成员的期限陈述与到期日。

    到期日必须是确定值或互斥状态（尚未公开/不适用/来源未列示/技术暂不可用），
    绝不推断或填充默认日期；期限绑定成员，即绑定单一法域，不允许跨法域
    拼接到期日。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    member_id: str
    term_zh: str
    expiry: EvidenceField
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "member_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("term_zh")
    @classmethod
    def _term_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class RegulatoryExclusivityRecord(BaseModel):
    """AV07 版本化记录：一个产品的监管独占（与专利完全分离）。

    独占类型为封闭枚举，法域为单一确定值，到期日为确定值或互斥状态。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    exclusivity_kind: RegulatoryExclusivityKind
    jurisdiction: str
    expiry: EvidenceField
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "jurisdiction", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class PatentFamilyRow(BaseModel):
    """AV07 专利族行：族身份、族标题与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: str
    family_label_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("family_id", "fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("family_label_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class PatentMemberRow(BaseModel):
    """AV07 法域成员行：单一法域、程序状态标签与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: str
    member_id: str
    jurisdiction: str
    member_status: str
    fact_version_id: str
    source_location: str

    @field_validator("family_id", "member_id", "fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("jurisdiction", "member_status")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class PatentScopeRow(BaseModel):
    """AV07 保护范围行：范围描述与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: str
    scope_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("family_id", "fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("scope_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class PatentTermRow(BaseModel):
    """AV07 期限行：期限陈述、到期日标签与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    member_id: str
    term_zh: str
    expiry: str
    fact_version_id: str
    source_location: str

    @field_validator("member_id", "fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("term_zh", "expiry")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class RegulatoryExclusivityRow(BaseModel):
    """AV07 监管独占行：类型中文标签、法域、到期日与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exclusivity_kind_zh: str
    jurisdiction: str
    expiry: str
    fact_version_id: str
    source_location: str

    @field_validator("fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("exclusivity_kind_zh", "jurisdiction", "expiry")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class PatentProtectionProduct(BaseModel):
    """AV07 一个产品的专利与保护档案：五类独立类型化集合。

    无专利/无独占时保留显式空集合，不失败、不删除、不占位。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    families: tuple[PatentFamilyRow, ...] = ()
    members: tuple[PatentMemberRow, ...] = ()
    scopes: tuple[PatentScopeRow, ...] = ()
    terms: tuple[PatentTermRow, ...] = ()
    exclusivities: tuple[RegulatoryExclusivityRow, ...] = ()

    @field_validator("project_id", "canonical_name")
    @classmethod
    def _identity_text_is_not_blank(cls, value: str) -> str:
        return _text(value)


class PatentProtectionView(BaseModel):
    """AV07 专利与保护视图：全部产品 + 五类独立类型化集合。

    产品 ID 集合必须等于锁定快照且顺序一致；空集合是合法显式状态。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: AViewSnapshotIdentity
    products: tuple[PatentProtectionProduct, ...] = Field(min_length=1)
    content_digest: str

    @model_validator(mode="after")
    def _content_digest_matches(self) -> Self:
        _view_digest_validator(self.model_dump(mode="json"))
        return self

    @model_validator(mode="after")
    def _products_exactly_match_locked_snapshot(self) -> Self:
        ids = tuple(product.project_id for product in self.products)
        if ids != self.identity.product_ids:
            raise ValueError("专利与保护视图产品集必须等于锁定快照且顺序一致")
        return self

    @property
    def total_products(self) -> int:
        return len(self.products)

    def product(self, project_id: str) -> PatentProtectionProduct:
        for product in self.products:
            if product.project_id == project_id:
                return product
        raise KeyError(f"锁定快照内不存在产品：{project_id}")


def _assert_patent_records_closed(
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    *,
    families: Sequence[PatentFamilyRecord],
    members: Sequence[PatentMemberRecord],
    scopes: Sequence[PatentScopeRecord],
    terms: Sequence[PatentTermRecord],
    exclusivities: Sequence[RegulatoryExclusivityRecord],
) -> None:
    """专利/独占记录必须绑定锁定快照内产品、当前证据快照且各自唯一。

    未知产品、同类记录重复（同一自然身份键）失败关闭；法域成员必须引用
    本产品已声明专利族，期限必须引用本产品已声明法域成员——跨产品引用或
    跨法域拼接失败关闭；记录事实必须绑定当前证据快照（各自封闭字段集合、
    定位、展示值精确一致）；五类记录互不混写；同一事实版本不得支撑多个
    记录；当前证据快照中专利/独占事实必须全部被消费。
    """
    families = tuple(
        cast(PatentFamilyRecord, item) for item in _revalidate_records(families, PatentFamilyRecord)
    )
    members = tuple(
        cast(PatentMemberRecord, item) for item in _revalidate_records(members, PatentMemberRecord)
    )
    scopes = tuple(
        cast(PatentScopeRecord, item) for item in _revalidate_records(scopes, PatentScopeRecord)
    )
    terms = tuple(
        cast(PatentTermRecord, item) for item in _revalidate_records(terms, PatentTermRecord)
    )
    exclusivities = tuple(
        cast(RegulatoryExclusivityRecord, item)
        for item in _revalidate_records(exclusivities, RegulatoryExclusivityRecord)
    )
    consumed_fact_ids: set[str] = set()
    seen_fact_versions: set[str] = set()

    def _consume(record: object, fact_version_id: str) -> None:
        if fact_version_id in seen_fact_versions:
            raise GateEvaluationError("同一事实版本不得支撑多个专利/独占记录，必须失败关闭")
        seen_fact_versions.add(fact_version_id)
        consumed_fact_ids.add(fact_version_id)

    family_ids_by_project: dict[str, set[str]] = {}
    seen_family: set[tuple[str, str]] = set()
    for family_record in families:
        if family_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("专利族记录引用未知产品，必须失败关闭")
        family_key = (family_record.project_id, family_record.family_id)
        if family_key in seen_family:
            raise GateEvaluationError("同一产品同一专利族不得重复记录")
        seen_family.add(family_key)
        family_ids_by_project.setdefault(family_record.project_id, set()).add(
            family_record.family_id
        )
        _consume(family_record, family_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=family_record.project_id,
            fact_version_id=family_record.fact_version_id,
            source_location=family_record.source_location,
            allowed_field_ids=_FIELD_PATENT_FAMILY,
            canonical_value=_record_canonical(family_record),
        )

    member_ids_by_project: dict[str, set[str]] = {}
    seen_member: set[tuple[str, str]] = set()
    for member_record in members:
        if member_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("法域成员记录引用未知产品，必须失败关闭")
        if member_record.family_id not in family_ids_by_project.get(
            member_record.project_id, set()
        ):
            raise GateEvaluationError(
                "法域成员必须引用本产品已声明的专利族，跨产品或未知族失败关闭"
            )
        member_key = (member_record.project_id, member_record.member_id)
        if member_key in seen_member:
            raise GateEvaluationError("同一产品同一法域成员不得重复记录")
        seen_member.add(member_key)
        member_ids_by_project.setdefault(member_record.project_id, set()).add(
            member_record.member_id
        )
        _consume(member_record, member_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=member_record.project_id,
            fact_version_id=member_record.fact_version_id,
            source_location=member_record.source_location,
            allowed_field_ids=_FIELD_PATENT_MEMBER,
            canonical_value=_record_canonical(member_record),
        )

    seen_scope: set[tuple[str, str, str]] = set()
    for scope_record in scopes:
        if scope_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("保护范围记录引用未知产品，必须失败关闭")
        if scope_record.family_id not in family_ids_by_project.get(scope_record.project_id, set()):
            raise GateEvaluationError(
                "保护范围必须引用本产品已声明的专利族，跨产品或未知族失败关闭"
            )
        scope_key = (scope_record.project_id, scope_record.family_id, scope_record.scope_zh)
        if scope_key in seen_scope:
            raise GateEvaluationError("同一产品同一专利族同一保护范围不得重复记录")
        seen_scope.add(scope_key)
        _consume(scope_record, scope_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=scope_record.project_id,
            fact_version_id=scope_record.fact_version_id,
            source_location=scope_record.source_location,
            allowed_field_ids=_FIELD_PATENT_SCOPE,
            canonical_value=_record_canonical(scope_record),
        )

    seen_term: set[tuple[str, str, str, tuple[str | None, object | None]]] = set()
    for term_record in terms:
        if term_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("专利期限记录引用未知产品，必须失败关闭")
        if term_record.member_id not in member_ids_by_project.get(term_record.project_id, set()):
            raise GateEvaluationError(
                "专利期限必须绑定本产品已声明的法域成员，跨产品或未知成员失败关闭"
            )
        term_key = (
            term_record.project_id,
            term_record.member_id,
            term_record.term_zh,
            (term_record.expiry.value, term_record.expiry.state),
        )
        if term_key in seen_term:
            raise GateEvaluationError("同一产品同一成员同一期限同一到期日不得重复记录")
        seen_term.add(term_key)
        _consume(term_record, term_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=term_record.project_id,
            fact_version_id=term_record.fact_version_id,
            source_location=term_record.source_location,
            allowed_field_ids=_FIELD_PATENT_TERM,
            canonical_value=_record_canonical(term_record),
        )

    seen_exclusivity: set[
        tuple[str, RegulatoryExclusivityKind, str, tuple[str | None, object | None]]
    ] = set()
    for exclusivity_record in exclusivities:
        if exclusivity_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("监管独占记录引用未知产品，必须失败关闭")
        exclusivity_key = (
            exclusivity_record.project_id,
            exclusivity_record.exclusivity_kind,
            exclusivity_record.jurisdiction,
            (exclusivity_record.expiry.value, exclusivity_record.expiry.state),
        )
        if exclusivity_key in seen_exclusivity:
            raise GateEvaluationError("同一产品同一独占类型同一法域同一到期日不得重复记录")
        seen_exclusivity.add(exclusivity_key)
        _consume(exclusivity_record, exclusivity_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=exclusivity_record.project_id,
            fact_version_id=exclusivity_record.fact_version_id,
            source_location=exclusivity_record.source_location,
            allowed_field_ids=_FIELD_REGULATORY_EXCLUSIVITY,
            canonical_value=_record_canonical(exclusivity_record),
        )

    _assert_fact_coverage(
        evidence,
        field_ids=(
            _FIELD_PATENT_FAMILY
            | _FIELD_PATENT_MEMBER
            | _FIELD_PATENT_SCOPE
            | _FIELD_PATENT_TERM
            | _FIELD_REGULATORY_EXCLUSIVITY
        ),
        entity_ids=frozenset(snapshot.product_ids),
        consumed_fact_ids=consumed_fact_ids,
        type_label_zh="专利与保护",
    )


def build_patent_protection_view(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    *,
    authoritative_contract_store: ProjectContractStore,
    families: Sequence[PatentFamilyRecord] = (),
    members: Sequence[PatentMemberRecord] = (),
    scopes: Sequence[PatentScopeRecord] = (),
    terms: Sequence[PatentTermRecord] = (),
    exclusivities: Sequence[RegulatoryExclusivityRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> PatentProtectionView:
    """AV07 专利与保护投影：全部产品 + 五类独立类型化集合。

    空集合是合法显式状态（无专利/无独占不失败、不占位）；到期日未知
    显式表达互斥状态，不推断；视图不做有效性法律结论；记录事实必须属于
    当前证据快照。
    """
    projects, snapshot, bindings, results_posted_evidence, evidence = _revalidate_inputs(
        projects, snapshot, evidence, bindings, results_posted_evidence
    )
    analysis = analyze_universe(projects, snapshot, bindings, results_posted_evidence)
    _assert_report_ready(analysis)
    _assert_view_inputs_bound(projects, snapshot, analysis)
    _assert_evidence_context_bound(snapshot, evidence, authoritative_contract_store)
    _assert_patent_records_closed(
        snapshot,
        evidence,
        families=families,
        members=members,
        scopes=scopes,
        terms=terms,
        exclusivities=exclusivities,
    )
    contract_by_project = {project.project_id: project for project in projects}

    families_by_project: dict[str, list[PatentFamilyRow]] = {}
    for family_record in families:
        families_by_project.setdefault(family_record.project_id, []).append(
            PatentFamilyRow(
                family_id=family_record.family_id,
                family_label_zh=family_record.family_label_zh,
                fact_version_id=family_record.fact_version_id,
                source_location=family_record.source_location,
            )
        )
    members_by_project: dict[str, list[PatentMemberRow]] = {}
    for member_record in members:
        members_by_project.setdefault(member_record.project_id, []).append(
            PatentMemberRow(
                family_id=member_record.family_id,
                member_id=member_record.member_id,
                jurisdiction=member_record.jurisdiction,
                member_status=_display_label(member_record.member_status),
                fact_version_id=member_record.fact_version_id,
                source_location=member_record.source_location,
            )
        )
    scopes_by_project: dict[str, list[PatentScopeRow]] = {}
    for scope_record in scopes:
        scopes_by_project.setdefault(scope_record.project_id, []).append(
            PatentScopeRow(
                family_id=scope_record.family_id,
                scope_zh=scope_record.scope_zh,
                fact_version_id=scope_record.fact_version_id,
                source_location=scope_record.source_location,
            )
        )
    terms_by_project: dict[str, list[PatentTermRow]] = {}
    for term_record in terms:
        terms_by_project.setdefault(term_record.project_id, []).append(
            PatentTermRow(
                member_id=term_record.member_id,
                term_zh=term_record.term_zh,
                expiry=_display_label(term_record.expiry),
                fact_version_id=term_record.fact_version_id,
                source_location=term_record.source_location,
            )
        )
    exclusivities_by_project: dict[str, list[RegulatoryExclusivityRow]] = {}
    for exclusivity_record in exclusivities:
        exclusivities_by_project.setdefault(exclusivity_record.project_id, []).append(
            RegulatoryExclusivityRow(
                exclusivity_kind_zh=_EXCLUSIVITY_KIND_LABELS_ZH[
                    exclusivity_record.exclusivity_kind
                ],
                jurisdiction=exclusivity_record.jurisdiction,
                expiry=_display_label(exclusivity_record.expiry),
                fact_version_id=exclusivity_record.fact_version_id,
                source_location=exclusivity_record.source_location,
            )
        )

    products = tuple(
        PatentProtectionProduct(
            project_id=project_id,
            canonical_name=contract_by_project[project_id].canonical_name,
            families=tuple(families_by_project.get(project_id, ())),
            members=tuple(members_by_project.get(project_id, ())),
            scopes=tuple(scopes_by_project.get(project_id, ())),
            terms=tuple(terms_by_project.get(project_id, ())),
            exclusivities=tuple(exclusivities_by_project.get(project_id, ())),
        )
        for project_id in snapshot.product_ids
    )
    return PatentProtectionView(
        identity=_identity_from_snapshot(snapshot),
        products=products,
        content_digest=_view_digest(
            identity=_identity_from_snapshot(snapshot),
            products=products,
        ),
    )


# ── AV08 历史与边缘：暂停/终止/撤回/放弃及邻近机制观察显式保留 ─────────────


class HistoricalStatusKind(StrEnum):
    """历史状态类型封闭集合：暂停、终止、撤回、放弃。"""

    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    WITHDRAWN = "withdrawn"
    ABANDONED = "abandoned"


_HISTORICAL_STATUS_LABELS_ZH: dict[HistoricalStatusKind, str] = {
    HistoricalStatusKind.SUSPENDED: "暂停",
    HistoricalStatusKind.TERMINATED: "终止",
    HistoricalStatusKind.WITHDRAWN: "撤回",
    HistoricalStatusKind.ABANDONED: "放弃",
}


class HistoricalStatusRecord(BaseModel):
    """AV08 版本化记录：一个产品的历史状态（暂停/终止/撤回/放弃）。

    历史状态必须引用当前产品合同的稳定 ``regulatory_event_id`` 及当前证据
    事实：撤回/终止/暂停/放弃必须与相应监管事件闭合，不得给仍在活跃临床
    开发且没有对应监管事件的产品伪造历史状态。历史状态地域只接受中国/境外
    分轨；状态日期必须是确定值或互斥状态。相邻观察与正式监管状态分开保存。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    regulatory_event_id: str
    status_kind: HistoricalStatusKind
    jurisdiction: str
    status_date: EvidenceField
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "regulatory_event_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("jurisdiction")
    @classmethod
    def _jurisdiction_is_a_track(cls, value: str) -> str:
        normalized = _text(value)
        if normalized not in _REGIONS_ZH:
            raise ValueError("历史状态地域必须是锁定分轨：中国或境外")
        return normalized


class AdjacentObservationRecord(BaseModel):
    """AV08 版本化记录：一个产品的邻近机制观察显式声明。

    机制相关但适应症关系未确立的项目独立观察，不进入核心比较；记录必须
    携带明确的机制关系依据与版本血统。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    relation_basis_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("project_id", "fact_version_id", "source_location")
    @classmethod
    def _record_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("relation_basis_zh")
    @classmethod
    def _relation_basis_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class HistoricalStatusRow(BaseModel):
    """AV08 一条历史状态行：类型中文标签、地域、日期与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status_kind_zh: str
    jurisdiction: str
    status_date: str
    fact_version_id: str
    source_location: str

    @field_validator("fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("status_kind_zh", "jurisdiction", "status_date")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class AdjacentObservationRow(BaseModel):
    """AV08 一条邻近观察行：机制关系依据与版本血统。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relation_basis_zh: str
    fact_version_id: str
    source_location: str

    @field_validator("fact_version_id", "source_location")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("relation_basis_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class HistoryEdgeProduct(BaseModel):
    """AV08 一个产品的历史与边缘行：开发状态、历史状态与邻近观察。

    暂停/终止/撤回/放弃产品保留显式历史状态；活跃产品保留显式空集合。
    任何状态下产品都留在视图中，不因当前开发状态被过滤或删除。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    canonical_name: str
    development_status_zh: str
    historical_statuses: tuple[HistoricalStatusRow, ...] = ()
    adjacent_observations: tuple[AdjacentObservationRow, ...] = ()

    @field_validator("project_id")
    @classmethod
    def _row_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("canonical_name", "development_status_zh")
    @classmethod
    def _row_fact_is_user_facing(cls, value: str) -> str:
        return _user_facing_text(value)


class HistoryEdgeView(BaseModel):
    """AV08 历史与边缘视图：全部产品 + 历史状态与邻近观察显式保留。

    产品 ID 集合必须等于锁定快照且顺序一致；空集合是合法显式状态。
    视图不提供任何状态筛选/删除出口。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: AViewSnapshotIdentity
    products: tuple[HistoryEdgeProduct, ...] = Field(min_length=1)
    content_digest: str

    @model_validator(mode="after")
    def _content_digest_matches(self) -> Self:
        _view_digest_validator(self.model_dump(mode="json"))
        return self

    @model_validator(mode="after")
    def _products_exactly_match_locked_snapshot(self) -> Self:
        ids = tuple(product.project_id for product in self.products)
        if ids != self.identity.product_ids:
            raise ValueError("历史与边缘视图产品集必须等于锁定快照且顺序一致")
        return self

    @property
    def total_products(self) -> int:
        return len(self.products)

    def product(self, project_id: str) -> HistoryEdgeProduct:
        for product in self.products:
            if product.project_id == project_id:
                return product
        raise KeyError(f"锁定快照内不存在产品：{project_id}")


def _assert_history_edge_records_closed(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    maturity_by_project: Mapping[str, DevelopmentMaturity],
    *,
    historical_statuses: Sequence[HistoricalStatusRecord],
    adjacent_observations: Sequence[AdjacentObservationRecord],
) -> None:
    """历史/边缘记录必须与锁定快照、合同监管事件、产品成熟度与当前证据快照闭合。

    - 未知产品、同类记录重复（同一自然身份键）失败关闭；
    - 历史状态必须引用本产品合同存在的稳定 ``regulatory_event_id``，且状态
      类型与监管事件类型封闭映射一致：撤回/终止/暂停/放弃不得伪造——没有
      对应监管事件的产品无法携带历史状态；
    - 仍处于活跃临床开发（临床层）的产品只允许暂停状态（对应暂停事件），
      不得伪造终止/撤回/放弃；
    - 历史状态与相邻观察的事实必须绑定当前证据快照（各自封闭字段集合、
      定位、展示值精确一致）；两类记录互不混写；同一事实版本不得支撑多个
      记录；当前证据快照中历史/边缘事实必须全部被消费。
    """
    historical_statuses = tuple(
        cast(HistoricalStatusRecord, item)
        for item in _revalidate_records(historical_statuses, HistoricalStatusRecord)
    )
    adjacent_observations = tuple(
        cast(AdjacentObservationRecord, item)
        for item in _revalidate_records(adjacent_observations, AdjacentObservationRecord)
    )
    contract_by_project = {project.project_id: project for project in projects}
    consumed_fact_ids: set[str] = set()
    seen_fact_versions: set[str] = set()

    def _consume(record: object, fact_version_id: str) -> None:
        if fact_version_id in seen_fact_versions:
            raise GateEvaluationError("同一事实版本不得支撑多个历史/边缘记录，必须失败关闭")
        seen_fact_versions.add(fact_version_id)
        consumed_fact_ids.add(fact_version_id)

    seen_status: set[
        tuple[str, str, HistoricalStatusKind, str, tuple[str | None, object | None]]
    ] = set()
    for status_record in historical_statuses:
        if status_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("历史状态记录引用未知产品，必须失败关闭")
        contract = contract_by_project[status_record.project_id]
        contract_event = next(
            (
                event
                for event in contract.regulatory_events
                if event.event_id == status_record.regulatory_event_id
            ),
            None,
        )
        if contract_event is None:
            raise GateEvaluationError(
                "历史状态必须引用本产品合同存在的稳定监管事件 ID，伪造状态失败关闭"
            )
        expected_kind = _HISTORICAL_STATUS_TO_EVENT_KIND[status_record.status_kind.value]
        if contract_event.event_kind is not expected_kind:
            raise GateEvaluationError("历史状态类型必须与所引用监管事件类型一致，必须失败关闭")
        if maturity_by_project.get(
            status_record.project_id
        ) is DevelopmentMaturity.CLINICAL and status_record.status_kind not in (
            HistoricalStatusKind.SUSPENDED,
        ):
            raise GateEvaluationError(
                "仍在活跃临床开发的产品不得伪造终止/撤回/放弃历史状态，必须失败关闭"
            )
        status_key = (
            status_record.project_id,
            status_record.regulatory_event_id,
            status_record.status_kind,
            status_record.jurisdiction,
            (status_record.status_date.value, status_record.status_date.state),
        )
        if status_key in seen_status:
            raise GateEvaluationError("同一产品同一监管事件同一历史状态不得重复记录")
        seen_status.add(status_key)
        _consume(status_record, status_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=status_record.project_id,
            fact_version_id=status_record.fact_version_id,
            source_location=status_record.source_location,
            allowed_field_ids=_FIELD_HISTORICAL_STATUS,
            canonical_value=_record_canonical(status_record),
        )

    seen_observation: set[tuple[str, str]] = set()
    for observation_record in adjacent_observations:
        if observation_record.project_id not in snapshot.product_ids:
            raise GateEvaluationError("邻近观察记录引用未知产品，必须失败关闭")
        observation_key = (
            observation_record.project_id,
            observation_record.relation_basis_zh,
        )
        if observation_key in seen_observation:
            raise GateEvaluationError("同一产品同一机制关系依据不得重复声明")
        seen_observation.add(observation_key)
        _consume(observation_record, observation_record.fact_version_id)
        _assert_record_fact_bound(
            evidence,
            project_id=observation_record.project_id,
            fact_version_id=observation_record.fact_version_id,
            source_location=observation_record.source_location,
            allowed_field_ids=_FIELD_ADJACENT_OBSERVATION,
            canonical_value=_record_canonical(observation_record),
        )

    _assert_fact_coverage(
        evidence,
        field_ids=_FIELD_HISTORICAL_STATUS | _FIELD_ADJACENT_OBSERVATION,
        entity_ids=frozenset(snapshot.product_ids),
        consumed_fact_ids=consumed_fact_ids,
        type_label_zh="历史与边缘",
    )


def build_history_edge_view(
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    bindings: Sequence[GateEvidenceBinding],
    *,
    authoritative_contract_store: ProjectContractStore,
    historical_statuses: Sequence[HistoricalStatusRecord] = (),
    adjacent_observations: Sequence[AdjacentObservationRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> HistoryEdgeView:
    """AV08 历史与边缘投影：全部产品 + 历史状态与邻近观察显式保留。

    视图不存在状态筛选/删除出口：暂停、终止、撤回、放弃产品与活跃产品
    同等保留；无历史状态/无邻近观察时保留显式空集合。历史状态与合同监管
    事件及当前证据快照闭合。
    """
    projects, snapshot, bindings, results_posted_evidence, evidence = _revalidate_inputs(
        projects, snapshot, evidence, bindings, results_posted_evidence
    )
    analysis = analyze_universe(projects, snapshot, bindings, results_posted_evidence)
    _assert_report_ready(analysis)
    _assert_view_inputs_bound(projects, snapshot, analysis)
    _assert_evidence_context_bound(snapshot, evidence, authoritative_contract_store)
    maturity_by_project = {
        result.project_id: result.gate.development_maturity for result in analysis.projects
    }
    _assert_history_edge_records_closed(
        projects,
        snapshot,
        evidence,
        maturity_by_project,
        historical_statuses=historical_statuses,
        adjacent_observations=adjacent_observations,
    )
    contract_by_project = {project.project_id: project for project in projects}
    gate_by_project = {result.project_id: result.gate for result in analysis.projects}

    statuses_by_project: dict[str, list[HistoricalStatusRow]] = {}
    for status_record in historical_statuses:
        statuses_by_project.setdefault(status_record.project_id, []).append(
            HistoricalStatusRow(
                status_kind_zh=_HISTORICAL_STATUS_LABELS_ZH[status_record.status_kind],
                jurisdiction=status_record.jurisdiction,
                status_date=_display_date(status_record.status_date),
                fact_version_id=status_record.fact_version_id,
                source_location=status_record.source_location,
            )
        )
    observations_by_project: dict[str, list[AdjacentObservationRow]] = {}
    for observation_record in adjacent_observations:
        observations_by_project.setdefault(observation_record.project_id, []).append(
            AdjacentObservationRow(
                relation_basis_zh=observation_record.relation_basis_zh,
                fact_version_id=observation_record.fact_version_id,
                source_location=observation_record.source_location,
            )
        )

    products = tuple(
        HistoryEdgeProduct(
            project_id=project_id,
            canonical_name=contract_by_project[project_id].canonical_name,
            development_status_zh=_DEVELOPMENT_STATUS_LABELS_ZH[
                gate_by_project[project_id].development_maturity
            ],
            historical_statuses=tuple(statuses_by_project.get(project_id, ())),
            adjacent_observations=tuple(observations_by_project.get(project_id, ())),
        )
        for project_id in snapshot.product_ids
    )
    return HistoryEdgeView(
        identity=_identity_from_snapshot(snapshot),
        products=products,
        content_digest=_view_digest(
            identity=_identity_from_snapshot(snapshot),
            products=products,
        ),
    )


# ── 渲染边界权威校验：重新验证当前项目/快照/证据/内容摘要，拒绝旧视图 ──────


def assert_landscape_view_authoritative(
    view: LandscapeView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
    bindings: Sequence[GateEvidenceBinding],
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> None:
    """竞争格局视图权威校验：按当前输入重建并精确比对，拒绝旧视图/手工 DTO。"""
    rebuilt = build_landscape_view(
        projects, snapshot, evidence, bindings,
        authoritative_contract_store=authoritative_contract_store,
        results_posted_evidence=results_posted_evidence
    )
    if rebuilt != view:
        raise GateEvaluationError("竞争格局视图与当前输入不一致，拒绝旧视图或手工 DTO")


def assert_product_overview_view_authoritative(
    view: ProductOverviewView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
    bindings: Sequence[GateEvidenceBinding],
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> None:
    """产品总览权威校验：完整作用域视图必须等于当前输入重建结果。

    筛选子视图（``view_scope == "filtered"``）是派生视图，必须携带明确
    作用域标记且内容摘要有效，禁止冒充完整视图。
    """
    if not isinstance(view, ProductOverviewView) or view.view_scope != ViewScope.COMPLETE:
        raise GateEvaluationError("渲染边界只接受完整作用域的产品总览视图")
    rebuilt = build_product_overview_view(
        projects, snapshot, evidence, bindings,
        authoritative_contract_store=authoritative_contract_store,
        results_posted_evidence=results_posted_evidence
    )
    if rebuilt != view:
        raise GateEvaluationError("产品总览视图与当前输入不一致，拒绝旧视图或手工 DTO")


def assert_product_dossier_view_authoritative(
    view: ProductDossierView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
    bindings: Sequence[GateEvidenceBinding],
    trial_region_records: Sequence[ClinicalTrialRegionRecord] = (),
    versioned_events: Sequence[RegulatoryEventVersionRecord] = (),
    organization_roles: Sequence[OrganizationRoleRecord] = (),
    relationships: Sequence[CompanyRelationshipRecord] = (),
    geographic_rights: Sequence[GeographicRightsRecord] = (),
    transaction_events: Sequence[TransactionEventRecord] = (),
    public_terms: Sequence[PublicTermRecord] = (),
    families: Sequence[PatentFamilyRecord] = (),
    members: Sequence[PatentMemberRecord] = (),
    scopes: Sequence[PatentScopeRecord] = (),
    terms: Sequence[PatentTermRecord] = (),
    exclusivities: Sequence[RegulatoryExclusivityRecord] = (),
    historical_statuses: Sequence[HistoricalStatusRecord] = (),
    adjacent_observations: Sequence[AdjacentObservationRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> None:
    """产品档案权威校验：重建并精确比对，拒绝旧视图/手工 DTO。"""
    rebuilt = build_product_dossier_view(
        projects,
        snapshot,
        evidence,
        bindings,
        trial_region_records=trial_region_records,
        versioned_events=versioned_events,
        organization_roles=organization_roles,
        relationships=relationships,
        geographic_rights=geographic_rights,
        transaction_events=transaction_events,
        public_terms=public_terms,
        families=families,
        members=members,
        scopes=scopes,
        terms=terms,
        exclusivities=exclusivities,
        historical_statuses=historical_statuses,
        adjacent_observations=adjacent_observations,
        authoritative_contract_store=authoritative_contract_store,
        results_posted_evidence=results_posted_evidence,
    )
    if rebuilt != view:
        raise GateEvaluationError("产品档案视图与当前输入不一致，拒绝旧视图或手工 DTO")


def assert_clinical_portfolio_view_authoritative(
    view: ClinicalPortfolioView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
    bindings: Sequence[GateEvidenceBinding],
    trial_region_records: Sequence[ClinicalTrialRegionRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> None:
    """临床组合权威校验：重建并精确比对，拒绝旧视图/手工 DTO。"""
    rebuilt = build_clinical_portfolio_view(
        projects,
        snapshot,
        evidence,
        bindings,
        trial_region_records=trial_region_records,
        authoritative_contract_store=authoritative_contract_store,
        results_posted_evidence=results_posted_evidence,
    )
    if rebuilt != view:
        raise GateEvaluationError("临床组合视图与当前输入不一致，拒绝旧视图或手工 DTO")


def assert_regulatory_view_authoritative(
    view: RegulatoryView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
    bindings: Sequence[GateEvidenceBinding],
    versioned_events: Sequence[RegulatoryEventVersionRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> None:
    """监管视图权威校验：重建并精确比对，拒绝旧视图/手工 DTO。"""
    rebuilt = build_regulatory_view(
        projects,
        snapshot,
        evidence,
        bindings,
        versioned_events=versioned_events,
        authoritative_contract_store=authoritative_contract_store,
        results_posted_evidence=results_posted_evidence,
    )
    if rebuilt != view:
        raise GateEvaluationError("监管视图与当前输入不一致，拒绝旧视图或手工 DTO")


def assert_company_deal_view_authoritative(
    view: CompanyDealView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
    bindings: Sequence[GateEvidenceBinding],
    organization_roles: Sequence[OrganizationRoleRecord] = (),
    relationships: Sequence[CompanyRelationshipRecord] = (),
    geographic_rights: Sequence[GeographicRightsRecord] = (),
    transaction_events: Sequence[TransactionEventRecord] = (),
    public_terms: Sequence[PublicTermRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> None:
    """企业与交易视图权威校验：重建并精确比对，拒绝旧视图/手工 DTO。"""
    rebuilt = build_company_deal_view(
        projects,
        snapshot,
        evidence,
        bindings,
        organization_roles=organization_roles,
        relationships=relationships,
        geographic_rights=geographic_rights,
        transaction_events=transaction_events,
        public_terms=public_terms,
        authoritative_contract_store=authoritative_contract_store,
        results_posted_evidence=results_posted_evidence,
    )
    if rebuilt != view:
        raise GateEvaluationError("企业与交易视图与当前输入不一致，拒绝旧视图或手工 DTO")


def assert_patent_protection_view_authoritative(
    view: PatentProtectionView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
    bindings: Sequence[GateEvidenceBinding],
    families: Sequence[PatentFamilyRecord] = (),
    members: Sequence[PatentMemberRecord] = (),
    scopes: Sequence[PatentScopeRecord] = (),
    terms: Sequence[PatentTermRecord] = (),
    exclusivities: Sequence[RegulatoryExclusivityRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> None:
    """专利与保护视图权威校验：重建并精确比对，拒绝旧视图/手工 DTO。"""
    rebuilt = build_patent_protection_view(
        projects,
        snapshot,
        evidence,
        bindings,
        families=families,
        members=members,
        scopes=scopes,
        terms=terms,
        exclusivities=exclusivities,
        authoritative_contract_store=authoritative_contract_store,
        results_posted_evidence=results_posted_evidence,
    )
    if rebuilt != view:
        raise GateEvaluationError("专利与保护视图与当前输入不一致，拒绝旧视图或手工 DTO")


def assert_history_edge_view_authoritative(
    view: HistoryEdgeView,
    *,
    projects: Sequence[AProjectContract],
    snapshot: ApplicableUniverseSnapshot,
    evidence: AEvidenceContext,
    authoritative_contract_store: ProjectContractStore,
    bindings: Sequence[GateEvidenceBinding],
    historical_statuses: Sequence[HistoricalStatusRecord] = (),
    adjacent_observations: Sequence[AdjacentObservationRecord] = (),
    results_posted_evidence: Sequence[RegistryResultsPostedEvidence] = (),
) -> None:
    """历史与边缘视图权威校验：重建并精确比对，拒绝旧视图/手工 DTO。"""
    rebuilt = build_history_edge_view(
        projects,
        snapshot,
        evidence,
        bindings,
        historical_statuses=historical_statuses,
        adjacent_observations=adjacent_observations,
        authoritative_contract_store=authoritative_contract_store,
        results_posted_evidence=results_posted_evidence,
    )
    if rebuilt != view:
        raise GateEvaluationError("历史与边缘视图与当前输入不一致，拒绝旧视图或手工 DTO")
