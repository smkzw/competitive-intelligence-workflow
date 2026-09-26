"""Typed inputs and receipts for rebuilding native portal consumers from active facts.

This module deliberately contains no page-selection rules and does not render UI.
Each A/B/C renderer resolves its own domain row and records the concrete consumer
identities it actually rebuilt.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ci_workflow.reports.common.evidence_view import UserEditDisclosure

ReportCode = Literal["A", "B", "C"]
DomainCollection = Literal["safety", "efficacy", "observations"]


class ActiveFactBinding(BaseModel):
    """Immutable scientific identity of one original portal consumer row.

    Optional values are still required keys: ``None`` means the original report
    contract explicitly has no such axis.  It never means "skip comparison".
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportCode
    collection: DomainCollection
    row_id: str
    product_id: str
    drug_name: str
    trial_id: str
    registry_id: str
    group_id: str | None
    arm: str | None
    cohort_id: str | None
    period: str | None
    endpoint_definition: str | None
    event_definition: str | None
    statistical_form: str
    measure_object: str
    unit: str
    normalized_unit: str
    source_version_id: str
    source_pointer: str
    original_row_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _identity_is_complete(self) -> ActiveFactBinding:
        required_text = (
            "row_id",
            "product_id",
            "drug_name",
            "trial_id",
            "registry_id",
            "statistical_form",
            "measure_object",
            "unit",
            "normalized_unit",
            "source_version_id",
            "source_pointer",
        )
        if any(not str(getattr(self, field)).strip() for field in required_text):
            raise ValueError("active fact消费者科学身份必填字段不能为空")
        definitions = (self.endpoint_definition, self.event_definition)
        if sum(value is not None and value.strip() != "" for value in definitions) != 1:
            raise ValueError("active fact消费者必须且只能声明endpoint或event定义之一")
        if self.collection == "safety" and self.event_definition is None:
            raise ValueError("安全性消费者必须声明事件定义")
        if self.collection in {"efficacy", "observations"} and self.endpoint_definition is None:
            raise ValueError("疗效/设计消费者必须声明终点或设计定义")
        return self


class ActiveFact(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    fact_id: str
    fact_version_id: str
    field_id: str
    raw_value: str | None = None
    normalized_value: str | int | float | bool | None = None
    disclosure_state: str = "reported_value"
    primary_fragment_id: str
    source_version_id: str
    source_locator: str
    source_quote: str
    consumer_bindings: tuple[ActiveFactBinding, ...] = ()


class ActiveFactRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    revision: int = Field(ge=1)
    request_id: str
    fact_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    facts: tuple[ActiveFact, ...]

    def bindings_for(self, report: ReportCode) -> tuple[tuple[ActiveFact, ActiveFactBinding], ...]:
        return tuple(
            (fact, binding)
            for fact in self.facts
            for binding in fact.consumer_bindings
            if binding.report == report
        )


class PortalConsumerNode(BaseModel):
    """Concrete identities emitted by a report renderer after native projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportCode
    fact_id: str
    fact_version_id: str
    collection: DomainCollection
    row_id: str
    binding_identity: ActiveFactBinding
    original_row_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_relative_path: str
    chart_consumer: str
    table_consumer: str
    narrative_consumer: str
    index_consumer: str
    source_binding_consumer: str

    @model_validator(mode="after")
    def _binding_matches_consumer(self) -> PortalConsumerNode:
        if (
            self.binding_identity.report != self.report
            or self.binding_identity.collection != self.collection
            or self.binding_identity.row_id != self.row_id
            or self.binding_identity.original_row_sha256 != self.original_row_sha256
        ):
            raise ValueError("portal consumer与已验证binding身份不一致")
        return self


class PortalRenderReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0"] = "2.0"
    report: ReportCode
    revision: int
    request_id: str
    fact_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_relative_path: Literal["data/report.js"] = "data/report.js"
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    search_index_relative_path: Literal["data/search-index.js"] = "data/search-index.js"
    search_index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    html_sha256: dict[str, str]
    consumers: tuple[PortalConsumerNode, ...]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonical_source_pointer(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_active_fact_binding(
    fact: ActiveFact,
    declared: ActiveFactBinding,
    actual: ActiveFactBinding,
) -> ActiveFactBinding:
    """Fail closed before projection if either row or fact identity drifts."""
    if declared != actual:
        differing = [
            field
            for field in ActiveFactBinding.model_fields
            if getattr(declared, field) != getattr(actual, field)
        ]
        raise ValueError("active fact原消费者科学身份不一致：" + ",".join(differing))
    extra = fact.model_extra or {}
    source_pointer = fact.source_locator
    # Registry fragments preserve the full JSON locator; A's existing row
    # contract carries its exact field_path. Both must identify the same atom.
    if actual.report == "A" and actual.source_pointer.startswith("$."):
        try:
            locator_value = json.loads(source_pointer)
        except json.JSONDecodeError:
            locator_value = None
        if isinstance(locator_value, dict) and isinstance(
            locator_value.get("field_path"), str
        ):
            source_pointer = locator_value["field_path"]
    fact_identity: dict[str, Any] = {
        "product_id": extra.get("product_id"),
        "drug_name": extra.get("drug_name"),
        "trial_id": extra.get("trial_id"),
        "registry_id": extra.get("registry_id"),
        "group_id": extra.get("group_id"),
        "arm": extra.get("arm"),
        "cohort_id": extra.get("cohort_id"),
        "period": extra.get("period"),
        "endpoint_definition": extra.get("endpoint_definition"),
        "event_definition": extra.get("event_definition"),
        "statistical_form": extra.get("statistical_form"),
        "measure_object": extra.get("measure_object"),
        "unit": extra.get("unit"),
        "normalized_unit": extra.get("normalized_unit"),
        "source_version_id": fact.source_version_id,
        "source_pointer": source_pointer,
    }
    mismatches = [
        field
        for field, value in fact_identity.items()
        if value != getattr(actual, field)
    ]
    if mismatches:
        raise ValueError("active fact与消费者科学身份不一致：" + ",".join(mismatches))
    return actual


def user_edit_disclosure(
    fact: ActiveFact,
    active_revision: ActiveFactRevision,
    *,
    original_value: str,
    current_value: str | None = None,
) -> UserEditDisclosure:
    """Build the explicit user layer without copying it into source fields."""
    extra = fact.model_extra or {}
    provenance = extra.get("user_edit")
    if extra.get("review_state") != "user_modified" or not isinstance(provenance, dict):
        raise ValueError("active projection只接受带完整provenance的user_modified事实")
    edit_request_id = provenance.get("request_id")
    edit_revision = provenance.get("revision")
    if (
        not isinstance(edit_request_id, str)
        or not edit_request_id.strip()
        or type(edit_revision) is not int
        or edit_revision < 1
        or edit_revision > active_revision.revision
        or (
            edit_revision == active_revision.revision
            and edit_request_id != active_revision.request_id
        )
    ):
        raise ValueError("用户修订provenance与当前事实闭包不一致")
    cleared = fact.disclosure_state == "user_cleared"
    value = "用户清除，待重新核实" if cleared else current_value or fact.raw_value
    if value is None:
        if fact.normalized_value is None:
            raise ValueError("用户修订当前值缺失，且并非显式清除")
        value = str(fact.normalized_value)
    try:
        parsed_locator = json.loads(fact.source_locator)
    except json.JSONDecodeError:
        parsed_locator = {"field_path": fact.source_locator}
    if not isinstance(parsed_locator, dict):
        parsed_locator = {"field_path": fact.source_locator}
    operation = provenance.get("operation")
    if operation not in {"save", "undo"}:
        raise ValueError("用户修订provenance操作类型无效")
    typed_operation: Literal["save", "undo"] = operation
    return UserEditDisclosure(
        fact_id=fact.fact_id,
        fact_version_id=fact.fact_version_id,
        request_id=edit_request_id,
        revision=edit_revision,
        status_label_zh=(
            "用户清除，待重新核实" if cleared else "用户修订，未独立复核"
        ),
        primary_fragment_id=fact.primary_fragment_id,
        source_version_id=fact.source_version_id,
        source_locator=parsed_locator,
        current_value=str(value),
        original_value=original_value,
        basis=str(provenance.get("basis") or ""),
        saved_by=str(provenance.get("saved_by") or ""),
        saved_at=str(provenance.get("saved_at") or ""),
        operation=typed_operation,
    )


def write_render_receipt(
    site_root: Path,
    *,
    report: ReportCode,
    active_revision: ActiveFactRevision,
    consumers: tuple[PortalConsumerNode, ...],
) -> PortalRenderReceipt:
    if not consumers:
        raise ValueError(f"{report} renderer没有实际消费任何active revision事实")
    html_paths = sorted({item.page_relative_path for item in consumers})
    html_sha256 = {
        relative: sha256_file(site_root / relative)
        for relative in html_paths
    }
    receipt = PortalRenderReceipt(
        report=report,
        revision=active_revision.revision,
        request_id=active_revision.request_id,
        fact_revision_digest=active_revision.fact_revision_digest,
        payload_sha256=sha256_file(site_root / "data/report.js"),
        search_index_sha256=sha256_file(site_root / "data/search-index.js"),
        html_sha256=html_sha256,
        consumers=consumers,
    )
    path = site_root / "data/consumer-receipt.json"
    path.write_text(
        json.dumps(
            receipt.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt


def numeric_value(fact: ActiveFact) -> float:
    value: Any = fact.normalized_value
    if isinstance(value, bool) or value is None:
        raise ValueError(f"事实 {fact.fact_id} 缺少可投影数值")
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"事实 {fact.fact_id} 的规范值不是数值") from error


__all__ = [
    "ActiveFact",
    "ActiveFactBinding",
    "ActiveFactRevision",
    "PortalConsumerNode",
    "PortalRenderReceipt",
    "canonical_sha256",
    "canonical_source_pointer",
    "numeric_value",
    "validate_active_fact_binding",
    "write_render_receipt",
]
