"""Task 3.4 结构化守卫：从证据字段确定性求值，缺失/矛盾/跨对象一律拒绝。

每个守卫是 GuardSpec：必需真键、任一组真键、必需字段、字面矛盾对。
求值顺序固定，理由确定性（missing_evidence / guard_not_satisfied /
contradictory_evidence / scope_mismatch），绝无 allowed=True 绕过。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ci_workflow.graph.types import GuardResult


@dataclass(frozen=True)
class GuardSpec:
    """声明式结构化守卫：全部字段为字面常量。

    ``required_fields`` 非空字符串；``sha256_fields`` 必须为小写 SHA-256；
    ``object_bound_fields`` 必须等于请求目标对象标识；``forbidden_fields``
    出现即拒绝（如可修复否决不得携带穷尽记录摘要）。
    """

    guard_id: str
    required_true: tuple[str, ...] = ()
    required_any: tuple[tuple[str, ...], ...] = ()
    required_fields: tuple[str, ...] = ()
    sha256_fields: tuple[str, ...] = ()
    object_bound_fields: tuple[str, ...] = ()
    forbidden_fields: tuple[str, ...] = ()
    contradictions: tuple[tuple[str, str], ...] = ()
    description: str = ""


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def evaluate_spec(
    spec: GuardSpec,
    evidence: dict[str, Any],
    *,
    target_family: str,
    target_object_id: str,
) -> GuardResult:
    """按固定顺序求值：作用域 → 必需字段 → SHA-256 → 对象绑定 → 必需真键 →
    任一组 → 禁字段 → 矛盾对。"""
    # 跨对象/跨族证据失败关闭：证据可声明 target_family/target_object_id，
    # 一旦声明就必须与请求目标一致
    declared_family = evidence.get("target_family")
    if declared_family is not None and declared_family != target_family:
        return GuardResult(False, f"scope_mismatch:target_family:{declared_family}")
    declared_object = evidence.get("target_object_id")
    if declared_object is not None and declared_object != target_object_id:
        return GuardResult(False, f"scope_mismatch:target_object_id:{declared_object}")

    for key in spec.required_fields:
        if key not in evidence:
            return GuardResult(False, f"missing_evidence:{key}")
        value = evidence[key]
        if value is None or value == "" or value == [] or value == {}:
            return GuardResult(False, f"guard_not_satisfied:{key}")

    for key in spec.sha256_fields:
        value = evidence.get(key)
        if value is None or not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
            return GuardResult(False, f"guard_not_satisfied:{key}")

    for key in spec.object_bound_fields:
        value = evidence.get(key)
        if value is None or value != target_object_id:
            return GuardResult(False, f"scope_mismatch:object:{key}")

    for key in spec.required_true:
        if key not in evidence:
            return GuardResult(False, f"missing_evidence:{key}")
        if evidence[key] is not True:
            return GuardResult(False, f"guard_not_satisfied:{key}")

    for group in spec.required_any:
        if any(evidence.get(key) is True for key in group):
            continue
        missing = [key for key in group if key not in evidence]
        marker = "+".join(group)
        if missing:
            return GuardResult(False, f"missing_evidence:{marker}")
        return GuardResult(False, f"guard_not_satisfied:{marker}")

    for key in spec.forbidden_fields:
        if key in evidence and evidence.get(key) is not None:
            return GuardResult(False, f"guard_not_satisfied:{key}")

    for first, second in spec.contradictions:
        if evidence.get(first) and evidence.get(second):
            return GuardResult(False, f"contradictory_evidence:{first}/{second}")

    return GuardResult(True, "guard_satisfied")


# ── 项目运行族守卫 ─────────────────────────────────────────────────────────
GUARD_SPECS: dict[str, GuardSpec] = {
    "g_project_create_running": GuardSpec(
        guard_id="g_project_create_running",
        required_true=("project_contract_established", "preflight_records_established"),
        description="项目合同与包/能力预检记录已建立",
    ),
    "g_project_running_awaiting_user": GuardSpec(
        guard_id="g_project_running_awaiting_user",
        required_true=(
            "double_exhaustion_complete",
            "critical_gap_remains",
            "audit_package_written",
            "request_written",
        ),
        required_fields=("audit_package_path",),
        description="科学双重穷尽或技术恢复穷尽通过、关键缺口仍在、审计包与精确请求已写入",
    ),
    "g_project_awaiting_user_running": GuardSpec(
        guard_id="g_project_awaiting_user_running",
        required_any=(("user_material_accepted", "environment_fix_confirmed"),),
        description="用户材料已接受或环境修复已确认；只重排失败节点及下游",
    ),
    "g_project_running_partially_delivered": GuardSpec(
        guard_id="g_project_running_partially_delivered",
        required_true=("at_least_one_artifact_delivery_ready", "selected_objects_continuable"),
        description="至少一个选定产物 delivery_ready，且仍有可继续的非终态对象",
    ),
    "g_project_partially_delivered_partial_delivery_blocked": GuardSpec(
        guard_id="g_project_partially_delivered_partial_delivery_blocked",
        required_true=(
            "at_least_one_artifact_delivered",
            "remaining_selected_exhausted_blocked",
            "no_running_selected_object",
        ),
        description="至少一个产物已交付、剩余选定对象已穷尽阻断、没有仍运行的选定对象",
    ),
    "g_project_any_incomplete_blocked": GuardSpec(
        guard_id="g_project_any_incomplete_blocked",
        required_true=(
            "no_deliverable_artifact",
            "at_least_one_terminal_blocked",
            "no_running_selected_object",
        ),
        description="尚无产物可交付、至少一个选定对象终态阻断、没有仍运行的选定对象",
    ),
    "g_project_any_incomplete_complete": GuardSpec(
        guard_id="g_project_any_incomplete_complete",
        required_true=(
            "all_selected_html_delivery_ready",
            "all_selected_optional_formats_delivery_ready",
        ),
        description="每个选定报告的 HTML 与每个选定可选格式均 delivery_ready",
    ),
    "g_project_blocked_running": GuardSpec(
        guard_id="g_project_blocked_running",
        required_any=(
            ("user_material_accepted", "environment_fix_confirmed", "new_contract_version_reopens"),
        ),
        description="显式用户材料、环境修复或新项目合同版本重新打开对应节点",
    ),
    # ── 报告证据族守卫 ─────────────────────────────────────────────────────
    "g_report_queued_collecting": GuardSpec(
        guard_id="g_report_queued_collecting",
        required_true=("candidate_scope_locked",),
        description="候选范围已锁定",
    ),
    "g_report_collecting_recovering": GuardSpec(
        guard_id="g_report_collecting_recovering",
        required_true=("candidate_scope_locked", "first_gate_failure"),
        description="候选范围已锁定且首次门槛失败",
    ),
    "g_report_collecting_scientific_qc": GuardSpec(
        guard_id="g_report_collecting_scientific_qc",
        required_true=("gate_deterministic_pass", "candidate_snapshot_established"),
        description="GateSpec 确定性通过且候选快照已建立",
    ),
    "g_report_recovering_scientific_qc": GuardSpec(
        guard_id="g_report_recovering_scientific_qc",
        required_true=("gate_deterministic_pass", "candidate_snapshot_established"),
        description="GateSpec 确定性通过且候选快照已建立",
    ),
    "g_report_scientific_qc_snapshot_locked": GuardSpec(
        guard_id="g_report_scientific_qc_snapshot_locked",
        required_true=("isolated_qc_accepted",),
        required_fields=(
            "qc_verdict_id",
            "qc_verdict_digest",
            "qc_candidate_snapshot_id",
            "qc_candidate_content_digest",
            "qc_review_input_digest",
            "qc_report_object_id",
            "qc_context_digest",
            "qc_authorization_id",
        ),
        sha256_fields=(
            "qc_verdict_digest",
            "qc_candidate_content_digest",
            "qc_review_input_digest",
            "qc_context_digest",
        ),
        object_bound_fields=("qc_report_object_id",),
        forbidden_fields=("qc_exhaustion_record_digest",),
        contradictions=(
            ("isolated_qc_accepted", "qc_veto"),
            ("isolated_qc_accepted", "qc_veto_fixable"),
            ("isolated_qc_accepted", "qc_veto_unfixable"),
            ("isolated_qc_accepted", "recovery_exhausted"),
            ("isolated_qc_accepted", "independent_review_exhausted"),
            ("isolated_qc_accepted", "no_continuable_user_action"),
        ),
        description=(
            "隔离质控接受且携带由质控边界发出的验证授权材料"
            "（摘要为小写 SHA-256、对象绑定报告对象）；"
            "否决/恢复/穷尽标志与接受互斥"
        ),
    ),
    "g_report_scientific_qc_recovering": GuardSpec(
        guard_id="g_report_scientific_qc_recovering",
        required_true=("qc_veto", "qc_veto_fixable"),
        required_fields=(
            "qc_verdict_id",
            "qc_verdict_digest",
            "qc_candidate_snapshot_id",
            "qc_candidate_content_digest",
            "qc_review_input_digest",
            "qc_report_object_id",
            "qc_context_digest",
            "qc_authorization_id",
        ),
        sha256_fields=(
            "qc_verdict_digest",
            "qc_candidate_content_digest",
            "qc_review_input_digest",
            "qc_context_digest",
        ),
        object_bound_fields=("qc_report_object_id",),
        forbidden_fields=("qc_exhaustion_record_digest",),
        contradictions=(
            ("qc_veto", "isolated_qc_accepted"),
            ("qc_veto_fixable", "qc_veto_unfixable"),
            ("qc_veto_fixable", "recovery_exhausted"),
            ("qc_veto_fixable", "independent_review_exhausted"),
            ("qc_veto_fixable", "no_continuable_user_action"),
            ("qc_veto", "recovery_exhausted"),
            ("qc_veto", "independent_review_exhausted"),
            ("qc_veto", "no_continuable_user_action"),
        ),
        description=(
            "质控否决且可修复（携带验证授权材料）：只能回 recovering；"
            "不得携带穷尽记录摘要或穷尽标志"
        ),
    ),
    "g_report_collecting_evidence_blocked": GuardSpec(
        guard_id="g_report_collecting_evidence_blocked",
        required_true=(
            "critical_units_still_failing",
            "recovery_exhausted",
            "independent_review_exhausted",
            "no_continuable_user_action",
        ),
        description="关键单元仍失败、恢复与独立审查已穷尽、无继续用户动作",
    ),
    "g_report_recovering_evidence_blocked": GuardSpec(
        guard_id="g_report_recovering_evidence_blocked",
        required_true=(
            "critical_units_still_failing",
            "recovery_exhausted",
            "independent_review_exhausted",
            "no_continuable_user_action",
        ),
        description="关键单元仍失败、恢复与独立审查已穷尽、无继续用户动作",
    ),
    "g_report_scientific_qc_evidence_blocked": GuardSpec(
        guard_id="g_report_scientific_qc_evidence_blocked",
        required_true=(
            "qc_veto",
            "qc_veto_unfixable",
            "recovery_exhausted",
            "independent_review_exhausted",
            "no_continuable_user_action",
        ),
        required_fields=(
            "qc_verdict_id",
            "qc_verdict_digest",
            "qc_candidate_snapshot_id",
            "qc_candidate_content_digest",
            "qc_review_input_digest",
            "qc_report_object_id",
            "qc_context_digest",
            "qc_exhaustion_record_digest",
            "qc_authorization_id",
        ),
        sha256_fields=(
            "qc_verdict_digest",
            "qc_candidate_content_digest",
            "qc_review_input_digest",
            "qc_context_digest",
            "qc_exhaustion_record_digest",
        ),
        object_bound_fields=("qc_report_object_id",),
        contradictions=(
            ("qc_veto_fixable", "qc_veto_unfixable"),
            ("qc_veto_unfixable", "isolated_qc_accepted"),
            ("qc_veto", "isolated_qc_accepted"),
            ("qc_veto_unfixable", "qc_veto_fixable"),
        ),
        description="质控否决且不可修复（携带验证授权材料与穷尽记录摘要）、恢复与独立审查已穷尽、无继续用户动作；接受/可修复标志互斥",
    ),
    "g_report_collecting_awaiting_user": GuardSpec(
        guard_id="g_report_collecting_awaiting_user",
        required_true=(
            "recovery_exhausted",
            "critical_gap_remains",
            "audit_package_written",
            "request_written",
        ),
        required_fields=("audit_package_path",),
        description="适用恢复已穷尽、审计包与下载/材料请求已建立",
    ),
    "g_report_recovering_awaiting_user": GuardSpec(
        guard_id="g_report_recovering_awaiting_user",
        required_true=(
            "recovery_exhausted",
            "critical_gap_remains",
            "audit_package_written",
            "request_written",
        ),
        required_fields=("audit_package_path",),
        description="适用恢复已穷尽、审计包与下载/材料请求已建立",
    ),
    "g_report_awaiting_user_recovering": GuardSpec(
        guard_id="g_report_awaiting_user_recovering",
        required_any=(
            (
                "required_file_accepted",
                "permission_or_environment_restored",
                "user_provided_verifiable_lead",
            ),
        ),
        description="所需文件已接受、权限/环境已恢复或用户提供可核验新线索",
    ),
    "g_report_snapshot_locked_superseded": GuardSpec(
        guard_id="g_report_snapshot_locked_superseded",
        required_true=("new_version_explicitly_supersedes",),
        description="新版本已明确取代；旧版本保持只读和可复现",
    ),
    # ── 格式产物族守卫 ─────────────────────────────────────────────────────
    "g_format_queued_generating": GuardSpec(
        guard_id="g_format_queued_generating",
        required_true=("report_snapshot_locked",),
        description="具有锁定报告快照",
    ),
    "g_format_generating_quality_check": GuardSpec(
        guard_id="g_format_generating_quality_check",
        required_true=("artifact_built",),
        description="构建产物",
    ),
    "g_format_quality_check_passed": GuardSpec(
        guard_id="g_format_quality_check_passed",
        required_true=(
            "deterministic_check_recorded",
            "coverage_check_recorded",
            "real_render_check_recorded",
        ),
        description="确定性/覆盖/真实渲染接受记录",
    ),
    "g_format_passed_delivery_ready": GuardSpec(
        guard_id="g_format_passed_delivery_ready",
        required_true=("atomic_publish_complete", "manifest_digest_recorded"),
        description="原子发布及清单摘要",
    ),
    "g_format_generating_blocked": GuardSpec(
        guard_id="g_format_generating_blocked",
        required_true=("format_recovery_exhausted", "failure_evidence_saved"),
        description="格式特定技术/内容/视觉恢复已穷尽并保存失败证据",
    ),
    "g_format_quality_check_blocked": GuardSpec(
        guard_id="g_format_quality_check_blocked",
        required_true=("format_recovery_exhausted", "failure_evidence_saved"),
        description="格式特定技术/内容/视觉恢复已穷尽并保存失败证据",
    ),
    "g_format_blocked_queued": GuardSpec(
        guard_id="g_format_blocked_queued",
        required_any=(("environment_fixed", "generator_fixed", "new_contract_version_reopens"),),
        description="环境/生成器已修复或新合同版本明确重新打开；继续使用同一快照",
    ),
    "g_format_delivery_ready_superseded": GuardSpec(
        guard_id="g_format_delivery_ready_superseded",
        required_true=("new_version_explicitly_supersedes",),
        description="新版本已明确取代；旧版本保持只读",
    ),
    # ── 下载请求族守卫（与已接受 Task 3.3 语义一致）────────────────────────
    "g_download_awaiting_user_file_detected": GuardSpec(
        guard_id="g_download_awaiting_user_file_detected",
        required_true=("new_file_detected",),
        required_any=(("inbox_scan_complete", "user_downloaded_signal"),),
        description="唯一收件箱发现新文件或用户已下载信号并完成库存",
    ),
    "g_download_file_detected_matched": GuardSpec(
        guard_id="g_download_file_detected_matched",
        required_true=("unique_high_confidence_match",),
        required_fields=("content_sha256",),
        contradictions=(("unique_high_confidence_match", "ambiguous_match"),),
        description="摘要、元数据、标题页和标识符形成唯一高置信内容匹配",
    ),
    "g_download_file_detected_needs_re_download": GuardSpec(
        guard_id="g_download_file_detected_needs_re_download",
        required_true=("quarantined", "reason_recorded"),
        required_any=(
            (
                "file_incomplete",
                "login_or_error_page",
                "identity_ambiguous",
                "wrong_attachment",
                "unreadable",
            ),
        ),
        description="文件不完整/登录错误页/身份歧义/错误附件/不可读；留在隔离区并记录原因",
    ),
    "g_download_matched_needs_re_download": GuardSpec(
        guard_id="g_download_matched_needs_re_download",
        required_true=("quarantined", "reason_recorded"),
        required_any=(
            (
                "file_incomplete",
                "login_or_error_page",
                "identity_ambiguous",
                "wrong_attachment",
                "unreadable",
            ),
        ),
        description="文件不完整/登录错误页/身份歧义/错误附件/不可读；留在隔离区并记录原因",
    ),
    "g_download_matched_accepted": GuardSpec(
        guard_id="g_download_matched_accepted",
        required_true=(
            "type_valid",
            "integrity_valid",
            "identity_valid",
            "digest_valid",
            "parent_child_valid",
            "canonical_naming_valid",
            "atomic_archive_complete",
        ),
        description="类型、完整性、身份、摘要、父子关系和规范命名均通过且原子归档完成",
    ),
    "g_download_needs_re_download_awaiting_user": GuardSpec(
        guard_id="g_download_needs_re_download_awaiting_user",
        required_true=("deduplicated_request_generated",),
        description="已生成去重的新请求或更精确下载说明",
    ),
    "g_download_awaiting_user_needs_re_download": GuardSpec(
        guard_id="g_download_awaiting_user_needs_re_download",
        required_true=("no_valid_target_in_inbox",),
        description="扫描收件目录后未发现任何合法目标 → 直接需要重新下载",
    ),
    "g_download_awaiting_user_not_required": GuardSpec(
        guard_id="g_download_awaiting_user_not_required",
        required_true=("gap_closed_by_accepted_evidence",),
        required_fields=("reason_zh",),
        contradictions=(("gap_closed_by_accepted_evidence", "gap_still_open"),),
        description="其他已接受证据已关闭原缺口，保存取消理由；不能掩盖仍失败的关键单元",
    ),
    "g_download_file_detected_not_required": GuardSpec(
        guard_id="g_download_file_detected_not_required",
        required_true=("gap_closed_by_accepted_evidence",),
        required_fields=("reason_zh",),
        contradictions=(("gap_closed_by_accepted_evidence", "gap_still_open"),),
        description="其他已接受证据已关闭原缺口，保存取消理由",
    ),
    "g_download_matched_not_required": GuardSpec(
        guard_id="g_download_matched_not_required",
        required_true=("gap_closed_by_accepted_evidence",),
        required_fields=("reason_zh",),
        contradictions=(("gap_closed_by_accepted_evidence", "gap_still_open"),),
        description="其他已接受证据已关闭原缺口，保存取消理由",
    ),
    "g_download_needs_re_download_not_required": GuardSpec(
        guard_id="g_download_needs_re_download_not_required",
        required_true=("gap_closed_by_accepted_evidence",),
        required_fields=("reason_zh",),
        contradictions=(("gap_closed_by_accepted_evidence", "gap_still_open"),),
        description="其他已接受证据已关闭原缺口，保存取消理由",
    ),
    # ── 修订审批族守卫：验证与用户批准分离 ─────────────────────────────────
    "g_revision_submitted_needs_evidence": GuardSpec(
        guard_id="g_revision_submitted_needs_evidence",
        required_true=("validation_complete", "needs_more_evidence", "disposition_reason_saved"),
        contradictions=(
            ("validation_passed", "validation_rejected"),
            ("validation_passed", "needs_more_evidence"),
            ("validation_rejected", "needs_more_evidence"),
        ),
        description="Agent 完成验证并保存处置理由；需要更多证据",
    ),
    "g_revision_submitted_rejected": GuardSpec(
        guard_id="g_revision_submitted_rejected",
        required_true=("validation_complete", "validation_rejected", "disposition_reason_saved"),
        contradictions=(
            ("validation_passed", "validation_rejected"),
            ("validation_passed", "needs_more_evidence"),
            ("validation_rejected", "needs_more_evidence"),
        ),
        description="Agent 完成验证并保存处置理由；验证拒绝",
    ),
    "g_revision_submitted_validated_pending_user_approval": GuardSpec(
        guard_id="g_revision_submitted_validated_pending_user_approval",
        required_true=("validation_complete", "validation_passed", "disposition_reason_saved"),
        contradictions=(
            ("validation_passed", "validation_rejected"),
            ("validation_passed", "needs_more_evidence"),
            ("validation_rejected", "needs_more_evidence"),
        ),
        description="验证通过但未批准；等待报告所有者显式决定",
    ),
    "g_revision_needs_evidence_submitted": GuardSpec(
        guard_id="g_revision_needs_evidence_submitted",
        required_true=("new_evidence_appended",),
        required_fields=("evidence_id",),
        description="新证据作为同一建议的新事件附加，原提交历史不覆盖",
    ),
    "g_revision_validated_approved": GuardSpec(
        guard_id="g_revision_validated_approved",
        required_true=("owner_explicit_decision", "decision_approve"),
        contradictions=(
            ("decision_approve", "decision_reject"),
            ("decision_approve", "decision_needs_evidence"),
            ("decision_reject", "decision_needs_evidence"),
        ),
        description="报告所有者作出显式批准；验证本身不能批准",
    ),
    "g_revision_validated_rejected": GuardSpec(
        guard_id="g_revision_validated_rejected",
        required_true=("owner_explicit_decision", "decision_reject"),
        contradictions=(
            ("decision_approve", "decision_reject"),
            ("decision_approve", "decision_needs_evidence"),
            ("decision_reject", "decision_needs_evidence"),
        ),
        description="报告所有者作出显式拒绝",
    ),
    "g_revision_validated_needs_evidence": GuardSpec(
        guard_id="g_revision_validated_needs_evidence",
        required_true=("owner_explicit_decision", "decision_needs_evidence"),
        contradictions=(
            ("decision_approve", "decision_reject"),
            ("decision_approve", "decision_needs_evidence"),
            ("decision_reject", "decision_needs_evidence"),
        ),
        description="报告所有者要求补充证据",
    ),
    "g_revision_approved_published": GuardSpec(
        guard_id="g_revision_approved_published",
        required_true=(
            "new_snapshot_built",
            "affected_artifacts_rebuilt",
            "independent_qc_passed",
        ),
        required_fields=("approval_id",),
        description="新快照、受影响产物重建和独立质控全部通过；发布使用批准 ID 幂等",
    ),
}

# 供 registry 使用：GuardResult 延迟导入避免与 types 循环
__all__ = ["GuardSpec", "GUARD_SPECS", "evaluate_spec"]
