from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.domain.ids import stable_id

_SHA256 = re.compile(r"[0-9a-f]{64}")


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("监管材料字段不能为空")
    return normalized


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("监管材料日期必须包含明确时区")
    return parsed


class RegulatoryClaimScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_domain: str
    locator: EvidenceLocator

    @field_validator("claim_domain")
    @classmethod
    def _claim_domain_is_not_blank(cls, value: str) -> str:
        return _text(value)


class RegulatoryDocumentVersion(BaseModel):
    """一个监管文件的不可变版本及其允许支持的声明领域。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_document_id: str
    source_version_id: str
    jurisdiction: str
    authority: str
    document_id: str
    title: str
    version_label: str
    published_at: datetime
    acquired_at: datetime
    content_sha256: str
    source_url: str
    claim_scopes: tuple[RegulatoryClaimScope, ...]

    @field_validator(
        "jurisdiction",
        "authority",
        "document_id",
        "title",
        "version_label",
        "source_url",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _text(value)

    @field_validator("content_sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("监管材料内容摘要必须是小写 SHA-256")
        return value

    @field_validator("published_at", "acquired_at")
    @classmethod
    def _dates_have_offsets(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("监管材料日期必须包含明确时区")
        return value

    @classmethod
    def create(
        cls,
        *,
        jurisdiction: str,
        authority: str,
        document_id: str,
        title: str,
        version_label: str,
        published_at: str,
        acquired_at: str,
        content_sha256: str,
        source_url: str,
        claim_scopes: tuple[Mapping[str, str], ...],
    ) -> RegulatoryDocumentVersion:
        jurisdiction = _text(jurisdiction).upper()
        authority = _text(authority)
        document_id = _text(document_id)
        source_document_id = stable_id(
            "regulatory-document", jurisdiction, authority, document_id
        )
        scopes: list[RegulatoryClaimScope] = []
        for item in claim_scopes:
            missing = {"claim_domain", "field_path", "locator_label"} - set(item)
            if missing:
                raise ValueError("监管材料声明范围缺少领域、字段或位置")
            scopes.append(
                RegulatoryClaimScope(
                    claim_domain=item["claim_domain"],
                    locator=EvidenceLocator(
                        document_role=f"{authority} 监管材料",
                        field_path=item["field_path"],
                        paragraph=item["locator_label"],
                        url=source_url,
                    ),
                )
            )
        if not scopes:
            raise ValueError("监管材料必须明确至少一个声明领域")
        if len({item.claim_domain for item in scopes}) != len(scopes):
            raise ValueError("同一监管材料版本的声明领域不得重复")
        return cls(
            source_document_id=source_document_id,
            source_version_id=stable_id(
                "regulatory-version", source_document_id, version_label, content_sha256
            ),
            jurisdiction=jurisdiction,
            authority=authority,
            document_id=document_id,
            title=title,
            version_label=version_label,
            published_at=_datetime(published_at),
            acquired_at=_datetime(acquired_at),
            content_sha256=content_sha256,
            source_url=source_url,
            claim_scopes=tuple(scopes),
        )

    def allows_claim(self, claim_domain: str) -> bool:
        normalized = _text(claim_domain)
        return any(item.claim_domain == normalized for item in self.claim_scopes)


class GuidelineBasis(BaseModel):
    """监管指南的一条版本化、可定位使用依据。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    guideline_series_id: str
    guideline_version_id: str
    jurisdiction: str
    agency: str
    document_id: str
    title: str
    guidance_status: Literal["draft", "final"]
    version_date: date
    population_context: str
    development_context: str
    source_url: str
    locator: EvidenceLocator
    content_sha256: str
    captured_at: datetime
    lifecycle_status: Literal["active", "superseded", "withdrawn"]
    supersedes_version_ids: tuple[str, ...] = ()
    superseded_by_version_id: str | None = None
    withdrawn_at: date | None = None
    can_drive_current_default: bool

    @field_validator(
        "guideline_series_id",
        "guideline_version_id",
        "jurisdiction",
        "agency",
        "document_id",
        "title",
        "population_context",
        "development_context",
        "source_url",
    )
    @classmethod
    def _guideline_text_is_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("content_sha256")
    @classmethod
    def _guideline_sha256(cls, value: str) -> str:
        if _SHA256.fullmatch(value) is None:
            raise ValueError("指南内容摘要必须是小写 SHA-256")
        return value

    @field_validator("captured_at")
    @classmethod
    def _captured_at_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("指南采集时间必须包含明确时区")
        return value

    @model_validator(mode="after")
    def _lifecycle_is_consistent(self) -> GuidelineBasis:
        expected = self.guidance_status == "final" and self.lifecycle_status == "active"
        if self.can_drive_current_default != expected:
            raise ValueError("指南当前默认状态与草案/生命周期不一致")
        if self.lifecycle_status == "superseded" and not self.superseded_by_version_id:
            raise ValueError("已替代指南必须指向替代版本")
        if self.lifecycle_status != "superseded" and self.superseded_by_version_id:
            raise ValueError("只有已替代指南可设置替代版本")
        if self.lifecycle_status == "withdrawn" and self.withdrawn_at is None:
            raise ValueError("已撤回指南必须保存撤回日期")
        if self.lifecycle_status != "withdrawn" and self.withdrawn_at is not None:
            raise ValueError("未撤回指南不得设置撤回日期")
        return self

    @classmethod
    def create(
        cls,
        *,
        jurisdiction: str,
        agency: str,
        document_id: str,
        title: str,
        guidance_status: Literal["draft", "final"],
        version_date: str,
        population_context: str,
        development_context: str,
        source_url: str,
        locator_label: str,
        locator_page: int,
        content_sha256: str,
        captured_at: str,
        lifecycle_status: Literal["active", "superseded", "withdrawn"],
        supersedes_version_ids: tuple[str, ...] = (),
        superseded_by_version_id: str | None = None,
        withdrawn_at: str | None = None,
    ) -> GuidelineBasis:
        jurisdiction = _text(jurisdiction).upper()
        agency = _text(agency)
        document_id = _text(document_id)
        series_id = stable_id("guideline-series", jurisdiction, agency, document_id)
        parsed_version_date = date.fromisoformat(version_date)
        version_id = stable_id(
            "guideline-version",
            series_id,
            parsed_version_date.isoformat(),
            content_sha256,
        )
        return cls(
            guideline_series_id=series_id,
            guideline_version_id=version_id,
            jurisdiction=jurisdiction,
            agency=agency,
            document_id=document_id,
            title=title,
            guidance_status=guidance_status,
            version_date=parsed_version_date,
            population_context=population_context,
            development_context=development_context,
            source_url=source_url,
            locator=EvidenceLocator(
                document_role=f"{agency} 指南",
                page=locator_page,
                paragraph=locator_label,
                url=source_url,
            ),
            content_sha256=content_sha256,
            captured_at=_datetime(captured_at),
            lifecycle_status=lifecycle_status,
            supersedes_version_ids=tuple(
                dict.fromkeys(_text(item) for item in supersedes_version_ids)
            ),
            superseded_by_version_id=(
                None if superseded_by_version_id is None else _text(superseded_by_version_id)
            ),
            withdrawn_at=None if withdrawn_at is None else date.fromisoformat(withdrawn_at),
            can_drive_current_default=(
                guidance_status == "final" and lifecycle_status == "active"
            ),
        )


def select_current_guideline_basis(
    guidelines: tuple[GuidelineBasis, ...], *, jurisdiction: str, population_context: str
) -> tuple[GuidelineBasis, ...]:
    validate_guideline_lineage(guidelines)
    target_jurisdiction = _text(jurisdiction).upper()
    target_population = _text(population_context)
    current = tuple(
        item
        for item in guidelines
        if item.jurisdiction == target_jurisdiction
        and item.population_context == target_population
        and item.can_drive_current_default
    )
    return tuple(sorted(current, key=lambda item: (item.version_date, item.title), reverse=True))


def validate_guideline_lineage(guidelines: tuple[GuidelineBasis, ...]) -> None:
    by_version = {item.guideline_version_id: item for item in guidelines}
    if len(by_version) != len(guidelines):
        raise ValueError("指南版本标识不得重复")
    current_by_series: dict[str, list[str]] = {}
    for item in guidelines:
        if item.can_drive_current_default:
            current_by_series.setdefault(item.guideline_series_id, []).append(
                item.guideline_version_id
            )
    if any(len(version_ids) > 1 for version_ids in current_by_series.values()):
        raise ValueError("同一指南系列存在多个当前版本")
    for item in guidelines:
        if item.lifecycle_status == "superseded":
            successor_id = item.superseded_by_version_id
            if successor_id not in by_version:
                raise ValueError("已替代指南指向不存在的后续版本")
            successor = by_version[successor_id]
            if item.guideline_version_id not in successor.supersedes_version_ids:
                raise ValueError("指南替代关系必须双向一致")
        for predecessor_id in item.supersedes_version_ids:
            if predecessor_id not in by_version:
                raise ValueError("指南版本引用了不存在的历史版本")
            predecessor = by_version[predecessor_id]
            if (
                predecessor.lifecycle_status != "superseded"
                or predecessor.superseded_by_version_id != item.guideline_version_id
            ):
                raise ValueError("指南替代关系必须双向一致")

    visited: set[str] = set()
    active_path: set[str] = set()

    def visit(version_id: str) -> None:
        if version_id in active_path:
            raise ValueError("指南替代关系存在循环")
        if version_id in visited:
            return
        active_path.add(version_id)
        successor_id = by_version[version_id].superseded_by_version_id
        if successor_id is not None:
            visit(successor_id)
        active_path.remove(version_id)
        visited.add(version_id)

    for version_id in by_version:
        visit(version_id)
