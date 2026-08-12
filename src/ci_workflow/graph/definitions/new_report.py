"""Task 3.4 新建报告图节点合同（v1.2 §10.1）。

每个节点声明版本化类型化输入/输出、完成谓词、读写集、重试策略、
声明错误、幂等材料、副作用类与 shared/report/artifact 作用域。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ci_workflow.graph.types import NodeContract, RetryPolicy, TypedField

# 幂等材料：所有节点统一以项目/运行/节点身份 + 输入摘要去重
_IDEMPOTENCY_MATERIAL: tuple[str, ...] = (
    "project_id",
    "run_id",
    "node_id",
    "input_digest",
)


def _completion_requires(*fields: str) -> Callable[[dict[str, Any]], bool]:
    """完成谓词：全部声明输出存在且非空才视为完成。"""

    def predicate(outputs: dict[str, Any]) -> bool:
        return all(outputs.get(field) is not None for field in fields) and bool(fields)

    return predicate


def _field(name: str, type_: str, description: str) -> TypedField:
    return TypedField(name=name, type=type_, description=description)


NEW_REPORT_NODES: tuple[NodeContract, ...] = (
    # ── 入口与预检、本体与宇宙、来源路由 ──────────────────────────────────
    NodeContract(
        node_id="intake",
        version="1.0",
        typed_inputs=(
            _field("report_kinds", "tuple[ReportKind]", "A/B/C 报告类型选择"),
            _field("indication", "str", "目标适应症"),
            _field("output_formats", "tuple[OutputFormat]", "可选输出格式"),
        ),
        typed_outputs=(_field("project_contract_id", "str", "项目合同稳定标识"),),
        completion_predicate=_completion_requires("project_contract_id"),
        completion_summary="接收最小输入并建立项目合同",
        reads=("project",),
        writes=(),
        retry_policy=RetryPolicy(1, 0.0, ("ValueError",)),
        declared_errors=("InvalidIndicationError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    NodeContract(
        node_id="preflight",
        version="1.0",
        typed_inputs=(_field("capability_inventory", "dict[str, bool]", "宿主能力清单"),),
        typed_outputs=(_field("capability_matrix_id", "str", "能力矩阵稳定标识"),),
        completion_predicate=_completion_requires("capability_matrix_id"),
        completion_summary="运行安装包与宿主能力预检",
        reads=("project",),
        writes=(),
        retry_policy=RetryPolicy(1, 0.0, ("CapabilityGapError",)),
        declared_errors=("CapabilityGapError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    NodeContract(
        node_id="universe",
        version="1.0",
        typed_inputs=(_field("indication_id", "str", "消解后的适应症稳定标识"),),
        typed_outputs=(_field("universe_receipt_id", "str", "全量分层竞品宇宙回执"),),
        completion_predicate=_completion_requires("universe_receipt_id"),
        completion_summary="解析适应症身份并建立创新药本体与全球分层竞品宇宙",
        reads=("evidence",),
        writes=(),
        retry_policy=RetryPolicy(1, 0.0, ("OntologyMatchError",)),
        declared_errors=("OntologyMatchError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    NodeContract(
        node_id="route",
        version="1.0",
        typed_inputs=(
            _field("universe_receipt_id", "str", "竞品宇宙回执"),
            _field("gap_ledger", "tuple[str]", "缺口账本"),
        ),
        typed_outputs=(_field("source_graph_id", "str", "来源关系图稳定标识"),),
        completion_predicate=_completion_requires("source_graph_id"),
        completion_summary="按实体、声明类型、地域和报告类型生成来源关系图",
        reads=("evidence",),
        writes=(),
        retry_policy=RetryPolicy(
            3, 2.0, ("TransientError", "RateLimitError", "CapabilityGapError")
        ),
        declared_errors=("RoutePlanError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 摄取、抽取、解析与冲突 ────────────────────────────────────────────
    NodeContract(
        node_id="ingest",
        version="1.0",
        typed_inputs=(_field("source_version_ids", "tuple[str]", "不可变来源版本标识"),),
        typed_outputs=(_field("ingest_receipt_id", "str", "摄取回执"),),
        completion_predicate=_completion_requires("ingest_receipt_id"),
        completion_summary="摄取、身份解析、结构化抽取、规范化和冲突登记",
        reads=("evidence",),
        writes=(),
        retry_policy=RetryPolicy(3, 2.0, ("TransientError", "RateLimitError", "ParserError")),
        declared_errors=("IngestError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    NodeContract(
        node_id="extract",
        version="1.0",
        typed_inputs=(_field("fragment_ids", "tuple[str]", "证据片段标识"),),
        typed_outputs=(_field("extract_receipt_id", "str", "抽取回执"),),
        completion_predicate=_completion_requires("extract_receipt_id"),
        completion_summary="原子事实抽取与规范化，原始表达永不覆盖",
        reads=("evidence",),
        writes=(),
        retry_policy=RetryPolicy(3, 2.0, ("TransientError", "ParserError", "ExtractionError")),
        declared_errors=("ExtractionError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    NodeContract(
        node_id="resolve",
        version="1.0",
        typed_inputs=(
            _field("candidate_entities", "tuple[str]", "候选实体标识"),
            _field("facts", "tuple[str]", "候选事实标识"),
        ),
        typed_outputs=(
            _field(
                "evidence_references",
                "tuple[EvidenceReference]",
                "证据引用账本（fragment_id/sha256）",
            ),
        ),
        completion_predicate=_completion_requires("evidence_references"),
        completion_summary="实体解析与冲突登记，形成稳定身份；引用写入共享证据账本",
        reads=("evidence",),
        writes=("evidence",),
        retry_policy=RetryPolicy(2, 1.0, ("ConflictUnresolvedError",)),
        declared_errors=("ResolutionConflictError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="shared",
    ),
    # ── 门槛与缺口恢复 ────────────────────────────────────────────────────
    NodeContract(
        node_id="gate",
        version="1.0",
        typed_inputs=(
            _field("report_kind", "ReportKind", "A/B/C 报告类型"),
            _field("evidence_references", "tuple[EvidenceReference]", "共享证据引用"),
        ),
        typed_outputs=(
            _field("gate_passed", "bool", "确定性门槛通过与否"),
            _field("failures", "tuple[str]", "失败关键单元"),
            _field("evidence_digest", "str", "所读共享证据快照摘要"),
        ),
        completion_predicate=_completion_requires("gate_passed", "failures", "evidence_digest"),
        completion_summary="分别计算 A/B/C 关键字段覆盖与缺口；读共享证据，写本报告 gate 键",
        reads=("evidence",),
        writes=("gate.{report_kind}",),
        retry_policy=RetryPolicy(1, 0.0, ("GateEvaluationError",)),
        declared_errors=("GateEvaluationError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="report",
    ),
    NodeContract(
        node_id="recovery",
        version="1.0",
        typed_inputs=(
            _field("report_kind", "ReportKind", "A/B/C 报告类型"),
            _field("failures", "tuple[str]", "失败关键单元"),
        ),
        typed_outputs=(_field("recovery_receipt", "str", "缺口驱动恢复回执"),),
        completion_predicate=_completion_requires("recovery_receipt"),
        completion_summary="对失败报告执行缺口驱动恢复；已成功的共享证据保持锁定",
        reads=("gate.{report_kind}", "evidence"),
        writes=(),
        retry_policy=RetryPolicy(
            3, 2.0, ("TransientError", "RateLimitError", "RecoveryExhaustedError")
        ),
        declared_errors=("RecoveryExhaustedError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="report",
    ),
    # ── 快照、独立科学质控与分析 ──────────────────────────────────────────
    NodeContract(
        node_id="snapshot",
        version="1.0",
        typed_inputs=(
            _field("report_kind", "ReportKind", "A/B/C 报告类型"),
            _field("gate_result", "dict[str, object]", "本报告 gate 结果"),
        ),
        typed_outputs=(_field("snapshot_id", "str", "候选事实/声明快照标识"),),
        completion_predicate=_completion_requires("snapshot_id"),
        completion_summary="对通过门槛的报告建立候选事实/声明快照",
        reads=("gate.{report_kind}", "evidence"),
        writes=("snapshot.{report_kind}",),
        retry_policy=RetryPolicy(1, 0.0, ("SnapshotBuildError",)),
        declared_errors=("SnapshotBuildError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="report",
    ),
    NodeContract(
        node_id="scientific_qc",
        version="1.0",
        typed_inputs=(
            _field("report_kind", "ReportKind", "A/B/C 报告类型"),
            _field("snapshot_id", "str", "候选快照标识"),
        ),
        typed_outputs=(_field("qc_verdict", "str", "隔离质控接受/否决裁定"),),
        completion_predicate=_completion_requires("qc_verdict"),
        completion_summary="执行独立科学质控：只能接受或否决，不能静默重写证据",
        reads=("snapshot.{report_kind}",),
        writes=("snapshot.{report_kind}",),
        retry_policy=RetryPolicy(1, 0.0, ("QCVerdictError",)),
        declared_errors=("QCVerdictError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="report",
    ),
    NodeContract(
        node_id="analyze",
        version="1.0",
        typed_inputs=(
            _field("report_kind", "ReportKind", "A/B/C 报告类型"),
            _field("snapshot_id", "str", "锁定快照标识"),
        ),
        typed_outputs=(_field("pages", "tuple[str]", "页面数据责任清单"),),
        completion_predicate=_completion_requires("pages"),
        completion_summary="A/B/C 分别分析并建立页面数据",
        reads=("snapshot.{report_kind}",),
        writes=("analysis.{report_kind}",),
        retry_policy=RetryPolicy(1, 0.0, ("AnalysisError",)),
        declared_errors=("AnalysisError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="none",
        scope="report",
    ),
    # ── 格式渲染与验收 ────────────────────────────────────────────────────
    NodeContract(
        node_id="format",
        version="1.0",
        typed_inputs=(
            _field("report_kind", "ReportKind", "A/B/C 报告类型"),
            _field("snapshot_id", "str", "锁定报告快照"),
            _field("format", "OutputFormat", "html/pdf/html-ppt/pptx"),
        ),
        typed_outputs=(
            _field("format", "OutputFormat", "格式类型"),
            _field("artifact_id", "str", "构建产物标识"),
        ),
        completion_predicate=_completion_requires("format", "artifact_id"),
        completion_summary="生成站点式 HTML 并按选择并行生成 PDF/HTML-PPT/PPTX；发布产物",
        reads=("snapshot.{report_kind}",),
        writes=("artifact.{report_kind}",),
        retry_policy=RetryPolicy(3, 2.0, ("RenderError", "TransientError", "CapabilityGapError")),
        declared_errors=("RenderError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="publish",
        scope="artifact",
    ),
    NodeContract(
        node_id="acceptance",
        version="1.0",
        typed_inputs=(
            _field("report_kind", "ReportKind", "A/B/C 报告类型"),
            _field("artifact_id", "str", "构建产物标识"),
            _field("format", "OutputFormat", "格式类型"),
        ),
        typed_outputs=(_field("acceptance_verdict", "str", "确定性/覆盖/真实渲染验收裁定"),),
        completion_predicate=_completion_requires("acceptance_verdict"),
        completion_summary="每个格式独立完成确定性、内容覆盖和真实渲染验收；交付移动",
        reads=("artifact.{report_kind}",),
        writes=(),
        retry_policy=RetryPolicy(1, 0.0, ("AcceptanceError",)),
        declared_errors=("AcceptanceError",),
        idempotency_material=_IDEMPOTENCY_MATERIAL,
        side_effect_class="move",
        scope="artifact",
    ),
)
