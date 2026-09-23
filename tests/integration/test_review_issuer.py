"""独立科学复核签发入口（review issue）负向优先测试。

合同目标（R2 独立复核信任根，Astra P1-1 裁决）：签发入口必须绑定运行时
已发布的唯一科学复核请求；复核者身份与复核会话必须与生产者真实分离；
``review.process`` 执行证据只能来自真实外部子进程运行（测试经同一 seam
注入，生产路径不接受调用方自报进程字段）；回执必须绑定正式 verdict 字节；
未来时间、过期结论、伪造回执（只有自洽 JSON、没有真实签发记录）一律
失败关闭。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.review_issuer import (
    ExternalProcessResult,
    ReviewIssuanceError,
    issue_review_receipt,
    resolve_host_executable,
    review_issuance_record_path,
    verify_receipt_issuance,
)
from ci_workflow.application.scientific_review_transition import (
    ScientificReviewTransitionError,
    build_scientific_review_context,
    capture_portal_artifact_binding,
    publish_production_context,
    publish_scientific_review_request,
    scientific_review_receipt_path,
)
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.cli import _build_parser
from ci_workflow.domain.evidence import EvidenceLocator
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

PRODUCED_AT = datetime(2026, 9, 5, 1, 0, 0, tzinfo=UTC)
REVIEW_STARTED_AT = datetime(2026, 9, 5, 2, 0, 0, tzinfo=UTC)
REVIEW_FINISHED_AT = datetime(2026, 9, 5, 2, 30, 0, tzinfo=UTC)
ISSUED_AT = datetime(2026, 9, 5, 3, 0, 0, tzinfo=UTC)
VALID_UNTIL = datetime(2099, 1, 1, tzinfo=UTC)

CANDIDATE_DIGEST = hashlib.sha256("候选内容".encode()).hexdigest()
FACT_VERSION_BY_REF = {
    "fact-1": "fact-version-1",
    "fact-2": "fact-version-1",
    "fact-3": "fact-version-2",
}
HOST_PATH = "/opt/homebrew/bin/codex"
REVIEW_SESSION = ReviewHostSession(
    session_id="review-session-9", launcher_pid=777, launcher_parent_pid=1
)
HOST_EXECUTABLE = ReviewExecutableEvidence(
    provenance="path_resolved",
    path=HOST_PATH,
    resolved_realpath=HOST_PATH,
    version="codex-cli 0.42.0",
)
REVIEW_ARGV = ("exec", "scientific-review")
VERDICT_RELATIVE = "receipts/scientific_review/B/verdict.json"


def _canonical_digest(value: object) -> str:
    material = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256((material + "\n").encode("utf-8")).hexdigest()


def _locator(role: str, *, page: int = 12) -> EvidenceLocator:
    return EvidenceLocator(document_role=role, page=page, table="Table 2")


def _sources() -> tuple[SourceCapture, ...]:
    def _capture(source_id: str, content: str, role: str) -> SourceCapture:
        return SourceCapture(
            source_id=source_id,
            route_id=f"route-{source_id}",
            source_type="registry",
            title=f"来源 {source_id}",
            url=f"https://example.org/{source_id}",
            query_or_identifier=f"NCT-{source_id}",
            language="en",
            access_method="public_registry",
            content_text='{"quote":"客观缓解率 80%"}',
            acquired_at=PRODUCED_AT,
            published_at=PRODUCED_AT,
            effective_at=None,
            first_disclosed_at=PRODUCED_AT,
            locator=EvidenceLocator(document_role=role, field_path="$"),
        )

    return (
        _capture("src-1", "试验一结果正文", "primary_result"),
        _capture("src-2", "试验二结果正文", "registry_posting"),
    )


def _facts() -> tuple[ResearchFact, ...]:
    def _fact(fact_id: str, source_id: str) -> ResearchFact:
        return ResearchFact(
            fact_id=fact_id,
            row_ref=f"{fact_id}-row",
            entity_id="product-alpha",
            entity_type="product",
            canonical_name="产品甲",
            field_id="orr",
            raw_value="80%",
            normalized_value="80",
            disclosure_state="reported_value",
            source_id=source_id,
            locator=EvidenceLocator(
                document_role="primary_result", field_path="$.quote"
            ),
            original_text="客观缓解率 80%",
        )

    return (
        _fact("fact-1", "src-1"),
        _fact("fact-2", "src-1"),
        _fact("fact-3", "src-2"),
    )


def _claims() -> tuple[ResearchClaim, ...]:
    return (
        ResearchClaim(
            claim_id="claim-1",
            claim_text="试验一客观缓解率为 80%",
            claim_kind="direct_evidence",
            fact_ids=("fact-1", "fact-2"),
        ),
        ResearchClaim(
            claim_id="claim-2",
            claim_text="试验二客观缓解率为 70%",
            claim_kind="direct_evidence",
            fact_ids=("fact-3",),
        ),
    )


def _context(**overrides: Any) -> Any:
    values: dict[str, Any] = {
        "project_id": "project-r2",
        "report_kind": "B",
        "report_version": "v1",
        "producer_id": "producer-agent",
        "candidate_snapshot_id": "report-snapshot_1",
        "candidate_content_digest": CANDIDATE_DIGEST,
        "criteria_version": "B-v1",
        "gate_result_key": "gate-key-1",
        "contract_version": "1.0",
        "coverage_set_id": "coverage-set_1",
        "evidence_snapshot_id": "evidence-snapshot_1",
        "claim_snapshot_id": "claim-snapshot_1",
        "sources": _sources(),
        "facts": _facts(),
        "claims": _claims(),
        "fact_version_by_ref": FACT_VERSION_BY_REF,
    }
    values.update(overrides)
    return build_scientific_review_context(**values)


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


def _publish_request(project_root: Path, context: Any) -> None:
    manifest_relative = "reports/B/v1/html.manifest.json"
    site_relative = "reports/B/v1/html"
    manifest_path = project_root / manifest_relative
    site_path = project_root / site_relative
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    site_path.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text('{"kind":"artifact-manifest"}\n', encoding="utf-8")
    (site_path / "index.html").write_text("<!doctype html><title>B</title>", encoding="utf-8")
    publish_production_context(project_root, "B", context)
    publish_scientific_review_request(
        project_root,
        "B",
        context,
        producer_session_id="producer-session-1",
        produced_at=PRODUCED_AT,
        portal_binding=capture_portal_artifact_binding(
            project_root,
            "B",
            manifest_relative=manifest_relative,
            site_relative=site_relative,
        ),
    )


def _verdict_payload(context: Any, **overrides: Any) -> dict[str, Any]:
    bundle = _review_bundle(context)
    verdict = ScientificQcVerdict(
        criteria_version=context.criteria_version,
        verdict_id="verdict-independent-1",
        verdict="accepted",
        project_id=context.project_id,
        contract_version=context.contract_version,
        report_kind=context.report_kind,
        report_version=context.report_version,
        report_object_id=context.report_object_id,
        candidate_snapshot_id=context.candidate_snapshot_id,
        candidate_content_digest=context.candidate_content_digest,
        gate_result_key=context.gate_result_key,
        coverage_set_id=context.coverage_set_id,
        coverage_digest=context.coverage_digest,
        source_refs=context.source_refs,
        locators=context.locators,
        reviewer_id="independent-reviewer",
        review_input_digest=bundle.input_digest,
        reviewed_at=REVIEW_FINISHED_AT,
        valid_until=VALID_UNTIL,
    )
    payload = verdict.model_dump(mode="json")
    payload.update(overrides)
    return payload


def _write_verdict(project_root: Path, payload: dict[str, Any]) -> None:
    path = project_root / VERDICT_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _fake_runner(
    project_root: Path,
    context: Any,
    *,
    verdict_payload: dict[str, Any] | None = None,
    returncode: int = 0,
    started_at: datetime = REVIEW_STARTED_AT,
    finished_at: datetime = REVIEW_FINISHED_AT,
    pid: int = 4242,
) -> Callable[[tuple[str, ...], str, float], ExternalProcessResult]:
    """测试 seam：复核进程真实写入 verdict 字节并返回真实进程样式的证据。"""

    def _run(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        assert argv == (HOST_PATH, *REVIEW_ARGV), "复核进程 argv 必须以宿主可执行文件开头"
        assert cwd == str(project_root)
        assert timeout > 0
        if verdict_payload is not None:
            _write_verdict(project_root, verdict_payload)
        return ExternalProcessResult(
            pid=pid,
            argv=argv,
            cwd=cwd,
            started_at=started_at,
            finished_at=finished_at,
            returncode=returncode,
            stdout_tail="SCIENTIFIC_REVIEW_DONE verdict=accepted\n",
            stderr_tail="",
        )

    return _run


def _issue(
    project_root: Path,
    context: Any,
    runner: Callable[[tuple[str, ...], str, float], ExternalProcessResult],
    *,
    reviewer_id: str = "independent-reviewer",
    review_session_id: str = "review-session-9",
    clock: Callable[[], datetime] | None = None,
    session: ReviewHostSession | None = None,
    host_executable: ReviewExecutableEvidence | None = None,
    verdict_relative: str = VERDICT_RELATIVE,
) -> Any:
    return issue_review_receipt(
        project_root=project_root,
        report_kind="B",
        reviewer_id=reviewer_id,
        review_session_id=review_session_id,
        host="codex",
        host_executable=host_executable or HOST_EXECUTABLE,
        review_argv=REVIEW_ARGV,
        verdict_relative_path=verdict_relative,
        session=session or REVIEW_SESSION,
        runner=runner,
        clock=clock or (lambda: ISSUED_AT),
    )


def _hand_written_receipt(context: Any, *, pid: int = 4242) -> Any:
    """构造结构完全自洽、但未经真实签发入口的回执（Astra P1-1 攻击样例）。"""

    return build_scientific_review_receipt(
        host="codex",
        issued_at=ISSUED_AT,
        production=ReviewProductionContext(
            project_id=context.project_id,
            report_kind="B",
            report_version=context.report_version,
            report_object_id=context.report_object_id,
            candidate_snapshot_id=context.candidate_snapshot_id,
            candidate_content_digest=context.candidate_content_digest,
            producer_id=context.producer_id,
            producer_session_id="producer-session-1",
            criteria_version=context.criteria_version,
            gate_result_key=context.gate_result_key,
            produced_at=PRODUCED_AT,
            production_context_digest=context.context_digest,
        ),
        review=ReviewContextEvidence(
            reviewer_id="independent-reviewer",
            host_executable=HOST_EXECUTABLE,
            session=REVIEW_SESSION,
            process=ReviewProcessEvidence(
                kind="external_subprocess",
                pid=pid,
                argv=(HOST_PATH, *REVIEW_ARGV),
                cwd="/tmp/项目-r2",
                started_at=REVIEW_STARTED_AT,
                finished_at=REVIEW_FINISHED_AT,
                returncode=0,
            ),
            independent_context="external_subprocess_session",
        ),
        content=ReviewContentBinding(
            reviewed_content_digest=context.candidate_content_digest,
            review_input_digest=_review_bundle(context).input_digest,
        ),
        artifact=ReviewArtifactBinding(
            artifact_kind="scientific_qc_verdict",
            path=VERDICT_RELATIVE,
            artifact_sha256="d" * 64,
        ),
    )


def _write_receipt_file(project_root: Path, receipt: Any) -> None:
    receipt_path = project_root / scientific_review_receipt_path("B")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )


# ─── 正向：真实执行证据 + 正式 verdict 字节 + 真实签发记录 ────────────────────


def test_issue_binds_published_request_and_real_execution(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    outcome = _issue(
        tmp_path,
        context,
        _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
    )
    receipt = outcome.receipt
    assert receipt.status == "verified"
    assert receipt.host == "codex"
    assert receipt.production.producer_id == "producer-agent"
    assert receipt.production.producer_session_id == "producer-session-1"
    assert receipt.review.reviewer_id == "independent-reviewer"
    assert receipt.review.session == REVIEW_SESSION
    assert receipt.review.process.pid == 4242
    assert receipt.review.process.argv == (HOST_PATH, *REVIEW_ARGV)
    assert receipt.content.review_input_digest == _review_bundle(context).input_digest
    assert receipt.artifact is not None
    assert receipt.artifact.path == VERDICT_RELATIVE
    artifact_bytes = (tmp_path / VERDICT_RELATIVE).read_bytes()
    assert receipt.artifact.artifact_sha256 == hashlib.sha256(artifact_bytes).hexdigest()
    assert outcome.receipt_path == tmp_path / scientific_review_receipt_path("B")
    record_path = tmp_path / review_issuance_record_path("B")
    assert record_path.is_file()
    attested = verify_receipt_issuance(tmp_path, "B")
    assert attested.receipt_digest == receipt.receipt_digest


def test_reissuance_overwrites_receipt_and_record_for_same_request(
    tmp_path: Path,
) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    first = _issue(
        tmp_path,
        context,
        _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
    )
    second = _issue(
        tmp_path,
        context,
        _fake_runner(
            tmp_path,
            context,
            verdict_payload=_verdict_payload(context),
            pid=5252,
        ),
        clock=lambda: ISSUED_AT + timedelta(hours=1),
    )
    assert second.receipt.receipt_digest != first.receipt.receipt_digest
    attested = verify_receipt_issuance(tmp_path, "B")
    assert attested.receipt_digest == second.receipt.receipt_digest


# ─── 负向：必须绑定运行时已发布的科学复核请求 ────────────────────────────────


def test_missing_review_request_fails_closed(tmp_path: Path) -> None:
    context = _context()
    publish_production_context(tmp_path, "B", context)
    with pytest.raises(ReviewIssuanceError, match="科学复核请求"):
        _issue(tmp_path, context, _fake_runner(tmp_path, context))
    assert not (tmp_path / scientific_review_receipt_path("B")).exists()


def test_tampered_review_request_fails_closed(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    request_path = tmp_path / "state/scientific_review/B/review_request.json"
    raw = json.loads(request_path.read_text(encoding="utf-8"))
    raw["production"]["producer_session_id"] = "forged-session"
    request_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ReviewIssuanceError, match="摘要漂移"):
        _issue(
            tmp_path,
            context,
            _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
        )


def test_request_for_other_candidate_fails_closed(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    drift_context = _context(candidate_snapshot_id="report-snapshot_2")
    with pytest.raises(ScientificReviewTransitionError, match="其他候选"):
        publish_production_context(tmp_path, "B", drift_context)


# ─── 负向：真实 reviewer/producer 分离（执行前失败关闭） ──────────────────────


def test_reviewer_self_review_rejected_before_execution(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    calls: list[tuple[str, ...]] = []

    def _spy(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        calls.append(argv)
        raise AssertionError("生产者自审不得执行复核进程")

    with pytest.raises(ReviewIssuanceError, match="生产者"):
        _issue(tmp_path, context, _spy, reviewer_id="producer-agent")
    assert calls == []


def test_same_host_session_as_producer_rejected_before_execution(
    tmp_path: Path,
) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    calls: list[tuple[str, ...]] = []

    def _spy(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        calls.append(argv)
        raise AssertionError("同宿主会话自审不得执行复核进程")

    with pytest.raises(ReviewIssuanceError, match="会话"):
        _issue(tmp_path, context, _spy, review_session_id="producer-session-1")
    assert calls == []


# ─── 负向：runner/host 执行证据失败关闭 ──────────────────────────────────────


def test_failed_review_process_rejects_issuance(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    with pytest.raises(ReviewIssuanceError, match="失败"):
        _issue(tmp_path, context, _fake_runner(tmp_path, context, returncode=1))
    assert not (tmp_path / scientific_review_receipt_path("B")).exists()


def test_future_process_time_rejected(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    future_finished = ISSUED_AT + timedelta(days=1)
    with pytest.raises(ReviewIssuanceError, match="未来"):
        _issue(
            tmp_path,
            context,
            _fake_runner(tmp_path, context, finished_at=future_finished),
        )
    assert not (tmp_path / scientific_review_receipt_path("B")).exists()


def test_unavailable_host_executable_rejected_before_execution(
    tmp_path: Path,
) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    calls: list[tuple[str, ...]] = []

    def _spy(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        calls.append(argv)
        raise AssertionError("宿主可执行文件不可用时不得执行复核进程")

    with pytest.raises(ReviewIssuanceError, match="宿主"):
        _issue(
            tmp_path,
            context,
            _spy,
            host_executable=ReviewExecutableEvidence(provenance="unavailable"),
        )
    assert calls == []


def test_resolve_host_executable_probes_real_path_and_version(
    tmp_path: Path,
) -> None:
    executable = tmp_path / "codex"
    executable.write_text("#!/bin/sh\necho codex-cli 0.42.0\n")

    def _run(argv: tuple[str, ...], cwd: str, timeout: float) -> ExternalProcessResult:
        assert argv[-1] == "--version"
        return ExternalProcessResult(
            pid=99,
            argv=argv,
            cwd=cwd,
            started_at=REVIEW_STARTED_AT,
            finished_at=REVIEW_FINISHED_AT,
            returncode=0,
            stdout_tail="codex-cli 0.42.0\n",
            stderr_tail="",
        )

    evidence = resolve_host_executable(
        "codex", explicit_path=str(executable), runner=_run
    )
    assert evidence.provenance == "explicit"
    assert evidence.path == str(executable)
    assert evidence.version == "codex-cli 0.42.0"


# ─── 负向：正式 verdict 字节与过期/未来时间 ──────────────────────────────────


def test_non_formal_verdict_bytes_rejected(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    payload = _verdict_payload(context)
    payload.pop("reviewer_id")
    with pytest.raises(ReviewIssuanceError, match="质控结论"):
        _issue(
            tmp_path,
            context,
            _fake_runner(tmp_path, context, verdict_payload=payload),
        )


def test_expired_verdict_rejected_at_issuance(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    payload = _verdict_payload(context, valid_until=ISSUED_AT.isoformat())
    with pytest.raises(ReviewIssuanceError, match="失效"):
        _issue(
            tmp_path,
            context,
            _fake_runner(tmp_path, context, verdict_payload=payload),
        )


def test_issued_receipt_expired_before_promotion_fails_closed(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    _issue(
        tmp_path,
        context,
        _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
    )
    with pytest.raises(ReviewIssuanceError, match="核验时已失效"):
        verify_receipt_issuance(tmp_path, "B", checked_at=VALID_UNTIL)


def test_issuance_verification_before_receipt_time_fails_closed(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    _issue(
        tmp_path,
        context,
        _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
    )
    with pytest.raises(ReviewIssuanceError, match="早于回执签发"):
        verify_receipt_issuance(
            tmp_path, "B", checked_at=ISSUED_AT - timedelta(microseconds=1)
        )


def test_veto_verdict_does_not_authorize_issuance(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    payload = _verdict_payload(
        context,
        verdict="veto",
        veto_disposition="recoverable",
        issues=[
            {
                "issue_id": "issue-1",
                "severity": "blocking",
                "category": "来源一致性",
                "description_zh": "客观缓解率数值与登记来源不一致。",
                "source_version_id": context.source_refs[0].source_version_id,
                "fragment_ids": list(context.source_refs[0].fragment_ids),
            }
        ],
    )
    with pytest.raises(ReviewIssuanceError, match="接受"):
        _issue(
            tmp_path,
            context,
            _fake_runner(tmp_path, context, verdict_payload=payload),
        )
    assert not (tmp_path / scientific_review_receipt_path("B")).exists()


def test_verdict_for_other_candidate_rejected(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    other = _context(candidate_snapshot_id="report-snapshot_2")
    with pytest.raises(ReviewIssuanceError, match="当前权威上下文"):
        _issue(
            tmp_path,
            context,
            _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(other)),
        )


# ─── 负向：只有自洽 JSON、没有真实签发记录 ───────────────────────────────────


def test_self_consistent_receipt_without_issuance_record_rejected(
    tmp_path: Path,
) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    _write_verdict(tmp_path, _verdict_payload(context))
    _write_receipt_file(tmp_path, _hand_written_receipt(context))
    with pytest.raises(ReviewIssuanceError, match="签发记录"):
        verify_receipt_issuance(tmp_path, "B")


def test_receipt_swapped_after_issuance_fails_closed(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    _issue(
        tmp_path,
        context,
        _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
    )
    _write_receipt_file(tmp_path, _hand_written_receipt(context, pid=5252))
    with pytest.raises(ReviewIssuanceError, match="签发记录"):
        verify_receipt_issuance(tmp_path, "B")


def test_tampered_issuance_record_fails_closed(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    _issue(
        tmp_path,
        context,
        _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
    )
    record_path = tmp_path / review_issuance_record_path("B")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["reviewer_id"] = "另一位复核者"
    record_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ReviewIssuanceError, match="摘要漂移"):
        verify_receipt_issuance(tmp_path, "B")


def test_stale_record_for_republished_request_fails_closed(tmp_path: Path) -> None:
    context = _context()
    _publish_request(tmp_path, context)
    _issue(
        tmp_path,
        context,
        _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
    )
    drift = _context(candidate_snapshot_id="report-snapshot_2")
    with pytest.raises(ScientificReviewTransitionError, match="其他候选|跨候选"):
        _publish_request(tmp_path, drift)


# ─── CLI 签发入口 ────────────────────────────────────────────────────────────


def _cli_args(project_root: Path) -> list[str]:
    return [
        "review",
        "issue",
        "--project",
        str(project_root),
        "--report",
        "B",
        "--reviewer-id",
        "independent-reviewer",
        "--review-session-id",
        "review-session-9",
        "--host",
        "codex",
        "--review-command",
        ",".join(REVIEW_ARGV),
        "--verdict",
        VERDICT_RELATIVE,
    ]


def test_cli_review_issue_wired_and_issues_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from ci_workflow.application import review_issuer
    from ci_workflow.cli import main

    context = _context()
    _publish_request(tmp_path, context)
    parsed = _build_parser().parse_args(_cli_args(tmp_path))
    assert parsed.report == "B"
    assert parsed.reviewer_id == "independent-reviewer"
    monkeypatch.setattr(
        review_issuer, "resolve_host_executable", lambda *a, **kw: HOST_EXECUTABLE
    )
    monkeypatch.setattr(
        review_issuer, "_current_host_session", lambda session_id: REVIEW_SESSION
    )
    monkeypatch.setattr(
        review_issuer,
        "run_external_process",
        _fake_runner(tmp_path, context, verdict_payload=_verdict_payload(context)),
    )
    exit_code = main(_cli_args(tmp_path))
    assert exit_code == 0
    assert "REVIEW_ISSUED" in capsys.readouterr().out
    attested = verify_receipt_issuance(tmp_path, "B")
    assert attested.status == "verified"


def test_cli_review_issue_maps_failure_to_contract_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from ci_workflow.application import review_issuer
    from ci_workflow.cli import main

    def _fail(*a: Any, **kw: Any) -> Any:
        raise ReviewIssuanceError("宿主可执行文件不可用：测试失败路径")

    monkeypatch.setattr(review_issuer, "resolve_host_executable", _fail)
    exit_code = main(_cli_args(tmp_path))
    assert exit_code == 2
    assert "CONTRACT_ERROR" in capsys.readouterr().err
