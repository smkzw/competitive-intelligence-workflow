from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_route_completion_is_separate_from_attempt_result() -> None:
    from ci_workflow.sources.planner import (
        RouteCompletion,
        RouteCompletionState,
        RouteProgress,
    )
    from ci_workflow.sources.receipts import AttemptResultClass, RouteAttemptResult

    route = RouteProgress(route_id="clinicaltrials-global-baseline")
    not_found = RouteAttemptResult(
        attempt_id="attempt-001",
        strategy_unit_id="registry-nct-id",
        entity_id="trial-001",
        gap_id="gap-design",
        claim_domain="trial_identity_design_status",
        result_class=AttemptResultClass.NOT_FOUND,
        detail_zh="按 NCT 号进行精确查询后未找到记录",
    )
    after_attempt = route.record_attempt(not_found)
    assert after_attempt.completion is None
    assert after_attempt.is_complete is False

    explicit_completion = RouteCompletion(
        state=RouteCompletionState.COMPLETED,
        rationale_zh="已完成本路线全部适用策略单元并保存回执",
        completed_strategy_unit_ids=("registry-nct-id",),
    )
    assert explicit_completion.state is RouteCompletionState.COMPLETED
    assert set(item.value for item in RouteCompletionState).isdisjoint(
        item.value for item in AttemptResultClass
    )


def test_recovery_round_changes_strategy_and_records_information_gain() -> None:
    from ci_workflow.domain.evidence import (
        DateEvidence,
        EvidenceLocator,
        SourceReceipt,
        SourceVersionRecord,
    )
    from ci_workflow.sources.retries import (
        InformationGain,
        RecoveryHistory,
        RecoveryRound,
        RecoveryStrategyKind,
        RecoveryStrategyUnit,
    )

    now = datetime(2026, 8, 11, 10, 0, tzinfo=timezone(timedelta(hours=8)))

    source_version = SourceVersionRecord(
        schema_version="1.0",
        source_version_id="source-version-new-result",
        source_id="clinicaltrials_gov",
        content_sha256="a" * 64,
        content_relative_path=f"evidence/raw/sha256/aa/{'a' * 64}.bin",
        media_type="application/json",
        acquired_at=now,
        acquired_locator=EvidenceLocator(
            document_role="ClinicalTrials.gov 官方接口",
            url="https://clinicaltrials.gov/study/NCT01234567",
        ),
        published_at=DateEvidence(
            state="not_publicly_disclosed",
            value=None,
            locator=EvidenceLocator(
                document_role="ClinicalTrials.gov 官方接口",
                field_path="resultsSection",
            ),
        ),
        effective_at=DateEvidence(
            state="not_applicable",
            value=None,
            locator=EvidenceLocator(
                document_role="ClinicalTrials.gov 官方接口",
                paragraph="登记结果不适用监管生效日期",
            ),
        ),
        first_disclosed_at=DateEvidence(
            state="not_publicly_disclosed",
            value=None,
            locator=EvidenceLocator(
                document_role="ClinicalTrials.gov 官方接口",
                field_path="resultsSection",
            ),
        ),
        created_at=now,
    )

    def receipt(
        strategy_unit_id: str,
        round_index: int,
        *,
        acquired: bool,
    ) -> SourceReceipt:
        return SourceReceipt.model_validate(
            {
                "schema_version": "1.0",
                "receipt_id": f"receipt-{strategy_unit_id}",
                "route_id": "clinicaltrials-global-baseline",
                "strategy_unit_id": strategy_unit_id,
                "entity_id": "trial-001",
                "gap_id": "gap-primary-efficacy",
                "claim_domain": "efficacy_safety_results",
                "query_or_identifier": strategy_unit_id,
                "language": "zh",
                "access_method": "公开来源检索",
                "attempt_index": 1,
                "started_at": now + timedelta(minutes=round_index),
                "ended_at": now + timedelta(minutes=round_index, seconds=1),
                "scheduled_backoff_ms": 0,
                "actual_backoff_ms": 0,
                "result_class": "content_acquired" if acquired else "not_found",
                "error_class": None if acquired else "未找到适格内容",
                "completeness_checks": ("已核对返回内容",),
                "alternative_paths": ("下一条恢复策略",),
                "source_version_id": (
                    "source-version-new-result" if acquired else None
                ),
                "content_sha256": "a" * 64 if acquired else None,
                "diagnostic_confidence": "high",
                "parent_attempt_id": "recovery-root",
                "recovery_round": round_index,
            }
        )

    first = RecoveryRound(
        round_index=1,
        gap_id="gap-primary-efficacy",
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="alias-round-1",
                kind=RecoveryStrategyKind.ALIAS_VARIANT,
                value="药物研发代号",
            ),
        ),
        source_receipts=(receipt("alias-round-1", 1, acquired=False),),
        information_gain=InformationGain(),
    )
    second = RecoveryRound(
        round_index=2,
        gap_id="gap-primary-efficacy",
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="identifier-round-2",
                kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
                value="NCT01234567→PMID",
            ),
        ),
        source_receipts=(receipt("identifier-round-2", 2, acquired=True),),
        source_versions=(
            source_version,
        ),
        information_gain=InformationGain(
            new_evidence_fragment_ids=("fragment-new-result",),
            changed_gate_unit_ids=("B-primary-efficacy",),
        ),
    )
    history = RecoveryHistory(gap_id="gap-primary-efficacy")
    history = history.add_round(first)
    history = history.add_round(second)

    assert history.rounds[0].strategy_signature != history.rounds[1].strategy_signature
    assert history.rounds[1].information_gain.has_gate_relevant_gain is True
    assert history.rounds[1].information_gain.new_evidence_fragment_ids == (
        "fragment-new-result",
    )


def test_two_distinct_saturated_rounds_are_required_before_exhaustion() -> None:
    from ci_workflow.domain.evidence import SourceReceipt
    from ci_workflow.sources.retries import (
        InformationGain,
        RecoveryHistory,
        RecoveryRound,
        RecoveryStrategyKind,
        RecoveryStrategyUnit,
    )

    start = datetime(2026, 8, 11, 10, 0, tzinfo=timezone(timedelta(hours=8)))

    def executed_receipt(strategy_unit_id: str, round_index: int) -> SourceReceipt:
        return SourceReceipt.model_validate(
            {
                "schema_version": "1.0",
                "receipt_id": f"receipt-{strategy_unit_id}",
                "route_id": "clinicaltrials-global-baseline",
                "strategy_unit_id": strategy_unit_id,
                "entity_id": "trial-001",
                "gap_id": "gap-saturation",
                "claim_domain": "efficacy_safety_results",
                "query_or_identifier": strategy_unit_id,
                "language": "zh",
                "access_method": "公开来源检索",
                "attempt_index": 1,
                "started_at": start + timedelta(minutes=round_index),
                "ended_at": start + timedelta(minutes=round_index, seconds=1),
                "scheduled_backoff_ms": 0,
                "actual_backoff_ms": 0,
                "result_class": "not_found",
                "error_class": "公开来源未找到适格内容",
                "completeness_checks": ("已核对检索结果",),
                "alternative_paths": ("下一条恢复策略",),
                "source_version_id": None,
                "content_sha256": None,
                "diagnostic_confidence": "high",
                "parent_attempt_id": "recovery-root",
                "recovery_round": round_index,
            }
        )

    def saturated_round(
        round_index: int,
        strategy_unit_id: str,
        kind: RecoveryStrategyKind,
        value: str,
    ) -> RecoveryRound:
        return RecoveryRound(
            round_index=round_index,
            gap_id="gap-saturation",
            strategy_units=(
                RecoveryStrategyUnit(
                    strategy_unit_id=strategy_unit_id,
                    kind=kind,
                    value=value,
                ),
            ),
            source_receipts=(executed_receipt(strategy_unit_id, round_index),),
            information_gain=InformationGain(),
        )

    history = RecoveryHistory(gap_id="gap-saturation")
    assert history.can_declare_information_saturated is False
    history = history.add_round(
        saturated_round(1, "alias-search", RecoveryStrategyKind.ALIAS_VARIANT, "研发代号")
    )
    assert history.can_declare_information_saturated is False
    history = history.add_round(
        saturated_round(
            2,
            "citation-search",
            RecoveryStrategyKind.CITATION_TRAVERSAL,
            "前后向引用",
        )
    )
    assert history.can_declare_information_saturated is True


def test_strategy_labels_cannot_hide_repeated_query_and_access_path() -> None:
    """改策略名称但复用同一查询/标识符和访问方式，不构成第二条恢复策略。"""
    from ci_workflow.sources.retries import RecoveryHistory
    from tests.integration.test_no_draft_when_blocked import gap_exhaustion

    proof = gap_exhaustion(
        gap_id="gap-repeated-retrieval-path"
    ).recovery_exhaustion_proofs[0]
    payload = proof.recovery_history.model_dump(mode="json")
    first_receipt = payload["rounds"][0]["source_receipts"][0]
    for receipt in payload["rounds"][1]["source_receipts"]:
        receipt["query_or_identifier"] = first_receipt["query_or_identifier"]
        receipt["access_method"] = first_receipt["access_method"]
    with pytest.raises(ValueError):
        RecoveryHistory.model_validate(payload)


def test_recovery_history_direct_validation_enforces_sequence_and_identity() -> None:
    """调用方不得绕过 add_round 直接构造跳轮、错缺口或重复策略的历史。"""
    from ci_workflow.sources.retries import RecoveryHistory
    from tests.integration.test_no_draft_when_blocked import gap_exhaustion

    proof = gap_exhaustion(
        gap_id="gap-history-direct-validation"
    ).recovery_exhaustion_proofs[0]
    base = proof.recovery_history.model_dump(mode="json")
    for mutate in ("skip_round", "wrong_gap", "duplicate_strategy"):
        payload = {
            **base,
            "rounds": [dict(item) for item in base["rounds"]],
        }
        if mutate == "skip_round":
            payload["rounds"][1]["round_index"] = 3
        elif mutate == "wrong_gap":
            payload["rounds"][1]["gap_id"] = "gap-other"
            for receipt in payload["rounds"][1]["source_receipts"]:
                receipt["gap_id"] = "gap-other"
        else:
            payload["rounds"][1]["strategy_units"] = payload["rounds"][0][
                "strategy_units"
            ]
            for receipt in payload["rounds"][1]["source_receipts"]:
                receipt["strategy_unit_id"] = payload["rounds"][0][
                    "strategy_units"
                ][0]["strategy_unit_id"]
        with pytest.raises(ValueError):
            RecoveryHistory.model_validate(payload)


def test_retryable_failure_requires_three_timed_same_path_attempts_with_backoff_before_route_exhaustion() -> None:  # noqa: E501
    from ci_workflow.domain.evidence import SourceReceipt
    from ci_workflow.sources.retries import RecoveryPolicy, SamePathRetryAudit

    policy = RecoveryPolicy.from_yaml(
        ROOT / "policies" / "recovery" / "source-strategies-v1.yaml"
    )

    start = datetime(2026, 8, 11, 10, 0, tzinfo=timezone(timedelta(hours=8)))

    def receipt(index: int, scheduled: int, actual: int) -> SourceReceipt:
        started_at = start + timedelta(seconds=index * 5)
        return SourceReceipt.model_validate(
            {
                "schema_version": "1.0",
                "receipt_id": f"receipt-{index}",
                "route_id": "clinicaltrials-global-baseline",
                "strategy_unit_id": "registry-nct-id",
                "entity_id": "trial-001",
                "gap_id": "gap-design",
                "claim_domain": "trial_identity_design_status",
                "query_or_identifier": "NCT01234567",
                "language": "en",
                "access_method": "registry-api-v2",
                "attempt_index": index,
                "started_at": started_at,
                "ended_at": started_at + timedelta(seconds=1),
                "scheduled_backoff_ms": scheduled,
                "actual_backoff_ms": actual,
                "result_class": "network_error",
                "error_class": "network_timeout",
                "completeness_checks": ("响应未形成可解析正文",),
                "alternative_paths": ("登记网页", "NCT 号论文交叉引用"),
                "source_version_id": None,
                "content_sha256": None,
                "diagnostic_confidence": "high",
                "parent_attempt_id": "route-attempt-root",
                "recovery_round": 1,
            }
        )

    attempts = (
        receipt(1, 0, 0),
        receipt(2, 1000, 1040),
        receipt(3, 2000, 2030),
    )
    assert policy.minimum_same_path_attempts == 3
    assert SamePathRetryAudit(
        receipts=attempts[:2], policy=policy
    ).minimum_retry_count_met is False
    audit = SamePathRetryAudit(receipts=attempts, policy=policy)
    assert audit.minimum_retry_count_met is True
    assert audit.can_leave_same_path_after_retryable_failure is True
    assert tuple(item.attempt_index for item in audit.receipts) == (1, 2, 3)


def test_persistent_failure_requires_two_distinct_applicable_alternative_strategy_units() -> None:  # noqa: E501
    from ci_workflow.domain.evidence import SourceReceipt
    from ci_workflow.sources.retries import (
        AlternativePathAudit,
        RecoveryPolicy,
        RecoveryStrategyKind,
        RecoveryStrategyUnit,
    )

    policy = RecoveryPolicy.from_yaml(
        ROOT / "policies" / "recovery" / "source-strategies-v1.yaml"
    )

    start = datetime(2026, 8, 11, 10, 0, tzinfo=timezone(timedelta(hours=8)))

    def executed_receipt(strategy_unit_id: str, index: int) -> SourceReceipt:
        return SourceReceipt.model_validate(
            {
                "schema_version": "1.0",
                "receipt_id": f"receipt-{strategy_unit_id}",
                "route_id": "clinicaltrials-global-baseline",
                "strategy_unit_id": strategy_unit_id,
                "entity_id": "trial-001",
                "gap_id": "gap-design",
                "claim_domain": "trial_identity_design_status",
                "query_or_identifier": strategy_unit_id,
                "language": "en",
                "access_method": "公开来源检索",
                "attempt_index": 1,
                "started_at": start + timedelta(minutes=index),
                "ended_at": start + timedelta(minutes=index, seconds=1),
                "scheduled_backoff_ms": 0,
                "actual_backoff_ms": 0,
                "result_class": "not_found",
                "error_class": "适格内容未找到",
                "completeness_checks": ("已核对返回内容",),
                "alternative_paths": ("其它恢复策略",),
                "source_version_id": None,
                "content_sha256": None,
                "diagnostic_confidence": "high",
                "parent_attempt_id": "recovery-root",
                "recovery_round": 1,
            }
        )

    repeated_query = (
        RecoveryStrategyUnit(
            strategy_unit_id="repeat-1",
            kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
            value="NCT01234567",
        ),
        RecoveryStrategyUnit(
            strategy_unit_id="repeat-2",
            kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
            value="nct01234567",
        ),
    )
    assert AlternativePathAudit(
        strategy_units=repeated_query,
        source_receipts=tuple(
            executed_receipt(item.strategy_unit_id, index)
            for index, item in enumerate(repeated_query, start=1)
        ),
        policy=policy,
    ).minimum_distinct_alternatives_met is False

    distinct_alternatives = (
        RecoveryStrategyUnit(
            strategy_unit_id="publication-cross-reference",
            kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
            value="NCT01234567→PMID",
        ),
        RecoveryStrategyUnit(
            strategy_unit_id="registry-html-fallback",
            kind=RecoveryStrategyKind.ALTERNATE_ACCESS,
            value="登记网页替代接口访问",
        ),
    )
    audit = AlternativePathAudit(
        strategy_units=distinct_alternatives,
        source_receipts=tuple(
            executed_receipt(item.strategy_unit_id, index)
            for index, item in enumerate(distinct_alternatives, start=1)
        ),
        policy=policy,
    )
    assert audit.distinct_completed_strategy_count == 2
    assert audit.minimum_distinct_alternatives_met is True
    mismatched_receipts = (
        audit.source_receipts[0],
        audit.source_receipts[1].model_copy(update={"entity_id": "trial-other"}),
    )
    with pytest.raises(ValueError, match="同一路线、实体、缺口和声明域"):
        AlternativePathAudit(
            strategy_units=distinct_alternatives,
            source_receipts=mismatched_receipts,
            policy=policy,
        )


def test_route_completion_and_recovery_cannot_be_fabricated_without_execution_receipts() -> None:
    from pydantic import ValidationError

    from ci_workflow.domain.evidence import EvidenceGap, SourceReceipt
    from ci_workflow.sources.planner import (
        RouteCompletion,
        RouteCompletionState,
        RouteProgress,
    )
    from ci_workflow.sources.policy import SourceEligibility
    from ci_workflow.sources.receipts import EvidenceAuditBundle
    from ci_workflow.sources.retries import (
        AlternativePathAudit,
        InformationGain,
        RecoveryHistory,
        RecoveryPolicy,
        RecoveryRound,
        RecoveryStrategyKind,
        RecoveryStrategyUnit,
    )

    policy = RecoveryPolicy.from_yaml(
        ROOT / "policies" / "recovery" / "source-strategies-v1.yaml"
    )
    now = datetime(2026, 8, 11, 10, 0, tzinfo=timezone(timedelta(hours=8)))
    eligibility = SourceEligibility.model_validate(
        {
            "schema_version": "1.0",
            "source_eligibility_id": "eligibility-001",
            "route_id": "clinicaltrials-global-baseline",
            "strategy_unit_id": "registry-nct-id",
            "entity_id": "trial-001",
            "gap_id": "gap-design",
            "claim_domain": "trial_identity_design_status",
            "applicability": "applicable",
            "required_by_policy": True,
            "rationale_zh": "全球登记基线路线",
            "policy_id": "source-policy-v1",
            "policy_version": "1.0",
            "evidence_fragment_ids": ("fragment-applicability",),
            "decided_by": "source-planner-v1",
            "decided_at": now,
        }
    )
    gap = EvidenceGap.model_validate(
        {
            "schema_version": "1.0",
            "gap_id": "gap-design",
            "gate_spec_id": "B-design",
            "object_type": "trial",
            "object_id": "trial-001",
            "field_id": "trial.design",
            "current_state": "unresolved_due_to_route",
            "required_context": "试验设计",
            "candidate_sources": ("ClinicalTrials.gov",),
            "completed_strategies": ("registry-nct-id",),
            "information_gain_diff": (
                {"round": 1, "new_fields": (), "new_source_versions": ()},
            ),
            "next_legal_action": "恢复访问",
        }
    )
    failed_receipt = SourceReceipt.model_validate(
        {
            "schema_version": "1.0",
            "receipt_id": "receipt-network-error",
            "route_id": "clinicaltrials-global-baseline",
            "strategy_unit_id": "registry-nct-id",
            "entity_id": "trial-001",
            "gap_id": "gap-design",
            "claim_domain": "trial_identity_design_status",
            "query_or_identifier": "NCT01234567",
            "language": "en",
            "access_method": "registry-api-v2",
            "attempt_index": 1,
            "started_at": now,
            "ended_at": now + timedelta(seconds=1),
            "scheduled_backoff_ms": 0,
            "actual_backoff_ms": 0,
            "result_class": "network_error",
            "error_class": "network_timeout",
            "completeness_checks": ("未取得正文",),
            "alternative_paths": ("登记网页",),
            "source_version_id": None,
            "content_sha256": None,
            "diagnostic_confidence": "high",
            "parent_attempt_id": "route-root",
            "recovery_round": 1,
        }
    )
    bundle = EvidenceAuditBundle(
        source_receipts=(failed_receipt,),
        source_eligibilities=(eligibility,),
        evidence_gap=gap,
    )
    with pytest.raises(ValueError, match="技术失败不能标记为路线已完成"):
        RouteProgress(route_id="clinicaltrials-global-baseline").complete(
            RouteCompletion(
                state=RouteCompletionState.COMPLETED,
                rationale_zh="错误地宣称完成",
                completed_strategy_unit_ids=("registry-nct-id",),
            ),
            audit_bundle=bundle,
        )

    units = (
        RecoveryStrategyUnit(
            strategy_unit_id="publication",
            kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
            value="NCT→PMID",
        ),
        RecoveryStrategyUnit(
            strategy_unit_id="registry-html",
            kind=RecoveryStrategyKind.ALTERNATE_ACCESS,
            value="登记网页",
        ),
    )
    with pytest.raises(ValidationError, match="source_receipts"):
        AlternativePathAudit(strategy_units=units, policy=policy)

    with pytest.raises(ValidationError, match="source_receipts"):
        RecoveryRound(
            round_index=1,
            gap_id="gap-design",
            strategy_units=(units[0],),
            information_gain=InformationGain(),
        )

    history = RecoveryHistory(gap_id="gap-design")
    assert history.can_declare_information_saturated is False


def test_not_found_route_requires_two_executed_alternatives_and_scientific_saturation() -> None:  # noqa: E501
    from ci_workflow.domain.evidence import EvidenceGap, SourceReceipt
    from ci_workflow.sources.planner import (
        RouteCompletion,
        RouteCompletionState,
        RouteProgress,
    )
    from ci_workflow.sources.policy import SourceEligibility
    from ci_workflow.sources.receipts import (
        AttemptResultClass,
        EvidenceAuditBundle,
        RouteAttemptResult,
    )
    from ci_workflow.sources.retries import (
        AlternativePathAudit,
        InformationGain,
        RecoveryExhaustionProof,
        RecoveryHistory,
        RecoveryPolicy,
        RecoveryRound,
        RecoveryStrategyKind,
        RecoveryStrategyUnit,
    )

    policy = RecoveryPolicy.from_yaml(
        ROOT / "policies" / "recovery" / "source-strategies-v1.yaml"
    )
    now = datetime(2026, 8, 12, 9, 0, tzinfo=timezone(timedelta(hours=8)))

    def receipt(
        strategy_id: str,
        round_index: int,
        result_class: str = "not_found",
    ) -> SourceReceipt:
        return SourceReceipt.model_validate(
            {
                "schema_version": "1.0",
                "receipt_id": f"receipt-{strategy_id}-{round_index}",
                "route_id": "clinicaltrials-global-baseline",
                "strategy_unit_id": strategy_id,
                "entity_id": "trial-001",
                "gap_id": "gap-no-result",
                "claim_domain": "efficacy_safety_results",
                "query_or_identifier": strategy_id,
                "language": "zh",
                "access_method": "公开来源检索",
                "attempt_index": 1,
                "started_at": now + timedelta(minutes=round_index),
                "ended_at": now + timedelta(minutes=round_index, seconds=1),
                "scheduled_backoff_ms": 0,
                "actual_backoff_ms": 0,
                "result_class": result_class,
                "error_class": (
                    "未找到适格内容"
                    if result_class == "not_found"
                    else "网络连接失败"
                ),
                "completeness_checks": ("已核对返回内容",),
                "alternative_paths": ("继续使用其它适用路径",),
                "source_version_id": None,
                "content_sha256": None,
                "diagnostic_confidence": "high",
                "parent_attempt_id": "recovery-root",
                "recovery_round": round_index,
            }
        )

    units = (
        RecoveryStrategyUnit(
            strategy_unit_id="publication-cross-reference",
            kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
            value="NCT 号交叉检索 PMID",
        ),
        RecoveryStrategyUnit(
            strategy_unit_id="registry-html-fallback",
            kind=RecoveryStrategyKind.ALTERNATE_ACCESS,
            value="登记网页替代接口访问",
        ),
    )
    alternative_receipts = (
        receipt(units[0].strategy_unit_id, 1),
        receipt(units[1].strategy_unit_id, 2),
    )
    history = RecoveryHistory(gap_id="gap-no-result")
    for index, unit in enumerate(units, start=1):
        history = history.add_round(
            RecoveryRound(
                round_index=index,
                gap_id="gap-no-result",
                strategy_units=(unit,),
                source_receipts=(alternative_receipts[index - 1],),
                information_gain=InformationGain(),
            )
        )
    exhaustion = RecoveryExhaustionProof(
        alternative_paths=AlternativePathAudit(
            strategy_units=units,
            source_receipts=alternative_receipts,
            policy=policy,
        ),
        recovery_history=history,
    )

    root_receipt = receipt("registry-nct-id", 0)
    eligibility = SourceEligibility.model_validate(
        {
            "schema_version": "1.0",
            "source_eligibility_id": "eligibility-registry-nct-id",
            "route_id": root_receipt.route_id,
            "strategy_unit_id": root_receipt.strategy_unit_id,
            "entity_id": root_receipt.entity_id,
            "gap_id": root_receipt.gap_id,
            "claim_domain": root_receipt.claim_domain,
            "applicability": "applicable",
            "required_by_policy": True,
            "rationale_zh": "试验具有 NCT 标识，必须核对登记平台",
            "policy_id": "source-policy-v1",
            "policy_version": "1.0",
            "evidence_fragment_ids": ("fragment-route-applicability",),
            "decided_by": "source-planner-v1",
            "decided_at": now,
        }
    )
    gap = EvidenceGap.model_validate(
        {
            "schema_version": "1.0",
            "gap_id": root_receipt.gap_id,
            "gate_spec_id": "B-primary-result",
            "object_type": "trial",
            "object_id": root_receipt.entity_id,
            "field_id": "efficacy.primary_endpoint",
            "current_state": "not_publicly_disclosed",
            "required_context": "主要疗效结果",
            "candidate_sources": ("ClinicalTrials.gov", "PubMed"),
            "completed_strategies": (
                root_receipt.strategy_unit_id,
                *(item.strategy_unit_id for item in units),
            ),
            "information_gain_diff": (
                {"round": 1, "new_fields": (), "new_source_versions": ()},
                {"round": 2, "new_fields": (), "new_source_versions": ()},
            ),
            "next_legal_action": "向用户说明未公开并保留刷新入口",
        }
    )
    bundle = EvidenceAuditBundle(
        source_receipts=(root_receipt,),
        source_eligibilities=(eligibility,),
        evidence_gap=gap,
    )
    progress = RouteProgress(
        route_id=root_receipt.route_id,
        attempts=(
            RouteAttemptResult(
                attempt_id=root_receipt.receipt_id,
                strategy_unit_id=root_receipt.strategy_unit_id,
                entity_id=root_receipt.entity_id,
                gap_id=root_receipt.gap_id,
                claim_domain=root_receipt.claim_domain,
                result_class=AttemptResultClass.NOT_FOUND,
                detail_zh="登记平台未找到适格结果",
            ),
        ),
    )
    completion = RouteCompletion(
        state=RouteCompletionState.COMPLETED,
        rationale_zh="全部适用路径完成后仍未发现适格结果",
        completed_strategy_unit_ids=(root_receipt.strategy_unit_id,),
    )
    with pytest.raises(ValueError, match="必须完成恢复与科学穷尽"):
        progress.complete(completion, audit_bundle=bundle)
    assert progress.complete(
        completion,
        audit_bundle=bundle,
        recovery_exhaustion=exhaustion,
    ).is_complete

    technical_history = RecoveryHistory(gap_id="gap-no-result")
    for index, unit in enumerate(units, start=1):
        technical_history = technical_history.add_round(
            RecoveryRound(
                round_index=index,
                gap_id="gap-no-result",
                strategy_units=(unit,),
                source_receipts=(
                    receipt(unit.strategy_unit_id, index, "network_error"),
                ),
                information_gain=InformationGain(),
            )
        )
    assert technical_history.can_declare_information_saturated is False

    incomplete_unit = RecoveryStrategyUnit(
        strategy_unit_id="incomplete-technical-path",
        kind=RecoveryStrategyKind.ALTERNATE_ACCESS,
        value="尚未完成的替代访问",
        completed=False,
    )
    with pytest.raises(ValueError, match="已完成策略与实际来源回执必须完全一致"):
        RecoveryRound(
            round_index=1,
            gap_id="gap-no-result",
            strategy_units=(incomplete_unit,),
            source_receipts=(
                receipt(incomplete_unit.strategy_unit_id, 1, "network_error"),
            ),
            information_gain=InformationGain(),
        )
    with pytest.raises(ValueError, match="已完成策略与实际来源回执必须完全一致"):
        RecoveryRound(
            round_index=1,
            gap_id="gap-no-result",
            strategy_units=(units[0],),
            source_receipts=(
                alternative_receipts[0],
                receipt("orphan-technical-receipt", 1, "network_error"),
            ),
            information_gain=InformationGain(),
        )
