"""Bound model proposals for candidate B views; not an independent acceptance receipt."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter, field_validator, model_validator

from ci_workflow.reports.b.semantic_contract import (
    ClinicalConstructObservation,
    SemanticAdjudicationReceipt,
    compare_clinical_constructs,
    semantic_value_is_unknown,
    time_policy_identity,
)

SEMANTIC_POLICY_VERSION = "b-candidate-hard-axes-v2"
_SOURCE_JSON = TypeAdapter(Any)


def semantic_source_digest(value: Any) -> str:
    """Bind the complete supplied fact, including locator and derivation metadata.

    This binds declared provenance; it does not attest that external bytes were
    retrieved or independently verified. Those remain acquisition/review gates.
    """
    return hashlib.sha256(json.dumps(
        _SOURCE_JSON.dump_python(value, mode="json"), ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


class SemanticGroupingProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1"] = "1"
    status: Literal["proposal"] = "proposal"
    proposal_id: str
    row_ids: tuple[str, str]
    row_digests: tuple[str, str]
    compatible: bool
    time_window_compatible: bool = False
    producer_id: str
    rationale_zh: str

    @field_validator("proposal_id", "producer_id", "rationale_zh")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("语义提案标识与理由不能为空")
        return value.strip()

    @model_validator(mode="after")
    def binding(self) -> SemanticGroupingProposal:
        if len(set(self.row_ids)) != 2 or any(not value.strip() for value in self.row_ids):
            raise ValueError("语义提案必须绑定两个不同观察")
        if any(len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
               for value in self.row_digests):
            raise ValueError("语义提案必须绑定完整观察摘要")
        return self


class ApprovedSemanticMerge(BaseModel):
    """已获独立复核签发的正向语义归并。

    候选 :class:`SemanticGroupingProposal` 自身不再授权合并；正向归并
    必须同时携带绑定同一观察对、裁决为 compatible 的独立复核回执。
    否决方向不需要签发（保守方向不受模型自信影响）。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1"] = "1"
    merge_id: str
    proposal: SemanticGroupingProposal
    receipt: SemanticAdjudicationReceipt

    @field_validator("merge_id")
    @classmethod
    def _merge_id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("归并标识不能为空")
        return value.strip()

    @model_validator(mode="after")
    def _receipt_binds_proposal(self) -> ApprovedSemanticMerge:
        # 重新走完整校验，阻止 model_copy(update=...) 绕过构造期约束。
        proposal = SemanticGroupingProposal.model_validate(
            self.proposal.model_dump(mode="json")
        )
        receipt = SemanticAdjudicationReceipt.model_validate(
            self.receipt.model_dump(mode="json")
        )
        if not proposal.compatible:
            raise ValueError("否决提案无需签发合并；正向归并提案必须为兼容裁决")
        if receipt.decision != "compatible":
            raise ValueError("独立复核裁决与正向归并不一致")
        if tuple(sorted(receipt.observation_ids)) != tuple(sorted(proposal.row_ids)):
            raise ValueError("回执观察对与提案观察对不一致")
        return self


def semantic_row_digest(row: Mapping[str, Any]) -> str:
    """Bind policy, complete supplied fact digest, and projected clinical values."""
    payload = {key: value for key, value in row.items() if not key.startswith("_")}
    payload["_source_binding"] = row.get("_source_binding")
    # 时间政策身份入摘要：政策升级使历史裁决摘要失效，必须重新研究和复核。
    payload["_semantic_policy"] = f"{SEMANTIC_POLICY_VERSION}+time:{time_policy_identity()}"
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def _observation(row: Mapping[str, Any]) -> ClinicalConstructObservation:
    return ClinicalConstructObservation.model_validate({
        "observation_id": row["row_id"],
        "clinical_construct": row.get("clinical_concept", "not_reported"),
        "definition": row.get("semantic_definition", "not_reported"),
        "direction": row.get("semantic_direction", "not_reported"),
        "unit": row.get("unit", "not_reported"),
        "estimand": row.get("semantic_estimand", "not_reported"),
        "denominator": row.get("semantic_denominator", "not_reported"),
        "analysis_set": row.get("semantic_analysis_set", "not_reported"),
        "analysis_form": row.get("semantic_analysis_form", "not_reported"),
        "instrument_or_scale": row.get("semantic_instrument_or_scale", "not_reported"),
        "actual_timepoint": row.get("actual_timepoint"),
        "actual_timepoint_unit": row.get("actual_timepoint_unit"),
    })


def proposed_semantic_buckets(
    buckets: Sequence[Sequence[tuple[dict[str, Any], Any]]],
    proposals: Sequence[SemanticGroupingProposal],
    *, descriptive_only: bool = False,
    approved_merges: Sequence[ApprovedSemanticMerge] = (),
) -> tuple[tuple[tuple[dict[str, Any], Any], ...], ...]:
    """Complete-link grouping: no transitive compatibility and no dropped observations.

    Same-trial descriptive groups remain available. Every cross-trial pair passes
    the deterministic guard, including pairs for which no proposal was supplied.
    Positive (model-asserted) merges additionally require an independently
    reviewed :class:`ApprovedSemanticMerge`; candidate proposals alone
    contribute vetoes and guard inputs, never merges.
    """
    rows: dict[str, tuple[dict[str, Any], Any]] = {}
    origin: dict[str, int] = {}
    for index, bucket in enumerate(buckets):
        for item in bucket:
            row_id = str(item[0]["row_id"])
            if row_id in rows:
                raise ValueError("语义视图观察标识重复")
            rows[row_id] = item
            origin[row_id] = index
    pairs: dict[frozenset[str], SemanticGroupingProposal] = {}
    for proposal in proposals:
        proposal = SemanticGroupingProposal.model_validate(proposal.model_dump(mode="json"))
        for row_id, digest in zip(proposal.row_ids, proposal.row_digests, strict=True):
            if row_id in rows and semantic_row_digest(rows[row_id][0]) != digest:
                raise ValueError("语义提案观察摘要不一致，必须重新研究和复核")
        if not set(proposal.row_ids).issubset(rows):
            continue  # Another physical page may own the other observation.
        if descriptive_only and proposal.compatible:
            raise ValueError("该域目前仅支持描述性展示，不能接受正向语义裁决提案")
        key = frozenset(proposal.row_ids)
        if key in pairs:
            raise ValueError("同一观察对存在重复语义提案")
        pairs[key] = proposal
    approved_pairs: dict[frozenset[str], ApprovedSemanticMerge] = {}
    for merge in approved_merges:
        merge = ApprovedSemanticMerge.model_validate(merge.model_dump(mode="json"))
        if not set(merge.proposal.row_ids).issubset(rows):
            continue  # Page-local projection; the full pool owns the other row.
        for row_id, digest in zip(
            merge.proposal.row_ids, merge.proposal.row_digests, strict=True
        ):
            if row_id in rows and semantic_row_digest(rows[row_id][0]) != digest:
                raise ValueError("已批准归并的观察摘要不一致，必须重新研究和复核")
        if descriptive_only:
            raise ValueError("描述性域不接受正向语义归并")
        key = frozenset(merge.proposal.row_ids)
        if key in approved_pairs:
            raise ValueError("同一观察对存在重复的已批准归并")
        approved_pairs[key] = merge

    def compatible(left_id: str, right_id: str) -> bool:
        proposal = pairs.get(frozenset((left_id, right_id)))
        if (proposal is not None and proposal.compatible
                and frozenset((left_id, right_id)) not in approved_pairs):
            # 候选正向提案未经独立复核签发：不作为合并依据，
            # 回退到确定性路径（同桶 + 守卫）或维持分离。
            proposal = None
        if proposal is None:
            if origin[left_id] != origin[right_id]:
                return False
            if descriptive_only:
                return True
            left_row, right_row = rows[left_id][0], rows[right_id][0]
            if (left_row.get("trial_id") and
                    left_row.get("trial_id") == right_row.get("trial_id") and
                    left_row.get("product_id") == right_row.get("product_id")):
                return True  # Within-trial longitudinal description, not cross-trial equivalence.
        elif not proposal.compatible:
            return False
        try:
            left, right = _observation(rows[left_id][0]), _observation(rows[right_id][0])
        except ValueError:
            return False
        if any(semantic_value_is_unknown(value) for value in (
            left.clinical_construct, left.definition, right.clinical_construct, right.definition,
        )):
            return False
        if proposal is None:
            return compare_clinical_constructs(left, right).compatible
        if left.timepoint_weeks != right.timepoint_weeks and not proposal.time_window_compatible:
            return False
        # Only wording is proposed equivalent. Original rows remain unchanged.
        right_for_guard = right.model_copy(update={
            "clinical_construct": left.clinical_construct, "definition": left.definition,
        })
        return compare_clinical_constructs(left, right_for_guard).compatible

    groups: list[list[str]] = []
    for row_id in sorted(rows):
        for group in groups:
            if all(compatible(row_id, existing) for existing in group):
                group.append(row_id)
                break
        else:
            groups.append([row_id])
    return tuple(tuple(rows[row_id] for row_id in group) for group in groups)
