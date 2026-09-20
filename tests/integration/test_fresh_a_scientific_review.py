"""R2：fresh A 与 B/C 同等级的两阶段科学复核状态机（负向优先）。

fresh A 渲染候选先为 ``rendered_unreviewed``；研究包内自带的
``scientific_review`` 自述只是宿主材料，不再是最终授权。只有真实
``scientific-review-v1`` 回执经 ``require_verified_review_receipt``、权威
``ScientificQcCurrentContext`` 绑定与运行时发布请求核对全部通过后，才迁移为
``scientifically_reviewed_rendered_candidate``。缺回执、伪回执、篡改产物、
自审、同会话与旧内容一律失败关闭，候选保持未复核。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.acceptance_boundary import (
    AcceptanceBoundaryError,
    require_accepted_origin_report_states,
)
from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.application.review_issuer import (
    ExternalProcessResult,
    issue_review_receipt,
)
from ci_workflow.application.run_service import ContractConfigError, run_project
from ci_workflow.application.scientific_review_transition import (
    RENDERED_UNREVIEWED,
    SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE,
    reload_production_context,
    scientific_review_receipt_path,
    scientific_review_request_path,
)
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.qc.review_receipt import (
    ReviewArtifactBinding,
    ReviewContentBinding,
    ReviewContextEvidence,
    ReviewExecutableEvidence,
    ReviewHostSession,
    ReviewProcessEvidence,
    ReviewProductionContext,
    build_scientific_review_receipt,
)
from ci_workflow.qc.scientific import ScientificQcReviewBundle, ScientificQcVerdict
from tests.integration.test_fresh_a_research_package import _package_payload

REVIEWER_ID = "独立复核者-a-1"
HOST_EXECUTABLE = "/opt/homebrew/bin/codex"
STALE_DIGEST = "f" * 64


def _run_ready_project(project: Path, **kwargs: Any) -> Any:
    return run_project(project, capability_probe=StaticCapabilityProbe(), **kwargs)


def _request_digest(payload: dict[str, Any]) -> str:
    """与 scientific_review_transition._sha256_hex 相同的请求摘要材料。"""
    material = {key: value for key, value in payload.items() if key != "request_digest"}
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _write_a_project(tmp_path: Path) -> Path:
    contract = create_project_contract(
        indication="特应性皮炎",
        reports=["A"],
        outputs=["html"],
        cutoff="2026-07-31",
    )
    project = create_project_workspace(tmp_path / "项目", contract)
    package_path = project / "evidence/library/a-research-package.json"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    package_path.write_text(
        json.dumps(_package_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return project


def _run_manifest(project: Path) -> dict[str, Any]:
    return json.loads((project / "manifests/current_run.json").read_text(encoding="utf-8"))


def _published_request(project: Path) -> dict[str, Any]:
    return json.loads((project / scientific_review_request_path("A")).read_text(encoding="utf-8"))


def _review_bundle(context: Any) -> ScientificQcReviewBundle:
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


def _write_verdict_artifact(
    project: Path,
    context: Any,
    *,
    review_input_digest: str,
    produced_at: datetime,
    candidate_content_digest: str | None = None,
    reviewed_at: datetime | None = None,
) -> ReviewArtifactBinding:
    effective_reviewed_at = reviewed_at or produced_at + timedelta(minutes=80)
    verdict = ScientificQcVerdict(
        criteria_version=context.criteria_version,
        verdict_id="verdict-independent-a-1",
        verdict="accepted",
        project_id=context.project_id,
        contract_version=context.contract_version,
        report_kind=context.report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=candidate_content_digest or context.candidate_content_digest,
        gate_result_key=context.gate_result_key,
        coverage_set_id=context.coverage_set_id,
        coverage_digest=context.coverage_digest,
        source_refs=context.source_refs,
        locators=context.locators,
        reviewer_id=REVIEWER_ID,
        review_input_digest=review_input_digest,
        reviewed_at=effective_reviewed_at,
        valid_until=effective_reviewed_at + timedelta(days=7),
    )
    path = project / "receipts" / "scientific_review" / "A" / "verdict.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(verdict.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    return ReviewArtifactBinding(
        artifact_kind="scientific_qc_verdict",
        path="receipts/scientific_review/A/verdict.json",
        artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _verified_a_receipt(
    project: Path,
    context: Any,
    *,
    production: ReviewProductionContext,
    review_input_digest: str,
    artifact: ReviewArtifactBinding,
) -> Any:
    produced_at = production.produced_at
    review = ReviewContextEvidence(
        reviewer_id=REVIEWER_ID,
        host_executable=ReviewExecutableEvidence(
            provenance="path_resolved",
            path=HOST_EXECUTABLE,
            resolved_realpath=HOST_EXECUTABLE,
            version="codex-cli 0.42.0",
        ),
        session=ReviewHostSession(
            session_id="review-session-a-9",
            launcher_pid=777,
            launcher_parent_pid=1,
        ),
        process=ReviewProcessEvidence(
            kind="external_subprocess",
            pid=4242,
            argv=(HOST_EXECUTABLE, "exec", "scientific-review"),
            cwd=str(project),
            started_at=produced_at + timedelta(hours=1),
            finished_at=produced_at + timedelta(hours=1, minutes=30),
            returncode=0,
        ),
        independent_context="external_subprocess_session",
    )
    return build_scientific_review_receipt(
        host="codex",
        issued_at=produced_at + timedelta(hours=2),
        production=production,
        review=review,
        content=ReviewContentBinding(
            reviewed_content_digest=production.candidate_content_digest,
            review_input_digest=review_input_digest,
        ),
        artifact=artifact,
    )


def _write_receipt_payload(payload: dict[str, Any], project: Path) -> None:
    path = project / scientific_review_receipt_path("A")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def _stage_verified_receipt(project: Path) -> tuple[Any, Any]:
    """首轮渲染后按发布请求铸造并落盘一份真实绑定的独立回执。"""
    context = reload_production_context(project, "A")
    request = _published_request(project)
    production = ReviewProductionContext.model_validate(request["production"])
    artifact = _write_verdict_artifact(
        project,
        context,
        review_input_digest=request["review_input_digest"],
        produced_at=production.produced_at,
        reviewed_at=production.produced_at + timedelta(microseconds=2),
    )
    executable = ReviewExecutableEvidence(
        provenance="path_resolved",
        path=HOST_EXECUTABLE,
        resolved_realpath=HOST_EXECUTABLE,
        version="codex-cli-test",
    )
    started_at = production.produced_at + timedelta(microseconds=1)
    finished_at = production.produced_at + timedelta(microseconds=3)
    issued_at = production.produced_at + timedelta(microseconds=4)
    outcome = issue_review_receipt(
        project_root=project,
        report_kind="A",
        reviewer_id=REVIEWER_ID,
        review_session_id="review-session-a-9",
        host="codex",
        host_executable=executable,
        review_argv=("exec", "scientific-review"),
        verdict_relative_path=artifact.path,
        session=ReviewHostSession(
            session_id="review-session-a-9",
            launcher_pid=777,
            launcher_parent_pid=1,
        ),
        runner=lambda argv, cwd, _timeout: ExternalProcessResult(
            pid=4242,
            argv=argv,
            cwd=cwd,
            started_at=started_at,
            finished_at=finished_at,
            returncode=0,
        ),
        clock=lambda: issued_at,
    )
    return context, outcome.receipt


# ─── 阶段一：缺回执时保持未复核，包内自审不构成授权 ──────────────────────────


def test_fresh_a_without_receipt_stays_rendered_unreviewed(tmp_path: Path) -> None:
    project = _write_a_project(tmp_path)

    result = _run_ready_project(project)

    assert result.outcome == "completed"
    # 研究包内 scientific_review 自述被接受，也不得产生科学质控完成节点
    assert "scientific_qc:A" not in result.node_summary
    assert result.node_summary["format:A"] == "completed"
    manifest = _run_manifest(project)
    assert manifest["report_states"] == {"A": RENDERED_UNREVIEWED}
    assert manifest["format_states"] == {"A": {"html": "quality_check"}}
    assert "scientific_review_receipts" not in manifest
    context = manifest["scientific_review_contexts"]["A"]
    assert context["report_kind"] == "A"
    assert context["candidate_content_digest"]
    # 权威上下文与审查请求已发布，供外部独立复核会话绑定
    published = reload_production_context(project, "A")
    assert published.context_digest == context["context_digest"]
    request = _published_request(project)
    assert request["production"]["producer_session_id"] == result.run_id
    assert request["production"]["production_context_digest"] == published.context_digest
    assert request["request_digest"] == _request_digest(request)
    # 未复核候选只能作为开发预览，不得进入真实来源验收
    with pytest.raises(AcceptanceBoundaryError):
        require_accepted_origin_report_states(manifest, reports=("A",))


# ─── 阶段二：真实独立回执绑定后不可变晋级 ────────────────────────────────────


def test_fresh_a_independent_receipt_promotes_rendered_candidate(
    tmp_path: Path,
) -> None:
    project = _write_a_project(tmp_path)
    first = _run_ready_project(project)
    assert first.outcome == "completed"
    context, receipt = _stage_verified_receipt(project)
    assert context.report_kind.value == "A"

    second = _run_ready_project(project, resume=True)

    assert second.outcome == "completed"
    assert second.node_summary["scientific_qc:A"] == "completed"
    assert second.node_summary["format:A"] == "reused"
    manifest = _run_manifest(project)
    assert manifest["report_states"] == {"A": SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE}
    assert manifest["scientific_review_receipts"] == {"A": receipt.receipt_digest}
    # 晋级后的候选满足真实来源验收的起点状态要求
    assert (
        require_accepted_origin_report_states(manifest, reports=("A",))["A"]
        == SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE
    )


# ─── 负向：伪回执、篡改产物、旧内容、自审与同会话全部失败关闭 ────────────────


def test_fresh_a_tampered_verdict_artifact_fails_closed(tmp_path: Path) -> None:
    project = _write_a_project(tmp_path)
    first = _run_ready_project(project)
    assert first.outcome == "completed"
    _stage_verified_receipt(project)
    artifact = project / "receipts" / "scientific_review" / "A" / "verdict.json"
    artifact.write_bytes(b'{"verdict":"changed"}')

    with pytest.raises(ContractConfigError, match="候选保持未复核"):
        _run_ready_project(project, resume=True)

    manifest = _run_manifest(project)
    assert manifest["run_id"] == first.run_id
    assert manifest["report_states"] == {"A": RENDERED_UNREVIEWED}


def test_fresh_a_stale_content_receipt_fails_closed(tmp_path: Path) -> None:
    project = _write_a_project(tmp_path)
    first = _run_ready_project(project)
    assert first.outcome == "completed"
    context = reload_production_context(project, "A")
    request = _published_request(project)
    production = ReviewProductionContext.model_validate(request["production"])
    stale_production = production.model_copy(update={"candidate_content_digest": STALE_DIGEST})
    artifact = _write_verdict_artifact(
        project,
        context,
        review_input_digest=request["review_input_digest"],
        produced_at=production.produced_at,
        candidate_content_digest=STALE_DIGEST,
    )
    receipt = _verified_a_receipt(
        project,
        context,
        production=stale_production,
        review_input_digest=request["review_input_digest"],
        artifact=artifact,
    )
    _write_receipt_payload(receipt.model_dump(mode="json"), project)

    with pytest.raises(ContractConfigError, match="候选保持未复核"):
        _run_ready_project(project, resume=True)

    manifest = _run_manifest(project)
    assert manifest["run_id"] == first.run_id
    assert manifest["report_states"] == {"A": RENDERED_UNREVIEWED}


def test_fresh_a_self_reviewed_receipt_rejected(tmp_path: Path) -> None:
    project = _write_a_project(tmp_path)
    first = _run_ready_project(project)
    assert first.outcome == "completed"
    _stage_verified_receipt(project)
    payload = json.loads(
        (project / scientific_review_receipt_path("A")).read_text(encoding="utf-8")
    )
    # 复核者改写为生产者身份：身份分离校验先于摘要校验失败关闭
    payload["review"]["reviewer_id"] = payload["production"]["producer_id"]
    _write_receipt_payload(payload, project)

    with pytest.raises(ContractConfigError):
        _run_ready_project(project, resume=True)

    manifest = _run_manifest(project)
    assert manifest["run_id"] == first.run_id
    assert manifest["report_states"] == {"A": RENDERED_UNREVIEWED}


def test_fresh_a_same_session_receipt_rejected(tmp_path: Path) -> None:
    project = _write_a_project(tmp_path)
    first = _run_ready_project(project)
    assert first.outcome == "completed"
    _stage_verified_receipt(project)
    payload = json.loads(
        (project / scientific_review_receipt_path("A")).read_text(encoding="utf-8")
    )
    # 复核会话改写为生产会话：会话分离校验失败关闭
    payload["review"]["session"]["session_id"] = payload["production"]["producer_session_id"]
    _write_receipt_payload(payload, project)

    with pytest.raises(ContractConfigError):
        _run_ready_project(project, resume=True)

    manifest = _run_manifest(project)
    assert manifest["run_id"] == first.run_id
    assert manifest["report_states"] == {"A": RENDERED_UNREVIEWED}
