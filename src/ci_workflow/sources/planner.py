from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ci_workflow.domain.evidence import SourceVersionRecord
from ci_workflow.sources.receipts import EvidenceAuditBundle, RouteAttemptResult


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
    ) -> RouteProgress:
        if self.completion is not None:
            raise ValueError("路线完成状态不得重复写入")
        audit_bundle.assert_supports(
            route_id=self.route_id,
            completion_state=completion.state.value,
            completed_strategy_unit_ids=completion.completed_strategy_unit_ids,
        )
        return self.model_copy(update={"completion": completion})


class HistoricalCutoffState(StrEnum):
    SNAPSHOT_ELIGIBLE = "snapshot_eligible"
    REFRESH_CANDIDATE = "refresh_candidate"
    BLOCKED_UNKNOWN_DISCLOSURE = "blocked_unknown_disclosure"


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
