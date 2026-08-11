from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ci_workflow.domain.evidence import SourceReceipt
from ci_workflow.sources.receipts import AttemptResultClass


class RecoveryStrategyKind(StrEnum):
    ALIAS_VARIANT = "alias_variant"
    LANGUAGE_VARIANT = "language_variant"
    IDENTIFIER_CROSS_REFERENCE = "identifier_cross_reference"
    CITATION_TRAVERSAL = "citation_traversal"
    ALTERNATE_ACCESS = "alternate_access"
    ALTERNATE_SOURCE = "alternate_source"


class RecoveryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    policy_id: Literal["source-strategies-v1"]
    version: Literal["1.0"]
    minimum_same_path_attempts: Literal[3]
    minimum_alternative_strategy_units: Literal[2]
    saturation_rounds: Literal[2]
    retryable_result_classes: tuple[AttemptResultClass, ...] = Field(min_length=1)
    alternative_strategy_kinds: tuple[RecoveryStrategyKind, ...] = Field(min_length=2)
    diagnostic_branches: tuple[AttemptResultClass, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _policy_lists_are_unique_and_complete(self) -> RecoveryPolicy:
        for values in (
            self.retryable_result_classes,
            self.alternative_strategy_kinds,
            self.diagnostic_branches,
        ):
            if len(set(values)) != len(values):
                raise ValueError("恢复策略列表不得重复")
        technical_results = set(AttemptResultClass) - {
            AttemptResultClass.CONTENT_ACQUIRED,
            AttemptResultClass.NOT_FOUND,
        }
        if set(self.diagnostic_branches) != technical_results:
            raise ValueError("技术诊断分支必须覆盖全部精确失败类型")
        return self

    @classmethod
    def from_yaml(cls, path: Path) -> RecoveryPolicy:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise ValueError("无法读取来源恢复策略") from error
        if not isinstance(payload, dict):
            raise ValueError("来源恢复策略顶层必须是对象")
        return cls.model_validate(cast(dict[str, object], payload))


class RecoveryStrategyUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_unit_id: str = Field(min_length=1)
    kind: RecoveryStrategyKind
    value: str = Field(min_length=1)
    applicable: bool = True
    completed: bool = True


class InformationGain(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    new_evidence_fragment_ids: tuple[str, ...] = ()
    changed_gate_unit_ids: tuple[str, ...] = ()
    reduced_conflict_set_ids: tuple[str, ...] = ()

    @property
    def has_gate_relevant_gain(self) -> bool:
        return any(
            (
                self.new_evidence_fragment_ids,
                self.changed_gate_unit_ids,
                self.reduced_conflict_set_ids,
            )
        )


class RecoveryRound(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    round_index: int = Field(ge=1)
    strategy_units: tuple[RecoveryStrategyUnit, ...] = Field(min_length=1)
    information_gain: InformationGain

    @model_validator(mode="after")
    def _strategy_unit_ids_are_unique(self) -> RecoveryRound:
        unit_ids = tuple(item.strategy_unit_id for item in self.strategy_units)
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("同一恢复轮次的策略单元不得重复")
        return self

    @property
    def strategy_signature(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted((item.kind.value, item.value.casefold()) for item in self.strategy_units)
        )

    @property
    def is_saturated(self) -> bool:
        return not self.information_gain.has_gate_relevant_gain


class RecoveryHistory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gap_id: str = Field(min_length=1)
    rounds: tuple[RecoveryRound, ...] = ()

    @property
    def can_declare_information_saturated(self) -> bool:
        if len(self.rounds) < 2:
            return False
        previous, current = self.rounds[-2:]
        return (
            previous.is_saturated
            and current.is_saturated
            and previous.strategy_signature != current.strategy_signature
        )

    def add_round(self, recovery_round: RecoveryRound) -> RecoveryHistory:
        expected_index = len(self.rounds) + 1
        if recovery_round.round_index != expected_index:
            raise ValueError("恢复轮次必须连续递增")
        if recovery_round.strategy_signature in {
            item.strategy_signature for item in self.rounds
        }:
            raise ValueError("重复策略不能形成新的恢复轮次")
        return self.model_copy(update={"rounds": (*self.rounds, recovery_round)})


class SamePathRetryAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipts: tuple[SourceReceipt, ...] = Field(min_length=1)
    policy: RecoveryPolicy

    @model_validator(mode="after")
    def _receipts_form_one_timed_path(self) -> SamePathRetryAudit:
        first = self.receipts[0]
        path_signature = (
            first.route_id,
            first.strategy_unit_id,
            first.entity_id,
            first.gap_id,
            first.claim_domain,
            first.query_or_identifier,
            first.language,
            first.access_method,
            first.parent_attempt_id,
        )
        if first.parent_attempt_id is None:
            raise ValueError("同路径重试必须绑定共同父尝试")
        for expected_index, receipt in enumerate(self.receipts, start=1):
            receipt_signature = (
                receipt.route_id,
                receipt.strategy_unit_id,
                receipt.entity_id,
                receipt.gap_id,
                receipt.claim_domain,
                receipt.query_or_identifier,
                receipt.language,
                receipt.access_method,
                receipt.parent_attempt_id,
            )
            if receipt_signature != path_signature:
                raise ValueError("同路径重试不得改变路线、查询或访问方式")
            if receipt.attempt_index != expected_index:
                raise ValueError("同路径重试序号必须从一开始连续递增")
            if expected_index == 1:
                if receipt.scheduled_backoff_ms or receipt.actual_backoff_ms:
                    raise ValueError("首次尝试不得伪造退避时间")
                continue
            previous = self.receipts[expected_index - 2]
            if receipt.scheduled_backoff_ms <= 0 or receipt.actual_backoff_ms <= 0:
                raise ValueError("后续重试必须保存计划与实际退避时间")
            elapsed_ms = (receipt.started_at - previous.ended_at).total_seconds() * 1000
            if elapsed_ms < receipt.actual_backoff_ms:
                raise ValueError("实际重试间隔短于记录的退避时间")
        return self

    @property
    def minimum_retry_count_met(self) -> bool:
        return len(self.receipts) >= self.policy.minimum_same_path_attempts

    @property
    def can_leave_same_path_after_retryable_failure(self) -> bool:
        return self.minimum_retry_count_met and all(
            item.result_class
            in {result.value for result in self.policy.retryable_result_classes}
            for item in self.receipts
        )


class AlternativePathAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_units: tuple[RecoveryStrategyUnit, ...] = Field(min_length=1)
    policy: RecoveryPolicy

    @model_validator(mode="after")
    def _strategy_unit_ids_are_unique(self) -> AlternativePathAudit:
        unit_ids = tuple(item.strategy_unit_id for item in self.strategy_units)
        if len(set(unit_ids)) != len(unit_ids):
            raise ValueError("替代策略单元标识不得重复")
        if any(
            item.kind not in self.policy.alternative_strategy_kinds
            for item in self.strategy_units
        ):
            raise ValueError("替代策略类型未进入当前版本策略")
        return self

    @property
    def distinct_completed_strategy_count(self) -> int:
        return len(
            {
                (item.kind.value, item.value.casefold())
                for item in self.strategy_units
                if item.applicable and item.completed
            }
        )

    @property
    def minimum_distinct_alternatives_met(self) -> bool:
        return (
            self.distinct_completed_strategy_count
            >= self.policy.minimum_alternative_strategy_units
        )
