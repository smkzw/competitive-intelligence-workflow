from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClaimDomain(StrEnum):
    DRUG_IDENTITY_MECHANISM = "drug_identity_mechanism"
    TRIAL_IDENTITY_DESIGN_STATUS = "trial_identity_design_status"
    EFFICACY_SAFETY_RESULTS = "efficacy_safety_results"
    BASELINE_DISPOSITION = "baseline_disposition"
    REGULATORY_DEVELOPMENT_STATUS = "regulatory_development_status"
    CHINA_DEVELOPMENT_REGULATORY_STATUS = (
        "china_development_regulatory_status"
    )
    COMPANY_RELATIONSHIPS_TRANSACTIONS = (
        "company_relationships_transactions"
    )
    PATENTS_PROTECTION = "patents_protection"


class SourceAuthority(StrEnum):
    DIRECT = "direct"
    CROSS_CHECK = "cross_check"
    LEAD_ONLY = "lead_only"
    NOT_APPLICABLE = "not_applicable"


class SourceApplicability(StrEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    ACCESS_BLOCKED = "access_blocked"


class SourceEligibility(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    source_eligibility_id: str
    route_id: str
    strategy_unit_id: str
    entity_id: str
    gap_id: str
    claim_domain: ClaimDomain
    applicability: SourceApplicability
    required_by_policy: bool
    rationale_zh: str
    policy_id: str
    policy_version: str
    evidence_fragment_ids: tuple[str, ...] = Field(min_length=1)
    decided_by: str
    decided_at: datetime

    @field_validator(
        "source_eligibility_id",
        "route_id",
        "strategy_unit_id",
        "entity_id",
        "gap_id",
        "rationale_zh",
        "policy_id",
        "policy_version",
        "decided_by",
    )
    @classmethod
    def _required_text_is_not_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("来源适用性字段不能为空")
        return normalized

    @field_validator("evidence_fragment_ids")
    @classmethod
    def _evidence_ids_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(values)) != len(values) or any(not item.strip() for item in values):
            raise ValueError("来源适用性证据必须非空且不重复")
        return values

    @field_validator("decided_at")
    @classmethod
    def _decision_time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("来源适用性决定时间必须包含时区")
        return value


class SourceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    label_zh: str = Field(min_length=1)
    required_global_baseline: bool
    required_for_china: bool
    authoritative_secondary: bool
    authorities: dict[ClaimDomain, SourceAuthority]

    @model_validator(mode="after")
    def _all_claim_domains_are_explicit(self) -> SourceDefinition:
        if set(self.authorities) != set(ClaimDomain):
            raise ValueError("每个来源必须明确覆盖全部声明域")
        return self


class SourcePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    policy_id: str
    version: str
    claim_domains: tuple[ClaimDomain, ...]
    sources: tuple[SourceDefinition, ...]

    @model_validator(mode="after")
    def _matrix_is_complete_and_unique(self) -> SourcePolicy:
        if set(self.claim_domains) != set(ClaimDomain):
            raise ValueError("来源策略声明域矩阵不完整")
        if len(set(self.claim_domains)) != len(self.claim_domains):
            raise ValueError("来源策略声明域不得重复")
        source_ids = tuple(item.source_id for item in self.sources)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("来源策略标识不得重复")
        return self

    @classmethod
    def from_yaml(cls, path: Path) -> SourcePolicy:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise ValueError("无法读取来源策略") from error
        if not isinstance(payload, dict):
            raise ValueError("来源策略顶层必须是对象")
        return cls.model_validate(cast(dict[str, object], payload))

    def source(self, source_id: str) -> SourceDefinition:
        matches = tuple(item for item in self.sources if item.source_id == source_id)
        if len(matches) != 1:
            raise KeyError(f"未找到唯一来源：{source_id}")
        return matches[0]

    def authority_for(
        self, source_id: str, claim_domain: ClaimDomain
    ) -> SourceAuthority:
        return self.source(source_id).authorities[claim_domain]
