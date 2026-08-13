"""Task 3.7 测试专用质控授权夹具（隔离于生产，仅供图/转换测试驱动 QC 迁移）。

生产路径只允许 ``capabilities.scientific_qc.apply_scientific_qc_verdict``
经完整重验证后通过私有证明构造授权；普通测试不经边界驱动 QC 迁移时，
使用本夹具构造不透明证明、调用执行器私有发行方法，并返回执行器签发的
授权标识（与守卫证据中的 qc_authorization_id 一致）。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from ci_workflow.domain.enums import ReportKind
from ci_workflow.graph.executor import GraphExecutor, _ScientificQcAuthorizationProof
from ci_workflow.qc.scientific import (
    ScientificQcCurrentContext,
    ScientificQcVerdict,
)
from tests.integration.test_scientific_qc_gate import _locators, _source_refs

_PROJECT_ID = "p_gt06"


def _payload_digest(value: object) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _valid_verdict(
    *,
    report_object_id: str,
    to_state: str,
    verdict: str = "accepted",
    verdict_id: str = "qc-verdict-1",
) -> ScientificQcVerdict:
    issue = (
        (
            {
                "issue_id": "issue-1",
                "severity": "blocking",
                "category": "结果解读",
                "description_zh": "主要终点结果解读存在可修正偏差，需复核。",
                "source_version_id": "source-1",
                "fragment_ids": ["frag-1"],
            },
        )
        if verdict == "veto"
        else ()
    )
    payload: dict = {
        "schema_version": "1.0",
        "criteria_version": "1.0",
        "verdict_id": verdict_id,
        "verdict": verdict,
        "project_id": _PROJECT_ID,
        "contract_version": "1",
        "report_kind": ReportKind.A.value,
        "report_version": "v1",
        "report_object_id": report_object_id,
        "candidate_snapshot_id": "snap-1",
        "candidate_content_digest": "b" * 64,
        "gate_result_key": "k",
        "coverage_set_id": "coverage-set-1",
        "coverage_digest": "a" * 64,
        "source_refs": _source_refs(),
        "locators": _locators(),
        "issues": list(issue),
        "reviewer_id": "qc-reviewer-1",
        "review_input_digest": "c" * 64,
        "reviewed_at": "2026-08-12T10:00:00+08:00",
        "valid_until": "2027-01-01T00:00:00+08:00",
    }
    if verdict == "veto":
        payload["veto_disposition"] = (
            "recoverable" if to_state == "recovering" else "exhausted"
        )
    return ScientificQcVerdict.model_validate(payload)


def _valid_context(*, report_object_id: str) -> ScientificQcCurrentContext:
    return ScientificQcCurrentContext.model_validate(
        {
            "schema_version": "1.0",
            "context_id": "ctx-test",
            "producer_id": "qc-producer-1",
            "project_id": _PROJECT_ID,
            "report_kind": ReportKind.A.value,
            "report_version": "v1",
            "report_object_id": report_object_id,
            "candidate_snapshot_id": "snap-1",
            "candidate_content_digest": "b" * 64,
            "criteria_version": "1.0",
            "gate_result_key": "k",
            "contract_version": "1",
            "coverage_set_id": "coverage-set-1",
            "coverage_digest": "a" * 64,
            "source_refs": _source_refs(),
            "locators": _locators(),
        }
    )


def issue_test_qc_authorization(
    executor: GraphExecutor,
    *,
    report_object_id: str,
    from_state: str = "scientific_qc",
    to_state: str = "snapshot_locked",
    verdict: str = "accepted",
    exhaustion_record_digest: str | None = None,
    evidence_digest: str = "e" * 64,
    actor_id: str = "pi",
    project_id: str = _PROJECT_ID,
    occurred_at: datetime,
) -> str:
    """测试专用：构造不透明证明、调用私有发行方法，返回签发授权标识。"""
    verdict_model = _valid_verdict(
        report_object_id=report_object_id, to_state=to_state, verdict=verdict
    )
    context_model = _valid_context(report_object_id=report_object_id)
    proof = _ScientificQcAuthorizationProof(
        project_id=project_id,
        run_id=executor.run_id,
        report_object_id=report_object_id,
        from_state=from_state,
        to_state=to_state,
        verdict=verdict_model,
        context=context_model,
        exhaustion_record_digest=exhaustion_record_digest,
        reviewer_actor_id=actor_id,
        evidence_digest=evidence_digest,
        occurred_at=occurred_at,
    )
    executor._issue_scientific_qc_authorization(proof)
    # 与执行器一致的授权标识派生
    return _payload_digest(
        {
            "project_id": project_id,
            "run_id": executor.run_id,
            "report_object_id": report_object_id,
            "from_state": from_state,
            "to_state": to_state,
            "verdict_id": verdict_model.verdict_id,
            "verdict_digest": verdict_model.verdict_digest,
            "candidate_snapshot_id": verdict_model.candidate_snapshot_id,
            "candidate_content_digest": verdict_model.candidate_content_digest,
            "review_input_digest": verdict_model.review_input_digest,
            "context_digest": context_model.context_digest,
            "exhaustion_record_digest": exhaustion_record_digest,
        }
    )
