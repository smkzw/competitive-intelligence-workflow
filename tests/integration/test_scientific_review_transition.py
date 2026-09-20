"""B/C 两阶段科学复核状态迁移负向优先测试。

合同目标（R2 运行时接线）：B/C 候选先为 ``rendered_unreviewed``；只有真实
``scientific-review-v1`` 回执经实际文件字节核验
（``require_verified_review_receipt``）与权威
``ScientificQcCurrentContext`` 绑定（``bind_receipt_to_production_context``）
全部通过后，才迁移为 ``scientifically_reviewed_rendered_candidate``。
缺回执、伪回执、同会话、自审、旧内容与宿主不可用全部失败关闭。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.scientific_review_transition import (
    RENDERED_UNREVIEWED,
    SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE,
    ScientificReviewTransitionError,
    build_scientific_review_context,
    capture_portal_artifact_binding,
    derive_scientific_source_refs,
    load_scientific_review_receipt,
    production_context_publication_path,
    promote_rendered_candidate,
    publish_production_context,
    publish_scientific_review_request,
    reload_production_context,
    scientific_review_receipt_path,
    scientific_review_request_path,
    verify_portal_artifact_binding,
)
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.qc.review_receipt import (
    ReviewArtifactBinding,
    ReviewContentBinding,
    ReviewContextEvidence,
    ReviewExecutableEvidence,
    ReviewHostSession,
    ReviewProcessEvidence,
    ReviewProductionContext,
    ScientificReviewReceiptError,
    build_scientific_review_receipt,
)
from ci_workflow.qc.scientific import ScientificQcReviewBundle, ScientificQcVerdict

PRODUCED_AT = datetime(2026, 9, 5, 1, 0, 0, tzinfo=UTC)
REVIEW_STARTED_AT = datetime(2026, 9, 5, 2, 0, 0, tzinfo=UTC)
REVIEW_FINISHED_AT = datetime(2026, 9, 5, 2, 30, 0, tzinfo=UTC)
ISSUED_AT = datetime(2026, 9, 5, 3, 0, 0, tzinfo=UTC)

CANDIDATE_DIGEST = hashlib.sha256("候选内容".encode()).hexdigest()
FACT_VERSION_BY_REF = {
    "fact-1": "fact-version-1",
    "fact-1-row": "fact-version-1",
    "fact-2": "fact-version-2",
    "fact-3": "fact-version-3",
}


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
            content_text=content,
            acquired_at=PRODUCED_AT,
            published_at=PRODUCED_AT,
            effective_at=None,
            first_disclosed_at=PRODUCED_AT,
            locator=_locator(role),
        )

    return (
        _capture("src-1", "试验一结果正文", "primary_result"),
        _capture("src-2", "试验二结果正文", "registry_posting"),
    )


def _facts() -> tuple[ResearchFact, ...]:
    def _fact(fact_id: str, row_ref: str, source_id: str) -> ResearchFact:
        return ResearchFact(
            fact_id=fact_id,
            row_ref=row_ref,
            entity_id="product-alpha",
            entity_type="product",
            canonical_name="产品甲",
            field_id="orr",
            raw_value="80%",
            normalized_value="80",
            disclosure_state="reported_value",
            source_id=source_id,
            locator=_locator("primary_result"),
            original_text="客观缓解率 80%",
        )

    return (
        _fact("fact-1", "fact-1-row", "src-1"),
        _fact("fact-2", "fact-2-row", "src-1"),
        _fact("fact-3", "fact-3-row", "src-2"),
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


def _artifact_file(context: Any, project_root: Path) -> ReviewArtifactBinding:
    path = project_root / "receipts" / "scientific_review" / "B" / "verdict.json"
    path.parent.mkdir(parents=True, exist_ok=True)
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
        valid_until=ISSUED_AT + timedelta(days=7),
    )
    path.write_text(
        json.dumps(verdict.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    return ReviewArtifactBinding(
        artifact_kind="scientific_qc_verdict",
        path="receipts/scientific_review/B/verdict.json",
        artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


MANIFEST_RELATIVE = "reports/B/v1/html.manifest.json"
SITE_RELATIVE = "reports/B/v1/html"


def _portal_site(project_root: Path) -> None:
    """写入最小门户站点与产物清单，供门户字节绑定测试使用。"""
    manifest_path = project_root / MANIFEST_RELATIVE
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text('{"artifact": {"sha256": "0"}}', encoding="utf-8")
    page = project_root / SITE_RELATIVE / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("<!doctype html><title>门户</title>", encoding="utf-8")


def _portal_binding(project_root: Path) -> Any:
    return capture_portal_artifact_binding(
        project_root,
        "B",
        manifest_relative=MANIFEST_RELATIVE,
        site_relative=SITE_RELATIVE,
    )


def _production(context: Any, **overrides: Any) -> ReviewProductionContext:
    values: dict[str, Any] = {
        "project_id": context.project_id,
        "report_kind": context.report_kind.value,
        "report_version": context.report_version,
        "report_object_id": context.report_object_id,
        "candidate_snapshot_id": context.candidate_snapshot_id,
        "candidate_content_digest": context.candidate_content_digest,
        "producer_id": context.producer_id,
        "producer_session_id": "producer-session-1",
        "criteria_version": context.criteria_version,
        "gate_result_key": context.gate_result_key,
        "produced_at": PRODUCED_AT,
        "production_context_digest": context.context_digest,
    }
    values.update(overrides)
    return ReviewProductionContext(**values)


def _review_evidence(**overrides: Any) -> ReviewContextEvidence:
    values: dict[str, Any] = {
        "reviewer_id": "independent-reviewer",
        "host_executable": ReviewExecutableEvidence(
            provenance="path_resolved",
            path="/opt/homebrew/bin/codex",
            resolved_realpath="/opt/homebrew/bin/codex",
            version="codex-cli 0.42.0",
        ),
        "session": ReviewHostSession(
            session_id="review-session-9",
            launcher_pid=777,
            launcher_parent_pid=1,
        ),
        "process": ReviewProcessEvidence(
            kind="external_subprocess",
            pid=4242,
            argv=("/opt/homebrew/bin/codex", "exec", "scientific-review"),
            cwd="/tmp/项目-r2",
            started_at=REVIEW_STARTED_AT,
            finished_at=REVIEW_FINISHED_AT,
            returncode=0,
        ),
        "independent_context": "external_subprocess_session",
    }
    values.update(overrides)
    return ReviewContextEvidence(**values)


def _verified_receipt(
    context: Any, project_root: Path, **overrides: Any
) -> Any:
    _portal_site(project_root)
    publish_scientific_review_request(
        project_root,
        context.report_kind.value,
        context,
        producer_session_id="producer-session-1",
        produced_at=PRODUCED_AT,
        portal_binding=_portal_binding(project_root),
    )
    values: dict[str, Any] = {
        "host": "codex",
        "issued_at": ISSUED_AT,
        "production": _production(context),
        "review": _review_evidence(),
        "content": ReviewContentBinding(
            reviewed_content_digest=context.candidate_content_digest,
            review_input_digest=_review_bundle(context).input_digest,
        ),
        "artifact": _artifact_file(context, project_root),
    }
    values.update(overrides)
    return build_scientific_review_receipt(**values)


def _write_receipt(receipt: Any, project_root: Path, report_kind: str = "B") -> Path:
    path = project_root / scientific_review_receipt_path(report_kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return path


# ─── 权威上下文重建：来源引用绑定真实摄取谱系 ────────────────────────────────


def test_source_refs_recompute_persisted_lineage_ids(tmp_path: Path) -> None:
    from ci_workflow.application.project_service import create_project_workspace
    from ci_workflow.domain.contracts import create_project_contract

    contract = create_project_contract(
        indication="特应性皮炎", reports=["B"], outputs=["html"], cutoff="2026-09-01"
    )
    project_root = create_project_workspace(tmp_path / "项目", contract)
    lineage = ingest_research_evidence(
        project_root=project_root,
        project_id="project-r2",
        contract_version=1,
        report_kind="B",
        data_cutoff=PRODUCED_AT,
        scientific_content_digest=CANDIDATE_DIGEST,
        created_at=PRODUCED_AT,
        sources=_sources(),
        route_attempts=(),
        facts=_facts(),
        claims=_claims(),
    )
    refs = derive_scientific_source_refs(
        sources=_sources(),
        facts=_facts(),
        claims=_claims(),
        fact_version_by_ref=lineage.fact_version_by_ref,
    )
    assert {ref.source_version_id for ref in refs} == set(lineage.source_version_ids)
    assert {loc.fragment_id for ref in refs for loc in ref.locators} == set(
        lineage.fragment_ids
    )
    assert sorted(
        version for ref in refs for version in ref.fact_version_ids
    ) == sorted(lineage.fact_version_ids)
    by_source = {ref.source_version_id: ref for ref in refs}
    # Read the actual persisted identity; the reviewer must not maintain a
    # parallel content-only identity algorithm that drops date revisions.
    from ci_workflow.storage.sqlite import open_database

    with open_database(project_root / "state/project.sqlite") as database:
        src_version = database.execute(
            "SELECT source_version_id FROM source_versions WHERE source_id = ?", ("src-1",)
        ).fetchone()[0]
    assert by_source[src_version].claim_ids == ("claim-1",)
    assert by_source[src_version].fact_version_ids == (
        lineage.fact_version_by_ref["fact-1"],
        lineage.fact_version_by_ref["fact-2"],
    )


def test_source_without_fact_lineage_is_excluded_not_trusted() -> None:
    """没有事实谱系的来源不进入权威上下文（仍经候选内容摘要间接绑定）。"""
    refs = derive_scientific_source_refs(
        sources=_sources(),
        facts=_facts()[:2],
        claims=_claims(),
        fact_version_by_ref=FACT_VERSION_BY_REF,
    )
    assert len(refs) == 1
    assert refs[0].claim_ids == ("claim-1",)


def test_unpersisted_fact_reference_fails_closed() -> None:
    with pytest.raises(ScientificReviewTransitionError, match="事实版本"):
        derive_scientific_source_refs(
            sources=_sources(),
            facts=_facts(),
            claims=_claims(),
            fact_version_by_ref={},
        )


def test_context_rebuild_is_deterministic_and_bound() -> None:
    first = _context()
    second = _context()
    assert first == second
    assert first.context_digest == second.context_digest
    assert first.report_object_id == "report_B"
    assert first.criteria_version == "B-v1"
    assert len(first.source_refs) == 2
    assert len(first.locators) == 2


# ─── 发布/重载：生产上下文物化与篡改检测 ─────────────────────────────────────


def test_production_context_publication_roundtrip(tmp_path: Path) -> None:
    context = _context()
    path = publish_production_context(tmp_path, "B", context)
    assert path == tmp_path / production_context_publication_path("B")
    assert path.is_file()
    assert reload_production_context(tmp_path, "B") == context


def test_tampered_production_context_publication_fails_closed(tmp_path: Path) -> None:
    context = _context()
    publish_production_context(tmp_path, "B", context)
    path = tmp_path / production_context_publication_path("B")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["producer_id"] = "另一位生产者"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ScientificReviewTransitionError, match="篡改"):
        reload_production_context(tmp_path, "B")


def test_missing_production_context_publication_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ScientificReviewTransitionError, match="生产上下文"):
        reload_production_context(tmp_path, "B")


# ─── 两阶段迁移：正向与全部失败关闭分支 ──────────────────────────────────────


def test_verified_receipt_promotes_rendered_candidate(tmp_path: Path) -> None:
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    state = promote_rendered_candidate(
        project_root=tmp_path,
        current_state=RENDERED_UNREVIEWED,
        context=context,
        receipt=receipt,
    )
    assert state == SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE


def test_verified_receipt_with_non_verdict_artifact_fails_closed(
    tmp_path: Path,
) -> None:
    """外部进程和字节摘要有效，不能把任意 JSON 冒充医学接受结论。"""
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    artifact = tmp_path / "receipts/scientific_review/B/verdict.json"
    artifact.write_text('{"verdict":"accepted"}', encoding="utf-8")
    forged = receipt.model_dump(mode="json")
    forged["artifact"]["artifact_sha256"] = hashlib.sha256(
        artifact.read_bytes()
    ).hexdigest()
    rebuilt = build_scientific_review_receipt(
        host="codex",
        issued_at=ISSUED_AT,
        production=ReviewProductionContext.model_validate(forged["production"]),
        review=ReviewContextEvidence.model_validate(forged["review"]),
        content=ReviewContentBinding.model_validate(forged["content"]),
        artifact=ReviewArtifactBinding.model_validate(forged["artifact"]),
    )
    with pytest.raises(ScientificReviewTransitionError, match="结论产物验证失败"):
        promote_rendered_candidate(
            project_root=tmp_path,
            current_state=RENDERED_UNREVIEWED,
            context=context,
            receipt=rebuilt,
        )


def test_missing_receipt_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ScientificReviewTransitionError, match="缺失"):
        load_scientific_review_receipt(tmp_path, "B")


def test_receipt_file_on_disk_binds_and_promotes(tmp_path: Path) -> None:
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    _write_receipt(receipt, tmp_path)
    loaded = load_scientific_review_receipt(tmp_path, "B")
    assert loaded.receipt_digest == receipt.receipt_digest
    assert (
        promote_rendered_candidate(
            project_root=tmp_path,
            current_state=RENDERED_UNREVIEWED,
            context=context,
            receipt=loaded,
        )
        == SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE
    )


def _write_raw_receipt(payload: dict[str, Any], project_root: Path) -> None:
    path = project_root / scientific_review_receipt_path("B")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_forged_receipt_payload_fails_closed(tmp_path: Path) -> None:
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    payload = receipt.model_dump(mode="json")
    payload["content"]["reviewed_content_digest"] = "f" * 64
    _write_raw_receipt(payload, tmp_path)
    with pytest.raises(ScientificReviewTransitionError, match="验证失败"):
        load_scientific_review_receipt(tmp_path, "B")


def test_unreadable_receipt_payload_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / scientific_review_receipt_path("B")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ScientificReviewTransitionError, match="JSON"):
        load_scientific_review_receipt(tmp_path, "B")


def test_host_unavailable_receipt_fails_closed(tmp_path: Path) -> None:
    context = _context()
    receipt = _verified_receipt(
        context,
        tmp_path,
        review=_review_evidence(
            host_executable=ReviewExecutableEvidence(provenance="unavailable"),
            independent_context="unavailable",
        ),
        unavailable_reason_zh="宿主无法创建独立上下文。",
        artifact=None,
    )
    with pytest.raises(ScientificReviewReceiptError, match="独立上下文"):
        promote_rendered_candidate(
            project_root=tmp_path,
            current_state=RENDERED_UNREVIEWED,
            context=context,
            receipt=receipt,
        )


# ─── format 先行：门户 manifest/站点字节摘要绑定进 review request ─────────────


def test_publish_requires_portal_artifact_binding(tmp_path: Path) -> None:
    """review request 必须绑定门户字节；没有 format 产物就没有请求。"""
    context = _context()
    with pytest.raises(TypeError):
        publish_scientific_review_request(
            tmp_path,
            "B",
            context,
            producer_session_id="producer-session-1",
            produced_at=PRODUCED_AT,
        )


def test_portal_binding_is_bound_into_request_payload(tmp_path: Path) -> None:
    context = _context()
    _portal_site(tmp_path)
    binding = _portal_binding(tmp_path)
    publish_scientific_review_request(
        tmp_path,
        "B",
        context,
        producer_session_id="producer-session-1",
        produced_at=PRODUCED_AT,
        portal_binding=binding,
    )
    raw = json.loads(
        (tmp_path / scientific_review_request_path("B")).read_text(encoding="utf-8")
    )
    assert raw["portal_binding"] == binding.model_dump(mode="json")
    assert raw["portal_binding"]["manifest_relative"] == MANIFEST_RELATIVE
    assert raw["portal_binding"]["site_relative"] == SITE_RELATIVE
    assert len(raw["portal_binding"]["manifest_sha256"]) == 64
    assert len(raw["portal_binding"]["site_sha256"]) == 64


def test_republish_with_unchanged_bytes_is_idempotent(tmp_path: Path) -> None:
    context = _context()
    _portal_site(tmp_path)
    first = publish_scientific_review_request(
        tmp_path,
        "B",
        context,
        producer_session_id="producer-session-1",
        produced_at=PRODUCED_AT,
        portal_binding=_portal_binding(tmp_path),
    )
    second = publish_scientific_review_request(
        tmp_path,
        "B",
        context,
        producer_session_id="producer-session-2",
        produced_at=PRODUCED_AT,
        portal_binding=_portal_binding(tmp_path),
    )
    assert first == second


def test_portal_byte_drift_on_republish_fails_closed(tmp_path: Path) -> None:
    """恢复时重验字节：站点字节相对首次绑定漂移即失败关闭。"""
    context = _context()
    _portal_site(tmp_path)
    publish_scientific_review_request(
        tmp_path,
        "B",
        context,
        producer_session_id="producer-session-1",
        produced_at=PRODUCED_AT,
        portal_binding=_portal_binding(tmp_path),
    )
    page = tmp_path / SITE_RELATIVE / "index.html"
    page.write_text("<!doctype html><title>被篡改</title>", encoding="utf-8")
    with pytest.raises(ScientificReviewTransitionError, match="门户"):
        publish_scientific_review_request(
            tmp_path,
            "B",
            context,
            producer_session_id="producer-session-1",
            produced_at=PRODUCED_AT,
            portal_binding=_portal_binding(tmp_path),
        )


def test_verify_portal_artifact_binding_detects_drift(tmp_path: Path) -> None:
    _portal_site(tmp_path)
    binding = _portal_binding(tmp_path)
    verify_portal_artifact_binding(tmp_path, "B", binding)
    manifest = tmp_path / MANIFEST_RELATIVE
    manifest.write_text('{"artifact": {"sha256": "tampered"}}', encoding="utf-8")
    with pytest.raises(ScientificReviewTransitionError, match="门户"):
        verify_portal_artifact_binding(tmp_path, "B", binding)


def test_cross_project_request_publication_fails_closed(tmp_path: Path) -> None:
    """既有请求属于其他项目时不得覆盖：不接受跨项目历史。"""
    foreign = _context(project_id="project-other")
    _portal_site(tmp_path)
    publish_scientific_review_request(
        tmp_path,
        "B",
        foreign,
        producer_session_id="producer-session-1",
        produced_at=PRODUCED_AT,
        portal_binding=_portal_binding(tmp_path),
    )
    with pytest.raises(ScientificReviewTransitionError, match="跨项目|其他"):
        publish_scientific_review_request(
            tmp_path,
            "B",
            _context(),
            producer_session_id="producer-session-1",
            produced_at=PRODUCED_AT,
            portal_binding=_portal_binding(tmp_path),
        )


def test_cross_candidate_request_publication_fails_closed(tmp_path: Path) -> None:
    """既有请求属于其他候选时不得覆盖：不接受跨候选历史。"""
    stale = _context(candidate_content_digest=hashlib.sha256("旧内容".encode()).hexdigest())
    _portal_site(tmp_path)
    publish_scientific_review_request(
        tmp_path,
        "B",
        stale,
        producer_session_id="producer-session-1",
        produced_at=PRODUCED_AT,
        portal_binding=_portal_binding(tmp_path),
    )
    with pytest.raises(ScientificReviewTransitionError, match="跨候选|其他候选"):
        publish_scientific_review_request(
            tmp_path,
            "B",
            _context(),
            producer_session_id="producer-session-1",
            produced_at=PRODUCED_AT,
            portal_binding=_portal_binding(tmp_path),
        )


def test_promotion_reverifies_portal_bytes(tmp_path: Path) -> None:
    """晋级前重验门户字节：回执有效但站点漂移必须失败关闭。"""
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    page = tmp_path / SITE_RELATIVE / "index.html"
    page.write_text("<!doctype html><title>晋级前篡改</title>", encoding="utf-8")
    with pytest.raises(ScientificReviewTransitionError, match="门户"):
        promote_rendered_candidate(
            project_root=tmp_path,
            current_state=RENDERED_UNREVIEWED,
            context=context,
            receipt=receipt,
        )


def test_promotion_rejects_request_without_portal_binding(tmp_path: Path) -> None:
    """旧式（无门户绑定）请求不能授权晋级。"""
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    request_path = tmp_path / scientific_review_request_path("B")
    raw = json.loads(request_path.read_text(encoding="utf-8"))
    raw.pop("portal_binding")
    body = {key: value for key, value in raw.items() if key != "request_digest"}
    body["request_digest"] = hashlib.sha256(
        (
            json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    request_path.write_text(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(ScientificReviewTransitionError, match="门户"):
        promote_rendered_candidate(
            project_root=tmp_path,
            current_state=RENDERED_UNREVIEWED,
            context=context,
            receipt=receipt,
        )


def test_cross_project_receipt_fails_closed(tmp_path: Path) -> None:
    """其他项目的回执不能晋级当前候选。"""
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    foreign_context = _context(project_id="project-other")
    with pytest.raises(ScientificReviewReceiptError, match="项目"):
        promote_rendered_candidate(
            project_root=tmp_path,
            current_state=RENDERED_UNREVIEWED,
            context=foreign_context,
            receipt=receipt,
        )


def test_self_reviewed_receipt_fails_closed(tmp_path: Path) -> None:
    context = _context()
    forged = _verified_receipt(context, tmp_path).model_dump(mode="json")
    forged["review"]["reviewer_id"] = context.producer_id
    _write_raw_receipt(forged, tmp_path)
    with pytest.raises(ScientificReviewTransitionError, match="不同身份"):
        load_scientific_review_receipt(tmp_path, "B")


def test_same_session_receipt_fails_closed(tmp_path: Path) -> None:
    context = _context()
    forged = _verified_receipt(context, tmp_path).model_dump(mode="json")
    forged["review"]["session"]["session_id"] = "producer-session-1"
    _write_raw_receipt(forged, tmp_path)
    with pytest.raises(ScientificReviewTransitionError, match="会话分离"):
        load_scientific_review_receipt(tmp_path, "B")


def test_stale_content_receipt_fails_closed(tmp_path: Path) -> None:
    stale_context = _context(
        candidate_content_digest=hashlib.sha256("旧内容".encode()).hexdigest()
    )
    receipt = _verified_receipt(stale_context, tmp_path)
    current = _context()
    with pytest.raises(ScientificReviewReceiptError, match="不一致"):
        promote_rendered_candidate(
            project_root=tmp_path,
            current_state=RENDERED_UNREVIEWED,
            context=current,
            receipt=receipt,
        )


def test_promotion_requires_rendered_unreviewed_origin(tmp_path: Path) -> None:
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    for state in (
        SCIENTIFICALLY_REVIEWED_RENDERED_CANDIDATE,
        "evidence_blocked",
        "recovery_required",
        "snapshot_locked",
    ):
        with pytest.raises(ScientificReviewTransitionError, match="rendered_unreviewed"):
            promote_rendered_candidate(
                project_root=tmp_path,
                current_state=state,
                context=context,
                receipt=receipt,
            )


def test_artifact_byte_drift_fails_closed(tmp_path: Path) -> None:
    context = _context()
    receipt = _verified_receipt(context, tmp_path)
    artifact = tmp_path / "receipts" / "scientific_review" / "B" / "verdict.json"
    artifact.write_bytes(b'{"verdict":"changed"}')
    with pytest.raises(ScientificReviewReceiptError, match="实际字节"):
        promote_rendered_candidate(
            project_root=tmp_path,
            current_state=RENDERED_UNREVIEWED,
            context=context,
            receipt=receipt,
        )
