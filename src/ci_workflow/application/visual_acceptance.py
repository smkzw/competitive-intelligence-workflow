"""Persist an independently accepted visual artifact and its graph lineage."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from ci_workflow.application.acceptance_boundary import (
    AcceptanceBoundaryError,
    require_accepted_origin_report_states,
)
from ci_workflow.application.run_service import RunError, validate_run_manifest
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.recovery import format_object_id
from ci_workflow.graph.registry import TRANSITION_REGISTRY
from ci_workflow.graph.types import TransitionRequest
from ci_workflow.graph.visual_finalization import (
    VisualFinalizationError,
    validate_visual_finalization_plan,
    validate_visual_render_evidence,
    validate_visual_verification_reference,
    visual_contract_digest,
)
from ci_workflow.qc.browser import LockedSitemapSourceError, load_locked_sitemap_source
from ci_workflow.storage.manifest_store import (
    ArtifactManifest,
    ManifestIntegrityError,
    ManifestStore,
    ManifestWriteContext,
)
from ci_workflow.storage.snapshot_store import compute_locked_snapshot


class VisualAcceptanceError(RuntimeError):
    """视觉验收输入、清单继承或状态迁移失败。"""


def _publish_accepted_pointer(project_root: Path, accepted: ArtifactManifest) -> None:
    from ci_workflow.application.latest_delivery import (
        publish_latest_delivery,
        read_latest_delivery,
    )

    try:
        current = read_latest_delivery(project_root, accepted.report)
        if current is not None and (
            current.contract_version, current.accepted_at
        ) > (accepted.contract_version, accepted.render_verdict.verified_at):
            return  # Historical acceptance replay must never roll the pointer back.
        publish_latest_delivery(project_root, accepted.manifest_id)
    except (ValueError, RuntimeError, OSError) as error:
        raise VisualAcceptanceError(
            "接受记录已保留，但最新版指针发布未完成；修复后可幂等重试"
        ) from error


@dataclass(frozen=True)
class VisualAcceptanceResult:
    """视觉验收入口写入的清单和状态迁移证据。"""

    manifest: ArtifactManifest
    manifest_path: Path
    stored_manifest_path: Path
    predecessor_manifest_path: Path
    acceptance_run_id: str
    transition_event_ids: tuple[str, ...]


def _resolve_project_path(project_root: Path, raw: Path, label: str) -> Path:
    candidate = raw.expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    try:
        resolved = candidate.resolve()
    except OSError as error:
        raise VisualAcceptanceError(f"{label}路径无法解析：{raw}") from error
    if not resolved.is_relative_to(project_root):
        raise VisualAcceptanceError(f"{label}必须位于项目目录内：{raw}")
    return resolved


def _load_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise VisualAcceptanceError(f"缺少{label}：{path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise VisualAcceptanceError(f"{label}无法读取：{path}") from error
    except json.JSONDecodeError as error:
        raise VisualAcceptanceError(f"{label}不是有效 JSON：{path}") from error
    if not isinstance(payload, dict):
        raise VisualAcceptanceError(f"{label}顶层必须是对象：{path}")
    return cast(dict[str, Any], payload)


def _parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise VisualAcceptanceError(f"{label}缺少有效时间")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise VisualAcceptanceError(f"{label}时间格式无效：{value}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise VisualAcceptanceError(f"{label}时间必须包含时区偏移")
    return parsed.astimezone(UTC)


def _require_binding(payload: Mapping[str, Any], field: str, expected: object, label: str) -> None:
    if payload.get(field) != expected:
        raise VisualAcceptanceError(
            f"{label}的{field}与当前 HTML 候选不一致"
        )


def _snapshot_digest(source: Any) -> str:
    try:
        locked = compute_locked_snapshot(
            kind="report",
            report=source.manifest.report,
            manifest=source.snapshot.model_dump(mode="json"),
        )
    except (TypeError, ValueError) as error:
        raise VisualAcceptanceError("当前报告快照无法重算摘要") from error
    return locked.sha256


def _quality_check_evidence(
    *,
    candidate: ArtifactManifest,
    artifact_id: str,
    plan_digest: str,
    plan_id: str,
    render_evidence: dict[str, Any],
    render_digest: str,
    visual_verdict: dict[str, Any],
    verdict_digest: str,
    beautification_round: int,
) -> dict[str, Any]:
    domains = {
        str(domain["domain"]): str(domain["status"])
        for domain in cast(list[dict[str, Any]], visual_verdict["domains"])
    }
    deterministic_checks_passed = bool(candidate.deterministic_checks) and all(
        check.status == "passed" for check in candidate.deterministic_checks
    )
    beautification_record_digest = visual_contract_digest(
        {
            "format": "html",
            "round": beautification_round,
            "candidate_artifact_digest": candidate.artifact.sha256,
            "render_evidence_digest": render_digest,
            "visual_verdict_digest": verdict_digest,
        }
    )
    return {
        "deterministic_check_recorded": deterministic_checks_passed,
        "coverage_check_recorded": bool(
            candidate.coverage_set_id and candidate.coverage_projection_id
        ),
        "real_render_check_recorded": True,
        "visual_plan_bound": True,
        "candidate_current": True,
        "render_evidence_current": True,
        "current_run": True,
        "real_artifact": True,
        "real_render": True,
        "receipts_current": True,
        "independent_visual_review_recorded": True,
        "independent_visual_verifier": True,
        "visual_verdict_accepted": visual_verdict["verdict"] == "accepted",
        "visual_verdict_current": True,
        "render_evidence_validated": True,
        "visual_verdict_validated": True,
        "required_render_targets_complete": True,
        "required_interactions_complete": True,
        "visible_text_scan_passed": True,
        "responsive_content_complete": True,
        "beautification_loop_complete": True,
        "no_visual_defects_remain": True,
        "visual_copy_check_passed": domains.get("copy_zh") == "accepted",
        "visual_hierarchy_check_passed": domains.get("hierarchy_density") == "accepted",
        "visual_layout_check_passed": domains.get("typography_spacing") == "accepted",
        "visual_color_check_passed": domains.get("color_legibility") == "accepted",
        "visual_chart_table_check_passed": domains.get("charts_tables") == "accepted",
        "visual_interaction_check_passed": domains.get("interaction_consistency") == "accepted",
        "visual_format_render_check_passed": domains.get("format_rendering") == "accepted",
        "snapshot_id": candidate.report_snapshot_id,
        "format": "html",
        "visual_plan_id": plan_id,
        "visual_plan_digest": plan_digest,
        "artifact_id": artifact_id,
        "candidate_artifact_digest": candidate.artifact.sha256,
        "candidate_snapshot_id": candidate.report_snapshot_id,
        "candidate_visual_plan_digest": plan_digest,
        "candidate_format": "html",
        "render_evidence_id": render_evidence["evidence_id"],
        "render_evidence_digest": render_digest,
        "rendered_artifact_digest": candidate.artifact.sha256,
        "rendered_format": "html",
        "beautification_round": beautification_round,
        "beautification_record_digest": beautification_record_digest,
        "visual_verdict_id": visual_verdict["verdict_id"],
        "visual_verdict_digest": verdict_digest,
        "visual_verdict_artifact_digest": candidate.artifact.sha256,
        "visual_verdict_render_digest": render_digest,
        "visual_verdict_plan_digest": plan_digest,
        "visual_verdict_format": "html",
        "producer_identity": visual_verdict["producer_identity"],
        "verifier_identity": visual_verdict["verifier_identity"],
        "open_blocking_visual_defects": 0,
        "render_evidence": render_evidence,
        "visual_verdict": visual_verdict,
    }


def _queued_evidence(
    *, candidate: ArtifactManifest, plan: Mapping[str, Any], plan_digest: str
) -> dict[str, Any]:
    return {
        "report_snapshot_locked": True,
        "visual_plan_bound": True,
        "visual_plan_snapshot_matches": True,
        "visual_plan_format_matches": True,
        "visual_plan_design_contract_matches": True,
        "snapshot_id": candidate.report_snapshot_id,
        "format": "html",
        "visual_plan_id": plan["plan_id"],
        "visual_plan_digest": plan_digest,
        "visual_plan_snapshot_id": candidate.report_snapshot_id,
        "visual_plan_format": "html",
        "design_contract_digest": candidate.design_contract.digest,
    }


def _candidate_evidence(
    *, candidate: ArtifactManifest, artifact_id: str, plan_digest: str
) -> dict[str, Any]:
    return {
        "visual_plan_bound": True,
        "artifact_built": True,
        "candidate_current": True,
        "candidate_snapshot_matches": True,
        "candidate_visual_plan_matches": True,
        "snapshot_id": candidate.report_snapshot_id,
        "format": "html",
        "visual_plan_digest": plan_digest,
        "artifact_id": artifact_id,
        "candidate_artifact_digest": candidate.artifact.sha256,
        "candidate_snapshot_id": candidate.report_snapshot_id,
        "candidate_visual_plan_digest": plan_digest,
        "candidate_format": "html",
    }


def _delivery_evidence(
    *,
    candidate: ArtifactManifest,
    artifact_id: str,
    plan_digest: str,
    render_evidence: Mapping[str, Any],
    render_digest: str,
    verdict: Mapping[str, Any],
    verdict_digest: str,
) -> dict[str, Any]:
    return {
        "atomic_publish_complete": True,
        "manifest_digest_recorded": True,
        "independent_visual_verdict_accepted": True,
        "visual_verdict_current": True,
        "snapshot_id": candidate.report_snapshot_id,
        "format": "html",
        "visual_plan_digest": plan_digest,
        "artifact_id": artifact_id,
        "candidate_artifact_digest": candidate.artifact.sha256,
        "candidate_snapshot_id": candidate.report_snapshot_id,
        "candidate_visual_plan_digest": plan_digest,
        "candidate_format": "html",
        "render_evidence_id": render_evidence["evidence_id"],
        "render_evidence_digest": render_digest,
        "rendered_artifact_digest": candidate.artifact.sha256,
        "rendered_format": "html",
        "visual_verdict_id": verdict["verdict_id"],
        "visual_verdict_digest": verdict_digest,
        "visual_verdict_artifact_digest": candidate.artifact.sha256,
        "visual_verdict_render_digest": render_digest,
        "visual_verdict_plan_digest": plan_digest,
        "visual_verdict_format": "html",
        "producer_identity": verdict["producer_identity"],
        "verifier_identity": verdict["verifier_identity"],
        "render_evidence": render_evidence,
        "visual_verdict": verdict,
    }


def _submit_transition(
    executor: GraphExecutor,
    *,
    project_id: str,
    object_id: str,
    from_state: str,
    to_state: str,
    trigger: str,
    evidence: dict[str, Any],
    request_id: str,
    occurred_at: datetime,
) -> str:
    edge = TRANSITION_REGISTRY.declared("format_artifact", from_state, to_state)
    if edge is None:
        raise VisualAcceptanceError(
            f"格式状态迁移未声明：{from_state} -> {to_state}"
        )
    guard = TRANSITION_REGISTRY.evaluate_guard(
        edge.guard_id,
        evidence,
        target_family="format_artifact",
        target_object_id=object_id,
    )
    if not guard.allowed:
        raise VisualAcceptanceError(f"格式状态迁移被守卫拒绝：{guard.reason}")
    event = executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=request_id,
            project_id=project_id,
            run_id=executor.run_id,
            family="format_artifact",
            object_id=object_id,
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            evidence=evidence,
            actor_id="visual_acceptance",
            occurred_at=occurred_at,
        )
    )
    if event.event_type != "graph.transition.accepted":
        reason = str(event.payload.get("guard_reason") or event.payload.get("reason") or "unknown")
        raise VisualAcceptanceError(f"格式状态迁移未接受：{reason}")
    return event.event_id


def _successor_manifest(
    candidate: ArtifactManifest,
    *,
    manifest_id: str,
    verifier_identity: str,
    verdict_id: str,
    verified_at: datetime,
    anchor_ids: tuple[str, ...],
) -> ArtifactManifest:
    payload = candidate.model_dump(mode="json")
    payload.update(
        {
            "manifest_id": manifest_id,
            "render_verdict": {
                "verdict_id": verdict_id,
                "status": "accepted",
                "verified_at": verified_at.isoformat(),
                "anchor_ids": list(anchor_ids),
            },
            "accepted_by": verifier_identity,
            "status": "accepted",
            "supersedes_manifest_id": candidate.manifest_id,
        }
    )
    return ArtifactManifest.model_validate(payload)


def _stored_accepted_successors(
    store: ManifestStore, predecessor_id: str
) -> tuple[tuple[Path, ArtifactManifest], ...]:
    """找到同一前驱的已接受继承清单，供重放和冲突检查使用。"""
    matches: list[tuple[Path, ArtifactManifest]] = []
    for path in sorted(store.directory.glob("*.json")):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            not isinstance(payload, dict)
            or payload.get("supersedes_manifest_id") != predecessor_id
        ):
            continue
        try:
            manifest = ArtifactManifest.model_validate(payload)
        except ValueError as error:
            raise VisualAcceptanceError(f"已接受继承清单校验失败：{path}") from error
        if manifest.status == "accepted":
            matches.append((path, manifest))
    return tuple(matches)


def _validate_successor_binding(
    candidate: ArtifactManifest, accepted: ArtifactManifest
) -> None:
    candidate_payload = candidate.model_dump(mode="json")
    accepted_payload = accepted.model_dump(mode="json")
    mutable_fields = {
        "manifest_id",
        "render_verdict",
        "accepted_by",
        "status",
        "supersedes_manifest_id",
    }
    if any(
        accepted_payload.get(field) != candidate_payload[field]
        for field in candidate_payload
        if field not in mutable_fields
    ):
        raise VisualAcceptanceError("已接受继承清单未保留当前候选绑定")


def accept_visual_artifact(
    project_root: Path,
    *,
    version: str,
    visual_plan_path: Path,
    render_evidence_path: Path,
    verification_reference_path: Path,
    report: Literal["A", "B", "C"] = "B",
    beautification_round: int = 1,
    acceptance_run_id: str | None = None,
) -> VisualAcceptanceResult:
    """Validate one independent HTML portal and advance its bound acceptance graph."""
    if report not in {"A", "B", "C"}:
        raise VisualAcceptanceError("视觉验收报告类型只能是 A、B 或 C")
    if not isinstance(version, str) or not version.strip():
        raise VisualAcceptanceError("报告版本不能为空")
    if isinstance(beautification_round, bool) or not 1 <= beautification_round <= 3:
        raise VisualAcceptanceError("美化轮次必须是 1 到 3 的整数")

    project_root = project_root.expanduser().resolve()
    plan_path = _resolve_project_path(project_root, visual_plan_path, "视觉策划书")
    evidence_path = _resolve_project_path(project_root, render_evidence_path, "视觉呈现证据")
    verdict_path = _resolve_project_path(
        project_root, verification_reference_path, "独立视觉审阅结论"
    )
    manifest_path = project_root / "reports" / report / version / "html.manifest.json"

    try:
        source = load_locked_sitemap_source(project_root, ReportKind(report), version)
    except (LockedSitemapSourceError, OSError, ValueError) as error:
        raise VisualAcceptanceError(str(error)) from error
    candidate = source.manifest
    if candidate.status not in {"generated", "quality_check", "accepted"}:
        raise VisualAcceptanceError(f"当前 {report} 类候选状态不可验收：{candidate.status}")

    try:
        ManifestStore(project_root).verify_artifact(candidate)
    except ManifestIntegrityError as error:
        raise VisualAcceptanceError(str(error)) from error

    try:
        run_manifest = validate_run_manifest(project_root)
        require_accepted_origin_report_states(run_manifest, reports=(report,))
    except (RunError, AcceptanceBoundaryError) as error:
        raise VisualAcceptanceError(str(error)) from error

    snapshot_sha256 = _snapshot_digest(source)
    plan_raw = _load_object(plan_path, "视觉策划书")
    try:
        plan = validate_visual_finalization_plan(
            plan_raw,
            expected_report_snapshot_sha256=snapshot_sha256,
            expected_design_contract_sha256=candidate.design_contract.digest,
        )
    except VisualFinalizationError as error:
        raise VisualAcceptanceError(str(error)) from error
    _require_binding(plan, "report_kind", report, "视觉策划书")
    _require_binding(plan, "report_version", candidate.report_version, "视觉策划书")
    _require_binding(plan, "format", "html", "视觉策划书")
    report_snapshot = cast(dict[str, Any], plan["report_snapshot"])
    _require_binding(report_snapshot, "snapshot_id", candidate.report_snapshot_id, "视觉策划书")
    plan_digest = visual_contract_digest(plan)

    render_raw = _load_object(evidence_path, "视觉呈现证据")
    try:
        render_evidence = validate_visual_render_evidence(
            render_raw,
            expected_artifact_digest=candidate.artifact.sha256,
            expected_plan_digest=plan_digest,
        )
    except VisualFinalizationError as error:
        raise VisualAcceptanceError(str(error)) from error
    _require_binding(render_evidence, "report_kind", report, "视觉呈现证据")
    _require_binding(render_evidence, "report_version", candidate.report_version, "视觉呈现证据")
    _require_binding(render_evidence, "format", "html", "视觉呈现证据")
    render_created_at = _parse_timestamp(render_evidence["created_at"], "视觉呈现证据")
    candidate_modified_at = candidate.artifact.modified_at.astimezone(UTC)
    if render_created_at < candidate_modified_at:
        raise VisualAcceptanceError("视觉呈现证据早于当前 HTML 候选产物")
    render_digest = visual_contract_digest(render_evidence)

    verdict_raw = _load_object(verdict_path, "独立视觉审阅结论")
    try:
        visual_verdict = validate_visual_verification_reference(
            verdict_raw,
            expected_artifact_digest=candidate.artifact.sha256,
            expected_render_digest=render_digest,
            expected_plan_digest=plan_digest,
        )
    except VisualFinalizationError as error:
        raise VisualAcceptanceError(str(error)) from error
    _require_binding(visual_verdict, "format", "html", "独立视觉审阅结论")
    if visual_verdict["producer_identity"] != render_evidence["producer_identity"]:
        raise VisualAcceptanceError("独立视觉审阅结论未绑定真实呈现证据的生成者")
    if visual_verdict["verdict"] != "accepted":
        raise VisualAcceptanceError("独立视觉审阅结论不是接受")
    verdict_created_at = _parse_timestamp(visual_verdict["created_at"], "独立视觉审阅结论")
    if verdict_created_at < render_created_at:
        raise VisualAcceptanceError("独立视觉审阅结论早于真实呈现证据")
    verdict_digest = visual_contract_digest(visual_verdict)

    predecessor_id = candidate.supersedes_manifest_id or candidate.manifest_id
    successor_id = stable_id(
        "artifact-manifest-accepted",
        predecessor_id,
        str(render_evidence["evidence_id"]),
        str(visual_verdict["verdict_id"]),
    )
    current_acceptance_run_id = acceptance_run_id or stable_id(
        "visual-acceptance-run",
        candidate.project_id,
        predecessor_id,
        str(render_evidence["evidence_id"]),
        str(visual_verdict["verdict_id"]),
    )
    if not isinstance(current_acceptance_run_id, str) or not current_acceptance_run_id.strip():
        raise VisualAcceptanceError("视觉验收运行标识不能为空")

    store = ManifestStore(project_root)
    successors = _stored_accepted_successors(store, predecessor_id)
    if len(successors) > 1:
        raise VisualAcceptanceError("同一候选存在多个已接受继承清单，拒绝继续交付")
    if successors:
        stored_path, accepted = successors[0]
        if accepted.manifest_id != successor_id:
            raise VisualAcceptanceError("当前候选已有不同视觉证据的接受继承清单")
        if accepted.artifact != candidate.artifact:
            raise VisualAcceptanceError("已接受继承清单未绑定当前 HTML 候选产物")
        _validate_successor_binding(candidate, accepted)
        if (
            accepted.accepted_by != visual_verdict["verifier_identity"]
            or accepted.render_verdict.verdict_id != visual_verdict["verdict_id"]
            or accepted.render_verdict.verified_at != verdict_created_at
        ):
            raise VisualAcceptanceError("已接受继承清单未绑定本次独立视觉结论")
        try:
            store.verify_artifact(accepted)
        except ManifestIntegrityError as error:
            raise VisualAcceptanceError(str(error)) from error
        object_id = format_object_id(f"report_{report}", "html")
        stored_state = GraphExecutor(
            project_root, run_id=current_acceptance_run_id
        ).state()
        if stored_state.get("format_artifact", {}).get(object_id) != "delivery_ready":
            raise VisualAcceptanceError("已接受清单缺少可交付状态记录")
        predecessor_path = store.directory / f"{predecessor_id}.json"
        if not predecessor_path.is_file():
            raise VisualAcceptanceError("已接受清单缺少不可变前驱清单")
        _publish_accepted_pointer(project_root, accepted)
        return VisualAcceptanceResult(
            manifest=accepted,
            manifest_path=manifest_path,
            stored_manifest_path=stored_path,
            predecessor_manifest_path=predecessor_path,
            acceptance_run_id=current_acceptance_run_id,
            transition_event_ids=(),
        )
    if candidate.status == "accepted":
        raise VisualAcceptanceError("已接受候选缺少对应的不可变继承清单")

    artifact_id = stable_id("artifact", candidate.artifact.relative_path, candidate.artifact.sha256)
    quality_evidence = _quality_check_evidence(
        candidate=candidate,
        artifact_id=artifact_id,
        plan_digest=plan_digest,
        plan_id=str(plan["plan_id"]),
        render_evidence=render_evidence,
        render_digest=render_digest,
        visual_verdict=visual_verdict,
        verdict_digest=verdict_digest,
        beautification_round=beautification_round,
    )
    queued_evidence = _queued_evidence(
        candidate=candidate, plan=plan, plan_digest=plan_digest
    )
    candidate_evidence = _candidate_evidence(
        candidate=candidate, artifact_id=artifact_id, plan_digest=plan_digest
    )
    delivery_evidence = _delivery_evidence(
        candidate=candidate,
        artifact_id=artifact_id,
        plan_digest=plan_digest,
        render_evidence=render_evidence,
        render_digest=render_digest,
        verdict=visual_verdict,
        verdict_digest=verdict_digest,
    )

    executor = GraphExecutor(project_root, run_id=current_acceptance_run_id)
    object_id = format_object_id(f"report_{report}", "html")
    transition_event_ids: list[str] = []
    state: str = cast(
        str, executor.state().get("format_artifact", {}).get(object_id, "queued")
    )
    if state == "queued":
        transition_event_ids.append(
            _submit_transition(
                executor,
                project_id=candidate.project_id,
                object_id=object_id,
                from_state="queued",
                to_state="generating",
                trigger="snapshot_locked_ready",
                evidence=queued_evidence,
                request_id=stable_id(
                    "visual-acceptance-transition",
                    current_acceptance_run_id,
                    object_id,
                    "generating",
                ),
                occurred_at=datetime.now(UTC),
            )
        )
        state = "generating"
    if state == "generating":
        transition_event_ids.append(
            _submit_transition(
                executor,
                project_id=candidate.project_id,
                object_id=object_id,
                from_state="generating",
                to_state="quality_check",
                trigger="artifact_built",
                evidence=candidate_evidence,
                request_id=stable_id(
                    "visual-acceptance-transition",
                    current_acceptance_run_id,
                    object_id,
                    "quality-check",
                ),
                occurred_at=datetime.now(UTC),
            )
        )
        state = "quality_check"
    if state == "quality_check":
        transition_event_ids.append(
            _submit_transition(
                executor,
                project_id=candidate.project_id,
                object_id=object_id,
                from_state="quality_check",
                to_state="passed",
                trigger="acceptance_records_complete",
                evidence=quality_evidence,
                request_id=stable_id(
                    "visual-acceptance-transition", current_acceptance_run_id, object_id, "passed"
                ),
                occurred_at=datetime.now(UTC),
            )
        )
        state = "passed"
    if state != "passed":
        raise VisualAcceptanceError("当前格式尚未完成视觉验收，不能进入交付流程")

    try:
        predecessor_path = store.write(candidate)
    except ManifestIntegrityError as error:
        raise VisualAcceptanceError(str(error)) from error

    target_ids = tuple(
        str(target["target_id"])
        for target in cast(list[dict[str, Any]], render_evidence["render_targets"])
    )
    accepted = _successor_manifest(
        candidate,
        manifest_id=successor_id,
        verifier_identity=str(visual_verdict["verifier_identity"]),
        verdict_id=str(visual_verdict["verdict_id"]),
        verified_at=verdict_created_at,
        anchor_ids=target_ids,
    )
    context = ManifestWriteContext.model_validate(
        {key: getattr(accepted, key) for key in ManifestWriteContext.model_fields}
    )
    try:
        stored_path = store.write(accepted, current_context=context)
    except ManifestIntegrityError as error:
        raise VisualAcceptanceError(str(error)) from error


    transition_event_ids.append(
        _submit_transition(
            executor,
            project_id=candidate.project_id,
            object_id=object_id,
            from_state="passed",
            to_state="delivery_ready",
            trigger="atomic_publish_manifest",
            evidence=delivery_evidence,
            request_id=stable_id(
                "visual-acceptance-transition",
                current_acceptance_run_id,
                object_id,
                "delivery-ready",
            ),
            occurred_at=datetime.now(UTC),
        )
    )
    _publish_accepted_pointer(project_root, accepted)
    return VisualAcceptanceResult(
        manifest=accepted,
        manifest_path=manifest_path,
        stored_manifest_path=stored_path,
        predecessor_manifest_path=predecessor_path,
        acceptance_run_id=current_acceptance_run_id,
        transition_event_ids=tuple(transition_event_ids),
    )


__all__ = [
    "VisualAcceptanceError",
    "VisualAcceptanceResult",
    "accept_visual_artifact",
]
