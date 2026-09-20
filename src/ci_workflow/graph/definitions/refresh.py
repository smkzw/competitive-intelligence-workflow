"""Task 9.2 刷新控制图定义：刷新节点合同与"局部刷新 / 需要再基线"分支。

本模块只声明合同：七个刷新节点——读取父版本、筛选新适格候选、重评事实/
声明、重算受影响门槛、局部重建、质控、建立新版本——与重大合同变化分支。
节点执行、父版本绑定、回执登记与幂等恢复由 ``application/refresh_service.py``
持有；门槛收紧的只收紧偏序、变更单元与受影响报告计算全部复用
``gates.coverage``，这里不复制任何 GateSpec 规则。

两个批准节点：``refresh_qc``（独立质控只能接受或否决，不能静默重写）与
``refresh_accept_version``（建立并接受新的不可变版本）。任一未通过，子版本
不得登记为已接受。重大合同变化（项目合同 Schema/本体/证据合同）进入
``rebaseline_required`` 分支，明确要求重新建立基线，不得伪装成局部刷新。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from ci_workflow.graph.definitions.new_report import NEW_REPORT_NODES
from ci_workflow.graph.types import NodeContract, RetryPolicy, TypedField

__all__ = [
    "BRANCH_LOCAL_REFRESH",
    "BRANCH_REBASELINE_REQUIRED",
    "REBASELINE_REQUIRED_MESSAGE_ZH",
    "REFRESH_NODES",
    "RefreshBaselineIdentity",
    "RefreshBranch",
    "RefreshBranchDecision",
    "classify_refresh_branch",
    "refresh_node_contract",
]

# ── 分支词表：重大合同变化只识别并要求再基线，不产出局部刷新计划 ──────────

RefreshBranch = Literal["local_refresh", "rebaseline_required"]
BRANCH_LOCAL_REFRESH: RefreshBranch = "local_refresh"
BRANCH_REBASELINE_REQUIRED: RefreshBranch = "rebaseline_required"
REBASELINE_REQUIRED_MESSAGE_ZH = "重大合同变化：需要重新建立基线，不能局部刷新"

_DIMENSION_CONTRACT_SCHEMA = "contract_schema_version"
_DIMENSION_ONTOLOGY = "ontology_version"
_DIMENSION_EVIDENCE_CONTRACT = "evidence_contract_version"


@dataclass(frozen=True)
class RefreshBaselineIdentity:
    """刷新基线身份：三维任一变化即重大合同变化，必须再基线。

    GateSpec 单元级收紧不属于基线身份：它由 ``gates.coverage`` 的只收紧
    偏序与受影响报告计算在 ``local_refresh`` 分支内确定性处理。
    """

    contract_schema_version: str
    ontology_version: str
    evidence_contract_version: str

    def __post_init__(self) -> None:
        for name in (
            "contract_schema_version",
            "ontology_version",
            "evidence_contract_version",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"刷新基线身份字段不能为空: {name}")


@dataclass(frozen=True)
class RefreshBranchDecision:
    """确定性分支裁定：分支、发生变化的基线维度与可审计中文理由。"""

    branch: RefreshBranch
    changed_dimensions: tuple[str, ...]
    reason_zh: str


def classify_refresh_branch(
    parent: RefreshBaselineIdentity, child: RefreshBaselineIdentity
) -> RefreshBranchDecision:
    """比较父子基线身份；命中重大变化即要求再基线，不做局部刷新。"""
    changed: list[str] = []
    if parent.contract_schema_version != child.contract_schema_version:
        changed.append(_DIMENSION_CONTRACT_SCHEMA)
    if parent.ontology_version != child.ontology_version:
        changed.append(_DIMENSION_ONTOLOGY)
    if parent.evidence_contract_version != child.evidence_contract_version:
        changed.append(_DIMENSION_EVIDENCE_CONTRACT)
    if not changed:
        return RefreshBranchDecision(
            branch=BRANCH_LOCAL_REFRESH,
            changed_dimensions=(),
            reason_zh="基线身份一致，可局部刷新",
        )
    return RefreshBranchDecision(
        branch=BRANCH_REBASELINE_REQUIRED,
        changed_dimensions=tuple(sorted(changed)),
        reason_zh=REBASELINE_REQUIRED_MESSAGE_ZH,
    )


# ── 刷新节点合同 ─────────────────────────────────────────────────────────

_IDEMPOTENCY_MATERIAL: tuple[str, ...] = (
    "project_id",
    "run_id",
    "node_id",
    "input_digest",
)


def _field(name: str, type_: str, description: str) -> TypedField:
    return TypedField(name=name, type=type_, description=description)


def _completion_requires(*fields: str) -> Callable[[dict[str, Any]], bool]:
    """完成谓词：全部声明输出存在且非 None 才视为完成。"""

    def predicate(outputs: dict[str, Any]) -> bool:
        return all(outputs.get(field) is not None for field in fields) and bool(fields)

    return predicate


REFRESH_NODES: tuple[NodeContract, ...] = (
    # ── 读取父版本与分支裁定 ──────────────────────────────────────────────
    NodeContract(
        node_id="refresh_parent",
        version="1.0",
        typed_inputs=(
            _field("parent_contract_id", "str", "父项目合同稳定标识（只读）"),
            _field("child_contract_id", "str", "追加的子合同版本稳定标识"),
            _field("parent_baseline", "dict[str, object]", "父基线身份（合同/本体/证据合同版本）"),
            _field("child_baseline", "dict[str, object]", "刷新后基线身份"),
        ),
        typed_outputs=(
            _field("parent_binding", "dict[str, object]", "父合同版本、父快照与来源回执的只读绑定"),
            _field("refresh_branch", "str", "刷新分支标识"),
            _field("branch_reason_zh", "str", "分支裁定的可审计中文理由"),
        ),
        completion_predicate=_completion_requires(
            "parent_binding", "refresh_branch", "branch_reason_zh"
        ),
        completion_summary="读取父版本与基线身份并裁定分支；父合同、父快照只读",
        reads=("project", "evidence"),
        writes=(),
        retry_policy=RetryPolicy(1, 0.0, ("ValueError",)),
        declared_errors=("ParentContractError", "RebaselineRequiredError"),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 截止日扩大后的候选晋级 ────────────────────────────────────────────
    NodeContract(
        node_id="refresh_candidates",
        version="1.0",
        typed_inputs=(
            _field("child_contract_id", "str", "子合同版本稳定标识"),
            _field("parent_cutoff", "str", "父合同数据截止日"),
            _field("new_cutoff", "str", "扩大后的数据截止日"),
            _field("candidate_ids", "tuple[str]", "截止日后候选标识清单"),
        ),
        typed_outputs=(
            _field(
                "promoted_candidate_ids",
                "tuple[str]",
                "仅因截止日扩大而新适格、获准进入重评的候选；空集合表示无新候选",
            ),
        ),
        completion_predicate=_completion_requires("promoted_candidate_ids"),
        completion_summary="按首次披露时间而非获取时间筛选新适格候选；不能越过新截止日",
        reads=("evidence",),
        writes=(),
        retry_policy=RetryPolicy(1, 0.0, ("ValueError",)),
        declared_errors=("CandidatePromotionError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 重评事实与声明 ────────────────────────────────────────────────────
    NodeContract(
        node_id="refresh_reevaluate",
        version="1.0",
        typed_inputs=(
            _field("promoted_candidate_ids", "tuple[str]", "新适格候选标识"),
            _field("changed_source_ids", "tuple[str]", "发生新增/变化/撤回/修订/取代的来源版本"),
            _field("gap_unit_ids", "tuple[str]", "父版本未闭合缺口单元"),
        ),
        typed_outputs=(
            _field("reevaluated_fact_ids", "tuple[str]", "重评事实标识"),
            _field("reevaluated_claim_ids", "tuple[str]", "重评声明标识"),
            _field("change_records", "tuple[str]", "新增/变化/撤回/修订/取代记录标识"),
            _field("unchanged_digest", "str", "未变化对象按摘要复用的内容摘要"),
        ),
        completion_predicate=_completion_requires(
            "reevaluated_fact_ids",
            "reevaluated_claim_ids",
            "change_records",
            "unchanged_digest",
        ),
        completion_summary="只重评新候选与已变化来源；已接受且未变化的来源不重评",
        reads=("evidence",),
        writes=("evidence",),
        retry_policy=RetryPolicy(3, 2.0, ("TransientError", "RateLimitError")),
        declared_errors=("ReevaluationError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 重算受影响门槛（复用 gates.coverage，不复制规则） ─────────────────
    NodeContract(
        node_id="refresh_gate",
        version="1.0",
        typed_inputs=(
            _field("affected_report_kinds", "tuple[ReportKind]", "调用方声明的受影响报告集合"),
            _field("changed_unit_ids", "tuple[str]", "gates.coverage 计算的变更单元"),
            _field("parent_gate_results", "dict[str, object]", "父版本门槛结果（只读绑定）"),
        ),
        typed_outputs=(
            _field(
                "affected_report_kinds", "tuple[ReportKind]", "与确定性计算一致的受影响报告集合"
            ),
            _field("gate_receipt_id", "str", "重算门槛回执"),
            _field("gate_blocked", "bool", "受影响报告是否存在未达关键门槛"),
            _field("failures", "tuple[str]", "失败关键单元"),
        ),
        completion_predicate=_completion_requires(
            "affected_report_kinds", "gate_receipt_id", "gate_blocked", "failures"
        ),
        completion_summary="只重算受影响报告的覆盖门槛；声明集合必须与确定性计算一致",
        reads=("evidence",),
        writes=("gate.{report_kind}",),
        retry_policy=RetryPolicy(1, 0.0, ("GateEvaluationError",)),
        declared_errors=("GateDeclarationError", "GateBlockedError"),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="report",
    ),
    # ── 局部重建 ──────────────────────────────────────────────────────────
    NodeContract(
        node_id="refresh_rebuild",
        version="1.0",
        typed_inputs=(
            _field("impact_plan_digest", "str", "影响图闭包计划摘要（幂等键材料）"),
            _field("affected_claim_ids", "tuple[str]", "需重建的声明标识"),
            _field("affected_page_ids", "tuple[str]", "需重建的报告页面标识"),
            _field("reused_page_ids", "tuple[str]", "按摘要复用的页面标识"),
            _field("output_formats", "tuple[OutputFormat]", "选定格式；首版仅站点式 HTML"),
        ),
        typed_outputs=(
            _field("rebuild_receipt_id", "str", "局部重建回执（追加保存）"),
            _field("rebuilt_object_ids", "tuple[str]", "实际重建的对象标识"),
            _field("artifact_ids", "tuple[str]", "重建的候选产物标识"),
        ),
        completion_predicate=_completion_requires(
            "rebuild_receipt_id", "rebuilt_object_ids", "artifact_ids"
        ),
        completion_summary="只重建影响集合内的声明、页面与站点式 HTML；其余对象按摘要复用",
        reads=("snapshot.{report_kind}", "analysis.{report_kind}"),
        writes=("artifact.{report_kind}",),
        retry_policy=RetryPolicy(
            3, 2.0, ("RenderError", "TransientError", "CapabilityGapError")
        ),
        declared_errors=("RebuildError", "UnsupportedFormatError"),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="artifact",
    ),
    # ── 质控（批准节点一） ────────────────────────────────────────────────
    NodeContract(
        node_id="refresh_qc",
        version="1.0",
        typed_inputs=(
            _field("affected_report_kinds", "tuple[ReportKind]", "受影响报告集合"),
            _field("rebuild_receipt_id", "str", "局部重建回执"),
        ),
        typed_outputs=(
            _field("qc_verdict", "str", "独立质控裁定：接受或否决，不能静默重写"),
            _field("qc_verdict_digest", "str", "质控结论内容摘要"),
        ),
        completion_predicate=_completion_requires("qc_verdict", "qc_verdict_digest"),
        completion_summary="对受影响报告执行独立质控；只能接受或否决",
        reads=("artifact.{report_kind}",),
        writes=("qc.{report_kind}",),
        retry_policy=RetryPolicy(1, 0.0, ("QCVerdictError",)),
        declared_errors=("QCVerdictError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="report",
    ),
    # ── 建立新版本（批准节点二） ──────────────────────────────────────────
    NodeContract(
        node_id="refresh_accept_version",
        version="1.0",
        typed_inputs=(
            _field("child_contract_id", "str", "子合同版本稳定标识"),
            _field("rebuild_receipt_id", "str", "局部重建回执"),
            _field("qc_verdict_digest", "str", "独立质控结论摘要"),
            _field("child_snapshot_ids", "tuple[str]", "新的不可变快照标识"),
        ),
        typed_outputs=(
            _field("child_version_id", "str", "新版本稳定标识"),
            _field("accepted", "bool", "新版本是否建立并接受"),
        ),
        completion_predicate=_completion_requires("child_version_id", "accepted"),
        completion_summary="建立并接受新的不可变版本；质控或重建未完成不得登记",
        reads=("snapshot.{report_kind}", "artifact.{report_kind}"),
        writes=(),
        retry_policy=RetryPolicy(1, 0.0, ("VersionAcceptanceError",)),
        declared_errors=("VersionAcceptanceError", "IncompleteRebuildError"),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="move",
        scope="shared",
    ),
)

_NODE_IDS = tuple(contract.node_id for contract in REFRESH_NODES)
if len(set(_NODE_IDS)) != len(_NODE_IDS):
    raise ValueError("刷新节点标识不得重复")
_REPORT_NODE_IDS = {contract.node_id for contract in NEW_REPORT_NODES}
if _REPORT_NODE_IDS & set(_NODE_IDS):
    raise ValueError(f"刷新节点标识与新建报告图冲突: {sorted(_REPORT_NODE_IDS & set(_NODE_IDS))}")


def refresh_node_contract(node_id: str) -> NodeContract:
    """按 node_id 取刷新节点合同；未知节点失败关闭。"""
    for contract in REFRESH_NODES:
        if contract.node_id == node_id:
            return contract
    raise ValueError(f"未知刷新图节点: {node_id}")
