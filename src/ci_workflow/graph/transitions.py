"""Task 3.4 运行时迁移族冻结：v1.2 §10.2 字面迁移表。

测试中的 GT01–GT05 期望 fixture 与本文件逐边相等；任何一边漂移都使
missing/extra 断言失败。前四组证据状态族在此注册但不声明任何迁移边。
"""

from __future__ import annotations

from enum import Enum

from ci_workflow.domain.enums import (
    DownloadRequestState,
    FactDisclosureState,
    FactReviewState,
    FormatArtifactState,
    ProjectRunState,
    ReportEvidenceState,
    RevisionApprovalState,
    RouteAttemptResult,
    RouteCompletion,
)
from ci_workflow.graph.types import DeclaredEdge

# 九族枚举注册：前四组证据状态族 + 后五组运行状态族
FAMILY_STATE_ENUMS: dict[str, type[Enum]] = {
    "route_attempt": RouteAttemptResult,
    "route_completion": RouteCompletion,
    "fact_disclosure": FactDisclosureState,
    "fact_review": FactReviewState,
    "project": ProjectRunState,
    "report_evidence": ReportEvidenceState,
    "format_artifact": FormatArtifactState,
    "download_request": DownloadRequestState,
    "revision_approval": RevisionApprovalState,
}

_PR = ProjectRunState
_RE = ReportEvidenceState
_FA = FormatArtifactState
_DL = DownloadRequestState
_RV = RevisionApprovalState


def _edge(
    family: str,
    from_state: Enum | None,
    to_state: Enum,
    trigger: str,
    guard_id: str,
) -> DeclaredEdge:
    return DeclaredEdge(
        family,
        None if from_state is None else from_state.value,
        to_state.value,
        trigger,
        guard_id,
    )


# ── 项目运行族（v1.2 §10.2）───────────────────────────────────────────────
PROJECT_TRANSITIONS: frozenset[DeclaredEdge] = frozenset(
    {
        # 新建 -> running：项目合同和包/能力预检记录已建立
        _edge(
            "project", None, _PR.RUNNING,
            "project_contract_and_preflight",
            "g_project_create_running",
        ),
        _edge(
            "project", _PR.RUNNING, _PR.AWAITING_USER,
            "double_exhaustion_critical_gap",
            "g_project_running_awaiting_user",
        ),
        _edge(
            "project", _PR.AWAITING_USER, _PR.RUNNING,
            "user_material_accepted_or_env_fixed",
            "g_project_awaiting_user_running",
        ),
        _edge(
            "project", _PR.RUNNING, _PR.PARTIALLY_DELIVERED,
            "first_artifact_delivery_ready",
            "g_project_running_partially_delivered",
        ),
        _edge(
            "project", _PR.PARTIALLY_DELIVERED, _PR.PARTIAL_DELIVERY_BLOCKED,
            "remaining_selected_blocked",
            "g_project_partially_delivered_partial_delivery_blocked",
        ),
        # 任一未完成态 -> blocked：固定源集合 {running, awaiting_user, partially_delivered}
        _edge(
            "project", _PR.RUNNING, _PR.BLOCKED,
            "no_deliverable_and_terminal_block",
            "g_project_any_incomplete_blocked",
        ),
        _edge(
            "project", _PR.AWAITING_USER, _PR.BLOCKED,
            "no_deliverable_and_terminal_block",
            "g_project_any_incomplete_blocked",
        ),
        _edge(
            "project", _PR.PARTIALLY_DELIVERED, _PR.BLOCKED,
            "no_deliverable_and_terminal_block",
            "g_project_any_incomplete_blocked",
        ),
        # 任一未完成态 -> complete：固定源集合展开
        _edge(
            "project", _PR.RUNNING, _PR.COMPLETE,
            "all_selected_delivery_ready",
            "g_project_any_incomplete_complete",
        ),
        _edge(
            "project", _PR.AWAITING_USER, _PR.COMPLETE,
            "all_selected_delivery_ready",
            "g_project_any_incomplete_complete",
        ),
        _edge(
            "project", _PR.PARTIALLY_DELIVERED, _PR.COMPLETE,
            "all_selected_delivery_ready",
            "g_project_any_incomplete_complete",
        ),
        # blocked / partial_delivery_blocked -> running：显式重新打开
        _edge(
            "project", _PR.BLOCKED, _PR.RUNNING,
            "explicit_reopen",
            "g_project_blocked_running",
        ),
        _edge(
            "project", _PR.PARTIAL_DELIVERY_BLOCKED, _PR.RUNNING,
            "explicit_reopen",
            "g_project_blocked_running",
        ),
    }
)

# ── 报告证据族：质控接受/可修复否决/不可修复穷尽阻断 ──────────────────────
REPORT_EVIDENCE_TRANSITIONS: frozenset[DeclaredEdge] = frozenset(
    {
        _edge(
            "report_evidence", _RE.QUEUED, _RE.COLLECTING,
            "candidate_scope_locked",
            "g_report_queued_collecting",
        ),
        _edge(
            "report_evidence", _RE.COLLECTING, _RE.RECOVERING,
            "first_gate_failure",
            "g_report_collecting_recovering",
        ),
        _edge(
            "report_evidence", _RE.COLLECTING, _RE.SCIENTIFIC_QC,
            "gate_deterministic_pass",
            "g_report_collecting_scientific_qc",
        ),
        _edge(
            "report_evidence", _RE.RECOVERING, _RE.SCIENTIFIC_QC,
            "gate_deterministic_pass",
            "g_report_recovering_scientific_qc",
        ),
        _edge(
            "report_evidence", _RE.SCIENTIFIC_QC, _RE.SNAPSHOT_LOCKED,
            "isolated_qc_accepted",
            "g_report_scientific_qc_snapshot_locked",
        ),
        # 质控否决若仍可修复，只能回 recovering
        _edge(
            "report_evidence", _RE.SCIENTIFIC_QC, _RE.RECOVERING,
            "qc_veto_fixable",
            "g_report_scientific_qc_recovering",
        ),
        _edge(
            "report_evidence", _RE.COLLECTING, _RE.EVIDENCE_BLOCKED,
            "recovery_exhausted_gap_remains",
            "g_report_collecting_evidence_blocked",
        ),
        _edge(
            "report_evidence", _RE.RECOVERING, _RE.EVIDENCE_BLOCKED,
            "recovery_exhausted_gap_remains",
            "g_report_recovering_evidence_blocked",
        ),
        # 质控否决且不可修复、恢复与独立审查穷尽、无继续用户动作才到 evidence_blocked
        _edge(
            "report_evidence", _RE.SCIENTIFIC_QC, _RE.EVIDENCE_BLOCKED,
            "qc_veto_unfixable_exhausted",
            "g_report_scientific_qc_evidence_blocked",
        ),
        _edge(
            "report_evidence", _RE.COLLECTING, _RE.AWAITING_USER,
            "recovery_exhausted_need_user",
            "g_report_collecting_awaiting_user",
        ),
        _edge(
            "report_evidence", _RE.RECOVERING, _RE.AWAITING_USER,
            "recovery_exhausted_need_user",
            "g_report_recovering_awaiting_user",
        ),
        _edge(
            "report_evidence", _RE.AWAITING_USER, _RE.RECOVERING,
            "user_input_accepted",
            "g_report_awaiting_user_recovering",
        ),
        # 锁定快照被明确取代：旧版本保持只读和可复现
        _edge(
            "report_evidence", _RE.SNAPSHOT_LOCKED, _RE.SUPERSEDED,
            "explicit_supersede",
            "g_report_snapshot_locked_superseded",
        ),
    }
)

# ── 格式产物族：顺序链、独立阻断/重开、交付后取代 ──────────────────────────
FORMAT_ARTIFACT_TRANSITIONS: frozenset[DeclaredEdge] = frozenset(
    {
        _edge(
            "format_artifact", _FA.QUEUED, _FA.GENERATING,
            "snapshot_locked_ready",
            "g_format_queued_generating",
        ),
        _edge(
            "format_artifact", _FA.GENERATING, _FA.QUALITY_CHECK,
            "artifact_built",
            "g_format_generating_quality_check",
        ),
        _edge(
            "format_artifact", _FA.QUALITY_CHECK, _FA.PASSED,
            "acceptance_records_complete",
            "g_format_quality_check_passed",
        ),
        _edge(
            "format_artifact", _FA.PASSED, _FA.DELIVERY_READY,
            "atomic_publish_manifest",
            "g_format_passed_delivery_ready",
        ),
        # 阻断独立于顺序链；格式恢复穷尽并保存失败证据
        _edge(
            "format_artifact", _FA.GENERATING, _FA.BLOCKED,
            "format_recovery_exhausted",
            "g_format_generating_blocked",
        ),
        _edge(
            "format_artifact", _FA.QUALITY_CHECK, _FA.BLOCKED,
            "format_recovery_exhausted",
            "g_format_quality_check_blocked",
        ),
        _edge(
            "format_artifact", _FA.BLOCKED, _FA.QUEUED,
            "environment_fixed_reopen",
            "g_format_blocked_queued",
        ),
        # 交付后取代保留旧版本
        _edge(
            "format_artifact", _FA.DELIVERY_READY, _FA.SUPERSEDED,
            "explicit_supersede",
            "g_format_delivery_ready_superseded",
        ),
    }
)

# ── 下载请求族：与已接受 Task 3.3 状态机逐边一致 ───────────────────────────
DOWNLOAD_REQUEST_TRANSITIONS: frozenset[DeclaredEdge] = frozenset(
    {
        _edge(
            "download_request", _DL.AWAITING_USER, _DL.FILE_DETECTED,
            "file_found_in_inbox",
            "g_download_awaiting_user_file_detected",
        ),
        _edge(
            "download_request", _DL.FILE_DETECTED, _DL.MATCHED,
            "unique_high_confidence_content_match",
            "g_download_file_detected_matched",
        ),
        _edge(
            "download_request", _DL.FILE_DETECTED, _DL.NEEDS_RE_DOWNLOAD,
            "invalid_or_ambiguous_file",
            "g_download_file_detected_needs_re_download",
        ),
        _edge(
            "download_request", _DL.MATCHED, _DL.NEEDS_RE_DOWNLOAD,
            "invalid_or_ambiguous_file",
            "g_download_matched_needs_re_download",
        ),
        _edge(
            "download_request", _DL.MATCHED, _DL.ACCEPTED,
            "content_accept_archive",
            "g_download_matched_accepted",
        ),
        _edge(
            "download_request", _DL.NEEDS_RE_DOWNLOAD, _DL.AWAITING_USER,
            "deduplicated_re_request",
            "g_download_needs_re_download_awaiting_user",
        ),
        # 扫描收件目录后未发现任何合法目标 → 直接需要重新下载
        _edge(
            "download_request", _DL.AWAITING_USER, _DL.NEEDS_RE_DOWNLOAD,
            "no_valid_target_in_inbox",
            "g_download_awaiting_user_needs_re_download",
        ),
        # 任一未接受态 -> not_required：固定源集合；不能掩盖仍失败的关键单元
        _edge(
            "download_request", _DL.AWAITING_USER, _DL.NOT_REQUIRED,
            "accepted_evidence_closed_gap",
            "g_download_awaiting_user_not_required",
        ),
        _edge(
            "download_request", _DL.FILE_DETECTED, _DL.NOT_REQUIRED,
            "accepted_evidence_closed_gap",
            "g_download_file_detected_not_required",
        ),
        _edge(
            "download_request", _DL.MATCHED, _DL.NOT_REQUIRED,
            "accepted_evidence_closed_gap",
            "g_download_matched_not_required",
        ),
        _edge(
            "download_request", _DL.NEEDS_RE_DOWNLOAD, _DL.NOT_REQUIRED,
            "accepted_evidence_closed_gap",
            "g_download_needs_re_download_not_required",
        ),
    }
)

# ── 修订审批族：验证与用户批准分离、批准 ID 幂等发布 ───────────────────────
REVISION_APPROVAL_TRANSITIONS: frozenset[DeclaredEdge] = frozenset(
    {
        # 验证：Agent 完成来源身份、上下文、冲突和影响验证并保存处置理由
        _edge(
            "revision_approval", _RV.SUBMITTED, _RV.NEEDS_EVIDENCE,
            "validation_needs_evidence",
            "g_revision_submitted_needs_evidence",
        ),
        _edge(
            "revision_approval", _RV.SUBMITTED, _RV.REJECTED,
            "validation_rejected",
            "g_revision_submitted_rejected",
        ),
        _edge(
            "revision_approval", _RV.SUBMITTED, _RV.VALIDATED_PENDING_USER_APPROVAL,
            "validation_passed",
            "g_revision_submitted_validated_pending_user_approval",
        ),
        _edge(
            "revision_approval", _RV.NEEDS_EVIDENCE, _RV.SUBMITTED,
            "new_evidence_appended",
            "g_revision_needs_evidence_submitted",
        ),
        # 用户批准：验证本身不能批准，必须由报告所有者显式决定
        _edge(
            "revision_approval", _RV.VALIDATED_PENDING_USER_APPROVAL, _RV.APPROVED,
            "owner_explicit_approval",
            "g_revision_validated_approved",
        ),
        _edge(
            "revision_approval", _RV.VALIDATED_PENDING_USER_APPROVAL, _RV.REJECTED,
            "owner_explicit_rejection",
            "g_revision_validated_rejected",
        ),
        _edge(
            "revision_approval", _RV.VALIDATED_PENDING_USER_APPROVAL, _RV.NEEDS_EVIDENCE,
            "owner_requests_evidence",
            "g_revision_validated_needs_evidence",
        ),
        # 发布：新快照、受影响产物重建与独立质控全部通过；以批准 ID 幂等
        _edge(
            "revision_approval", _RV.APPROVED, _RV.PUBLISHED,
            "publish_after_rebuild_qc",
            "g_revision_approved_published",
        ),
    }
)

ALL_DECLARED_TRANSITIONS: frozenset[DeclaredEdge] = (
    PROJECT_TRANSITIONS
    | REPORT_EVIDENCE_TRANSITIONS
    | FORMAT_ARTIFACT_TRANSITIONS
    | DOWNLOAD_REQUEST_TRANSITIONS
    | REVISION_APPROVAL_TRANSITIONS
)
