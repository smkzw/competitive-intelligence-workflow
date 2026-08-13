"""Task 3.7 独立科学质控授权边界：验证唯一接受/否决依据并驱动真实图迁移。

位于 GateSpec 确定性通过与报告快照锁定之间。公共入口要求编排层创建的
``ScientificQcCurrentContext``（唯一权威的候选/门槛/覆盖/标准/来源/身份）、
schema 有效的审查输入包与结论；三者都从原始序列化内容完整重验证。

边界强制：
- 候选快照与 GateSpec 结果互相绑定（evidence_snapshot_id / universe_summary
  一致，杜绝跨快照门槛）；
- 当前上下文、审查包、结论在项目/报告/对象/候选/标准/门槛键/覆盖/来源
  定位上逐字一致，且 ``verdict.review_input_digest == bundle.input_digest``；
- 迁移 ``object_id`` 必须等于被审阅报告对象（三处一致）；
- 覆盖身份/摘要与标准版本只从当前上下文取得，调用方无法自由选择分离字符串；
- 审查者身份由边界显式传入（reviewer_actor_id），必须与当前上下文的
  生产者身份不同；两者都不能在结论/审查包中自由自选；
- 否决显式区分可修复/已穷尽；已穷尽否决要求原始重验证的双重穷尽记录，
  并把记录摘要写入守卫证据（小写 SHA-256）。

全部通过后才以边界内生成的真实守卫证据驱动 GraphExecutor 的真实迁移。
守卫证据包含唯一由本边界发出的验证授权材料（结论 ID/摘要、候选快照
ID/内容摘要、审阅输入摘要、报告对象、上下文摘要、穷尽记录摘要），
裸布尔（isolated_qc_accepted=True）永不构成守卫证据。

信任边界：Phase 3 没有权威持久化记录层，``ScientificQcCurrentContext``
由编排层显式构造为当前真源（persistence deferred，见报告），
调用方无法以分离字符串选择不同当前上下文。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.gates.blocker_audit import assert_no_report_downstream_artifacts
from ci_workflow.gates.exhaustion import DoubleExhaustionRecord
from ci_workflow.gates.models import ApplicableUniverseSnapshot, ReportDecision, ReportGateResult
from ci_workflow.graph.executor import GraphExecutor
from ci_workflow.graph.types import TransitionRequest
from ci_workflow.qc.scientific import (
    ScientificQcCurrentContext,
    ScientificQcReviewBundle,
    ScientificQcVerdict,
    check_scientific_qc_review_bundle_semantics,
    check_scientific_qc_verdict_semantics,
)


class ScientificQcBoundaryError(ValueError):
    """质控授权边界拒绝：绑定失败、过期或伪造。"""


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _content_digest(obj: Any) -> str:
    if hasattr(obj, "model_dump"):
        return _sha256_hex(obj.model_dump(mode="json"))
    return _sha256_hex(obj)


# 计算字段：重验证/内容转储时必须剔除，否则 extra=forbid 拒绝输入。
# 含结论摘要、审查输入摘要、上下文摘要与双重穷尽记录/缺口/复核/诊断摘要。
_COMPUTED_FIELDS = frozenset(
    {
        "verdict_digest",
        "input_digest",
        "context_digest",
        "gap_digest",
        "reviewer_inputs_digest",
        "conclusion_digest",
        "diagnosis_digest",
        "record_digest",
        "audit_digest",
        "evidence_digest",
        "universe_closure_digest",
    }
)


def _strip_computed(node: object) -> object:
    """递归剔除计算字段供从原始内容完整重验证。"""
    if isinstance(node, dict):
        return {k: _strip_computed(v) for k, v in node.items() if k not in _COMPUTED_FIELDS}
    if isinstance(node, list):
        return [_strip_computed(i) for i in node]
    return node


def _scientific_qc_verdict_schema() -> dict[str, Any]:
    """解析打包的质控结论 Schema（Draft 2020-12），不接受调用方选择路径。

    同时支持两种布局：
    - 源码树/目录安装包：仓库根 ``schemas/``（本仓库的安装单位是目录包，
      ``ci-workflow package verify --root .`` 以此布局校验）；
    - 打包安装布局：Schema 随包数据装入 ``ci_workflow/schemas/``
      （wheel/venv 安装时模块目录内携带数据文件的布局）。

    两处均缺失时以确定性的 ``ScientificQcBoundaryError`` 失败关闭。
    """
    candidates: tuple[Path, ...] = (
        Path(__file__).resolve().parents[3]
        / "schemas" / "scientific-qc-verdict.schema.json",
        Path(__file__).resolve().parents[1]
        / "schemas" / "scientific-qc-verdict.schema.json",
    )
    for candidate in candidates:
        try:
            return cast(dict[str, Any], json.loads(candidate.read_text(encoding="utf-8")))
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as error:
            raise ScientificQcBoundaryError(
                f"打包的质控结论 Schema 损坏：{candidate}"
            ) from error
    raise ScientificQcBoundaryError(
        "无法定位打包的质控结论 Schema（源码树与安装布局均缺失）"
    )


def validate_scientific_qc_verdict_payload(raw: dict[str, Any]) -> ScientificQcVerdict:
    """生产质控结论验证器：按序执行打包 Schema → Pydantic → 语义校验。

    1. Draft 2020-12：打包的 ``schemas/scientific-qc-verdict.schema.json``；
    2. Pydantic 模型：``ScientificQcVerdict``（extra=forbid、摘要/时间约束）；
    3. 语义校验：``check_scientific_qc_verdict_semantics``（Schema 无法表达
       的跨数组引用/定位精度/语义唯一）。

    任一阶段失败都以确定性的 ``ScientificQcBoundaryError`` 失败关闭，
    绝不让 Schema 违例的载荷进入签发路径。
    """
    stripped = _strip_computed(raw)
    schema = _scientific_qc_verdict_schema()
    try:
        Draft202012Validator(schema).validate(stripped)
    except JsonSchemaValidationError as error:
        raise ScientificQcBoundaryError(
            f"质控结论不符合打包 Schema（{schema.get('$id', 'scientific-qc-verdict')}）："
            f"{error.message}"
        ) from error
    try:
        verdict = ScientificQcVerdict.model_validate(stripped)
    except PydanticValidationError as error:
        raise ScientificQcBoundaryError(f"质控结论模型校验失败：{error}") from error
    violations = check_scientific_qc_verdict_semantics(
        cast(dict[str, Any], stripped)
    )
    if violations:
        raise ScientificQcBoundaryError(
            "质控结论语义校验失败：" + "；".join(violations)
        )
    return verdict


def _revalidate_verdict(raw: dict[str, Any]) -> ScientificQcVerdict:
    """从原始内容完整重验证（拒绝 model_copy 跳过校验）。

    生产验证器按序执行打包 Draft 2020-12 Schema → Pydantic 模型 → 语义
    校验（``validate_scientific_qc_verdict_payload``）；任何违例在签发
    授权前失败关闭。
    """
    return validate_scientific_qc_verdict_payload(raw)


def _revalidate_bundle(raw: dict[str, Any]) -> ScientificQcReviewBundle:
    stripped = _strip_computed(raw)
    bundle = ScientificQcReviewBundle.model_validate(stripped)
    violations = check_scientific_qc_review_bundle_semantics(
        cast(dict[str, Any], stripped)
    )
    if violations:
        raise ScientificQcBoundaryError(
            "审查包语义校验失败：" + "；".join(violations)
        )
    return bundle


def _revalidate_context(raw: dict[str, Any]) -> ScientificQcCurrentContext:
    stripped = _strip_computed(raw)
    context = ScientificQcCurrentContext.model_validate(stripped)
    violations = check_scientific_qc_review_bundle_semantics(
        cast(dict[str, Any], stripped)
    )
    if violations:
        raise ScientificQcBoundaryError(
            "当前上下文语义校验失败：" + "；".join(violations)
        )
    return context


def _revalidate_snapshot(snapshot: ApplicableUniverseSnapshot) -> ApplicableUniverseSnapshot:
    return ApplicableUniverseSnapshot.model_validate(snapshot.model_dump(mode="json"))


def _revalidate_gate_result(result: ReportGateResult) -> ReportGateResult:
    return ReportGateResult.model_validate(result.model_dump(mode="json"))


def _revalidate_exhaustion(record: DoubleExhaustionRecord) -> DoubleExhaustionRecord:
    """从原始内容完整重验证（拒绝 model_copy 伪造角色/内容/摘要）。"""
    return DoubleExhaustionRecord.model_validate(
        _strip_computed(record.model_dump(mode="json"))
    )


def lock_snapshot_requires_acceptance(
    *,
    gate_result: ReportGateResult,
    snapshot: ApplicableUniverseSnapshot,
    workspace_root: Path,
    database_path: Path,
) -> None:
    """GateSpec 通过本身绝不锁定快照。"""
    if gate_result.decision is not ReportDecision.PASSED:
        raise ScientificQcBoundaryError("科学质控必须绑定已通过的 GateSpec 结果")
    raise ScientificQcBoundaryError(
        "报告快照锁定必须由当前、schema 有效且绑定候选快照内容摘要的接受结论授权"
    )


def apply_scientific_qc_verdict(
    *,
    current_context: dict[str, Any] | ScientificQcCurrentContext,
    verdict: dict[str, Any] | ScientificQcVerdict,
    review_bundle: dict[str, Any] | ScientificQcReviewBundle,
    gate_result: ReportGateResult | dict[str, Any],
    snapshot: ApplicableUniverseSnapshot | dict[str, Any],
    workspace_root: Path,
    database_path: Path,
    reviewer_actor_id: str,
    executor: GraphExecutor | None = None,
    object_id: str | None = None,
    exhaustion: DoubleExhaustionRecord | None = None,
    now: datetime | None = None,
) -> str:
    """验证并驱动真实图迁移。返回 next_state。

    当前上下文、审查包与结论均为必填，全部从原始内容完整重验证；
    候选快照与门槛结果互相绑定（跨快照拒绝）；上下文/审查包/结论逐字一致；
    结论摘要绑定审查输入摘要；迁移对象绑定被审阅报告对象；覆盖/标准只来自
    当前上下文；审查者身份由边界传入且与上下文生产者不同；否决显式区分
    可修复/已穷尽；已穷尽否决要求原始重验证的双重穷尽记录。零下游断言在
    否决前后执行。
    """
    if now is None:
        now = datetime.now(UTC)

    # ── 三输入必须存在（schema 有效且从原始内容重验证） ─────────────────────
    if current_context is None:
        raise ScientificQcBoundaryError("科学质控必须携带编排层创建的当前上下文")
    if verdict is None:
        raise ScientificQcBoundaryError(
            "报告快照锁定必须由当前、schema 有效且绑定候选快照内容摘要的接受结论授权"
        )
    if review_bundle is None:
        raise ScientificQcBoundaryError("审查包缺失：科学质控必须携带 schema 有效的审查输入包")
    if isinstance(current_context, dict):
        ctx = _revalidate_context(current_context)
    else:
        ctx = _revalidate_context(current_context.model_dump(mode="json"))
    if isinstance(verdict, dict):
        v = _revalidate_verdict(verdict)
    else:
        v = _revalidate_verdict(verdict.model_dump(mode="json"))
    if isinstance(review_bundle, dict):
        b = _revalidate_bundle(review_bundle)
    else:
        b = _revalidate_bundle(review_bundle.model_dump(mode="json"))

    # ── 从原始内容重验证门控输入 ─────────────────────────────────────────────
    if isinstance(gate_result, dict):
        gr = _revalidate_gate_result(ReportGateResult.model_validate(gate_result))
    else:
        gr = _revalidate_gate_result(gate_result)
    if isinstance(snapshot, dict):
        sn = _revalidate_snapshot(ApplicableUniverseSnapshot.model_validate(snapshot))
    else:
        sn = _revalidate_snapshot(snapshot)

    if gr.decision is not ReportDecision.PASSED:
        raise ScientificQcBoundaryError("科学质控必须绑定已通过的 GateSpec 结果")

    # ── 候选快照与门槛结果互相绑定（跨快照门槛拒绝） ────────────────────────
    if gr.evidence_snapshot_id != sn.evidence_snapshot_id:
        raise ScientificQcBoundaryError("GateSpec 结果必须绑定当前候选快照")
    if gr.universe_summary != sn.universe_summary:
        raise ScientificQcBoundaryError("GateSpec 结果宇宙摘要必须与当前候选快照一致")

    # ── 当前上下文与门控输入绑定 ─────────────────────────────────────────────
    from ci_workflow.gates.models import compute_candidate_snapshot_digest

    current_candidate_digest = _content_digest(sn)
    ctx_bindings: tuple[tuple[object, object, str], ...] = (
        (ctx.project_id, sn.project_id, "项目"),
        (ctx.report_kind, gr.report_kind, "报告类型"),
        (ctx.candidate_snapshot_id, sn.evidence_snapshot_id, "候选快照"),
        (ctx.candidate_content_digest, current_candidate_digest, "候选内容摘要"),
        (ctx.gate_result_key, gr.result_key, "门槛结果键"),
        (ctx.contract_version, gr.contract_version, "合同版本"),
    )
    for context_value, current_value, label in ctx_bindings:
        if context_value != current_value:
            raise ScientificQcBoundaryError(f"当前上下文{label}与门控输入不一致")

    # ── 标准/规则版本绑定：当前标准必须等于产生门槛结果的规则版本 ────────────
    if ctx.criteria_version != gr.spec_version:
        raise ScientificQcBoundaryError("质控标准版本必须等于门槛结果规则版本")
    # ── 候选快照内容摘要绑定：门槛结果必须由当前候选快照完整内容产生 ────────
    gate_candidate_digest = compute_candidate_snapshot_digest(sn)
    if gr.candidate_snapshot_digest != gate_candidate_digest:
        raise ScientificQcBoundaryError(
            "GateSpec 结果必须由当前候选快照完整内容产生（内容漂移）"
        )

    # ── 当前上下文/审查包/结论逐字一致 ──────────────────────────────────────
    # 生产者身份只存在于当前上下文与审查包（结论侧为审查者，另行绑定）；
    # 其余字段三处必须一致。
    agreement: tuple[tuple[object, object, object, str], ...] = (
        (ctx.project_id, b.project_id, v.project_id, "项目"),
        (ctx.report_kind, b.report_kind, v.report_kind, "报告类型"),
        (ctx.report_version, b.report_version, v.report_version, "报告版本"),
        (ctx.report_object_id, b.report_object_id, v.report_object_id, "报告对象"),
        (ctx.candidate_snapshot_id, b.candidate_snapshot_id,
         v.candidate_snapshot_id, "候选快照"),
        (ctx.candidate_content_digest, b.candidate_content_digest,
         v.candidate_content_digest, "候选内容摘要"),
        (ctx.criteria_version, b.criteria_version, v.criteria_version, "标准版本"),
        (ctx.gate_result_key, b.gate_result_key, v.gate_result_key, "门槛结果键"),
        (ctx.coverage_set_id, b.coverage_set_id, v.coverage_set_id, "覆盖集"),
        (ctx.coverage_digest, b.coverage_digest, v.coverage_digest, "覆盖摘要"),
        (ctx.source_refs, b.source_refs, v.source_refs, "来源引用"),
        (ctx.locators, b.locators, v.locators, "来源定位"),
    )
    for context_value, bundle_value, verdict_value, label in agreement:
        if context_value != bundle_value or context_value != verdict_value:
            raise ScientificQcBoundaryError(f"当前上下文/审查包/结论的{label}不一致")
    # 生产者身份：审查包必须等于当前上下文（不能自由自选）
    if b.producer_id != ctx.producer_id:
        raise ScientificQcBoundaryError("审查包生产者必须等于当前上下文生产者")

    # ── 审阅输入摘要绑定：重新核算审查包摘要 ─────────────────────────────────
    if v.review_input_digest != b.input_digest:
        raise ScientificQcBoundaryError("质控结论必须绑定审查输入摘要（漂移）")

    # ── 审查者身份：边界显式传入，必须与上下文生产者不同 ────────────────────
    if v.reviewer_id != reviewer_actor_id:
        raise ScientificQcBoundaryError("结论审查者必须等于边界声明的审查者身份")
    if ctx.producer_id == reviewer_actor_id:
        raise ScientificQcBoundaryError(
            "审查者必须与候选快照生产者是不同身份"
        )

    # ── 新鲜度 ────────────────────────────────────────────────────────────────
    if v.valid_until <= now:
        raise ScientificQcBoundaryError("质控结论已过期或失效")
    if v.reviewed_at > now:
        raise ScientificQcBoundaryError("质控结论审阅时间晚于当前")

    # ── 否决处置：显式区分可修复/已穷尽 ──────────────────────────────────────
    exhaustion_digest: str | None = None
    if v.verdict == "veto":
        assert v.veto_disposition in ("recoverable", "exhausted")
        if v.veto_disposition == "recoverable":
            if exhaustion is not None:
                raise ScientificQcBoundaryError(
                    "可修复否决不得携带双重穷尽记录"
                )
        else:
            if exhaustion is None:
                raise ScientificQcBoundaryError(
                    "已穷尽否决必须绑定双重穷尽记录"
                )
            ex = _revalidate_exhaustion(exhaustion)
            if ex.project_id != v.project_id:
                raise ScientificQcBoundaryError(
                    "双重穷尽记录必须绑定同一项目"
                )
            if ex.report_kind is not v.report_kind:
                raise ScientificQcBoundaryError(
                    "双重穷尽记录必须绑定同一报告类型"
                )
            # 守卫证据需要小写 SHA-256 记录摘要（由原始重验证后的内容派生）
            exhaustion_digest = _sha256_hex(
                ex.model_dump(mode="json", exclude={"record_digest"})
            )
        # 否决路径：零下游产物（迁移前后均断言）
        assert_no_report_downstream_artifacts(
            database_path,
            project_id=v.project_id,
            report_kind=v.report_kind,
            report_version=v.report_version,
            workspace_root=workspace_root,
        )

    # ── 构建守卫证据、签发授权并驱动图迁移 ──────────────────────────────────
    if executor is None:
        raise ScientificQcBoundaryError("图迁移需要执行器")
    if object_id is None:
        raise ScientificQcBoundaryError("图迁移需要报告对象标识")
    if object_id != v.report_object_id:
        raise ScientificQcBoundaryError("迁移报告对象必须等于被审阅报告对象")

    auth: dict[str, object] = {
        "qc_verdict_id": v.verdict_id,
        "qc_verdict_digest": v.verdict_digest,
        "qc_candidate_snapshot_id": v.candidate_snapshot_id,
        "qc_candidate_content_digest": v.candidate_content_digest,
        "qc_review_input_digest": v.review_input_digest,
        "qc_report_object_id": v.report_object_id,
        "qc_context_digest": ctx.context_digest,
    }
    if v.verdict == "accepted":
        evidence: dict[str, object] = {"isolated_qc_accepted": True, **auth}
        to_state = "snapshot_locked"
        trigger = "isolated_qc_accepted"
    elif v.veto_disposition == "recoverable":
        evidence = {"qc_veto": True, "qc_veto_fixable": True, **auth}
        to_state = "recovering"
        trigger = "qc_veto_fixable"
    else:
        if exhaustion_digest is None:
            raise ScientificQcBoundaryError("已穷尽否决缺少穷尽记录摘要")
        evidence = {
            "qc_veto": True,
            "qc_veto_unfixable": True,
            "recovery_exhausted": True,
            "independent_review_exhausted": True,
            "no_continuable_user_action": True,
            "qc_exhaustion_record_digest": exhaustion_digest,
            **auth,
        }
        to_state = "evidence_blocked"
        trigger = "qc_veto_unfixable_exhausted"

    # 守卫证据摘要 = 不包含 qc_authorization_id 的证据
    # （与执行器 _payload_digest 的规范 JSON + 换行算法一致）
    evidence_digest = hashlib.sha256(
        (
            json.dumps(
                evidence,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
    # 不透明授权证明：只在此边界内从完整重验证的模型构造；执行器私有
    # 发行方法只接受该证明并重新计算全部摘要/绑定。
    from ci_workflow.graph.executor import _ScientificQcAuthorizationProof

    proof = _ScientificQcAuthorizationProof(
        project_id=v.project_id,
        run_id=executor.run_id,
        report_object_id=object_id,
        from_state="scientific_qc",
        to_state=to_state,
        verdict=v,
        context=ctx,
        exhaustion_record_digest=exhaustion_digest,
        reviewer_actor_id=reviewer_actor_id,
        evidence_digest=evidence_digest,
        occurred_at=now,
    )
    issued_event = executor._issue_scientific_qc_authorization(proof)
    evidence["qc_authorization_id"] = issued_event.payload["authorization_id"]

    event = executor.submit(
        TransitionRequest(
            schema_version="1.0",
            request_id=f"sqc:{v.verdict_id}",
            project_id=v.project_id,
            run_id=executor.run_id,
            family="report_evidence",
            object_id=object_id,
            from_state="scientific_qc",
            to_state=to_state,
            trigger=trigger,
            evidence=evidence,
            actor_id=reviewer_actor_id,
            occurred_at=now,
        )
    )
    if event.event_type != "graph.transition.accepted":
        reason = event.payload.get("reason", "unknown")
        raise ScientificQcBoundaryError(f"图迁移未被接受: {reason}")

    # ── 否决路径：迁移后再次断言零下游产物 ───────────────────────────────────
    if v.verdict == "veto":
        assert_no_report_downstream_artifacts(
            database_path,
            project_id=v.project_id,
            report_kind=v.report_kind,
            report_version=v.report_version,
            workspace_root=workspace_root,
        )

    return to_state
