"""Task 3.7 SQ01+SQ02：独立科学质控接受才可锁定快照，结论必须完整绑定。

SQ01：GateSpec 通过本身绝不锁定。当前上下文/审查包/结论都是必填且从原始
内容重验证；候选快照与 GateSpec 结果互相绑定（跨快照拒绝）；上下文/审查包/
结论在项目、报告类型/版本、报告对象、候选快照 ID/内容摘要、标准版本、门槛
结果键、覆盖 ID/摘要、来源引用/定位上逐字一致；结论摘要绑定审查输入摘要；
迁移对象绑定被审阅报告对象；覆盖/标准只来自当前上下文。缺失、过期、错项目/
报告/候选/结果键/覆盖/来源/定位、上下文缺失/被篡改、任意审查摘要、跨快照
门槛、跨对象迁移或泛化结论一律失败关闭且零下游。

SQ02：结论不可变、extra=forbid、规范确定性可摘要、JSON Schema 有效且独立
拒绝结构不一致结论；来源/定位/问题条目非空、身份唯一、问题片段非空且必须
属于已复核引用；accepted 无否决处置且无阻断性问题；veto 必须且只能声明
recoverable/exhausted 之一并携带至少一个阻断性问题；泛化“全部通过”自述
不能充当证据。
"""

from __future__ import annotations

import json as jsonlib
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from ci_workflow.domain.enums import ReportKind
from ci_workflow.gates.evaluator import evaluate_report
from ci_workflow.gates.models import ApplicableUniverseSnapshot, ReportGateResult
from tests.integration.test_no_draft_when_blocked import (
    assert_no_downstream_artifacts,
    prepare_workspace,
    satisfying_bindings_for,
    snapshot_for,
    spec_yaml,
)

ROOT = Path(__file__).resolve().parents[2]

PROJECT_ID = "project_000000000000000000000001"
PRODUCER_ID = "qc-producer-1"
REVIEWER_ID = "qc-reviewer-1"
OBJECT_ID = "report_A"


def _canonical_digest(value: object) -> str:
    import hashlib
    import json

    encoded = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ─── 共享工厂 ────────────────────────────────────────────────────────────────


def _passed_gate_result(report_kind: ReportKind) -> ReportGateResult:
    from ci_workflow.gates.models import ReportDecision

    spec = spec_yaml(report_kind.value)
    snapshot = snapshot_for(report_kind)
    result = evaluate_report(
        spec,
        snapshot,
        satisfying_bindings_for(spec, snapshot),
        contract_version="1",
    )
    assert result.decision is ReportDecision.PASSED
    return result


def _candidate_digest(snapshot: ApplicableUniverseSnapshot) -> str:
    from ci_workflow.qc.scientific import candidate_content_digest

    return candidate_content_digest(snapshot)


def _source_refs() -> list[dict[str, object]]:
    return [
        {
            "source_version_id": "source-1",
            "fragment_ids": ["frag-1"],
            "claim_ids": ["claim-1"],
            "fact_version_ids": ["fact-1"],
            "locators": [
                {
                    "fragment_id": "frag-1",
                    "locator": {
                        "document_role": "registry",
                        "field_path": "primary_outcome.measure",
                        "url": "https://registry.example/NCT0001",
                    },
                }
            ],
        }
    ]


def _locators() -> list[dict[str, object]]:
    return [
        {
            "fragment_id": "frag-1",
            "locator": {
                "document_role": "registry",
                "field_path": "primary_outcome.measure",
                "url": "https://registry.example/NCT0001",
            },
        }
    ]


def _context_payload(
    report_kind: ReportKind,
    gate_result: ReportGateResult,
    snapshot: ApplicableUniverseSnapshot,
    *,
    context_id: str = "ctx-1",
    producer_id: str = PRODUCER_ID,
    project_id: str = PROJECT_ID,
    report_version: str = "v1",
    report_object_id: str | None = None,
    candidate_snapshot_id: str | None = None,
    candidate_digest: str | None = None,
    criteria_version: str = "1.0",
    gate_result_key: str | None = None,
    contract_version: str = "1",
    coverage_set_id: str = "coverage-set-1",
    coverage_digest: str = "a" * 64,
    source_refs: list[dict[str, object]] | None = None,
    locators: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "context_id": context_id,
        "producer_id": producer_id,
        "project_id": project_id,
        "report_kind": report_kind.value,
        "report_version": report_version,
        "report_object_id": report_object_id or f"report_{report_kind.value}",
        "candidate_snapshot_id": candidate_snapshot_id
        or gate_result.evidence_snapshot_id,
        "candidate_content_digest": candidate_digest or _candidate_digest(snapshot),
        "criteria_version": criteria_version,
        "gate_result_key": gate_result_key or gate_result.result_key,
        "contract_version": contract_version,
        "coverage_set_id": coverage_set_id,
        "coverage_digest": coverage_digest,
        "source_refs": source_refs if source_refs is not None else _source_refs(),
        "locators": locators if locators is not None else _locators(),
    }


def _bundle_payload(
    report_kind: ReportKind,
    gate_result: ReportGateResult,
    snapshot: ApplicableUniverseSnapshot,
    *,
    producer_id: str = PRODUCER_ID,
    project_id: str = PROJECT_ID,
    report_version: str = "v1",
    report_object_id: str | None = None,
    candidate_snapshot_id: str | None = None,
    candidate_digest: str | None = None,
    gate_result_key: str | None = None,
    criteria_version: str = "1.0",
    coverage_set_id: str = "coverage-set-1",
    coverage_digest: str = "a" * 64,
    source_refs: list[dict[str, object]] | None = None,
    locators: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "producer_id": producer_id,
        "project_id": project_id,
        "report_kind": report_kind.value,
        "report_version": report_version,
        "report_object_id": report_object_id or f"report_{report_kind.value}",
        "candidate_snapshot_id": candidate_snapshot_id
        or gate_result.evidence_snapshot_id,
        "candidate_content_digest": candidate_digest or _candidate_digest(snapshot),
        "criteria_version": criteria_version,
        "gate_result_key": gate_result_key or gate_result.result_key,
        "coverage_set_id": coverage_set_id,
        "coverage_digest": coverage_digest,
        "source_refs": source_refs if source_refs is not None else _source_refs(),
        "locators": locators if locators is not None else _locators(),
    }


def _verdict_payload(
    report_kind: ReportKind,
    gate_result: ReportGateResult,
    snapshot: ApplicableUniverseSnapshot,
    *,
    verdict: str = "accepted",
    veto_disposition: str | None = None,
    verdict_id: str = "qc-verdict-1",
    project_id: str = PROJECT_ID,
    contract_version: str = "1",
    report_version: str = "v1",
    report_object_id: str | None = None,
    candidate_snapshot_id: str | None = None,
    candidate_digest: str | None = None,
    gate_result_key: str | None = None,
    criteria_version: str = "1.0",
    coverage_set_id: str = "coverage-set-1",
    coverage_digest: str = "a" * 64,
    source_refs: list[dict[str, object]] | None = None,
    locators: list[dict[str, object]] | None = None,
    issues: tuple[dict[str, object], ...] = (),
    reviewer_id: str = REVIEWER_ID,
    review_input_digest: str | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "criteria_version": criteria_version,
        "verdict_id": verdict_id,
        "verdict": verdict,
        "project_id": project_id,
        "contract_version": contract_version,
        "report_kind": report_kind.value,
        "report_version": report_version,
        "report_object_id": report_object_id or f"report_{report_kind.value}",
        "candidate_snapshot_id": candidate_snapshot_id
        or gate_result.evidence_snapshot_id,
        "candidate_content_digest": candidate_digest or _candidate_digest(snapshot),
        "gate_result_key": gate_result_key or gate_result.result_key,
        "coverage_set_id": coverage_set_id,
        "coverage_digest": coverage_digest,
        "source_refs": source_refs if source_refs is not None else _source_refs(),
        "locators": locators if locators is not None else _locators(),
        "issues": list(issues),
        "reviewer_id": reviewer_id,
        "review_input_digest": review_input_digest or "c" * 64,
        "reviewed_at": "2026-08-12T10:00:00+08:00",
        "valid_until": "2027-01-01T00:00:00+08:00",
    }
    if veto_disposition is not None:
        payload["veto_disposition"] = veto_disposition
    if extra:
        payload.update(extra)
    return payload


def _accepted_trio(
    report_kind: ReportKind,
    gate_result: ReportGateResult,
    snapshot: ApplicableUniverseSnapshot,
    **overrides: object,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """构造内容一致的 (上下文, 审查包, 结论) 三元组；结论摘要绑定审查包摘要。

    ``contract_version`` 只属于上下文与结论；``producer_id`` 只属于上下文与
    审查包；``reviewer_id`` 只属于结论。
    """
    from ci_workflow.qc.scientific import ScientificQcReviewBundle

    ctx_only = {"contract_version", "producer_id", "context_id"}
    bundle_only = {"producer_id"}
    verdict_only = {"contract_version", "reviewer_id"}
    ctx_overrides = {k: v for k, v in overrides.items() if k in ctx_only or k not in (
        set(ctx_only) | set(bundle_only) | set(verdict_only)
    )}
    bundle_overrides = {
        k: v for k, v in overrides.items() if k in bundle_only or k not in (
            set(ctx_only) | set(verdict_only)
        )
    }
    verdict_overrides = {
        k: v for k, v in overrides.items() if k in verdict_only or k not in (
            set(ctx_only) | set(bundle_only)
        )
    }
    ctx_dict = _context_payload(report_kind, gate_result, snapshot, **ctx_overrides)
    bundle_dict = _bundle_payload(report_kind, gate_result, snapshot, **bundle_overrides)
    bundle = ScientificQcReviewBundle.model_validate(bundle_dict)
    verdict_dict = _verdict_payload(
        report_kind, gate_result, snapshot,
        review_input_digest=bundle.input_digest,
        **verdict_overrides,
    )
    return ctx_dict, bundle_dict, verdict_dict


def _veto_trio(
    report_kind: ReportKind,
    gate_result: ReportGateResult,
    snapshot: ApplicableUniverseSnapshot,
    veto_disposition: str,
    **overrides: object,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """构造可修复/已穷尽否决三元组；结论摘要绑定审查包摘要。"""
    from ci_workflow.qc.scientific import ScientificQcReviewBundle

    ctx_only = {"contract_version", "producer_id", "context_id"}
    bundle_only = {"producer_id"}
    verdict_only = {"contract_version", "reviewer_id"}
    ctx_overrides = {k: v for k, v in overrides.items() if k in ctx_only or k not in (
        set(ctx_only) | set(bundle_only) | set(verdict_only)
    )}
    bundle_overrides = {
        k: v for k, v in overrides.items() if k in bundle_only or k not in (
            set(ctx_only) | set(verdict_only)
        )
    }
    verdict_overrides = {
        k: v for k, v in overrides.items() if k in verdict_only or k not in (
            set(ctx_only) | set(bundle_only)
        )
    }
    ctx_dict = _context_payload(report_kind, gate_result, snapshot, **ctx_overrides)
    bundle_dict = _bundle_payload(report_kind, gate_result, snapshot, **bundle_overrides)
    bundle = ScientificQcReviewBundle.model_validate(bundle_dict)
    blocking_issue = {
        "issue_id": "issue-1",
        "severity": "blocking",
        "category": "结果解读",
        "description_zh": "主要终点结果解读存在可修正偏差，需复核。",
        "source_version_id": "source-1",
        "fragment_ids": ["frag-1"],
    }
    verdict_dict = _verdict_payload(
        report_kind, gate_result, snapshot,
        verdict="veto",
        veto_disposition=veto_disposition,
        issues=(blocking_issue,),
        review_input_digest=bundle.input_digest,
        **verdict_overrides,
    )
    return ctx_dict, bundle_dict, verdict_dict


def _apply_boundary(
    *,
    current_context: dict[str, object],
    verdict: dict[str, object],
    review_bundle: dict[str, object],
    gate_result: ReportGateResult,
    snapshot: ApplicableUniverseSnapshot,
    workspace_root: Path,
    database_path: Path,
    reviewer_actor_id: str = REVIEWER_ID,
    executor=None,
    object_id: str | None = None,
    exhaustion=None,
) -> str:
    from ci_workflow.capabilities.scientific_qc import apply_scientific_qc_verdict

    return apply_scientific_qc_verdict(
        current_context=current_context,
        verdict=verdict,
        review_bundle=review_bundle,
        gate_result=gate_result,
        snapshot=snapshot,
        workspace_root=workspace_root,
        database_path=database_path,
        reviewer_actor_id=reviewer_actor_id,
        executor=executor,
        object_id=object_id,
        exhaustion=exhaustion,
    )


# ─── SQ01 ────────────────────────────────────────────────────────────────────


def test_snapshot_lock_requires_explicit_schema_valid_scientific_qc_acceptance(
    tmp_path: Path,
) -> None:
    """GateSpec 通过 + 候选快照，但无有效接受结论时不锁定、零下游。"""
    from ci_workflow.capabilities.scientific_qc import (
        apply_scientific_qc_verdict,
        lock_snapshot_requires_acceptance,
    )
    from ci_workflow.qc.scientific import (
        ScientificQcCurrentContext,
        ScientificQcReviewBundle,
        ScientificQcVerdict,
    )

    report_kind = ReportKind.A
    workspace_root = prepare_workspace(tmp_path)
    gate_result = _passed_gate_result(report_kind)
    snapshot = snapshot_for(report_kind)
    database_path = workspace_root / "project.sqlite"

    def assert_zero_downstream(project_id: str = PROJECT_ID, version: str = "v1") -> None:
        assert_no_downstream_artifacts(
            workspace_root,
            project_id=project_id,
            report_kind=report_kind,
            report_version=version,
        )

    # 1) GateSpec 通过本身绝不锁定
    with pytest.raises(ValueError, match="接受结论"):
        lock_snapshot_requires_acceptance(
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 2) 结论缺失 → 失败关闭
    ctx_dict, bundle_dict, _ = _accepted_trio(report_kind, gate_result, snapshot)
    with pytest.raises(ValueError, match="接受结论"):
        apply_scientific_qc_verdict(
            current_context=ctx_dict,
            verdict=None,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            reviewer_actor_id=REVIEWER_ID,
        )
    assert_zero_downstream()

    # 3) 审查包缺失 → 失败关闭
    ctx_dict, _, verdict_dict = _accepted_trio(report_kind, gate_result, snapshot)
    with pytest.raises(ValueError, match="审查包"):
        apply_scientific_qc_verdict(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=None,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            reviewer_actor_id=REVIEWER_ID,
        )
    assert_zero_downstream()

    # 4) 当前上下文缺失 → 失败关闭
    _, bundle_dict, verdict_dict = _accepted_trio(report_kind, gate_result, snapshot)
    with pytest.raises(ValueError, match="当前上下文"):
        apply_scientific_qc_verdict(
            current_context=None,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            reviewer_actor_id=REVIEWER_ID,
        )
    assert_zero_downstream()

    # 5) 过期/失效结论 → 失败关闭
    ctx_dict, bundle_dict, stale_verdict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    stale_verdict["valid_until"] = "2026-01-01T00:00:00+08:00"
    with pytest.raises(ValueError, match="过期|有效"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=stale_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 6) 畸形结论 → 模型层拒绝
    with pytest.raises(ValidationError):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "verdict": "yes_please",
            }
        )
    assert_zero_downstream()

    # 7) 错误项目 → 失败关闭
    ctx_dict, bundle_dict, wrong_project_verdict = _accepted_trio(
        report_kind, gate_result, snapshot, project_id="project-other"
    )
    with pytest.raises(ValueError, match="项目"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=wrong_project_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream(project_id="project-other")

    # 8) 错误报告类型 → 失败关闭
    ctx_dict, bundle_dict, wrong_report_verdict = _accepted_trio(
        ReportKind.B, gate_result, snapshot
    )
    with pytest.raises(ValueError, match="报告类型"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=wrong_report_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 9) 错误版本 → 失败关闭（结论报告版本与当前上下文不一致）
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    wrong_version_verdict = dict(verdict_dict)
    wrong_version_verdict["report_version"] = "v9"
    with pytest.raises(ValueError, match="版本"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=wrong_version_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream(version="v9")

    # 10) 错误候选快照 → 失败关闭
    ctx_dict, bundle_dict, wrong_candidate_verdict = _accepted_trio(
        report_kind, gate_result, snapshot, candidate_snapshot_id="snapshot-wrong"
    )
    with pytest.raises(ValueError, match="候选快照"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=wrong_candidate_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 11) 候选内容摘要漂移（上下文/结论绑定旧摘要）→ 失败关闭
    ctx_dict, bundle_dict, drifted_verdict = _accepted_trio(
        report_kind, gate_result, snapshot, candidate_digest="f" * 64
    )
    with pytest.raises(ValueError, match="内容摘要|漂移|不一致"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=drifted_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 12) 错误 GateSpec 结果键 → 失败关闭
    ctx_dict, bundle_dict, wrong_gate_key_verdict = _accepted_trio(
        report_kind, gate_result, snapshot, gate_result_key="forged-key"
    )
    with pytest.raises(ValueError, match="结果键"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=wrong_gate_key_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 13) 错误合同版本 → 失败关闭
    ctx_dict, bundle_dict, wrong_contract_verdict = _accepted_trio(
        report_kind, gate_result, snapshot, contract_version="2"
    )
    with pytest.raises(ValueError, match="合同版本"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=wrong_contract_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 14) 覆盖被当前上下文权威绑定：伪造覆盖上下文（model_copy 漂移）→ 拒绝
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    forged_coverage_ctx = ScientificQcCurrentContext.model_validate(
        ctx_dict
    ).model_copy(update={"coverage_set_id": "coverage-set-forged"})
    with pytest.raises(ValueError, match="不一致"):
        _apply_boundary(
            current_context=forged_coverage_ctx.model_dump(mode="json"),
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 15) 任意分离 criteria/coverage 不再可选：边界只接受当前上下文 ──────────
    # 调用方无法以分离字符串选择不同当前上下文（签名不再接受 criteria/coverage）
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    with pytest.raises(TypeError):
        apply_scientific_qc_verdict(  # type: ignore[call-arg]
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            reviewer_actor_id=REVIEWER_ID,
            criteria_version="9.9",
            coverage_set_id="coverage-set-9",
            coverage_digest="9" * 64,
        )
    assert_zero_downstream()

    # 16) 审查包被篡改（候选摘要与上下文/结论不一致）→ 失败关闭
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    tampered_bundle = dict(bundle_dict)
    tampered_bundle["candidate_content_digest"] = "e" * 64
    with pytest.raises(ValueError, match="审查包与结论|不一致"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=tampered_bundle,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 17) 上下文被篡改（model_copy/dict 漂移）→ 从原始内容重验证失败关闭
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    forged_ctx = ScientificQcCurrentContext.model_validate(ctx_dict).model_copy(
        update={"criteria_version": "9.9"}
    )
    with pytest.raises(ValueError, match="标准版本|不一致"):
        _apply_boundary(
            current_context=forged_ctx.model_dump(mode="json"),
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 18) 任意审查输入摘要（结论不绑定审查包内容）→ 失败关闭
    ctx_dict, bundle_dict, _ = _accepted_trio(report_kind, gate_result, snapshot)
    arbitrary_verdict = _verdict_payload(
        report_kind, gate_result, snapshot, review_input_digest="d" * 64
    )
    with pytest.raises(ValueError, match="审查输入摘要"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=arbitrary_verdict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 19) 跨快照 GateSpec：门槛结果绑定不同候选快照/宇宙摘要 → 失败关闭 ────
    # 使用 schema 有效的另一快照（evidence_snapshot_id 不同、摘要自洽）
    from tests.integration.test_no_draft_when_blocked import _snapshot

    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    other_snapshot = _snapshot(evidence_snapshot_id="snapshot-other")
    assert other_snapshot.evidence_snapshot_id != snapshot.evidence_snapshot_id
    with pytest.raises(ValueError, match="候选快照"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=other_snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    ctx_dict2, bundle2, verdict2 = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    other_summary_snapshot = snapshot_for(report_kind).model_copy(
        update={"universe_summary": "forged-summary"}
    )
    with pytest.raises(ValueError, match="宇宙摘要|不一致"):
        _apply_boundary(
            current_context=ctx_dict2,
            verdict=verdict2,
            review_bundle=bundle2,
            gate_result=gate_result,
            snapshot=other_summary_snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 20) 跨报告对象：A 结论不能迁移 B 对象（对象已在 scientific_qc）────────
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.graph.types import TransitionRequest

    executor = GraphExecutor(workspace_root, run_id="run-sqc-cross")
    from tests.graph.test_transition_matrix import _NOW

    for obj in ("report_B", "report_A"):
        executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=f"cross:{obj}:collect",
                project_id=PROJECT_ID,
                run_id="run-sqc-cross",
                family="report_evidence",
                object_id=obj,
                from_state="queued",
                to_state="collecting",
                trigger="candidate_scope_locked",
                evidence={"candidate_scope_locked": True},
                actor_id="builder",
                occurred_at=_NOW,
            )
        )
        executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id=f"cross:{obj}:qc",
                project_id=PROJECT_ID,
                run_id="run-sqc-cross",
                family="report_evidence",
                object_id=obj,
                from_state="collecting",
                to_state="scientific_qc",
                trigger="gate_deterministic_pass",
                evidence={
                    "gate_deterministic_pass": True,
                    "candidate_snapshot_established": True,
                },
                actor_id="builder",
                occurred_at=_NOW,
            )
        )
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    # A 结论（report_object_id=report_A）迁移 B 对象 → 失败关闭
    with pytest.raises(ValueError, match="报告对象"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id="report_B",
        )
    assert_zero_downstream()

    # 21) 无效来源/定位绑定（定位引用未声明的来源片段）→ 模型层拒绝 ──────────
    with pytest.raises(ValidationError, match="来源片段"):
        ScientificQcReviewBundle.model_validate(
            {
                **_bundle_payload(report_kind, gate_result, snapshot),
                "locators": [
                    {
                        "fragment_id": "frag-not-declared",
                        "locator": {
                            "document_role": "unknown",
                            "url": "https://nowhere.example/does-not-exist",
                        },
                    }
                ],
            }
        )
    assert_zero_downstream()

    # 22) 泛化接受结论（无来源/定位绑定）→ 模型层拒绝 ────────────────────────
    with pytest.raises(ValidationError, match="来源引用"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "source_refs": [],
            }
        )
    with pytest.raises(ValidationError, match="精确来源定位"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "locators": [],
            }
        )
    assert_zero_downstream()

    # 23) 接受结论携带阻断性问题 → 模型层拒绝 ────────────────────────────────
    with pytest.raises(ValidationError, match="阻断"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot, verdict="accepted"),
                "issues": [
                    {
                        "issue_id": "issue-1",
                        "severity": "blocking",
                        "category": "结果解读",
                        "description_zh": "主要终点结果解读存在可修正偏差，需复核。",
                        "source_version_id": "source-1",
                        "fragment_ids": ["frag-1"],
                    }
                ],
            }
        )
    assert_zero_downstream()

    # 24) 否决无否决处置 → 模型层拒绝 ────────────────────────────────────────
    with pytest.raises(ValidationError, match="可修复或已穷尽"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot, verdict="veto"),
                "issues": (
                    {
                        "issue_id": "issue-1",
                        "severity": "blocking",
                        "category": "结果解读",
                        "description_zh": "主要终点结果解读存在可修正偏差，需复核。",
                        "source_version_id": "source-1",
                        "fragment_ids": ["frag-1"],
                    },
                ),
            }
        )
    assert_zero_downstream()

    # 25) 摘要字段严格小写 SHA-256 ───────────────────────────────────────────
    for bad_digest in ("x", "X" * 64, "a" * 63, "g" * 64, "A" * 64):
        with pytest.raises(ValidationError, match="SHA-256"):
            ScientificQcReviewBundle.model_validate(
                {
                    **_bundle_payload(report_kind, gate_result, snapshot),
                    "candidate_content_digest": bad_digest,
                }
            )
        with pytest.raises(ValidationError, match="SHA-256"):
            ScientificQcVerdict.model_validate(
                {
                    **_verdict_payload(report_kind, gate_result, snapshot),
                    "review_input_digest": bad_digest,
                }
            )
        with pytest.raises(ValidationError, match="SHA-256"):
            ScientificQcCurrentContext.model_validate(
                {
                    **_context_payload(report_kind, gate_result, snapshot),
                    "candidate_content_digest": bad_digest,
                }
            )
    assert_zero_downstream()

    # 26) 定位精度：仅 document_role 或空白维度不构成精确定位 ────────────────
    with pytest.raises(ValidationError, match="真实维度"):
        ScientificQcReviewBundle.model_validate(
            {
                **_bundle_payload(report_kind, gate_result, snapshot),
                "locators": [
                    {
                        "fragment_id": "frag-1",
                        "locator": {"document_role": "registry"},
                    }
                ],
            }
        )
    with pytest.raises(ValidationError, match="文本不能为空"):
        ScientificQcReviewBundle.model_validate(
            {
                **_bundle_payload(report_kind, gate_result, snapshot),
                "locators": [
                    {
                        "fragment_id": "frag-1",
                        "locator": {
                            "document_role": "registry",
                            "field_path": "   ",
                        },
                    }
                ],
            }
        )
    assert_zero_downstream()

    # 27) 来源引用必须携带声明/事实谱系与定位：空列表全部拒绝 ────────────────
    for empty_field in ("fragment_ids", "claim_ids", "fact_version_ids", "locators"):
        with pytest.raises(ValidationError, match="至少|List|item"):
            ScientificQcReviewBundle.model_validate(
                {
                    **_bundle_payload(report_kind, gate_result, snapshot),
                    "source_refs": [
                        {
                            "source_version_id": "source-1",
                            "fragment_ids": ["frag-1"],
                            "claim_ids": ["claim-1"],
                            "fact_version_ids": ["fact-1"],
                            "locators": _locators(),
                            **{empty_field: []},
                        }
                    ],
                }
            )
    assert_zero_downstream()

    # 28) 问题片段证据：空 fragment_ids → 模型层拒绝 ─────────────────────────
    for model, payload in (
        (ScientificQcVerdict, _verdict_payload(report_kind, gate_result, snapshot)),
    ):
        with pytest.raises(ValidationError, match="至少|List|item"):
            model.model_validate(
                {
                    **payload,
                    "issues": [
                        {
                            "issue_id": "issue-1",
                            "severity": "blocking",
                            "category": "结果解读",
                            "description_zh": "主要终点结果解读存在可修正偏差，需复核。",
                            "source_version_id": "source-1",
                            "fragment_ids": [],
                        }
                    ],
                }
            )
    assert_zero_downstream()

    # 29) 审查者身份：边界传入的 reviewer_actor 与结论审查者不一致 → 拒绝 ───
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    with pytest.raises(ValueError, match="审查者"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            reviewer_actor_id="someone-else",
        )
    assert_zero_downstream()

    # 30) 候选快照内容漂移：同一 evidence_snapshot_id 但内容改变 → 拒绝 ──────
    # 门槛结果绑定的是快照完整内容摘要；内容改变（即使 ID/宇宙摘要相同）
    # 使门槛结果不再适用于当前候选。
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    altered_snapshot = snapshot_for(report_kind).model_copy(
        update={"trial_ids": ("trial-1", "trial-2")}
    )
    # 模型层：快照摘要校验会在重验证时失败（universe_summary 不匹配内容）
    with pytest.raises(ValueError, match="不一致|摘要"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=altered_snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    # 直接攻击：构造一个"同 ID 同宇宙摘要但内容不同"的快照字典，重验证拒绝
    with pytest.raises(ValueError, match="内容摘要|不一致"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot={
                **snapshot.model_dump(mode="json"),
                "trial_ids": ["trial-1", "trial-2"],
            },
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 31) 标准/规则版本绑定：criteria_version 必须等于 gate_result.spec_version
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    # 当前上下文标准版本与门槛结果规则版本不一致 → 拒绝
    forged_criteria_ctx = ScientificQcCurrentContext.model_validate(
        ctx_dict
    ).model_copy(update={"criteria_version": "9.9"})
    with pytest.raises(ValueError, match="标准版本|规则版本"):
        _apply_boundary(
            current_context=forged_criteria_ctx.model_dump(mode="json"),
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    # 门槛结果规则版本与当前标准不一致（spec_version=9.9 vs criteria=1.0）
    # model_copy 伪造 spec_version 使结果键不一致 → 从原始内容重验证失败关闭
    forged_gate = gate_result.model_copy(update={"spec_version": "9.9"})
    with pytest.raises(ValueError, match="结果键与标识字段不一致"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=forged_gate,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
        )
    assert_zero_downstream()

    # 32) 边界签发授权：直接自造完整证据（含 SHA 摘要）无法伪造迁移 ──────────
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.graph.types import TransitionRequest

    forged_executor = GraphExecutor(workspace_root, run_id="run-forged")
    from tests.graph.test_transition_matrix import _NOW as _TM_NOW

    for obj in ("report_A",):
        forged_executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id="forged:collect",
                project_id=PROJECT_ID,
                run_id="run-forged",
                family="report_evidence",
                object_id=obj,
                from_state="queued",
                to_state="collecting",
                trigger="candidate_scope_locked",
                evidence={"candidate_scope_locked": True},
                actor_id="attacker",
                occurred_at=_TM_NOW,
            )
        )
        forged_executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id="forged:qc",
                project_id=PROJECT_ID,
                run_id="run-forged",
                family="report_evidence",
                object_id=obj,
                from_state="collecting",
                to_state="scientific_qc",
                trigger="gate_deterministic_pass",
                evidence={
                    "gate_deterministic_pass": True,
                    "candidate_snapshot_established": True,
                },
                actor_id="attacker",
                occurred_at=_TM_NOW,
            )
        )
    # 自造完整证据（所有 SHA 字段形状正确）但不经边界签发授权 → 拒绝
    forged_evidence = {
        "isolated_qc_accepted": True,
        "qc_verdict_id": "forged-verdict",
        "qc_verdict_digest": "f" * 64,
        "qc_candidate_snapshot_id": "snap-1",
        "qc_candidate_content_digest": "f" * 64,
        "qc_review_input_digest": "f" * 64,
        "qc_report_object_id": "report_A",
        "qc_context_digest": "f" * 64,
        "qc_authorization_id": "forged-auth-1",
    }
    forged_event = forged_executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id="forged:lock",
            project_id=PROJECT_ID,
            run_id="run-forged",
            family="report_evidence",
            object_id="report_A",
            from_state="scientific_qc",
            to_state="snapshot_locked",
            trigger="isolated_qc_accepted",
            evidence=forged_evidence,
            actor_id="attacker",
            occurred_at=_TM_NOW,
        )
    )
    assert forged_event.event_type == "graph.transition.rejected"
    assert forged_event.payload["reason"] == "qc_authorization_missing"
    assert "authorization_not_found" in forged_event.payload["guard_reason"]
    assert forged_executor.state()["report_evidence"]["report_A"] == "scientific_qc"
    assert_zero_downstream()

    # 33) 公开自填发行 API 已移除：普通调用方无法签发授权 ────────────────────
    from ci_workflow.graph.executor import GraphExecutor as _GE

    assert not hasattr(_GE, "issue_scientific_qc_authorization")
    # 执行器只有私有证明发行方法（不透明证明构造器不可公开导入/调用）
    assert hasattr(_GE, "_issue_scientific_qc_authorization")
    assert not hasattr(_GE, "issue_scientific_qc_authorization")

    # 34) 公开追加无条件拒绝授权事件；磁盘篡改仍被归约/重放拒绝 ────────────
    from ci_workflow.graph.executor import IdempotentSideEffects
    from ci_workflow.graph.reducer import graph_reducer
    from ci_workflow.graph.state import initial_state
    from ci_workflow.storage.checkpoint_store import CheckpointStore
    from ci_workflow.storage.event_store import (
        AuthorizationAppendForbiddenError,
        EventStore,
        WorkflowEvent,
    )

    direct_root = workspace_root / "direct_append"
    direct_root.mkdir(parents=True, exist_ok=True)
    direct_store = EventStore(direct_root)
    # 攻击者直接构造授权事件：payload 形状正确但 boundary_proof_digest 错误
    forged_auth = {
        "authorization_id": "auth-direct-1",
        "boundary_proof_digest": "f" * 64,
        "qc_entry_epoch": 0,
        "project_id": PROJECT_ID,
        "run_id": "run-direct",
        "report_object_id": "report_A",
        "from_state": "scientific_qc",
        "to_state": "snapshot_locked",
        "verdict_id": "v1",
        "verdict_digest": "a" * 64,
        "candidate_snapshot_id": "snap-1",
        "candidate_content_digest": "b" * 64,
        "review_input_digest": "c" * 64,
        "context_digest": "d" * 64,
        "reviewer_actor_id": "attacker",
        "evidence_digest": "e" * 64,
    }
    # 直接构造 WorkflowEvent 并调用公开 append（绕过执行器发行）
    from ci_workflow.domain.ids import stable_id

    forged_event = WorkflowEvent(
        schema_version="1.0",
        event_id=stable_id(
            "scientific-qc-authorization", PROJECT_ID, "run-direct",
            "report_A", "auth-direct-1",
        ),
        project_id=PROJECT_ID,
        run_id="run-direct",
        event_type="scientific_qc.authorization.issued",
        occurred_at=_TM_NOW,
        actor_id="attacker",
        idempotency_key=(
            f"scientific_qc.authorization:{PROJECT_ID}:run-direct:"
            f"report_A:auth-direct-1"
        ),
        payload=forged_auth,
    )
    # 公开 append 在存储前无条件拒绝（即使摘要/事件 ID/幂等键形状完全正确）
    with pytest.raises(AuthorizationAppendForbiddenError, match="专用路径"):
        direct_store.append(forged_event)
    assert direct_store.read_all() == ()
    assert direct_store.path.read_text(encoding="utf-8") == ""
    # 磁盘被直接篡改（绕过 API 写入形状正确的存储记录）：
    # 归约/重放仍以 boundary_proof_digest 不匹配失败关闭
    from ci_workflow.storage.event_store import (
        StoredWorkflowEvent,
        _canonical_json,
        _event_digest,
    )

    tampered_record = StoredWorkflowEvent(
        **forged_event.model_dump(),
        sequence=1,
        event_digest=_event_digest(forged_event, 1),
    )
    direct_store.path.write_bytes(
        _canonical_json(tampered_record.model_dump(mode="json"))
    )
    from ci_workflow.graph.reducer import GraphEventContractError

    with pytest.raises(GraphEventContractError, match="boundary_proof_digest"):
        state = initial_state()
        for ev in direct_store.read_all():
            state = graph_reducer(state, ev)
    # 完整重放同样失败
    with pytest.raises(GraphEventContractError, match="boundary_proof_digest"):
        CheckpointStore(direct_root).replay(
            direct_store,
            run_id="run-direct",
            initial_state=initial_state(),
            reducer=graph_reducer,
            side_effect=IdempotentSideEffects(direct_root),
        )
    assert_zero_downstream()

    # 35) 一次性消费 + 代次绑定：恢复周期后旧授权不得重复消费 ────────────────
    from tests.graph._qc_authorization_fixture import (
        issue_test_qc_authorization,
    )

    epoch_executor = GraphExecutor(workspace_root, run_id="run-epoch")
    for obj in ("report_E",):
        epoch_executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id="epoch:collect",
                project_id=PROJECT_ID,
                run_id="run-epoch",
                family="report_evidence",
                object_id=obj,
                from_state="queued",
                to_state="collecting",
                trigger="candidate_scope_locked",
                evidence={"candidate_scope_locked": True},
                actor_id="builder",
                occurred_at=_TM_NOW,
            )
        )
        epoch_executor.submit(
            TransitionRequest(
                schema_version="1.0",
                request_id="epoch:qc",
                project_id=PROJECT_ID,
                run_id="run-epoch",
                family="report_evidence",
                object_id=obj,
                from_state="collecting",
                to_state="scientific_qc",
                trigger="gate_deterministic_pass",
                evidence={
                    "gate_deterministic_pass": True,
                    "candidate_snapshot_established": True,
                },
                actor_id="builder",
                occurred_at=_TM_NOW,
            )
        )
    # 签发授权并消费一次（可修复否决 → recovering）
    veto_evidence = {
        "qc_veto": True,
        "qc_veto_fixable": True,
        "qc_verdict_id": "qc-verdict-1",
        "qc_verdict_digest": "a" * 64,
        "qc_candidate_snapshot_id": "snap-1",
        "qc_candidate_content_digest": "b" * 64,
        "qc_review_input_digest": "c" * 64,
        "qc_report_object_id": "report_E",
        "qc_context_digest": "d" * 64,
    }
    rec_evidence = dict(veto_evidence)
    rec_evidence_without = {
        k: v for k, v in rec_evidence.items() if k != "qc_authorization_id"
    }
    rec_digest = _canonical_digest(rec_evidence_without)
    old_auth = issue_test_qc_authorization(
        epoch_executor,
        report_object_id="report_E",
        from_state="scientific_qc",
        to_state="recovering",
        verdict="veto",
        evidence_digest=rec_digest,
        actor_id="pi",
        project_id=PROJECT_ID,
        occurred_at=_TM_NOW,
    )
    rec_evidence["qc_authorization_id"] = old_auth
    first = epoch_executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id="epoch:veto",
            project_id=PROJECT_ID,
            run_id="run-epoch",
            family="report_evidence",
            object_id="report_E",
            from_state="scientific_qc",
            to_state="recovering",
            trigger="qc_veto_fixable",
            evidence=rec_evidence,
            actor_id="pi",
            occurred_at=_TM_NOW,
        )
    )
    assert first.event_type == "graph.transition.accepted"
    # 恢复周期：recovering -> scientific_qc（代次 +1）
    epoch_executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id="epoch:reopen",
            project_id=PROJECT_ID,
            run_id="run-epoch",
            family="report_evidence",
            object_id="report_E",
            from_state="recovering",
            to_state="scientific_qc",
            trigger="gate_deterministic_pass",
            evidence={
                "gate_deterministic_pass": True,
                "candidate_snapshot_established": True,
            },
            actor_id="builder",
            occurred_at=_TM_NOW,
        )
    )
    # 新请求 ID 复用旧授权 → 拒绝（一次性消费 + 代次不匹配）
    reuse_evidence = dict(rec_evidence)
    reuse_evidence["qc_authorization_id"] = old_auth
    reuse = epoch_executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id="epoch:veto-reuse",
            project_id=PROJECT_ID,
            run_id="run-epoch",
            family="report_evidence",
            object_id="report_E",
            from_state="scientific_qc",
            to_state="recovering",
            trigger="qc_veto_fixable",
            evidence=reuse_evidence,
            actor_id="pi",
            occurred_at=_TM_NOW,
        )
    )
    assert reuse.event_type == "graph.transition.rejected"
    assert reuse.payload["reason"] == "qc_authorization_mismatch"
    assert reuse.payload["guard_reason"] in (
        "authorization_already_consumed",
        "authorization_epoch_mismatch",
    )
    assert_zero_downstream()

    # 36) 语义校验进入正式边界：嵌套定位重复在签发授权前被拒绝 ──────────────
    nested_dup_ref = {
        "source_version_id": "source-1",
        "fragment_ids": ["frag-1"],
        "claim_ids": ["claim-1"],
        "fact_version_ids": ["fact-1"],
        "locators": [
            {
                "fragment_id": "frag-1",
                "locator": {
                    "document_role": "registry",
                    "field_path": "primary_outcome",
                },
            },
            {
                "fragment_id": "frag-1",
                "locator": {
                    "document_role": "registry",
                    "field_path": "secondary_outcome",
                },
            },
        ],
    }
    from ci_workflow.qc.scientific import ScientificQcVerdict as _SV

    with pytest.raises(ValidationError):
        _SV.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "source_refs": [nested_dup_ref],
            }
        )
    assert_zero_downstream()


# ─── SQ02 ────────────────────────────────────────────────────────────────────


def test_verdict_has_report_scope_snapshot_candidate_sources_issues_and_locators() -> None:
    """accepted 结论必须完整绑定报告作用域、候选快照、来源、定位与问题。"""
    from ci_workflow.qc.scientific import (
        ScientificQcReviewBundle,
        ScientificQcVerdict,
        candidate_content_digest,
    )

    report_kind = ReportKind.A
    gate_result = _passed_gate_result(report_kind)
    snapshot = snapshot_for(report_kind)
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    bundle = ScientificQcReviewBundle.model_validate(bundle_dict)
    verdict = ScientificQcVerdict.model_validate(verdict_dict)

    # ── 不可变、extra=forbid、确定性摘要、JSON Schema 有效 ──────────────────
    assert verdict.model_config.get("extra") == "forbid"
    assert verdict.model_config.get("frozen") is True
    assert bundle.model_config.get("extra") == "forbid"
    assert bundle.model_config.get("frozen") is True

    with pytest.raises(ValidationError):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "arbitrary_extra_field": True,
            }
        )
    with pytest.raises(ValidationError):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "verdict_digest": "forged-digest",
            }
        )

    # 规范性：同内容同摘要；重验证保留摘要
    assert verdict.verdict_digest == ScientificQcVerdict.model_validate(
        verdict.model_dump(mode="json", exclude={"verdict_digest"})
    ).verdict_digest
    assert len(verdict.verdict_digest) == 64
    assert bundle.input_digest == ScientificQcReviewBundle.model_validate(
        bundle.model_dump(mode="json", exclude={"input_digest"})
    ).input_digest

    # ── 必需绑定字段 ─────────────────────────────────────────────────────────
    assert verdict.project_id == PROJECT_ID
    assert verdict.contract_version == "1"
    assert verdict.report_kind is ReportKind.A
    assert verdict.report_version == "v1"
    assert verdict.report_object_id == "report_A"
    assert verdict.candidate_snapshot_id == gate_result.evidence_snapshot_id
    assert verdict.candidate_content_digest == candidate_content_digest(snapshot)
    assert verdict.gate_result_key == gate_result.result_key
    assert verdict.coverage_set_id == "coverage-set-1"
    assert verdict.coverage_digest == "a" * 64
    assert verdict.source_refs
    assert verdict.locators
    assert verdict.issues == ()
    assert verdict.reviewer_id == REVIEWER_ID
    assert verdict.reviewed_at.utcoffset() is not None
    assert verdict.valid_until.utcoffset() is not None
    assert verdict.veto_disposition is None

    # ── 结论来源引用/定位与审查包逐字一致 ────────────────────────────────────
    assert verdict.source_refs == bundle.source_refs
    assert verdict.locators == bundle.locators
    assert verdict.review_input_digest == bundle.input_digest

    # ── 来源/定位/问题条目非空、身份唯一、非占位 ─────────────────────────────
    with pytest.raises(ValidationError):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "reviewer_id": "   ",
            }
        )
    with pytest.raises(ValidationError, match="来源引用"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "source_refs": [],
            }
        )
    with pytest.raises(ValidationError, match="重复|唯一"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "source_refs": [
                    {
                        "source_version_id": "dup",
                        "fragment_ids": ["frag-1"],
                        "claim_ids": ["claim-1"],
                        "fact_version_ids": ["fact-1"],
                        "locators": [
                            {
                                "fragment_id": "frag-1",
                                "locator": {
                                    "document_role": "registry",
                                    "field_path": "primary_outcome",
                                },
                            }
                        ],
                    },
                    {
                        "source_version_id": "dup",
                        "fragment_ids": ["frag-2"],
                        "claim_ids": ["claim-2"],
                        "fact_version_ids": ["fact-2"],
                        "locators": [
                            {
                                "fragment_id": "frag-2",
                                "locator": {
                                    "document_role": "registry",
                                    "field_path": "secondary_outcome",
                                },
                            }
                        ],
                    },
                ],
            }
        )

    # ── accepted 不可能存在阻断性问题；veto 必须有阻断性问题 ────────────────
    blocking_issue = {
        "issue_id": "issue-1",
        "severity": "blocking",
        "category": "结果解读",
        "description_zh": "主要终点结果解读存在可修正偏差，需复核。",
        "source_version_id": "source-1",
        "fragment_ids": ["frag-1"],
    }
    with pytest.raises(ValidationError, match="阻断"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot, verdict="accepted"),
                "issues": (blocking_issue,),
            }
        )
    veto_recoverable = ScientificQcVerdict.model_validate(
        {
            **_verdict_payload(report_kind, gate_result, snapshot, verdict="veto"),
            "veto_disposition": "recoverable",
            "issues": (blocking_issue,),
        }
    )
    assert veto_recoverable.verdict == "veto"
    assert veto_recoverable.veto_disposition == "recoverable"
    assert veto_recoverable.has_blocking_issues() is True
    with pytest.raises(ValidationError, match="阻断性问题"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot, verdict="veto"),
                "veto_disposition": "recoverable",
            }
        )
    with pytest.raises(ValidationError, match="否决处置"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot, verdict="accepted"),
                "veto_disposition": "recoverable",
            }
        )

    # ── 问题来源/片段必须属于已复核引用 ──────────────────────────────────────
    with pytest.raises(ValidationError, match="来源"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot, verdict="veto"),
                "veto_disposition": "recoverable",
                "issues": (
                    {
                        **blocking_issue,
                        "source_version_id": "source-unknown",
                    },
                ),
            }
        )
    with pytest.raises(ValidationError, match="片段"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot, verdict="veto"),
                "veto_disposition": "recoverable",
                "issues": (
                    {
                        **blocking_issue,
                        "fragment_ids": ["frag-unknown"],
                    },
                ),
            }
        )

    # ── 泛化“全部通过”自述不能充当证据（无来源/定位）────────────────────────
    with pytest.raises(ValidationError, match="来源引用"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "source_refs": [],
            }
        )

    # ── JSON Schema 独立拒绝结构不一致结论（非仅 Pydantic） ─────────────────
    schema = jsonlib.loads(
        (ROOT / "schemas/scientific-qc-verdict.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    def schema_errors(payload: dict[str, object]) -> list:
        return list(validator.iter_errors(payload))

    # 合法接受结论：0 错误
    assert schema_errors(verdict.model_dump(mode="json")) == []
    # 合法否决结论：0 错误
    veto_payload = ScientificQcVerdict.model_validate(
        {
            **_verdict_payload(report_kind, gate_result, snapshot, verdict="veto"),
            "veto_disposition": "recoverable",
            "issues": (blocking_issue,),
        }
    )
    assert schema_errors(veto_payload.model_dump(mode="json")) == []
    # accepted + 阻断性问题 → Pydantic 拒绝构造；schema 拒绝不一致字典
    inconsistent = {
        **verdict.model_dump(mode="json"),
        "verdict": "accepted",
        "veto_disposition": "recoverable",
    }
    assert schema_errors(inconsistent) != []
    # veto 无处置 → schema 拒绝
    veto_no_disposition = {
        **veto_payload.model_dump(mode="json"),
        "veto_disposition": None,
    }
    assert schema_errors(veto_no_disposition) != []
    # veto 无阻断性问题 → schema 拒绝
    veto_no_issue = {
        **veto_payload.model_dump(mode="json"),
        "issues": [],
    }
    assert schema_errors(veto_no_issue) != []
    # 问题空片段 → schema 拒绝
    empty_frag_issue = {
        **veto_payload.model_dump(mode="json"),
        "issues": [
            {
                **blocking_issue,
                "fragment_ids": [],
            }
        ],
    }
    assert schema_errors(empty_frag_issue) != []
    # 重复来源引用（完全相同的对象）→ schema 拒绝（uniqueItems）
    dup_ref = {
        "source_version_id": "dup",
        "fragment_ids": ["frag-1"],
        "claim_ids": ["claim-1"],
        "fact_version_ids": ["fact-1"],
        "locators": [
            {
                "fragment_id": "frag-1",
                "locator": {
                    "document_role": "registry",
                    "field_path": "primary_outcome",
                },
            }
        ],
    }
    dup_sources = {
        **verdict.model_dump(mode="json"),
        "source_refs": [dup_ref, dict(dup_ref)],
    }
    assert schema_errors(dup_sources) != []

    # ── 语义校验器：Draft 2020-12 无法表达的跨数组语义唯一/定位精度 ────────
    from ci_workflow.qc.scientific import check_scientific_qc_verdict_semantics

    # 合法结论：0 违例
    assert check_scientific_qc_verdict_semantics(
        verdict.model_dump(mode="json")
    ) == []
    # 重复语义 source_version_id（不同内容）→ 违例（uniqueItems 无法捕获）
    dup_semantic = {
        **verdict.model_dump(mode="json"),
        "source_refs": [
            {
                "source_version_id": "dup",
                "fragment_ids": ["frag-1"],
                "claim_ids": ["claim-1"],
                "fact_version_ids": ["fact-1"],
                "locators": [
                    {
                        "fragment_id": "frag-1",
                        "locator": {
                            "document_role": "registry",
                            "field_path": "primary_outcome",
                        },
                    }
                ],
            },
            {
                "source_version_id": "dup",
                "fragment_ids": ["frag-2"],
                "claim_ids": ["claim-2"],
                "fact_version_ids": ["fact-2"],
                "locators": [
                    {
                        "fragment_id": "frag-2",
                        "locator": {
                            "document_role": "registry",
                            "field_path": "secondary_outcome",
                        },
                    }
                ],
            },
        ],
    }
    assert check_scientific_qc_verdict_semantics(dup_semantic) != []
    # 重复语义定位 fragment_id → 违例
    dup_loc = {
        **verdict.model_dump(mode="json"),
        "locators": [
            {
                "fragment_id": "frag-1",
                "locator": {
                    "document_role": "registry",
                    "field_path": "primary_outcome",
                },
            },
            {
                "fragment_id": "frag-1",
                "locator": {
                    "document_role": "registry",
                    "field_path": "secondary_outcome",
                },
            },
        ],
    }
    assert check_scientific_qc_verdict_semantics(dup_loc) != []
    # 重复语义 issue_id → 违例
    dup_issue = {
        **veto_payload.model_dump(mode="json"),
        "issues": [blocking_issue, dict(blocking_issue)],
    }
    assert check_scientific_qc_verdict_semantics(dup_issue) != []
    # 定位缺少真实维度（仅 document_role）→ 违例
    imprecise_loc = {
        **verdict.model_dump(mode="json"),
        "locators": [
            {
                "fragment_id": "frag-1",
                "locator": {"document_role": "registry"},
            }
        ],
    }
    assert check_scientific_qc_verdict_semantics(imprecise_loc) != []
    # 定位引用未声明片段 → 违例
    unbound_loc = {
        **verdict.model_dump(mode="json"),
        "locators": [
            {
                "fragment_id": "frag-unknown",
                "locator": {
                    "document_role": "registry",
                    "field_path": "primary_outcome",
                },
            }
        ],
    }
    assert check_scientific_qc_verdict_semantics(unbound_loc) != []
    # 问题片段为空 → 违例
    empty_issue_frags = {
        **veto_payload.model_dump(mode="json"),
        "issues": [{**blocking_issue, "fragment_ids": []}],
    }
    assert check_scientific_qc_verdict_semantics(empty_issue_frags) != []

    # ── 嵌套定位重复/未绑定（P1-2）：同一 SourceRef.locators 内相同
    #    fragment_id 但定位字段不同 → 模型/语义/边界全部拒绝 ────────────────
    nested_dup_ref = {
        "source_version_id": "source-1",
        "fragment_ids": ["frag-1"],
        "claim_ids": ["claim-1"],
        "fact_version_ids": ["fact-1"],
        "locators": [
            {
                "fragment_id": "frag-1",
                "locator": {
                    "document_role": "registry",
                    "field_path": "primary_outcome",
                },
            },
            {
                "fragment_id": "frag-1",
                "locator": {
                    "document_role": "registry",
                    "field_path": "secondary_outcome",
                },
            },
        ],
    }
    # Pydantic 模型层拒绝
    with pytest.raises(ValidationError, match="重复|片段"):
        ScientificQcVerdict.model_validate(
            {
                **_verdict_payload(report_kind, gate_result, snapshot),
                "source_refs": [nested_dup_ref],
            }
        )
    # 语义校验器拒绝
    nested_dup_payload = {
        **verdict.model_dump(mode="json"),
        "source_refs": [nested_dup_ref],
    }
    assert check_scientific_qc_verdict_semantics(nested_dup_payload) != []
    # 嵌套定位片段未声明于本来源 → 拒绝
    nested_unbound = {
        **verdict.model_dump(mode="json"),
        "source_refs": [
            {
                **nested_dup_ref,
                "fragment_ids": ["frag-other"],
            }
        ],
    }
    assert check_scientific_qc_verdict_semantics(nested_unbound) != []

    # ── 审查输入摘要绑定内容：内容变化 → 摘要变化 ───────────────────────────
    other_bundle = ScientificQcReviewBundle.model_validate(
        {
            **_bundle_payload(report_kind, gate_result, snapshot),
            "candidate_content_digest": "f" * 64,
        }
    )
    assert other_bundle.input_digest != bundle.input_digest


# ─── 第三轮修复：公开追加能力边界 + 生产 Schema 校验 ────────────────────────


def test_public_event_store_append_rejects_exact_authorization_event(
    tmp_path: Path,
) -> None:
    """攻击：攻击者已取得/计算出完全正确的授权事件（boundary_proof_digest、
    事件 ID、幂等键与载荷全部与边界签发一致），直接调用公开
    ``EventStore.append`` → 存储前确定性拒绝，事件流不变。"""
    from datetime import UTC, datetime

    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.storage.event_store import (
        AuthorizationAppendForbiddenError,
        EventStore,
        WorkflowEvent,
    )
    from tests.graph._qc_authorization_fixture import (
        issue_test_qc_authorization,
    )

    root = tmp_path / "attack_root"
    root.mkdir()
    executor = GraphExecutor(root, run_id="run-attack")
    issue_test_qc_authorization(
        executor=executor,
        report_object_id="report_A",
        occurred_at=datetime(2026, 8, 12, 10, 0, 0, tzinfo=UTC),
    )
    stored = executor.store.read_all()
    auth_records = [
        event
        for event in stored
        if event.event_type == "scientific_qc.authorization.issued"
    ]
    assert len(auth_records) == 1
    legit = auth_records[0]
    # 攻击者复制真实事件的每个字段（payload/摘要/事件 ID/幂等键逐字一致）
    forged = WorkflowEvent(**legit.model_dump(exclude={"sequence", "event_digest"}))
    # 同一事件库公开追加（即使内容完全相同）→ 存储前拒绝，事件流不变
    with pytest.raises(AuthorizationAppendForbiddenError, match="专用路径"):
        executor.store.append(forged)
    assert executor.store.read_all() == stored
    # 全新事件库公开追加完全正确的授权事件 → 存储前拒绝，无任何记录写入
    fresh = EventStore(tmp_path / "fresh_root")
    with pytest.raises(AuthorizationAppendForbiddenError, match="专用路径"):
        fresh.append(forged)
    assert fresh.read_all() == ()
    assert fresh.path.read_text(encoding="utf-8") == ""


def test_specialized_authorization_append_requires_module_private_capability(
    tmp_path: Path,
) -> None:
    """专用追加路径必须携带模块私有能力对象并按身份（``is``）校验；公开 API
    不存在授权追加工厂/别名，通用测试/事件助手无法在生成环境中走专用路径。"""
    import copy
    from datetime import UTC, datetime

    from ci_workflow.storage.event_store import (
        EventStore,
        EventStoreError,
        WorkflowEvent,
    )

    # 公开 API 断言：不存在公开的授权追加工厂/别名
    assert not hasattr(EventStore, "append_authorization")
    assert not hasattr(EventStore, "append_authorization_event")
    assert not hasattr(EventStore, "issue_authorization")

    store = EventStore(tmp_path / "cap_root")
    event = WorkflowEvent(
        schema_version="1.0",
        event_id="evt-1",
        project_id="p",
        run_id="r",
        event_type="graph.node.completed",
        occurred_at=datetime(2026, 8, 12, 10, 0, 0, tzinfo=UTC),
        actor_id="a",
        idempotency_key="k:1",
        payload={},
    )
    # 伪造能力对象（任意对象冒充）→ 身份校验拒绝
    with pytest.raises(EventStoreError, match="能力"):
        store._append_authorization(event, object())  # type: ignore[arg-type]
    # 复制能力对象（同类型不同身份）→ 身份校验拒绝
    from ci_workflow.storage.event_store import _AUTHORIZATION_APPEND_CAPABILITY

    with pytest.raises(EventStoreError, match="能力"):
        store._append_authorization(event, copy.copy(_AUTHORIZATION_APPEND_CAPABILITY))
    # 缺少能力参数 → 拒绝
    with pytest.raises(TypeError):
        store._append_authorization(event)  # type: ignore[call-arg]
    # 真实能力但非授权事件类型 → 拒绝（专用路径只接受授权事件）
    with pytest.raises(EventStoreError, match="授权事件"):
        store._append_authorization(event, _AUTHORIZATION_APPEND_CAPABILITY)
    # 公开追加普通事件仍正常（非授权事件不受能力边界影响）
    stored = store.append(event)
    assert stored.event_type == "graph.node.completed"
    assert len(store.read_all()) == 1


def test_boundary_rejects_payload_that_only_json_schema_catches(
    tmp_path: Path,
) -> None:
    """负例：Pydantic+语义单独通过但 Draft 2020-12 Schema 拒绝
    （``locator.page=true`` 被 Pydantic 宽松强转为 1）→ 生产验证器先跑
    Schema，公开 ``apply_scientific_qc_verdict`` 在签发任何授权事件前
    失败关闭。"""
    from ci_workflow.capabilities.scientific_qc import (
        ScientificQcBoundaryError,
        _strip_computed,
    )
    from ci_workflow.graph.executor import GraphExecutor
    from ci_workflow.qc.scientific import (
        ScientificQcVerdict,
        check_scientific_qc_verdict_semantics,
    )

    report_kind = ReportKind.A
    workspace_root = prepare_workspace(tmp_path)
    database_path = workspace_root / "project.sqlite"
    gate_result = _passed_gate_result(report_kind)
    snapshot = snapshot_for(report_kind)
    ctx_dict, bundle_dict, verdict_dict = _accepted_trio(
        report_kind, gate_result, snapshot
    )
    # 仅把嵌套定位的 page 从整数改为布尔 true（其余全部合法）
    verdict_dict["locators"][0]["locator"]["page"] = True

    # 1) 三层独立验证：Pydantic 通过、语义通过、Schema 拒绝
    stripped = _strip_computed(verdict_dict)
    coerced = ScientificQcVerdict.model_validate(stripped)
    assert coerced.locators[0].locator.page == 1
    assert check_scientific_qc_verdict_semantics(dict(stripped)) == []
    schema = jsonlib.loads(
        (ROOT / "schemas/scientific-qc-verdict.schema.json").read_text(
            encoding="utf-8"
        )
    )
    schema_errors = list(Draft202012Validator(schema).iter_errors(stripped))
    assert schema_errors

    # 2) 生产边界：公开 apply 在签发授权前拒绝（确定性错误）
    executor = GraphExecutor(workspace_root, run_id="run-schema-reject")
    with pytest.raises(ScientificQcBoundaryError, match="打包 Schema"):
        _apply_boundary(
            current_context=ctx_dict,
            verdict=verdict_dict,
            review_bundle=bundle_dict,
            gate_result=gate_result,
            snapshot=snapshot,
            workspace_root=workspace_root,
            database_path=database_path,
            executor=executor,
            object_id="report_A",
        )
    # 授权写入前拒绝：事件流为空，无授权事件、无迁移事件
    assert executor.store.read_all() == ()
    assert not any(
        event.event_type == "scientific_qc.authorization.issued"
        for event in executor.store.read_all()
    )
