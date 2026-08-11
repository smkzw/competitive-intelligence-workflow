from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ci_workflow.domain.evidence import SourceVersionRecord
from ci_workflow.sources.receipts import EvidenceAuditBundle, RouteAttemptResult
from ci_workflow.sources.retries import RecoveryExhaustionProof


class RouteCompletionState(StrEnum):
    COMPLETED = "route_completed"
    NOT_APPLICABLE = "route_not_applicable"
    ACCESS_BLOCKED = "route_access_blocked"


class RouteCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: RouteCompletionState
    rationale_zh: str = Field(min_length=1)
    completed_strategy_unit_ids: tuple[str, ...] = Field(min_length=1)


class RouteProgress(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    route_id: str = Field(min_length=1)
    attempts: tuple[RouteAttemptResult, ...] = ()
    completion: RouteCompletion | None = None

    @property
    def is_complete(self) -> bool:
        return self.completion is not None

    def record_attempt(self, attempt: RouteAttemptResult) -> RouteProgress:
        if self.completion is not None:
            raise ValueError("已完成路线不能追加尝试")
        if attempt.attempt_id in {item.attempt_id for item in self.attempts}:
            raise ValueError("路线尝试标识不得重复")
        return self.model_copy(update={"attempts": (*self.attempts, attempt)})

    def complete(
        self,
        completion: RouteCompletion,
        *,
        audit_bundle: EvidenceAuditBundle,
        recovery_exhaustion: RecoveryExhaustionProof | None = None,
    ) -> RouteProgress:
        if self.completion is not None:
            raise ValueError("路线完成状态不得重复写入")
        audit_bundle.assert_supports(
            route_id=self.route_id,
            completion_state=completion.state.value,
            completed_strategy_unit_ids=completion.completed_strategy_unit_ids,
        )
        receipts_by_id = {
            item.receipt_id: item for item in audit_bundle.source_receipts
        }
        attempts_by_id = {item.attempt_id: item for item in self.attempts}
        if set(receipts_by_id) != set(attempts_by_id):
            raise ValueError("路线尝试与来源审计回执必须逐条对应")
        for receipt_id, receipt in receipts_by_id.items():
            attempt = attempts_by_id[receipt_id]
            if (
                attempt.strategy_unit_id,
                attempt.entity_id,
                attempt.gap_id,
                attempt.claim_domain,
                attempt.result_class.value,
            ) != (
                receipt.strategy_unit_id,
                receipt.entity_id,
                receipt.gap_id,
                receipt.claim_domain,
                receipt.result_class,
            ):
                raise ValueError("路线尝试内容与来源审计回执不一致")
        if completion.state is RouteCompletionState.COMPLETED:
            final_receipts = tuple(
                max(
                    (
                        receipt
                        for receipt in audit_bundle.source_receipts
                        if receipt.strategy_unit_id == strategy_unit_id
                    ),
                    key=lambda receipt: receipt.attempt_index,
                )
                for strategy_unit_id in completion.completed_strategy_unit_ids
            )
            if any(item.result_class == "not_found" for item in final_receipts):
                if recovery_exhaustion is None:
                    raise ValueError("未找到适格内容前必须完成恢复与科学穷尽")
                first = final_receipts[0]
                expected_context = (
                    self.route_id,
                    first.entity_id,
                    first.gap_id,
                    first.claim_domain,
                )
                if recovery_exhaustion.execution_context != expected_context:
                    raise ValueError("路线终态与恢复穷尽证据不属于同一任务语境")
                if not recovery_exhaustion.completed_strategy_unit_ids <= set(
                    audit_bundle.evidence_gap.completed_strategies
                ):
                    raise ValueError("恢复穷尽策略未完整写入证据缺口审计")
        elif recovery_exhaustion is not None:
            raise ValueError("非科学性未找到终态不得附加恢复穷尽证据")
        return self.model_copy(update={"completion": completion})


class HistoricalCutoffState(StrEnum):
    SNAPSHOT_ELIGIBLE = "snapshot_eligible"
    REFRESH_CANDIDATE = "refresh_candidate"
    BLOCKED_UNKNOWN_DISCLOSURE = "blocked_unknown_disclosure"
    BLOCKED_AMBIGUOUS_DISCLOSURE_DAY = "blocked_ambiguous_disclosure_day"


class HistoricalCutoffAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_version_id: str
    state: HistoricalCutoffState
    can_enter_snapshot: bool
    refresh_candidate: bool
    recovery_required: bool
    rationale_zh: str


def assess_historical_source(
    source: SourceVersionRecord, *, cutoff: datetime, key_evidence: bool
) -> HistoricalCutoffAssessment:
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("历史截止日必须包含明确时区")
    disclosed = source.first_disclosed_at
    if (
        disclosed.state == "reported"
        and disclosed.value is not None
        and disclosed.precision == "calendar_day"
    ):
        day_start = disclosed.value
        next_day = day_start + timedelta(days=1)
        if cutoff < day_start:
            return HistoricalCutoffAssessment(
                source_version_id=source.source_version_id,
                state=HistoricalCutoffState.REFRESH_CANDIDATE,
                can_enter_snapshot=False,
                refresh_candidate=True,
                recovery_required=False,
                rationale_zh="首次披露自然日晚于历史截止时点，仅进入后续刷新候选",
            )
        if cutoff < next_day - timedelta(microseconds=1):
            return HistoricalCutoffAssessment(
                source_version_id=source.source_version_id,
                state=HistoricalCutoffState.BLOCKED_AMBIGUOUS_DISCLOSURE_DAY,
                can_enter_snapshot=False,
                refresh_candidate=False,
                recovery_required=key_evidence,
                rationale_zh="来源只公开首次披露自然日，当前截止时点位于该日内，无法证明先后顺序",
            )
    if (
        disclosed.state == "reported"
        and disclosed.value is not None
        and disclosed.value <= cutoff
    ):
        return HistoricalCutoffAssessment(
            source_version_id=source.source_version_id,
            state=HistoricalCutoffState.SNAPSHOT_ELIGIBLE,
            can_enter_snapshot=True,
            refresh_candidate=False,
            recovery_required=False,
            rationale_zh="首次披露时间不晚于历史截止日，可进入当前快照",
        )
    if (
        disclosed.state == "reported"
        and disclosed.value is not None
        and disclosed.value > cutoff
    ):
        return HistoricalCutoffAssessment(
            source_version_id=source.source_version_id,
            state=HistoricalCutoffState.REFRESH_CANDIDATE,
            can_enter_snapshot=False,
            refresh_candidate=True,
            recovery_required=False,
            rationale_zh="首次披露时间晚于历史截止日，仅进入后续刷新候选",
        )
    return HistoricalCutoffAssessment(
        source_version_id=source.source_version_id,
        state=HistoricalCutoffState.BLOCKED_UNKNOWN_DISCLOSURE,
        can_enter_snapshot=False,
        refresh_candidate=False,
        recovery_required=key_evidence,
        rationale_zh=(
            "关键证据的首次披露时间尚未解决，不能进入当前历史快照"
            if key_evidence
            else "首次披露时间尚未解决，当前历史快照不采用该来源"
        ),
    )
