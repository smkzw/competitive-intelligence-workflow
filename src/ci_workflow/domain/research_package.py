"""Strict v1.3 research-package boundary.

The public Skill may accept a natural-language request, but the deterministic
engine only consumes :class:`ResearchPackage`.  This module intentionally owns
no browser, network, filesystem, or model-runtime behavior.  It validates the
portable, redacted hand-off between those layers and fails closed on ambiguous
identity, internal absolute locators, secrets, or incomplete closure claims.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any, Literal, Self
from urllib.parse import parse_qsl, urlsplit

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from ci_workflow.domain.evidence import EvidenceLocator, SourceTextDerivation
from ci_workflow.domain.publication import PublicationRecord, PublicationSearchReceipt

ReportName = Literal["A", "B", "C"]
ExpansionDimension = Literal["alias", "target", "company", "trial"]
ExpansionResultClass = Literal[
    "success_with_evidence",
    "searched_no_evidence",
    "not_applicable",
    "access_or_permission_blocked",
    "transient_network_failure",
    "rate_limited",
    "anti_bot_or_captcha",
    "source_unavailable",
    "parser_or_schema_failure",
    "tool_capability_gap",
    "content_truncated",
    "network_error",
]


class ResearchPackageValidationError(ValueError):
    """研究包未满足 v1.3 的严格边界。"""


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=False,
    )


def _text(value: str, *, label: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{label}不能为空")
    return normalized


def _items(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, label=label) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label}不能重复")
    return normalized


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含明确时区")
    return value


def compute_universe_review_digest(
    *,
    contract_identity: Mapping[str, Any],
    data_cutoff: date | str,
    source_policy_id: str,
    source_policy_version: str,
    entities: Sequence[Mapping[str, Any]],
    routes: Sequence[Mapping[str, Any]],
    expansion_receipts: Sequence[Mapping[str, Any]],
    closure: Mapping[str, Any],
    report_payloads: Sequence[Mapping[str, Any]] = (),
    sources: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Hash the exact universe candidate reviewed by an isolated verifier."""

    normalized_contract = ContractIdentity.model_validate(contract_identity).model_dump(mode="json")
    normalized_entities = tuple(
        EntityCandidate.model_validate(item).model_dump(mode="json") for item in entities
    )
    normalized_routes = tuple(
        RouteReceipt.model_validate(item).model_dump(mode="json") for item in routes
    )
    normalized_expansions = tuple(
        UniverseExpansionReceipt.model_validate(item).model_dump(mode="json")
        for item in expansion_receipts
    )
    normalized_report_payloads = tuple(
        ReportPayloadBinding.model_validate(item).model_dump(mode="json")
        for item in report_payloads
    )
    closure_for_validation = dict(closure)
    closure_for_validation.setdefault("reviewed_universe_sha256", "0" * 64)
    normalized_closure = UniverseClosure.model_validate(closure_for_validation).model_dump(
        mode="json"
    )
    digest_version = normalized_closure["review_digest_version"]
    closure_material = {
        key: value
        for key, value in normalized_closure.items()
        if key
        not in {
            "independent_review_id",
            "independent_reviewer_id",
            "independent_context",
            "reviewed_universe_sha256",
            "review_digest_version",
        }
    }
    material: dict[str, Any] = {
        "contract_identity": normalized_contract,
        "data_cutoff": (
            data_cutoff.isoformat()
            if isinstance(data_cutoff, date)
            else date.fromisoformat(data_cutoff).isoformat()
        ),
        "source_policy_id": source_policy_id,
        "source_policy_version": source_policy_version,
        "entities": sorted(normalized_entities, key=lambda item: item["entity_id"]),
        "routes": sorted(normalized_routes, key=lambda item: item["route_id"]),
        "expansion_receipts": sorted(normalized_expansions, key=lambda item: item["receipt_id"]),
        "closure": closure_material,
        "report_payloads": sorted(
            normalized_report_payloads, key=lambda item: item["report"]
        ),
    }
    if digest_version == "2":
        if not sources:
            raise ResearchPackageValidationError("来源复核摘要v2必须提供完整来源集合")
        normalized_sources = []
        for item in sources:
            source = ResearchSource.model_validate(item)
            normalized = source.model_dump(mode="json")
            if source.locator_detail is None:
                normalized.pop("locator_detail")  # Preserve existing v2 digest identity.
            if source.text_derivation is None:
                normalized.pop("text_derivation")
            normalized["retrieved_at"] = source.retrieved_at.astimezone(UTC).isoformat()
            normalized_sources.append(normalized)
        if len({item["source_id"] for item in normalized_sources}) != len(normalized_sources):
            raise ResearchPackageValidationError("来源复核摘要不能包含重复来源实例")
        material["review_digest_version"] = "2"
        material["sources"] = sorted(normalized_sources, key=lambda item: item["source_id"])
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ContractIdentity(_StrictModel):
    """项目与适应症的稳定身份，不接受模型自行猜测的歧义身份。"""

    project_id: str
    indication: str
    contract_version: Literal["1.3"]

    @field_validator("project_id", "indication")
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))


class ReportPayloadBinding(_StrictModel):
    """Bind one report-specific scientific payload without duplicating it."""

    report: ReportName
    relative_path: str
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_schema_version: Literal["1.0"] = "1.0"
    universe_product_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("universe_product_ids")
    @classmethod
    def _universe_products_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _items(values, label="universe_product_ids")

    @field_validator("relative_path")
    @classmethod
    def _canonical_relative_path(cls, value: str, info: Any) -> str:
        normalized = _text(value, label=str(info.field_name))
        expected = {
            "A": "evidence/library/a-research-package.json",
            "B": "evidence/library/b-research-package.json",
            "C": "evidence/library/c-research-package.json",
        }
        report = info.data.get("report")
        if report is not None and normalized != expected[report]:
            raise ResearchPackageValidationError("报告科学载荷必须使用规范项目相对路径")
        return normalized


class EntityCandidate(_StrictModel):
    entity_id: str
    entity_type: Literal["product", "target", "company", "trial", "regimen"]
    name: str
    aliases: tuple[str, ...] = ()
    identity_status: Literal["resolved", "excluded"]
    disposition: Literal["included", "excluded"]
    ontology_rule_id: str
    identity_evidence_ids: tuple[str, ...] = ()

    @field_validator("entity_id", "name", "ontology_rule_id")
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("aliases", "identity_evidence_ids")
    @classmethod
    def _unique_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, label=str(info.field_name))

    @model_validator(mode="after")
    def _identity_is_unambiguous(self) -> Self:
        if self.identity_status not in {"resolved", "excluded"}:
            raise ResearchPackageValidationError(f"实体身份必须先解决歧义：{self.entity_id}")
        if self.identity_status == "resolved" and not self.identity_evidence_ids:
            raise ResearchPackageValidationError(f"已解决实体必须保留身份依据：{self.entity_id}")
        if self.identity_status == "excluded" and self.disposition != "excluded":
            raise ResearchPackageValidationError("身份已排除的实体不得进入竞品宇宙")
        return self


class ResearchSource(_StrictModel):
    """来源版本摘要；URL 是外部来源，精确定位不允许指向本机路径。"""

    source_id: str
    title: str
    source_role: Literal[
        "official_registry",
        "registry_history",
        "registry_attachment",
        "regulatory",
        "primary_publication",
        "extension_publication",
        "safety_publication",
        "long_term_publication",
        "conference",
        "company_disclosure",
        "design_document",
        "specified_secondary",
        "commercial_database",
    ]
    source_type: Literal[
        "registry",
        "regulatory",
        "publication",
        "attachment",
        "company",
        "conference",
        "secondary",
    ]
    url: str
    locator: str
    locator_detail: EvidenceLocator | None = None
    text_derivation: SourceTextDerivation | None = None
    content_sha256: str | None = Field(pattern=r"^[0-9a-f]{64}$")
    retrieved_at: datetime
    published_at: date | None = None
    effective_at: date | None = None
    linked_trial_ids: tuple[str, ...] = ()
    publication_classification: Literal[
        "primary_result",
        "extension_primary_result",
        "key_safety_or_long_term",
        "review",
        "ad_hoc",
        "irrelevant_exploratory",
        "not_applicable",
    ]
    access_state: Literal["available", "not_accessible", "not_applicable"]
    limitations: tuple[str, ...] = ()

    @field_validator("source_id", "title", "locator")
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("url")
    @classmethod
    def _external_url(cls, value: str) -> str:
        normalized = _text(value, label="url")
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("来源 URL 必须是带主机的 http(s) 地址")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("来源 URL 不得携带用户名或密码")
        if any(_SECRET_KEY_RE.search(key) for key, _value in parse_qsl(parsed.query)):
            raise ValueError("来源 URL 查询参数不得携带凭据或令牌")
        return normalized

    @field_validator("retrieved_at")
    @classmethod
    def _retrieved_at_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("linked_trial_ids", "limitations")
    @classmethod
    def _unique_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, label=str(info.field_name))

    @model_validator(mode="after")
    def _classification_is_coherent(self) -> Self:
        if self.text_derivation is not None and (
            self.content_sha256 != self.text_derivation.text_sha256
        ):
            raise ValueError("来源文本摘要与原始资产派生回执不一致")
        if self.locator_detail is not None and self.locator_detail.url is not None:
            self._external_url(self.locator_detail.url)
        is_publication = self.source_type == "publication"
        if is_publication and self.publication_classification == "not_applicable":
            raise ResearchPackageValidationError(
                f"论文来源必须有 publication 分类：{self.source_id}"
            )
        if not is_publication and self.publication_classification != "not_applicable":
            raise ResearchPackageValidationError(
                f"非论文来源的 publication 分类必须为 not_applicable：{self.source_id}"
            )
        if self.access_state == "available":
            if self.content_sha256 is None:
                raise ResearchPackageValidationError(
                    f"可访问来源必须携带内容摘要：{self.source_id}"
                )
        elif self.content_sha256 is not None:
            raise ResearchPackageValidationError(
                f"不可访问来源不得携带已获取内容摘要：{self.source_id}"
            )
        host = (urlsplit(self.url).hostname or "").casefold()
        if host == "vip.yaozh.com" and self.source_role != "commercial_database":
            raise ResearchPackageValidationError(
                "药智企业版来源不得重标为官方或其他来源角色"
            )
        if self.source_role == "commercial_database":
            if self.source_type != "secondary":
                raise ResearchPackageValidationError("商业数据库来源类型必须为 secondary")
            if host != "vip.yaozh.com":
                raise ResearchPackageValidationError("v1 商业数据库来源必须来自药智企业版域名")
        return self


class RouteReceipt(_StrictModel):
    route_id: str
    region: Literal["global", "china", "other"]
    strategy_id: str
    result_class: Literal[
        "completed",
        "success_with_evidence",
        "not_applicable",
        "success_irrelevant_only",
        "searched_no_evidence",
        "not_publicly_disclosed",
        "access_blocked",
        "access_or_permission_blocked",
        "not_found",
        "network_error",
        "transient_network_failure",
        "rate_limited",
        "captcha_required",
        "anti_bot_or_captcha",
        "permission_denied",
        "source_unavailable",
        "parser_error",
        "parser_or_schema_failure",
        "tool_capability_gap",
        "content_truncated",
        "network_failure",
    ] = Field(validation_alias=AliasChoices("result_class", "status"))
    attempt_ids: tuple[str, ...] = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    query_or_identifier: str | None = None
    diagnostic: str | None = None

    @field_validator("route_id", "strategy_id")
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("attempt_ids", "source_ids")
    @classmethod
    def _unique_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, label=str(info.field_name))

    @field_validator("query_or_identifier", "diagnostic")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, label="回执说明")

    @model_validator(mode="after")
    def _result_has_required_evidence(self) -> Self:
        if self.result_class in {"completed", "success_with_evidence"} and not self.source_ids:
            raise ResearchPackageValidationError(
                f"有证据的来源路线必须关联至少一个来源版本：{self.route_id}"
            )
        if self.result_class == "not_applicable" and not self.diagnostic:
            raise ResearchPackageValidationError(
                f"不适用路线必须给出适用性依据，不能让闭包门静默通过：{self.route_id}"
            )
        if (
            self.result_class
            not in {
                "completed",
                "success_with_evidence",
                "not_applicable",
            }
            and not self.diagnostic
        ):
            raise ResearchPackageValidationError(f"非成功路线必须保留细粒度诊断：{self.route_id}")
        return self


class UniverseExpansionReceipt(_StrictModel):
    """One auditable reverse-expansion attempt over the competitor universe."""

    receipt_id: str
    dimension: ExpansionDimension
    round_id: str
    strategy_id: str
    route_ids: tuple[str, ...] = Field(min_length=1)
    attempt_ids: tuple[str, ...] = Field(min_length=1)
    input_entity_ids: tuple[str, ...] = ()
    discovered_entity_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    query_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_class: ExpansionResultClass
    diagnostic: str | None = None

    @field_validator("receipt_id", "round_id", "strategy_id")
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator(
        "route_ids",
        "attempt_ids",
        "input_entity_ids",
        "discovered_entity_ids",
        "source_ids",
    )
    @classmethod
    def _unique_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, label=str(info.field_name))

    @field_validator("diagnostic")
    @classmethod
    def _optional_diagnostic(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, label="扩展诊断")

    @model_validator(mode="after")
    def _result_is_coherent(self) -> Self:
        if self.discovered_entity_ids:
            if self.result_class != "success_with_evidence" or not self.source_ids:
                raise ResearchPackageValidationError("扩展发现实体必须绑定成功状态和来源")
        elif self.result_class == "success_with_evidence":
            raise ResearchPackageValidationError("成功扩展必须列出发现实体")
        if self.result_class != "success_with_evidence" and not self.diagnostic:
            raise ResearchPackageValidationError("无新增或失败的扩展必须保留细粒度诊断")
        return self


class UniverseClosure(_StrictModel):
    # Version 1 remains readable as historical evidence, never upgraded in place.
    review_digest_version: Literal["1", "2"] = "1"
    """全球/中国路线与四类反向扩展的可审计闭包证明。"""

    closed: bool
    global_route_ids: tuple[str, ...] = Field(min_length=1)
    china_route_ids: tuple[str, ...] = Field(min_length=1)
    alias_expansion_receipts: tuple[str, ...] = Field(min_length=1)
    target_expansion_receipts: tuple[str, ...] = Field(min_length=1)
    company_expansion_receipts: tuple[str, ...] = Field(min_length=1)
    trial_expansion_receipts: tuple[str, ...] = Field(min_length=1)
    independent_review_id: str | None = None
    independent_reviewer_id: str | None = None
    independent_context: str | None = None
    reviewed_universe_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    candidate_entity_ids: tuple[str, ...] = ()
    excluded_entity_ids: tuple[str, ...] = ()
    new_entity_ids_by_round: Mapping[str, tuple[str, ...]] = Field(default_factory=dict)
    convergence_round_ids: tuple[str, ...] = ()

    @field_validator(
        "global_route_ids",
        "china_route_ids",
        "alias_expansion_receipts",
        "target_expansion_receipts",
        "company_expansion_receipts",
        "trial_expansion_receipts",
        "excluded_entity_ids",
    )
    @classmethod
    def _unique_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, label=str(info.field_name))

    @field_validator("independent_review_id", "independent_reviewer_id", "independent_context")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, label="独立复核")

    @field_validator("candidate_entity_ids")
    @classmethod
    def _candidate_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _items(values, label="candidate_entity_ids")

    @field_validator("new_entity_ids_by_round")
    @classmethod
    def _round_entities(
        cls, values: Mapping[str, tuple[str, ...]]
    ) -> Mapping[str, tuple[str, ...]]:
        return {
            _text(round_id, label="扩展轮次"): _items(entity_ids, label="轮次实体")
            for round_id, entity_ids in values.items()
        }

    @field_validator("convergence_round_ids")
    @classmethod
    def _convergence_rounds(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _items(values, label="收敛轮次")

    @model_validator(mode="after")
    def _closed_requires_independent_review(self) -> Self:
        if set(self.global_route_ids) & set(self.china_route_ids):
            raise ResearchPackageValidationError("全球与中国路线标识不得重叠")
        if self.closed and (
            not self.independent_review_id
            or not self.independent_reviewer_id
            or not self.independent_context
            or not self.reviewed_universe_sha256
        ):
            raise ResearchPackageValidationError("宇宙闭包必须绑定独立干净上下文复核")
        if self.closed:
            round_ids = tuple(self.new_entity_ids_by_round)
            if (
                len(self.convergence_round_ids) < 2
                or (tuple(self.convergence_round_ids) != round_ids[-2:])
                or any(
                    self.new_entity_ids_by_round[round_id]
                    for round_id in self.convergence_round_ids
                )
            ):
                raise ResearchPackageValidationError("宇宙闭包必须由最后连续两轮零新增证明收敛")
        return self


class ExtractionCandidate(_StrictModel):
    candidate_id: str
    source_id: str
    locator: str
    field: str
    value: Any
    normalized_value: Any | None = None
    unit: str | None = None
    claim_domain: str | None = None

    @field_validator("candidate_id", "source_id", "locator", "field")
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("unit", "claim_domain")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, label="候选字段")


class RecoveryRound(_StrictModel):
    round_number: int = Field(ge=1)
    strategy_id: str
    strategy_kind: str
    target_gap_ids: tuple[str, ...] = Field(min_length=1)
    route_ids: tuple[str, ...] = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    information_gain: Literal[
        "new_evidence",
        "reduced_conflict",
        "changed_applicability",
        "no-new-evidence",
        "not_applicable",
    ]
    query_or_identifier: str | None = None

    @field_validator("strategy_id", "strategy_kind")
    @classmethod
    def _text_fields(cls, value: str, info: Any) -> str:
        return _text(value, label=str(info.field_name))

    @field_validator("target_gap_ids", "route_ids", "source_ids")
    @classmethod
    def _unique_items(cls, values: tuple[str, ...], info: Any) -> tuple[str, ...]:
        return _items(values, label=str(info.field_name))

    @field_validator("query_or_identifier")
    @classmethod
    def _optional_query(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, label="恢复查询")


class GapStrategy(_StrictModel):
    gap_id: str
    required: bool
    status: Literal[
        "open",
        "resolved",
        "not_reported",
        "not_publicly_disclosed",
        "blocked",
        "anomalous_reported_zero",
    ]
    recovery_required: bool = False
    strategy_ids: tuple[str, ...] = Field(min_length=1)
    reason: str | None = None

    @field_validator("gap_id")
    @classmethod
    def _gap_id(cls, value: str) -> str:
        return _text(value, label="gap_id")

    @field_validator("strategy_ids")
    @classmethod
    def _strategy_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return _items(values, label="strategy_ids")

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str | None) -> str | None:
        return None if value is None else _text(value, label="缺口原因")

    @model_validator(mode="after")
    def _missing_or_anomalous_requires_recovery(self) -> Self:
        if (
            self.required
            and self.status
            in {
                "open",
                "not_reported",
                "not_publicly_disclosed",
                "blocked",
                "anomalous_reported_zero",
            }
            and not self.recovery_required
        ):
            raise ResearchPackageValidationError("关键缺失或异常零值必须触发恢复检索")
        return self


_SECRET_KEY_RE = re.compile(
    r"(?:pass(?:word)?|secret|credential|api[_-]?key|access[_-]?token|refresh[_-]?token|cookie|authorization|auth[_-]?header|session[_-]?token)",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(
    r"^(?:bearer\s+|basic\s+|-----BEGIN|eyJ[A-Za-z0-9_-]{8,}\.|AKIA[0-9A-Z]{12,})",
    re.IGNORECASE,
)
_LOCAL_PATH_RE = re.compile(
    r"^(?:/|~/|~$|[A-Za-z]:[\\/]|\\\\)|(?:^|/)(?:Users|private|home|var|tmp|Volumes)(?:/|$)",
    re.IGNORECASE,
)


def _assert_safe_value(value: Any, *, path: str = "$") -> None:
    """Recursively reject secrets and machine-local absolute paths."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if _SECRET_KEY_RE.search(key_text):
                raise ResearchPackageValidationError(f"研究包包含凭据字段：{path}.{key_text}")
            _assert_safe_value(item, path=f"{path}.{key_text}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _assert_safe_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        if _SECRET_VALUE_RE.search(value.strip()):
            raise ResearchPackageValidationError(f"研究包包含疑似凭据值：{path}")
        if _LOCAL_PATH_RE.search(value.strip()):
            raise ResearchPackageValidationError(f"研究包包含内部绝对路径：{path}")


class ResearchPackage(_StrictModel):
    """确定性引擎唯一接受的 v1.3 科学输入。"""

    schema_version: Literal["1.3"]
    package_id: str = Field(validation_alias=AliasChoices("package_id", "research_package_id"))
    contract_identity: ContractIdentity
    reports: tuple[ReportName, ...] = Field(min_length=1)
    data_cutoff: date
    source_policy_id: str
    source_policy_version: str
    producer_id: str
    producer_context: str
    entities: tuple[EntityCandidate, ...] = ()
    sources: tuple[ResearchSource, ...] = ()
    publication_records: tuple[PublicationRecord, ...] = ()
    publication_search_receipts: tuple[PublicationSearchReceipt, ...] = ()
    routes: tuple[RouteReceipt, ...] = Field(min_length=1)
    expansion_receipts: tuple[UniverseExpansionReceipt, ...] = Field(min_length=4)
    closure: UniverseClosure
    extraction_candidates: tuple[ExtractionCandidate, ...] = Field(
        validation_alias=AliasChoices("extraction_candidates", "extractions"),
        default=(),
    )
    recovery_rounds: tuple[RecoveryRound, ...] = Field(default=())
    gap_strategies: tuple[GapStrategy, ...] = Field(
        validation_alias=AliasChoices("gap_strategies", "gaps"),
        default=(),
    )
    report_payloads: tuple[ReportPayloadBinding, ...] = ()
    metadata: Mapping[str, Any] = {}

    @field_validator(
        "package_id",
        "source_policy_id",
        "source_policy_version",
        "producer_id",
        "producer_context",
    )
    @classmethod
    def _package_id(cls, value: str) -> str:
        return _text(value, label="package_id")

    @model_validator(mode="after")
    def _references_and_safety_are_closed(self) -> Self:
        _assert_safe_value(self.model_dump(mode="python"))

        entity_ids = tuple(entity.entity_id for entity in self.entities)
        if len(entity_ids) != len(set(entity_ids)):
            raise ResearchPackageValidationError("实体候选标识不能重复")
        source_ids = tuple(source.source_id for source in self.sources)
        if len(source_ids) != len(set(source_ids)):
            raise ResearchPackageValidationError("来源版本标识不能重复")
        publication_ids = tuple(item.publication_id for item in self.publication_records)
        if len(publication_ids) != len(set(publication_ids)):
            raise ResearchPackageValidationError("publication verdict 标识不能重复")
        publication_source_ids = tuple(item.source_id for item in self.publication_records)
        if len(publication_source_ids) != len(set(publication_source_ids)):
            raise ResearchPackageValidationError("一个论文来源只能绑定一个正式 publication verdict")
        publication_search_ids = tuple(
            item.search_id for item in self.publication_search_receipts
        )
        if len(publication_search_ids) != len(set(publication_search_ids)):
            raise ResearchPackageValidationError("publication 检索回执标识不能重复")
        route_ids = tuple(route.route_id for route in self.routes)
        if len(route_ids) != len(set(route_ids)):
            raise ResearchPackageValidationError("来源路线标识不能重复")
        expansion_ids = tuple(item.receipt_id for item in self.expansion_receipts)
        if len(expansion_ids) != len(set(expansion_ids)):
            raise ResearchPackageValidationError("宇宙扩展回执标识不能重复")
        gap_ids = tuple(gap.gap_id for gap in self.gap_strategies)
        if len(gap_ids) != len(set(gap_ids)):
            raise ResearchPackageValidationError("缺口策略标识不能重复")
        payload_reports = tuple(binding.report for binding in self.report_payloads)
        if len(payload_reports) != len(set(payload_reports)):
            raise ResearchPackageValidationError("报告科学载荷绑定不能重复")
        if self.report_payloads and set(payload_reports) != set(self.reports):
            raise ResearchPackageValidationError("报告科学载荷绑定必须恰好覆盖报告集合")

        source_set = set(source_ids)
        route_set = set(route_ids)
        entity_set = set(entity_ids)
        entity_by_id = {item.entity_id: item for item in self.entities}
        gap_set = set(gap_ids)
        for entity in self.entities:
            unknown = set(entity.identity_evidence_ids) - source_set
            if unknown:
                raise ResearchPackageValidationError(
                    f"实体身份引用了未知来源：{entity.entity_id} -> {sorted(unknown)}"
                )
        for source in self.sources:
            unknown = set(source.linked_trial_ids) - entity_set
            if unknown:
                raise ResearchPackageValidationError(
                    f"来源引用了未知试验实体：{source.source_id} -> {sorted(unknown)}"
                )
        publication_sources = {
            source.source_id: source
            for source in self.sources
            if source.source_type == "publication"
        }
        if set(publication_source_ids) != set(publication_sources):
            raise ResearchPackageValidationError(
                "每个论文来源必须恰好绑定一个正式 publication verdict"
            )
        included_trial_ids = {
            item.entity_id
            for item in self.entities
            if item.entity_type == "trial" and item.disposition == "included"
        }
        search_by_trial = {
            item.trial_id: item for item in self.publication_search_receipts
        }
        if len(search_by_trial) != len(self.publication_search_receipts):
            raise ResearchPackageValidationError("每个试验只能绑定一个 publication 检索回执")
        if set(search_by_trial) != included_trial_ids:
            raise ResearchPackageValidationError(
                "每个纳入试验必须恰好绑定一个 publication 检索回执"
            )
        publication_ids_by_trial = {
            trial_id: {
                record.publication_id
                for record in self.publication_records
                if trial_id in record.linked_trial_ids
            }
            for trial_id in included_trial_ids
        }
        for trial_id, receipt in search_by_trial.items():
            if set(receipt.discovered_publication_ids) != publication_ids_by_trial[trial_id]:
                raise ResearchPackageValidationError(
                    f"publication 检索回执未完整绑定试验 verdict：{trial_id}"
                )
        attempt_ids: list[str] = []
        for record in self.publication_records:
            source = publication_sources[record.source_id]
            if record.publication_class != source.publication_classification:
                raise ResearchPackageValidationError(
                    f"来源信号与正式 publication verdict 不一致：{record.publication_id}"
                )
            if record.source_url != source.url:
                raise ResearchPackageValidationError(
                    f"publication verdict 未绑定当前来源地址：{record.publication_id}"
                )
            if set(record.linked_trial_ids) != set(source.linked_trial_ids):
                raise ResearchPackageValidationError(
                    f"publication verdict 与来源的试验绑定不一致：{record.publication_id}"
                )
            if any(
                trial_id not in entity_by_id or entity_by_id[trial_id].entity_type != "trial"
                for trial_id in record.linked_trial_ids
            ):
                raise ResearchPackageValidationError(
                    f"publication verdict 必须绑定已解决的试验实体：{record.publication_id}"
                )
            if (
                record.product_id not in entity_by_id
                or entity_by_id[record.product_id].entity_type != "product"
            ):
                raise ResearchPackageValidationError(
                    f"publication verdict 必须绑定已解决的产品实体：{record.publication_id}"
                )
            if not set(record.affected_reports) <= set(self.reports):
                raise ResearchPackageValidationError(
                    f"publication verdict 引用了未请求的报告：{record.publication_id}"
                )
            if record.acquisition_disposition == "acquired":
                if source.access_state != "available":
                    raise ResearchPackageValidationError(
                        f"已获取 publication 必须绑定可访问来源：{record.publication_id}"
                    )
            elif record.required and source.access_state != "not_accessible":
                raise ResearchPackageValidationError(
                    f"未获取的必需 publication 必须保持不可访问状态：{record.publication_id}"
                )
            for attempt in record.fetch_attempts:
                attempt_ids.append(attempt.attempt_id)
                if attempt.result_class == "acquired" and attempt.source_id != record.source_id:
                    raise ResearchPackageValidationError(
                        f"获取回执未绑定正式 publication 来源：{record.publication_id}"
                    )
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ResearchPackageValidationError("publication 获取尝试标识不能重复")
        for route in self.routes:
            unknown = set(route.source_ids) - source_set
            if unknown:
                raise ResearchPackageValidationError(
                    f"路线引用了未知来源：{route.route_id} -> {sorted(unknown)}"
                )
        for expansion in self.expansion_receipts:
            if not set(expansion.route_ids) <= route_set:
                raise ResearchPackageValidationError(
                    f"扩展回执引用了未知路线：{expansion.receipt_id}"
                )
            if not set(expansion.source_ids) <= source_set:
                raise ResearchPackageValidationError(
                    f"扩展回执引用了未知来源：{expansion.receipt_id}"
                )
            referenced_entities = set(
                (*expansion.input_entity_ids, *expansion.discovered_entity_ids)
            )
            if not referenced_entities <= entity_set:
                raise ResearchPackageValidationError(
                    f"扩展回执引用了未知实体：{expansion.receipt_id}"
                )
        for candidate in self.extraction_candidates:
            if candidate.source_id not in source_set:
                raise ResearchPackageValidationError(
                    f"抽取候选引用了未知来源：{candidate.candidate_id}"
                )
        closure_route_ids = set(self.closure.global_route_ids) | set(self.closure.china_route_ids)
        if not closure_route_ids <= route_set:
            raise ResearchPackageValidationError("宇宙闭包引用了未存在的路线回执")
        if not set(self.closure.candidate_entity_ids) <= entity_set:
            raise ResearchPackageValidationError("宇宙闭包引用了未知候选实体")
        if not set(self.closure.excluded_entity_ids) <= entity_set:
            raise ResearchPackageValidationError("宇宙闭包引用了未知排除实体")
        if set(self.closure.excluded_entity_ids) & set(self.closure.candidate_entity_ids):
            raise ResearchPackageValidationError("实体不能同时属于候选集合和排除集合")
        if any(
            entity_by_id[entity_id].disposition != "included"
            for entity_id in self.closure.candidate_entity_ids
        ):
            raise ResearchPackageValidationError("竞品宇宙候选实体必须有明确纳入处置")
        if any(
            entity_by_id[entity_id].disposition != "excluded"
            for entity_id in self.closure.excluded_entity_ids
        ):
            raise ResearchPackageValidationError("竞品宇宙排除实体必须有明确排除处置")
        candidate_products = {
            entity_id
            for entity_id in self.closure.candidate_entity_ids
            if entity_by_id[entity_id].entity_type == "product"
        }
        for binding in self.report_payloads:
            if not set(binding.universe_product_ids) <= candidate_products:
                raise ResearchPackageValidationError(
                    f"{binding.report} 类载荷候选竞品必须属于已闭合竞品宇宙"
                )
        if self.closure.independent_context == self.producer_context:
            raise ResearchPackageValidationError("宇宙闭包独立审查不得复用生产上下文")
        if self.closure.independent_reviewer_id == self.producer_id:
            raise ResearchPackageValidationError("宇宙闭包独立审查不得复用生产者身份")
        reviewed_digest = compute_universe_review_digest(
            contract_identity=self.contract_identity.model_dump(mode="json"),
            data_cutoff=self.data_cutoff,
            source_policy_id=self.source_policy_id,
            source_policy_version=self.source_policy_version,
            entities=tuple(item.model_dump(mode="json") for item in self.entities),
            routes=tuple(item.model_dump(mode="json") for item in self.routes),
            expansion_receipts=tuple(
                item.model_dump(mode="json") for item in self.expansion_receipts
            ),
            closure=self.closure.model_dump(mode="json"),
            report_payloads=tuple(
                item.model_dump(mode="json") for item in self.report_payloads
            ),
            sources=tuple(item.model_dump(mode="json") for item in self.sources),
        )
        if self.closure.reviewed_universe_sha256 != reviewed_digest:
            raise ResearchPackageValidationError("独立复核未绑定当前竞品宇宙候选字节")
        expansion_by_id = {item.receipt_id: item for item in self.expansion_receipts}
        closure_expansions = {
            "alias": self.closure.alias_expansion_receipts,
            "target": self.closure.target_expansion_receipts,
            "company": self.closure.company_expansion_receipts,
            "trial": self.closure.trial_expansion_receipts,
        }
        for dimension, receipt_ids in closure_expansions.items():
            actual_ids = {
                item.receipt_id for item in self.expansion_receipts if item.dimension == dimension
            }
            if set(receipt_ids) != actual_ids or any(
                receipt_id not in expansion_by_id
                or expansion_by_id[receipt_id].dimension != dimension
                for receipt_id in receipt_ids
            ):
                raise ResearchPackageValidationError(f"{dimension} 扩展回执未完整绑定")
        discovered_by_round: dict[str, set[str]] = {}
        for expansion in self.expansion_receipts:
            discovered_by_round.setdefault(expansion.round_id, set()).update(
                expansion.discovered_entity_ids
            )
        if set(discovered_by_round) != set(self.closure.new_entity_ids_by_round) or any(
            discovered_by_round[round_id] != set(entity_ids_for_round)
            for round_id, entity_ids_for_round in self.closure.new_entity_ids_by_round.items()
        ):
            raise ResearchPackageValidationError("扩展回执与逐轮新增实体记录不一致")
        discovered_entities = set().union(
            *(set(item.discovered_entity_ids) for item in self.expansion_receipts)
        )
        if not set((*self.closure.candidate_entity_ids, *self.closure.excluded_entity_ids)) <= (
            discovered_entities
        ):
            raise ResearchPackageValidationError("竞品宇宙实体必须来自可审计扩展回执")
        for round_id, entity_ids_for_round in self.closure.new_entity_ids_by_round.items():
            if not set(entity_ids_for_round) <= entity_set:
                raise ResearchPackageValidationError(f"宇宙闭包轮次 {round_id} 引用了未知实体")
        for round_item in self.recovery_rounds:
            if not set(round_item.route_ids) <= route_set:
                raise ResearchPackageValidationError(
                    f"恢复轮次引用了未知路线：{round_item.strategy_id}"
                )
            if not set(round_item.source_ids) <= source_set:
                raise ResearchPackageValidationError(
                    f"恢复轮次引用了未知来源：{round_item.strategy_id}"
                )
            if not set(round_item.target_gap_ids) <= gap_set:
                raise ResearchPackageValidationError(
                    f"恢复轮次引用了未知缺口：{round_item.strategy_id}"
                )
        return self

    def assert_gate_ready(self) -> None:
        """在进入门槛/快照前检查闭包、恢复和独立复核。"""

        if not self.closure.closed:
            raise ResearchPackageValidationError("竞品宇宙尚未闭包，不得进入门槛")
        if not self.closure.candidate_entity_ids:
            raise ResearchPackageValidationError("竞品宇宙为空，应进入证据不足流程而非报告门")
        route_by_id = {route.route_id: route for route in self.routes}
        required_route_ids = (*self.closure.global_route_ids, *self.closure.china_route_ids)
        for route_id in required_route_ids:
            route = route_by_id[route_id]
            if route.result_class not in {
                "completed",
                "success_with_evidence",
                "not_applicable",
                "access_blocked",
                "access_or_permission_blocked",
            }:
                raise ResearchPackageValidationError(
                    f"必查路线未完成：{route_id}（{route.result_class}）"
                )
        terminal_expansion_results = {
            "success_with_evidence",
            "searched_no_evidence",
            "not_applicable",
            "access_or_permission_blocked",
        }
        for expansion in self.expansion_receipts:
            if expansion.result_class not in terminal_expansion_results:
                raise ResearchPackageValidationError(
                    f"扩展回执未完成：{expansion.receipt_id}（{expansion.result_class}）"
                )
        rounds = {item.round_number: item for item in self.recovery_rounds}
        recovery_gap_ids = {gap.gap_id for gap in self.gap_strategies if gap.recovery_required}
        if not recovery_gap_ids and not rounds:
            return
        if (
            len(rounds) != len(self.recovery_rounds)
            or set(rounds) != set(range(1, len(rounds) + 1))
            or len(rounds) < 2
        ):
            raise ResearchPackageValidationError("恢复记录必须从第 1 轮连续编号且至少两轮")
        first, second = rounds[len(rounds) - 1], rounds[len(rounds)]
        if first.strategy_id == second.strategy_id or first.strategy_kind == second.strategy_kind:
            raise ResearchPackageValidationError("最后两轮恢复必须使用不同策略")
        if (
            first.route_ids == second.route_ids
            and first.query_or_identifier == second.query_or_identifier
        ):
            raise ResearchPackageValidationError("最后两轮恢复不得重复相同路线与查询")
        if first.information_gain not in {"no-new-evidence", "not_applicable"} or (
            second.information_gain not in {"no-new-evidence", "not_applicable"}
        ):
            raise ResearchPackageValidationError("最后两轮恢复尚未证明信息增益饱和")
        for gap_id in recovery_gap_ids:
            if gap_id not in first.target_gap_ids or gap_id not in second.target_gap_ids:
                raise ResearchPackageValidationError("最后两轮恢复必须逐项绑定关键缺口")
        if not self.closure.independent_review_id or not self.closure.independent_context:
            raise ResearchPackageValidationError("进入门槛前必须完成独立干净上下文复核")

    def assert_product_handoff_ready(self) -> None:
        """Require closure plus byte bindings before the product runner may consume it."""

        self.assert_gate_ready()
        if set(binding.report for binding in self.report_payloads) != set(self.reports):
            raise ResearchPackageValidationError("产品运行前必须绑定全部报告科学载荷字节")


def validate_research_package(
    payload: Mapping[str, Any], *, require_gate_ready: bool = False
) -> ResearchPackage:
    """Validate a mapping and optionally enforce pre-gate closure."""

    try:
        package = ResearchPackage.model_validate(payload)
        if require_gate_ready:
            package.assert_gate_ready()
        return package
    except ResearchPackageValidationError:
        raise
    except ValueError as error:
        raise ResearchPackageValidationError(str(error)) from error


__all__ = [
    "ContractIdentity",
    "compute_universe_review_digest",
    "EntityCandidate",
    "ExtractionCandidate",
    "GapStrategy",
    "PublicationRecord",
    "PublicationSearchReceipt",
    "RecoveryRound",
    "ReportPayloadBinding",
    "ResearchPackage",
    "ResearchPackageValidationError",
    "ResearchSource",
    "RouteReceipt",
    "UniverseClosure",
    "UniverseExpansionReceipt",
    "validate_research_package",
]
