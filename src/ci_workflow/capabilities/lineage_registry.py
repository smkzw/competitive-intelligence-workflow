from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from ci_workflow.capabilities.extraction_normalization import VerifiedEvidenceFragment
from ci_workflow.domain.enums import FactReviewState
from ci_workflow.domain.facts import AtomicFactVersion

_LINEAGE_REGISTRY_TOKEN = object()


class ScientificLineageRegistry(BaseModel):
    """声明生成前使用的已重开片段与已接受事实注册表。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verified_fragments: tuple[VerifiedEvidenceFragment, ...] = ()
    accepted_facts: tuple[AtomicFactVersion, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _requires_controlled_construction(
        cls, value: object, info: ValidationInfo
    ) -> object:
        if (info.context or {}).get("lineage_registry_token") is not _LINEAGE_REGISTRY_TOKEN:
            raise ValueError("科学证据注册表只能由项目真源库验真片段创建")
        return value

    @model_validator(mode="after")
    def _entries_are_unique_and_consistent(self) -> ScientificLineageRegistry:
        fragment_ids = tuple(
            item.fragment.fragment_id for item in self.verified_fragments
        )
        if len(set(fragment_ids)) != len(fragment_ids):
            raise ValueError("科学证据注册表中的片段不得重复")
        fact_ids = tuple(item.fact_version_id for item in self.accepted_facts)
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("科学证据注册表中的事实版本不得重复")
        if any(
            item.review_state is not FactReviewState.ACCEPTED
            for item in self.accepted_facts
        ):
            raise ValueError("科学证据注册表只能保存已接受事实")
        registered_fragments = set(fragment_ids)
        if any(
            not set(fact.source_fragment_ids) <= registered_fragments
            for fact in self.accepted_facts
        ):
            raise ValueError("已接受事实引用了尚未重开的证据片段")
        return self

    @classmethod
    def empty(cls) -> ScientificLineageRegistry:
        return cls.model_validate(
            {"verified_fragments": (), "accepted_facts": ()},
            context={"lineage_registry_token": _LINEAGE_REGISTRY_TOKEN},
        )

    @classmethod
    def from_verified_fragments(
        cls,
        fragments: tuple[VerifiedEvidenceFragment, ...],
    ) -> ScientificLineageRegistry:
        return cls._from_state(fragments, ())

    @classmethod
    def _from_state(
        cls,
        fragments: tuple[VerifiedEvidenceFragment, ...],
        accepted_facts: tuple[AtomicFactVersion, ...],
    ) -> ScientificLineageRegistry:
        return cls.model_validate(
            {
                "verified_fragments": fragments,
                "accepted_facts": accepted_facts,
            },
            context={"lineage_registry_token": _LINEAGE_REGISTRY_TOKEN},
        )

    @classmethod
    def from_state(
        cls,
        fragments: tuple[VerifiedEvidenceFragment, ...],
        accepted_facts: tuple[AtomicFactVersion, ...],
    ) -> ScientificLineageRegistry:
        """公开重建入口：由已重验片段与已接受事实重建注册表（同一受控构造）。"""
        return cls._from_state(fragments, accepted_facts)

    def with_revalidated_content(
        self,
        *,
        fragments: tuple[VerifiedEvidenceFragment, ...],
        accepted_facts: tuple[AtomicFactVersion, ...],
    ) -> ScientificLineageRegistry:
        """以重新验证后的片段/事实替换注册表内容，其余身份不变。"""
        return ScientificLineageRegistry._from_state(fragments, accepted_facts)

    @property
    def verified_fragment_ids(self) -> frozenset[str]:
        return frozenset(
            item.fragment.fragment_id for item in self.verified_fragments
        )

    def register_verified_fragment(
        self, fragment: VerifiedEvidenceFragment
    ) -> ScientificLineageRegistry:
        existing = {
            item.fragment.fragment_id: item for item in self.verified_fragments
        }
        prior = existing.get(fragment.fragment.fragment_id)
        if prior is not None:
            if prior != fragment:
                raise ValueError("同一证据片段对应了不同的重开内容")
            return self
        return ScientificLineageRegistry._from_state(
            (*self.verified_fragments, fragment),
            self.accepted_facts,
        )

    def accept_candidate_fact(
        self, fact: AtomicFactVersion
    ) -> tuple[ScientificLineageRegistry, AtomicFactVersion]:
        if fact.review_state is not FactReviewState.CANDIDATE:
            raise ValueError("只有候选事实可通过证据注册表接受")
        verified_by_id = {
            item.fragment.fragment_id: item for item in self.verified_fragments
        }
        if not set(fact.source_fragment_ids) <= set(verified_by_id):
            raise ValueError("候选事实引用了尚未重开的证据片段")
        primary = verified_by_id[fact.primary_fragment_id]
        if fact.raw_value != primary.reopened_original_text:
            raise ValueError("候选事实原始表达与主要重开片段不一致")
        accepted = AtomicFactVersion.model_validate(
            {**fact.model_dump(), "review_state": FactReviewState.ACCEPTED}
        )
        return (
            ScientificLineageRegistry._from_state(
                self.verified_fragments,
                (*self.accepted_facts, accepted),
            ),
            accepted,
        )

    def assert_registered_facts(
        self, facts: tuple[AtomicFactVersion, ...]
    ) -> None:
        accepted_by_id = {
            item.fact_version_id: item for item in self.accepted_facts
        }
        for fact in facts:
            registered = accepted_by_id.get(fact.fact_version_id)
            if registered is None or registered != fact:
                raise ValueError("声明引用了未在科学证据注册表接受的事实")

    def assert_registered_fact_version_ids(
        self, fact_version_ids: tuple[str, ...]
    ) -> None:
        registered_ids = {item.fact_version_id for item in self.accepted_facts}
        if not set(fact_version_ids) <= registered_ids:
            raise ValueError("声明引用了未在科学证据注册表接受的事实")


def _canonical_json(value: object) -> bytes:
    """规范 JSON：排序键、紧凑、中文不转义；与快照存储同一算法。"""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def compute_scientific_content_digest(registry: ScientificLineageRegistry) -> str:
    """科学证据内容摘要：每个已验证片段的完整内容 + 每条已接受事实。

    排序稳定（片段按 fragment_id、事实按 fact_version_id）。对每个
    ``VerifiedEvidenceFragment`` 纳入完整规范序列化：完整 ``fragment``
    （含定位/原文/摘要/创建时间）、完整 ``source_version``（含来源 ID、
    内容摘要/路径/媒体类型、获取/发布/生效/首次披露日期、定位）、以及
    ``reopened_original_text``；事实完整纳入。任何仅改来源版本内容或审计
    字段（保留全部 ID 与 manifest）的同步伪造都会改变摘要；写入与验证共用
    本实现。
    """
    fragments: list[dict[str, object]] = [
        {
            "fragment": item.fragment.model_dump(mode="json"),
            "source_version": item.source_version.model_dump(mode="json"),
            "reopened_original_text": item.reopened_original_text,
        }
        for item in registry.verified_fragments
    ]
    fragments_sorted = sorted(
        fragments,
        key=lambda entry: str(entry["fragment"]["fragment_id"]),  # type: ignore[index]
    )
    facts: list[dict[str, object]] = [
        fact.model_dump(mode="json") for fact in registry.accepted_facts
    ]
    facts_sorted = sorted(
        facts,
        key=lambda entry: str(entry["fact_version_id"]),
    )
    digest = hashlib.sha256(
        _canonical_json({"fragments": fragments_sorted, "facts": facts_sorted})
    )
    return digest.hexdigest()
