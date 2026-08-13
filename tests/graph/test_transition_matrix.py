"""Task 3.4 控制图迁移矩阵：v1.2 字面固定、结构化守卫、拒绝确定性与重放幂等。

本文件只含 GT01–GT06 六个顶层测试节点。所有期望边与守卫 ID 都是直接
写在测试里的 v1.2 字面 fixture；绝不从生产 registry/transition map 反向
生成期望，也不从生产枚举映射推导。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import pytest

ROOT = Path(__file__).resolve().parents[2]
_NOW = datetime(2026, 8, 13, 8, 0, tzinfo=UTC)


class LiteralEdge(NamedTuple):
    """v1.2 字面迁移边 fixture：family / from / to / trigger / guard_id。"""

    family: str
    from_state: str | None
    to_state: str
    trigger: str
    guard_id: str


# ── GT01 项目运行族：v1.2 §10.2 字面 fixture ───────────────────────────────

GT01_PROJECT_FIXTURE: tuple[LiteralEdge, ...] = (
    LiteralEdge(
        family="project",
        from_state=None,
        to_state="running",
        trigger="project_contract_and_preflight",
        guard_id="g_project_create_running",
    ),
    LiteralEdge(
        family="project",
        from_state="running",
        to_state="awaiting_user",
        trigger="double_exhaustion_critical_gap",
        guard_id="g_project_running_awaiting_user",
    ),
    LiteralEdge(
        family="project",
        from_state="awaiting_user",
        to_state="running",
        trigger="user_material_accepted_or_env_fixed",
        guard_id="g_project_awaiting_user_running",
    ),
    LiteralEdge(
        family="project",
        from_state="running",
        to_state="partially_delivered",
        trigger="first_artifact_delivery_ready",
        guard_id="g_project_running_partially_delivered",
    ),
    LiteralEdge(
        family="project",
        from_state="partially_delivered",
        to_state="partial_delivery_blocked",
        trigger="remaining_selected_blocked",
        guard_id="g_project_partially_delivered_partial_delivery_blocked",
    ),
    # v1.2 §10.2 勘误：有交付但剩余选定对象已穷尽阻断时，running /
    # awaiting_user 直接进入 partial_delivery_blocked（不需中间 partially_delivered）
    LiteralEdge(
        family="project",
        from_state="running",
        to_state="partial_delivery_blocked",
        trigger="remaining_selected_blocked",
        guard_id="g_project_partially_delivered_partial_delivery_blocked",
    ),
    LiteralEdge(
        family="project",
        from_state="awaiting_user",
        to_state="partial_delivery_blocked",
        trigger="remaining_selected_blocked",
        guard_id="g_project_partially_delivered_partial_delivery_blocked",
    ),
    # 任一未完成态 -> blocked：固定源集合展开，不用宽松通配符
    LiteralEdge(
        family="project",
        from_state="running",
        to_state="blocked",
        trigger="no_deliverable_and_terminal_block",
        guard_id="g_project_any_incomplete_blocked",
    ),
    LiteralEdge(
        family="project",
        from_state="awaiting_user",
        to_state="blocked",
        trigger="no_deliverable_and_terminal_block",
        guard_id="g_project_any_incomplete_blocked",
    ),
    LiteralEdge(
        family="project",
        from_state="partially_delivered",
        to_state="blocked",
        trigger="no_deliverable_and_terminal_block",
        guard_id="g_project_any_incomplete_blocked",
    ),
    # 任一未完成态 -> complete：固定源集合展开
    LiteralEdge(
        family="project",
        from_state="running",
        to_state="complete",
        trigger="all_selected_delivery_ready",
        guard_id="g_project_any_incomplete_complete",
    ),
    LiteralEdge(
        family="project",
        from_state="awaiting_user",
        to_state="complete",
        trigger="all_selected_delivery_ready",
        guard_id="g_project_any_incomplete_complete",
    ),
    LiteralEdge(
        family="project",
        from_state="partially_delivered",
        to_state="complete",
        trigger="all_selected_delivery_ready",
        guard_id="g_project_any_incomplete_complete",
    ),
    # blocked / partial_delivery_blocked -> running：显式重新打开
    LiteralEdge(
        family="project",
        from_state="blocked",
        to_state="running",
        trigger="explicit_reopen",
        guard_id="g_project_blocked_running",
    ),
    LiteralEdge(
        family="project",
        from_state="partial_delivery_blocked",
        to_state="running",
        trigger="explicit_reopen",
        guard_id="g_project_blocked_running",
    ),
)

GT01_VALID_EVIDENCE: dict[str, dict[str, object]] = {
    "g_project_create_running": {
        "project_contract_established": True,
        "preflight_records_established": True,
    },
    "g_project_running_awaiting_user": {
        "double_exhaustion_complete": True,
        "critical_gap_remains": True,
        "audit_package_written": True,
        "request_written": True,
        "audit_package_path": "blockers/A/v1/",
    },
    "g_project_awaiting_user_running": {"user_material_accepted": True},
    "g_project_running_partially_delivered": {
        "at_least_one_artifact_delivery_ready": True,
        "selected_objects_continuable": True,
    },
    "g_project_partially_delivered_partial_delivery_blocked": {
        "at_least_one_artifact_delivered": True,
        "remaining_selected_exhausted_blocked": True,
        "no_running_selected_object": True,
    },
    "g_project_any_incomplete_blocked": {
        "no_deliverable_artifact": True,
        "at_least_one_terminal_blocked": True,
        "no_running_selected_object": True,
    },
    "g_project_any_incomplete_complete": {
        "all_selected_html_delivery_ready": True,
        "all_selected_optional_formats_delivery_ready": True,
    },
    "g_project_blocked_running": {"user_material_accepted": True},
}

GT01_CONTRADICTIONS: dict[str, tuple[tuple[str, str], ...]] = {}


# ── GT02 报告证据族：质控接受/可修复否决/不可修复穷尽阻断 ─────────────────

GT02_REPORT_FIXTURE: tuple[LiteralEdge, ...] = (
    LiteralEdge(
        family="report_evidence",
        from_state="queued",
        to_state="collecting",
        trigger="candidate_scope_locked",
        guard_id="g_report_queued_collecting",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="collecting",
        to_state="recovering",
        trigger="first_gate_failure",
        guard_id="g_report_collecting_recovering",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="collecting",
        to_state="scientific_qc",
        trigger="gate_deterministic_pass",
        guard_id="g_report_collecting_scientific_qc",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="recovering",
        to_state="scientific_qc",
        trigger="gate_deterministic_pass",
        guard_id="g_report_recovering_scientific_qc",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="scientific_qc",
        to_state="snapshot_locked",
        trigger="isolated_qc_accepted",
        guard_id="g_report_scientific_qc_snapshot_locked",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="scientific_qc",
        to_state="recovering",
        trigger="qc_veto_fixable",
        guard_id="g_report_scientific_qc_recovering",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="collecting",
        to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        guard_id="g_report_collecting_evidence_blocked",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="recovering",
        to_state="evidence_blocked",
        trigger="recovery_exhausted_gap_remains",
        guard_id="g_report_recovering_evidence_blocked",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="scientific_qc",
        to_state="evidence_blocked",
        trigger="qc_veto_unfixable_exhausted",
        guard_id="g_report_scientific_qc_evidence_blocked",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="collecting",
        to_state="awaiting_user",
        trigger="recovery_exhausted_need_user",
        guard_id="g_report_collecting_awaiting_user",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="recovering",
        to_state="awaiting_user",
        trigger="recovery_exhausted_need_user",
        guard_id="g_report_recovering_awaiting_user",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="awaiting_user",
        to_state="recovering",
        trigger="user_input_accepted",
        guard_id="g_report_awaiting_user_recovering",
    ),
    LiteralEdge(
        family="report_evidence",
        from_state="snapshot_locked",
        to_state="superseded",
        trigger="explicit_supersede",
        guard_id="g_report_snapshot_locked_superseded",
    ),
)

GT02_VALID_EVIDENCE: dict[str, dict[str, object]] = {
    "g_report_queued_collecting": {"candidate_scope_locked": True},
    "g_report_collecting_recovering": {
        "candidate_scope_locked": True,
        "first_gate_failure": True,
    },
    "g_report_collecting_scientific_qc": {
        "gate_deterministic_pass": True,
        "candidate_snapshot_established": True,
    },
    "g_report_recovering_scientific_qc": {
        "gate_deterministic_pass": True,
        "candidate_snapshot_established": True,
    },
    "g_report_scientific_qc_snapshot_locked": {
        "isolated_qc_accepted": True,
        "qc_verdict_id": "qc-verdict-1",
        "qc_verdict_digest": "a" * 64,
        "qc_candidate_snapshot_id": "snap-1",
        "qc_candidate_content_digest": "b" * 64,
        "qc_review_input_digest": "c" * 64,
        "qc_report_object_id": "obj_probe",
        "qc_context_digest": "d" * 64,
        "qc_authorization_id": "auth-1",
    },
    "g_report_scientific_qc_recovering": {
        "qc_veto": True,
        "qc_veto_fixable": True,
        "qc_verdict_id": "qc-verdict-1",
        "qc_verdict_digest": "a" * 64,
        "qc_candidate_snapshot_id": "snap-1",
        "qc_candidate_content_digest": "b" * 64,
        "qc_review_input_digest": "c" * 64,
        "qc_report_object_id": "obj_probe",
        "qc_context_digest": "d" * 64,
        "qc_authorization_id": "auth-1",
    },
    "g_report_collecting_evidence_blocked": {
        "critical_units_still_failing": True,
        "recovery_exhausted": True,
        "independent_review_exhausted": True,
        "no_continuable_user_action": True,
    },
    "g_report_recovering_evidence_blocked": {
        "critical_units_still_failing": True,
        "recovery_exhausted": True,
        "independent_review_exhausted": True,
        "no_continuable_user_action": True,
    },
    "g_report_scientific_qc_evidence_blocked": {
        "qc_veto": True,
        "qc_veto_unfixable": True,
        "recovery_exhausted": True,
        "independent_review_exhausted": True,
        "no_continuable_user_action": True,
        "qc_verdict_id": "qc-verdict-1",
        "qc_verdict_digest": "a" * 64,
        "qc_candidate_snapshot_id": "snap-1",
        "qc_candidate_content_digest": "b" * 64,
        "qc_review_input_digest": "c" * 64,
        "qc_report_object_id": "obj_probe",
        "qc_context_digest": "d" * 64,
        "qc_exhaustion_record_digest": "e" * 64,
        "qc_authorization_id": "auth-1",
    },
    "g_report_collecting_awaiting_user": {
        "recovery_exhausted": True,
        "critical_gap_remains": True,
        "audit_package_written": True,
        "request_written": True,
        "audit_package_path": "blockers/A/v1/",
    },
    "g_report_recovering_awaiting_user": {
        "recovery_exhausted": True,
        "critical_gap_remains": True,
        "audit_package_written": True,
        "request_written": True,
        "audit_package_path": "blockers/A/v1/",
    },
    "g_report_awaiting_user_recovering": {"required_file_accepted": True},
    "g_report_snapshot_locked_superseded": {"new_version_explicitly_supersedes": True},
}

GT02_CONTRADICTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "g_report_scientific_qc_snapshot_locked": (("isolated_qc_accepted", "qc_veto"),),
    "g_report_scientific_qc_recovering": (("qc_veto", "isolated_qc_accepted"),),
    "g_report_scientific_qc_evidence_blocked": (("qc_veto_fixable", "qc_veto_unfixable"),),
}


# ── GT03 格式产物族：顺序链、独立阻断/重开、交付后取代 ─────────────────────

GT03_FORMAT_FIXTURE: tuple[LiteralEdge, ...] = (
    LiteralEdge(
        family="format_artifact",
        from_state="queued",
        to_state="generating",
        trigger="snapshot_locked_ready",
        guard_id="g_format_queued_generating",
    ),
    LiteralEdge(
        family="format_artifact",
        from_state="generating",
        to_state="quality_check",
        trigger="artifact_built",
        guard_id="g_format_generating_quality_check",
    ),
    LiteralEdge(
        family="format_artifact",
        from_state="quality_check",
        to_state="passed",
        trigger="acceptance_records_complete",
        guard_id="g_format_quality_check_passed",
    ),
    LiteralEdge(
        family="format_artifact",
        from_state="passed",
        to_state="delivery_ready",
        trigger="atomic_publish_manifest",
        guard_id="g_format_passed_delivery_ready",
    ),
    LiteralEdge(
        family="format_artifact",
        from_state="generating",
        to_state="blocked",
        trigger="format_recovery_exhausted",
        guard_id="g_format_generating_blocked",
    ),
    LiteralEdge(
        family="format_artifact",
        from_state="quality_check",
        to_state="blocked",
        trigger="format_recovery_exhausted",
        guard_id="g_format_quality_check_blocked",
    ),
    LiteralEdge(
        family="format_artifact",
        from_state="blocked",
        to_state="queued",
        trigger="environment_fixed_reopen",
        guard_id="g_format_blocked_queued",
    ),
    LiteralEdge(
        family="format_artifact",
        from_state="delivery_ready",
        to_state="superseded",
        trigger="explicit_supersede",
        guard_id="g_format_delivery_ready_superseded",
    ),
)

GT03_VALID_EVIDENCE: dict[str, dict[str, object]] = {
    "g_format_queued_generating": {"report_snapshot_locked": True},
    "g_format_generating_quality_check": {"artifact_built": True},
    "g_format_quality_check_passed": {
        "deterministic_check_recorded": True,
        "coverage_check_recorded": True,
        "real_render_check_recorded": True,
    },
    "g_format_passed_delivery_ready": {
        "atomic_publish_complete": True,
        "manifest_digest_recorded": True,
    },
    "g_format_generating_blocked": {
        "format_recovery_exhausted": True,
        "failure_evidence_saved": True,
    },
    "g_format_quality_check_blocked": {
        "format_recovery_exhausted": True,
        "failure_evidence_saved": True,
    },
    "g_format_blocked_queued": {"environment_fixed": True},
    "g_format_delivery_ready_superseded": {"new_version_explicitly_supersedes": True},
}

GT03_CONTRADICTIONS: dict[str, tuple[tuple[str, str], ...]] = {}


# ── GT04 下载请求族：与已接受 Task 3.3 状态机逐边一致 ──────────────────────

GT04_DOWNLOAD_FIXTURE: tuple[LiteralEdge, ...] = (
    LiteralEdge(
        family="download_request",
        from_state="awaiting_user",
        to_state="file_detected",
        trigger="file_found_in_inbox",
        guard_id="g_download_awaiting_user_file_detected",
    ),
    LiteralEdge(
        family="download_request",
        from_state="file_detected",
        to_state="matched",
        trigger="unique_high_confidence_content_match",
        guard_id="g_download_file_detected_matched",
    ),
    LiteralEdge(
        family="download_request",
        from_state="file_detected",
        to_state="needs_re_download",
        trigger="invalid_or_ambiguous_file",
        guard_id="g_download_file_detected_needs_re_download",
    ),
    LiteralEdge(
        family="download_request",
        from_state="matched",
        to_state="needs_re_download",
        trigger="invalid_or_ambiguous_file",
        guard_id="g_download_matched_needs_re_download",
    ),
    LiteralEdge(
        family="download_request",
        from_state="matched",
        to_state="accepted",
        trigger="content_accept_archive",
        guard_id="g_download_matched_accepted",
    ),
    LiteralEdge(
        family="download_request",
        from_state="needs_re_download",
        to_state="awaiting_user",
        trigger="deduplicated_re_request",
        guard_id="g_download_needs_re_download_awaiting_user",
    ),
    LiteralEdge(
        family="download_request",
        from_state="awaiting_user",
        to_state="needs_re_download",
        trigger="no_valid_target_in_inbox",
        guard_id="g_download_awaiting_user_needs_re_download",
    ),
    # 任一未接受态 -> not_required：固定源集合
    LiteralEdge(
        family="download_request",
        from_state="awaiting_user",
        to_state="not_required",
        trigger="accepted_evidence_closed_gap",
        guard_id="g_download_awaiting_user_not_required",
    ),
    LiteralEdge(
        family="download_request",
        from_state="file_detected",
        to_state="not_required",
        trigger="accepted_evidence_closed_gap",
        guard_id="g_download_file_detected_not_required",
    ),
    LiteralEdge(
        family="download_request",
        from_state="matched",
        to_state="not_required",
        trigger="accepted_evidence_closed_gap",
        guard_id="g_download_matched_not_required",
    ),
    LiteralEdge(
        family="download_request",
        from_state="needs_re_download",
        to_state="not_required",
        trigger="accepted_evidence_closed_gap",
        guard_id="g_download_needs_re_download_not_required",
    ),
)

GT04_VALID_EVIDENCE: dict[str, dict[str, object]] = {
    "g_download_awaiting_user_file_detected": {
        "new_file_detected": True,
        "inbox_scan_complete": True,
    },
    "g_download_file_detected_matched": {
        "unique_high_confidence_match": True,
        "content_sha256": "0" * 64,
    },
    "g_download_file_detected_needs_re_download": {
        "quarantined": True,
        "reason_recorded": True,
        "file_incomplete": True,
    },
    "g_download_matched_needs_re_download": {
        "quarantined": True,
        "reason_recorded": True,
        "identity_ambiguous": True,
    },
    "g_download_matched_accepted": {
        "type_valid": True,
        "integrity_valid": True,
        "identity_valid": True,
        "digest_valid": True,
        "parent_child_valid": True,
        "canonical_naming_valid": True,
        "atomic_archive_complete": True,
    },
    "g_download_needs_re_download_awaiting_user": {"deduplicated_request_generated": True},
    "g_download_awaiting_user_needs_re_download": {"no_valid_target_in_inbox": True},
    "g_download_awaiting_user_not_required": {
        "gap_closed_by_accepted_evidence": True,
        "reason_zh": "已由接受证据关闭",
    },
    "g_download_file_detected_not_required": {
        "gap_closed_by_accepted_evidence": True,
        "reason_zh": "已由接受证据关闭",
    },
    "g_download_matched_not_required": {
        "gap_closed_by_accepted_evidence": True,
        "reason_zh": "已由接受证据关闭",
    },
    "g_download_needs_re_download_not_required": {
        "gap_closed_by_accepted_evidence": True,
        "reason_zh": "已由接受证据关闭",
    },
}

GT04_CONTRADICTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "g_download_file_detected_matched": (("unique_high_confidence_match", "ambiguous_match"),),
    "g_download_awaiting_user_not_required": (
        ("gap_closed_by_accepted_evidence", "gap_still_open"),
    ),
    "g_download_file_detected_not_required": (
        ("gap_closed_by_accepted_evidence", "gap_still_open"),
    ),
    "g_download_matched_not_required": (
        ("gap_closed_by_accepted_evidence", "gap_still_open"),
    ),
    "g_download_needs_re_download_not_required": (
        ("gap_closed_by_accepted_evidence", "gap_still_open"),
    ),
}


# ── GT05 修订审批族：验证与用户批准分离、批准 ID 幂等发布 ──────────────────

GT05_REVISION_FIXTURE: tuple[LiteralEdge, ...] = (
    LiteralEdge(
        family="revision_approval",
        from_state="submitted",
        to_state="needs_evidence",
        trigger="validation_needs_evidence",
        guard_id="g_revision_submitted_needs_evidence",
    ),
    LiteralEdge(
        family="revision_approval",
        from_state="submitted",
        to_state="rejected",
        trigger="validation_rejected",
        guard_id="g_revision_submitted_rejected",
    ),
    LiteralEdge(
        family="revision_approval",
        from_state="submitted",
        to_state="validated_pending_user_approval",
        trigger="validation_passed",
        guard_id="g_revision_submitted_validated_pending_user_approval",
    ),
    LiteralEdge(
        family="revision_approval",
        from_state="needs_evidence",
        to_state="submitted",
        trigger="new_evidence_appended",
        guard_id="g_revision_needs_evidence_submitted",
    ),
    LiteralEdge(
        family="revision_approval",
        from_state="validated_pending_user_approval",
        to_state="approved",
        trigger="owner_explicit_approval",
        guard_id="g_revision_validated_approved",
    ),
    LiteralEdge(
        family="revision_approval",
        from_state="validated_pending_user_approval",
        to_state="rejected",
        trigger="owner_explicit_rejection",
        guard_id="g_revision_validated_rejected",
    ),
    LiteralEdge(
        family="revision_approval",
        from_state="validated_pending_user_approval",
        to_state="needs_evidence",
        trigger="owner_requests_evidence",
        guard_id="g_revision_validated_needs_evidence",
    ),
    LiteralEdge(
        family="revision_approval",
        from_state="approved",
        to_state="published",
        trigger="publish_after_rebuild_qc",
        guard_id="g_revision_approved_published",
    ),
)

GT05_VALID_EVIDENCE: dict[str, dict[str, object]] = {
    "g_revision_submitted_needs_evidence": {
        "validation_complete": True,
        "needs_more_evidence": True,
        "disposition_reason_saved": True,
    },
    "g_revision_submitted_rejected": {
        "validation_complete": True,
        "validation_rejected": True,
        "disposition_reason_saved": True,
    },
    "g_revision_submitted_validated_pending_user_approval": {
        "validation_complete": True,
        "validation_passed": True,
        "disposition_reason_saved": True,
    },
    "g_revision_needs_evidence_submitted": {"new_evidence_appended": True, "evidence_id": "ev_1"},
    "g_revision_validated_approved": {"owner_explicit_decision": True, "decision_approve": True},
    "g_revision_validated_rejected": {"owner_explicit_decision": True, "decision_reject": True},
    "g_revision_validated_needs_evidence": {
        "owner_explicit_decision": True,
        "decision_needs_evidence": True,
    },
    "g_revision_approved_published": {
        "new_snapshot_built": True,
        "affected_artifacts_rebuilt": True,
        "independent_qc_passed": True,
        "approval_id": "rev_001",
    },
}

GT05_CONTRADICTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "g_revision_submitted_needs_evidence": (
        ("validation_passed", "validation_rejected"),
        ("validation_passed", "needs_more_evidence"),
        ("validation_rejected", "needs_more_evidence"),
    ),
    "g_revision_submitted_rejected": (
        ("validation_passed", "validation_rejected"),
        ("validation_passed", "needs_more_evidence"),
        ("validation_rejected", "needs_more_evidence"),
    ),
    "g_revision_submitted_validated_pending_user_approval": (
        ("validation_passed", "validation_rejected"),
        ("validation_passed", "needs_more_evidence"),
        ("validation_rejected", "needs_more_evidence"),
    ),
    "g_revision_validated_approved": (
        ("decision_approve", "decision_reject"),
        ("decision_approve", "decision_needs_evidence"),
        ("decision_reject", "decision_needs_evidence"),
    ),
    "g_revision_validated_rejected": (
        ("decision_approve", "decision_reject"),
        ("decision_approve", "decision_needs_evidence"),
        ("decision_reject", "decision_needs_evidence"),
    ),
    "g_revision_validated_needs_evidence": (
        ("decision_approve", "decision_reject"),
        ("decision_approve", "decision_needs_evidence"),
        ("decision_reject", "decision_needs_evidence"),
    ),
}


_ALL_VALID_EVIDENCE: dict[str, dict[str, object]] = {
    **GT01_VALID_EVIDENCE,
    **GT02_VALID_EVIDENCE,
    **GT03_VALID_EVIDENCE,
    **GT04_VALID_EVIDENCE,
    **GT05_VALID_EVIDENCE,
}

# 类型化起始状态（字面 fixture）：与 v1.2 固定起始语义一致
_FAMILY_DEFAULTS: dict[str, str | None] = {
    "project": None,
    "report_evidence": "queued",
    "format_artifact": "queued",
    "download_request": "awaiting_user",
    "revision_approval": "submitted",
}


def _fixture_edges() -> dict[str, tuple[LiteralEdge, ...]]:
    """按族聚合本文件内的字面 fixture 边（绝不引用生产表）。"""
    by_family: dict[str, list[LiteralEdge]] = {}
    for edge in (
        *GT01_PROJECT_FIXTURE,
        *GT02_REPORT_FIXTURE,
        *GT03_FORMAT_FIXTURE,
        *GT04_DOWNLOAD_FIXTURE,
        *GT05_REVISION_FIXTURE,
    ):
        by_family.setdefault(edge.family, []).append(edge)
    return {family: tuple(edges) for family, edges in by_family.items()}


_FIXTURE_EDGES: dict[str, tuple[LiteralEdge, ...]] = _fixture_edges()


def _positioning_path(family: str, target: str) -> tuple[LiteralEdge, ...]:
    """在字面 fixture 边内从类型化起始状态 BFS 到目标源状态的合法路径。"""
    start = _FAMILY_DEFAULTS[family]
    frontier: list[tuple[str | None, tuple[LiteralEdge, ...]]] = [(start, ())]
    seen: set[str | None] = {start}
    while frontier:
        current, path = frontier.pop(0)
        if current == target:
            return path
        for edge in _FIXTURE_EDGES[family]:
            if edge.from_state == current and edge.to_state not in seen:
                seen.add(edge.to_state)
                frontier.append((edge.to_state, (*path, edge)))
    raise AssertionError(f"字面 fixture 中不存在到 {family}:{target} 的声明路径")


def _assert_family_frozen(
    *,
    fixture: tuple[LiteralEdge, ...],
    valid_evidence: dict[str, dict[str, object]],
    contradictions: dict[str, tuple[tuple[str, str], ...]],
) -> None:
    """字面 fixture 与生产注册表逐边相等（missing=0 extra=0），并验证守卫。

    守卫必须是结构化证据求值：缺失证据拒绝、任一必需键翻转拒绝、字面矛盾对拒绝。
    """
    from ci_workflow.graph.registry import TRANSITION_REGISTRY

    family = fixture[0].family
    expected = set(fixture)
    actual = {
        LiteralEdge(
            edge.family,
            edge.from_state,
            edge.to_state,
            edge.trigger,
            edge.guard_id,
        )
        for edge in TRANSITION_REGISTRY.declared_edges(family)
    }
    assert actual == expected, (
        f"family={family} missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
    )
    for edge in fixture:
        guard_id = edge.guard_id
        assert guard_id in TRANSITION_REGISTRY.guard_ids(), f"缺少守卫 {guard_id}"
        # 缺失证据必须拒绝（结构化证据，不是 allowed=True 绕过）
        missing = TRANSITION_REGISTRY.evaluate_guard(
            guard_id, {}, target_family=family, target_object_id="obj_probe"
        )
        assert missing.allowed is False, f"{guard_id} 空证据不应通过"
        assert missing.reason.startswith("missing_evidence:"), f"{guard_id}: {missing.reason}"
        # 有效证据通过
        valid = TRANSITION_REGISTRY.evaluate_guard(
            guard_id,
            valid_evidence[guard_id],
            target_family=family,
            target_object_id="obj_probe",
        )
        assert valid.allowed is True, f"{guard_id}: {valid.reason}"
        # 任一必需真键被翻转成 False → 拒绝
        flipped = False
        for key, value in valid_evidence[guard_id].items():
            if value is True:
                altered = dict(valid_evidence[guard_id])
                altered[key] = False
                flipped_result = TRANSITION_REGISTRY.evaluate_guard(
                    guard_id,
                    altered,
                    target_family=family,
                    target_object_id="obj_probe",
                )
                assert flipped_result.allowed is False, f"{guard_id} 翻转 {key} 后不应通过"
                flipped = True
                break
        assert flipped, f"{guard_id} 的有效证据必须包含至少一个布尔键"
        # 字面矛盾对 → 拒绝
        for first, second in contradictions.get(guard_id, ()):
            evidence = dict(valid_evidence[guard_id])
            evidence[first] = True
            evidence[second] = True
            result = TRANSITION_REGISTRY.evaluate_guard(
                guard_id,
                evidence,
                target_family=family,
                target_object_id="obj_probe",
            )
            assert result.allowed is False, f"{guard_id} 矛盾对 {first}/{second} 不应通过"
            assert "contradictory_evidence" in result.reason, f"{guard_id}: {result.reason}"


def test_project_run_transitions_and_guards_match_v12() -> None:
    """GT01：项目运行族迁移与守卫逐边冻结为 v1.2 字面 fixture。"""
    _assert_family_frozen(
        fixture=GT01_PROJECT_FIXTURE,
        valid_evidence=GT01_VALID_EVIDENCE,
        contradictions=GT01_CONTRADICTIONS,
    )


def test_report_evidence_transitions_and_guards_match_v12() -> None:
    """GT02：报告证据族；质控接受才锁定、可修复否决只回 recovering、
    不可修复且穷尽才到 evidence_blocked。"""
    from ci_workflow.graph.registry import TRANSITION_REGISTRY

    _assert_family_frozen(
        fixture=GT02_REPORT_FIXTURE,
        valid_evidence=GT02_VALID_EVIDENCE,
        contradictions=GT02_CONTRADICTIONS,
    )
    # 科学质控：接受 → snapshot_locked；可修复否决 → recovering；不可修复且穷尽 → evidence_blocked
    accepted = TRANSITION_REGISTRY.declared("report_evidence", "scientific_qc", "snapshot_locked")
    assert accepted is not None and accepted.guard_id == "g_report_scientific_qc_snapshot_locked"
    fixable = TRANSITION_REGISTRY.declared("report_evidence", "scientific_qc", "recovering")
    assert fixable is not None and fixable.guard_id == "g_report_scientific_qc_recovering"
    unfixable = TRANSITION_REGISTRY.declared("report_evidence", "scientific_qc", "evidence_blocked")
    assert unfixable is not None and unfixable.guard_id == "g_report_scientific_qc_evidence_blocked"
    # 否决与接受同时出现（矛盾证据）不能锁定快照
    contradictory = TRANSITION_REGISTRY.evaluate_guard(
        "g_report_scientific_qc_snapshot_locked",
        {
            **GT02_VALID_EVIDENCE["g_report_scientific_qc_snapshot_locked"],
            "qc_veto": True,
        },
        target_family="report_evidence",
        target_object_id="obj_probe",
    )
    assert contradictory.allowed is False
    assert "contradictory_evidence" in contradictory.reason
    # 否决但未声明可修复 → 不能回 recovering
    not_fixable = TRANSITION_REGISTRY.evaluate_guard(
        "g_report_scientific_qc_recovering",
        {
            **GT02_VALID_EVIDENCE["g_report_scientific_qc_recovering"],
            "qc_veto_fixable": False,
        },
        target_family="report_evidence",
        target_object_id="obj_probe",
    )
    assert not_fixable.allowed is False
    # 裸布尔（无验证授权材料）→ 不能锁定
    naked = TRANSITION_REGISTRY.evaluate_guard(
        "g_report_scientific_qc_snapshot_locked",
        {"isolated_qc_accepted": True},
        target_family="report_evidence",
        target_object_id="obj_probe",
    )
    assert naked.allowed is False
    assert naked.reason.startswith("missing_evidence:qc_verdict_id")
    # 非 SHA 摘要授权 → 拒绝
    bad_digest = TRANSITION_REGISTRY.evaluate_guard(
        "g_report_scientific_qc_snapshot_locked",
        {
            **GT02_VALID_EVIDENCE["g_report_scientific_qc_snapshot_locked"],
            "qc_verdict_digest": "not-a-digest",
        },
        target_family="report_evidence",
        target_object_id="obj_probe",
    )
    assert bad_digest.allowed is False
    assert bad_digest.reason.startswith("guard_not_satisfied:qc_verdict_digest")
    # 错对象授权 → 拒绝
    wrong_obj = TRANSITION_REGISTRY.evaluate_guard(
        "g_report_scientific_qc_snapshot_locked",
        {
            **GT02_VALID_EVIDENCE["g_report_scientific_qc_snapshot_locked"],
            "qc_report_object_id": "report_OTHER",
        },
        target_family="report_evidence",
        target_object_id="obj_probe",
    )
    assert wrong_obj.allowed is False
    assert wrong_obj.reason.startswith("scope_mismatch:object:qc_report_object_id")
    # ── 互斥路径证据（P1）：跨路径标志组合全部拒绝 ───────────────────────────
    # 接受路径：任何否决/恢复/穷尽标志 → 拒绝
    acc = GT02_VALID_EVIDENCE["g_report_scientific_qc_snapshot_locked"]
    for flag in (
        "qc_veto",
        "qc_veto_fixable",
        "qc_veto_unfixable",
        "recovery_exhausted",
        "independent_review_exhausted",
        "no_continuable_user_action",
    ):
        cross = TRANSITION_REGISTRY.evaluate_guard(
            "g_report_scientific_qc_snapshot_locked",
            {**acc, flag: True},
            target_family="report_evidence",
            target_object_id="obj_probe",
        )
        assert cross.allowed is False, f"accepted+{flag} 不应通过"
        assert cross.reason.startswith("contradictory_evidence"), cross.reason
    # 可修复否决路径：不可修复/穷尽标志与记录 → 拒绝
    rec = GT02_VALID_EVIDENCE["g_report_scientific_qc_recovering"]
    for flag in (
        "qc_veto_unfixable",
        "recovery_exhausted",
        "independent_review_exhausted",
        "no_continuable_user_action",
        "qc_exhaustion_record_digest",
    ):
        cross = TRANSITION_REGISTRY.evaluate_guard(
            "g_report_scientific_qc_recovering",
            {**rec, flag: True},
            target_family="report_evidence",
            target_object_id="obj_probe",
        )
        assert cross.allowed is False, f"recovering+{flag} 不应通过"
    # 可修复 + 不可修复标志并存 → 拒绝
    fixable_unfixable = TRANSITION_REGISTRY.evaluate_guard(
        "g_report_scientific_qc_recovering",
        {**rec, "qc_veto_unfixable": True},
        target_family="report_evidence",
        target_object_id="obj_probe",
    )
    assert fixable_unfixable.allowed is False
    # 已穷尽路径：接受/可修复标志 → 拒绝
    exh = GT02_VALID_EVIDENCE["g_report_scientific_qc_evidence_blocked"]
    for flag in ("isolated_qc_accepted", "qc_veto_fixable"):
        cross = TRANSITION_REGISTRY.evaluate_guard(
            "g_report_scientific_qc_evidence_blocked",
            {**exh, flag: True},
            target_family="report_evidence",
            target_object_id="obj_probe",
        )
        assert cross.allowed is False, f"evidence_blocked+{flag} 不应通过"
        assert cross.reason.startswith("contradictory_evidence"), cross.reason
    # 已穷尽路径缺穷尽记录摘要 → 拒绝（missing_evidence）
    no_record = TRANSITION_REGISTRY.evaluate_guard(
        "g_report_scientific_qc_evidence_blocked",
        {k: v for k, v in exh.items() if k != "qc_exhaustion_record_digest"},
        target_family="report_evidence",
        target_object_id="obj_probe",
    )
    assert no_record.allowed is False
    assert no_record.reason.startswith("missing_evidence:qc_exhaustion_record_digest")


def test_artifact_transitions_and_guards_match_v12() -> None:
    """GT03：格式产物族；顺序链、独立阻断/重开、delivery_ready 后取代。"""
    from ci_workflow.graph.registry import TRANSITION_REGISTRY

    _assert_family_frozen(
        fixture=GT03_FORMAT_FIXTURE,
        valid_evidence=GT03_VALID_EVIDENCE,
        contradictions=GT03_CONTRADICTIONS,
    )
    # 顺序链必须是 queued -> generating -> quality_check -> passed -> delivery_ready
    chain = (
        ("queued", "generating"),
        ("generating", "quality_check"),
        ("quality_check", "passed"),
        ("passed", "delivery_ready"),
    )
    for from_state, to_state in chain:
        assert TRANSITION_REGISTRY.declared("format_artifact", from_state, to_state) is not None
    # 阻断/重开独立于顺序链
    blocked_guards = {
        "generating": "g_format_generating_blocked",
        "quality_check": "g_format_quality_check_blocked",
    }
    for from_state, expected_guard in blocked_guards.items():
        edge = TRANSITION_REGISTRY.declared("format_artifact", from_state, "blocked")
        assert edge is not None and edge.guard_id == expected_guard
    assert TRANSITION_REGISTRY.declared("format_artifact", "blocked", "queued") is not None
    # 交付后取代保留旧版本
    supersede = TRANSITION_REGISTRY.declared("format_artifact", "delivery_ready", "superseded")
    assert supersede is not None and supersede.guard_id == "g_format_delivery_ready_superseded"


def test_download_request_transitions_and_guards_match_v12() -> None:
    """GT04：下载请求族逐边冻结，且与已接受 Task 3.3 状态机零漂移。"""
    from ci_workflow.graph.registry import TRANSITION_REGISTRY
    from ci_workflow.ingestion.manual_inbox import _DECLARED_TRANSITIONS

    _assert_family_frozen(
        fixture=GT04_DOWNLOAD_FIXTURE,
        valid_evidence=GT04_VALID_EVIDENCE,
        contradictions=GT04_CONTRADICTIONS,
    )
    # 漂移检查：Task 3.4 通用迁移表不得与 Task 3.3 已接受实现漂移
    graph_pairs = {
        (edge.from_state, edge.to_state)
        for edge in TRANSITION_REGISTRY.declared_edges("download_request")
    }
    task33_pairs = {(a.value, b.value) for a, b in _DECLARED_TRANSITIONS}
    assert graph_pairs == task33_pairs
    # accepted 是不可再迁移的终态（无 declared 边）
    assert TRANSITION_REGISTRY.declared("download_request", "accepted", "not_required") is None


def test_revision_approval_transitions_and_guards_match_v12() -> None:
    """GT05：修订审批族；验证与用户批准分离，发布以批准 ID 幂等。"""
    from ci_workflow.graph.registry import TRANSITION_REGISTRY

    _assert_family_frozen(
        fixture=GT05_REVISION_FIXTURE,
        valid_evidence=GT05_VALID_EVIDENCE,
        contradictions=GT05_CONTRADICTIONS,
    )
    validate = TRANSITION_REGISTRY.declared(
        "revision_approval", "submitted", "validated_pending_user_approval"
    )
    approve = TRANSITION_REGISTRY.declared(
        "revision_approval", "validated_pending_user_approval", "approved"
    )
    publish = TRANSITION_REGISTRY.declared("revision_approval", "approved", "published")
    assert validate is not None and approve is not None and publish is not None
    # 验证边与批准边必须使用不同守卫：验证本身不能批准
    assert validate.guard_id != approve.guard_id
    # 仅 validation_passed 而无报告所有者显式决定 → 拒绝批准
    no_owner = TRANSITION_REGISTRY.evaluate_guard(
        approve.guard_id,
        {"validation_passed": True, "disposition_reason_saved": True},
        target_family="revision_approval",
        target_object_id="rev_001",
    )
    assert no_owner.allowed is False
    assert "missing_evidence" in no_owner.reason
    # 发布必须携带批准 ID 且重建/质控通过
    publish_ok = TRANSITION_REGISTRY.evaluate_guard(
        publish.guard_id,
        {
            "new_snapshot_built": True,
            "affected_artifacts_rebuilt": True,
            "independent_qc_passed": True,
            "approval_id": "rev_001",
        },
        target_family="revision_approval",
        target_object_id="rev_001",
    )
    assert publish_ok.allowed is True
    # 缺少批准 ID → 拒绝
    publish_no_id = TRANSITION_REGISTRY.evaluate_guard(
        publish.guard_id,
        {
            "new_snapshot_built": True,
            "affected_artifacts_rebuilt": True,
            "independent_qc_passed": True,
        },
        target_family="revision_approval",
        target_object_id="rev_001",
    )
    assert publish_no_id.allowed is False
    assert "missing_evidence" in publish_no_id.reason


def test_every_undeclared_transition_is_rejected_and_logged(
    tmp_path: Path,
) -> None:
    """GT06：九族全部未声明笛卡尔积按合法路径确定性拒绝并写事件。

    - 每个运行源状态先经字面 fixture 声明路径定位到新鲜对象，再探测全部缺失边；
    - 前四组证据状态族完全不可改写：任一尝试都拒绝并写拒绝事件；
    - trigger 不匹配、规范当前状态不匹配、错误运行身份都失败关闭并写事件；
    - 精确重放同一请求返回既有事件；身份相同载荷不同触发 EventConflict。
    """
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.graph.registry import TRANSITION_REGISTRY
    from ci_workflow.graph.types import TransitionRequest
    from ci_workflow.storage.event_store import EventConflictError

    executor = GraphExecutor(tmp_path / "项目", run_id="run_gt06")

    families = TRANSITION_REGISTRY.families()
    assert set(families) == {
        "route_attempt",
        "route_completion",
        "fact_disclosure",
        "fact_review",
        "project",
        "report_evidence",
        "format_artifact",
        "download_request",
        "revision_approval",
    }
    evidence_families = set(TRANSITION_REGISTRY.evidence_families())
    assert evidence_families == {
        "route_attempt",
        "route_completion",
        "fact_disclosure",
        "fact_review",
    }

    request_counter = 0

    def make_request(
        *,
        family: str,
        object_id: str,
        from_state: str | None,
        to_state: str,
        trigger: str,
        evidence: dict[str, object] | None = None,
        run_id: str = "run_gt06",
        project_id: str = "p_gt06",
    ) -> TransitionRequest:
        nonlocal request_counter
        request_counter += 1
        return TransitionRequest(
            schema_version="1.0",
            request_id=f"gt06:{request_counter}:{family}:{object_id}",
            project_id=project_id,
            run_id=run_id,
            family=family,
            object_id=object_id,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            evidence=evidence or {},
            actor_id="pi",
            occurred_at=_NOW,
        )

    def issue_auth_for_evidence(
        *,
        object_id: str,
        from_state: str | None,
        to_state: str,
        evidence: dict[str, object],
        run_id: str = "run_gt06",
        project_id: str = "p_gt06",
    ) -> str:
        """测试专用：经测试夹具签发授权事件；返回 qc_authorization_id。"""
        from tests.graph._qc_authorization_fixture import (
            issue_test_qc_authorization,
        )

        evidence_without_auth = {
            k: v for k, v in evidence.items() if k != "qc_authorization_id"
        }
        evidence_digest = hashlib.sha256(
            (
                json.dumps(
                    evidence_without_auth,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
        ).hexdigest()
        auth_id = issue_test_qc_authorization(
            executor,
            report_object_id=object_id,
            from_state=from_state if from_state is not None else "scientific_qc",
            to_state=to_state,
            verdict="accepted" if to_state == "snapshot_locked" else "veto",
            exhaustion_record_digest=(
                evidence.get("qc_exhaustion_record_digest")
                if isinstance(evidence.get("qc_exhaustion_record_digest"), str)
                else None
            ),
            evidence_digest=evidence_digest,
            actor_id="pi",
            project_id=project_id,
            occurred_at=_NOW,
        )
        evidence["qc_authorization_id"] = auth_id
        return auth_id

    def position(family: str, target: str, object_id: str) -> None:
        """经字面 fixture 声明路径把新鲜对象定位到目标源状态。"""
        for edge in _positioning_path(family, target):
            evidence = dict(_ALL_VALID_EVIDENCE[edge.guard_id])
            if edge.guard_id in (
                "g_report_scientific_qc_snapshot_locked",
                "g_report_scientific_qc_recovering",
                "g_report_scientific_qc_evidence_blocked",
            ):
                evidence["qc_report_object_id"] = object_id
                issue_auth_for_evidence(
                    object_id=object_id,
                    from_state=edge.from_state,
                    to_state=edge.to_state,
                    evidence=evidence,
                )
            event = executor.submit(
                make_request(
                    family=family,
                    object_id=object_id,
                    from_state=edge.from_state,
                    to_state=edge.to_state,
                    trigger=edge.trigger,
                    evidence=evidence,
                )
            )
            assert event.event_type == "graph.transition.accepted", (
                family,
                target,
                edge.from_state,
                edge.to_state,
            )

    # 前四组证据状态族：任一尝试（含同状态、None 源）都拒绝并写事件
    for family in TRANSITION_REGISTRY.evidence_families():
        values = TRANSITION_REGISTRY.state_values(family)
        for from_state in (None, *values):
            for to_state in values:
                event = executor.submit(
                    make_request(
                        family=family,
                        object_id=f"obj_{family}",
                        from_state=from_state,
                        to_state=to_state,
                        trigger="gt06_probe",
                    )
                )
                assert event.event_type == "graph.transition.rejected", (
                    family,
                    from_state,
                    to_state,
                )
                assert event.payload["reason"] == "undeclared_transition"

    # 后五组运行族：每个 (from × to) 用新鲜对象；源状态经真实声明路径定位
    for family in TRANSITION_REGISTRY.runtime_families():
        values = TRANSITION_REGISTRY.state_values(family)
        for from_state in (None, *values):
            for to_state in values:
                object_id = f"obj_{family}_{from_state or 'none'}__{to_state}"
                declared = TRANSITION_REGISTRY.declared(family, from_state, to_state)
                if from_state is not None:
                    position(family, from_state, object_id)
                evidence = (
                    dict(_ALL_VALID_EVIDENCE[declared.guard_id])
                    if declared is not None
                    else {}
                )
                # 科学质控守卫把报告对象绑定到被定位的对象标识，并签发授权
                if declared is not None and declared.guard_id in (
                    "g_report_scientific_qc_snapshot_locked",
                    "g_report_scientific_qc_recovering",
                    "g_report_scientific_qc_evidence_blocked",
                ):
                    evidence["qc_report_object_id"] = object_id
                    issue_auth_for_evidence(
                        object_id=object_id,
                        from_state=from_state,
                        to_state=to_state,
                        evidence=evidence,
                    )
                event = executor.submit(
                    make_request(
                        family=family,
                        object_id=object_id,
                        from_state=from_state,
                        to_state=to_state,
                        trigger=(
                            declared.trigger if declared is not None else "gt06_probe"
                        ),
                        evidence=evidence,
                    )
                )
                if declared is None:
                    assert event.event_type == "graph.transition.rejected", (
                        family,
                        from_state,
                        to_state,
                    )
                    assert event.payload["reason"] == "undeclared_transition"
                else:
                    assert event.event_type == "graph.transition.accepted", (
                        family,
                        from_state,
                        to_state,
                    )
                # 同状态迁移（v -> v）一律拒绝
                if from_state == to_state:
                    assert event.event_type == "graph.transition.rejected"
                    assert event.payload["reason"] == "undeclared_transition"

    # 前四组证据状态族：不改写规范状态；后五组运行族被迁移事件改写
    state = executor.state()
    for family in evidence_families:
        assert family not in state
    assert state["project"]["obj_project_none__running"] == "running"

    # 拒绝事件是可审计的：family/object、前后状态、trigger、守卫证据、
    # 请求摘要、actor、时间、幂等键
    sample_rejected = next(
        event
        for event in executor.store.read_all()
        if event.event_type == "graph.transition.rejected"
    )
    for key in (
        "family",
        "object_id",
        "from_state",
        "to_state",
        "trigger",
        "guard_evidence",
        "request_digest",
    ):
        assert key in sample_rejected.payload
    assert sample_rejected.actor_id == "pi"
    assert sample_rejected.occurred_at == _NOW
    assert sample_rejected.idempotency_key

    # 跨枚举同值/跨族目标状态 → 拒绝并写事件
    for family in families:
        values = set(TRANSITION_REGISTRY.state_values(family))
        foreign = next(
            value
            for other in families
            if other != family
            for value in TRANSITION_REGISTRY.state_values(other)
            if value not in values
        )
        cross = executor.submit(
            make_request(
                family=family,
                object_id=f"obj_{family}_foreign",
                from_state=None,
                to_state=foreign,
                trigger="gt06_cross_family",
            )
        )
        assert cross.event_type == "graph.transition.rejected"
        assert cross.payload["reason"] == "undeclared_transition"

    # 声明边：守卫证据缺失 / 跨对象 → guard_failed 拒绝事件
    declared_collect_qc = TRANSITION_REGISTRY.declared(
        "report_evidence", "collecting", "scientific_qc"
    )
    assert declared_collect_qc is not None
    guard_failed_object = "obj_guard_failed"
    position("report_evidence", "collecting", guard_failed_object)
    guard_failed = executor.submit(
        make_request(
            family="report_evidence",
            object_id=guard_failed_object,
            from_state="collecting",
            to_state="scientific_qc",
            trigger=declared_collect_qc.trigger,
            evidence={},
        )
    )
    assert guard_failed.event_type == "graph.transition.rejected"
    assert guard_failed.payload["reason"] == "guard_failed"
    assert guard_failed.payload["guard_id"] == declared_collect_qc.guard_id
    assert guard_failed.payload["guard_reason"].startswith("missing_evidence:")
    scope_object = "obj_scope_mismatch"
    position("report_evidence", "collecting", scope_object)
    cross_object = executor.submit(
        make_request(
            family="report_evidence",
            object_id=scope_object,
            from_state="collecting",
            to_state="scientific_qc",
            trigger=declared_collect_qc.trigger,
            evidence={
                **_ALL_VALID_EVIDENCE[declared_collect_qc.guard_id],
                "target_object_id": "other_object",
            },
        )
    )
    assert cross_object.event_type == "graph.transition.rejected"
    assert cross_object.payload["reason"] == "guard_failed"
    assert "scope_mismatch" in cross_object.payload["guard_reason"]

    # trigger 不匹配声明边 → 拒绝并写事件
    trigger_object = "obj_trigger_mismatch"
    position("report_evidence", "collecting", trigger_object)
    trigger_bad = executor.submit(
        make_request(
            family="report_evidence",
            object_id=trigger_object,
            from_state="collecting",
            to_state="scientific_qc",
            trigger="WRONG_TRIGGER",
            evidence=_ALL_VALID_EVIDENCE[declared_collect_qc.guard_id],
        )
    )
    assert trigger_bad.event_type == "graph.transition.rejected"
    assert trigger_bad.payload["reason"] == "trigger_mismatch"
    assert trigger_bad.payload["expected_trigger"] == declared_collect_qc.trigger

    # from_state 与规范当前状态不一致 → 拒绝并写事件
    declared_recovering_qc = TRANSITION_REGISTRY.declared(
        "report_evidence", "recovering", "scientific_qc"
    )
    assert declared_recovering_qc is not None
    state_object = "obj_state_mismatch"
    position("report_evidence", "collecting", state_object)
    state_bad = executor.submit(
        make_request(
            family="report_evidence",
            object_id=state_object,
            from_state="recovering",
            to_state="scientific_qc",
            trigger=declared_recovering_qc.trigger,
            evidence=_ALL_VALID_EVIDENCE[declared_recovering_qc.guard_id],
        )
    )
    assert state_bad.event_type == "graph.transition.rejected"
    assert state_bad.payload["reason"] == "current_state_mismatch"
    assert state_bad.payload["expected_state"] == "collecting"

    # 请求运行身份与执行器不一致 → 拒绝并写事件；事件属于执行器运行
    run_bad = executor.submit(
        make_request(
            family="project",
            object_id="obj_run_mismatch",
            from_state=None,
            to_state="running",
            trigger="project_contract_and_preflight",
            evidence=GT01_VALID_EVIDENCE["g_project_create_running"],
            run_id="run_other",
        )
    )
    assert run_bad.event_type == "graph.transition.rejected"
    assert run_bad.payload["reason"] == "run_mismatch"
    assert run_bad.payload["requested_run_id"] == "run_other"
    assert run_bad.payload["expected_run_id"] == "run_gt06"
    # 审计事件锚定执行器运行存储，不污染所请求的外来运行
    assert run_bad.run_id == "run_gt06"
    assert run_bad.project_id == "p_gt06"
    assert "obj_run_mismatch" not in executor.state()["project"]
    # 后续针对所请求运行的合法执行器可正常处理自己的请求
    from ci_workflow.graph.executor import GraphExecutor

    executor_other = GraphExecutor(tmp_path / "项目", run_id="run_other")
    legit = executor_other.submit(
        make_request(
            family="project",
            object_id="obj_run_mismatch",
            from_state=None,
            to_state="running",
            trigger="project_contract_and_preflight",
            evidence=GT01_VALID_EVIDENCE["g_project_create_running"],
            run_id="run_other",
        )
    )
    assert legit.event_type == "graph.transition.accepted"
    assert executor_other.state()["project"]["obj_run_mismatch"] == "running"

    # 项目身份：项目根已确立 p_gt06，其他项目的请求失败关闭并写事件
    project_bad = executor.submit(
        make_request(
            family="project",
            object_id="obj_project_mismatch",
            from_state=None,
            to_state="running",
            trigger="project_contract_and_preflight",
            evidence=GT01_VALID_EVIDENCE["g_project_create_running"],
            project_id="p_other",
        )
    )
    assert project_bad.event_type == "graph.transition.rejected"
    assert project_bad.payload["reason"] == "project_mismatch"
    assert project_bad.payload["requested_project_id"] == "p_other"
    assert project_bad.payload["expected_project_id"] == "p_gt06"
    assert project_bad.project_id == "p_gt06"
    assert project_bad.run_id == "run_gt06"
    # 项目根事件流始终只含已确立项目
    assert {event.project_id for event in executor.store.read_all()} == {"p_gt06"}

    # 精确重放同一请求 → 返回既有事件、无新事件；同一身份不同载荷 → EventConflict
    replay_request = make_request(
        family="project",
        object_id="obj_project",
        from_state=None,
        to_state="running",
        trigger="project_contract_and_preflight",
        evidence=GT01_VALID_EVIDENCE["g_project_create_running"],
    )
    first = executor.submit(replay_request)
    total_before = len(executor.store.read_all())
    replay = executor.submit(replay_request)
    assert replay == first
    assert len(executor.store.read_all()) == total_before
    drifted = replay_request.model_copy(update={"to_state": "complete", "trigger": "drifted"})
    with pytest.raises(EventConflictError):
        executor.submit(drifted)
