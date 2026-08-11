from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    from ci_workflow.sources.retries import (
        InformationGain,
        RecoveryHistory,
        RecoveryRound,
        RecoveryStrategyKind,
        RecoveryStrategyUnit,
    )

    first = RecoveryRound(
        round_index=1,
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="alias-round-1",
                kind=RecoveryStrategyKind.ALIAS_VARIANT,
                value="药物研发代号",
            ),
        ),
        information_gain=InformationGain(),
    )
    second = RecoveryRound(
        round_index=2,
        strategy_units=(
            RecoveryStrategyUnit(
                strategy_unit_id="identifier-round-2",
                kind=RecoveryStrategyKind.IDENTIFIER_CROSS_REFERENCE,
                value="NCT01234567→PMID",
            ),
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
    from ci_workflow.sources.retries import (
        InformationGain,
        RecoveryHistory,
        RecoveryRound,
        RecoveryStrategyKind,
        RecoveryStrategyUnit,
    )

    def saturated_round(
        round_index: int,
        strategy_unit_id: str,
        kind: RecoveryStrategyKind,
        value: str,
    ) -> RecoveryRound:
        return RecoveryRound(
            round_index=round_index,
            strategy_units=(
                RecoveryStrategyUnit(
                    strategy_unit_id=strategy_unit_id,
                    kind=kind,
                    value=value,
                ),
            ),
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
    from ci_workflow.sources.retries import (
        AlternativePathAudit,
        RecoveryPolicy,
        RecoveryStrategyKind,
        RecoveryStrategyUnit,
    )

    policy = RecoveryPolicy.from_yaml(
        ROOT / "policies" / "recovery" / "source-strategies-v1.yaml"
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
        strategy_units=repeated_query, policy=policy
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
    audit = AlternativePathAudit(strategy_units=distinct_alternatives, policy=policy)
    assert audit.distinct_completed_strategy_count == 2
    assert audit.minimum_distinct_alternatives_met is True
