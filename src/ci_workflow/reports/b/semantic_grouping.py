"""Bound model proposals for candidate B views; not an independent acceptance receipt."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, TypeAdapter, field_validator, model_validator

from ci_workflow.reports.b.semantic_contract import (
    ClinicalConstructObservation,
    SemanticAdjudicationReceipt,
    compare_clinical_constructs,
    semantic_time_order,
    semantic_value_is_unknown,
    source_domain_conflicts,
    time_policy_identity,
)

SEMANTIC_POLICY_VERSION = "b-candidate-hard-axes-v8"
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


class _RowSemantics(NamedTuple):
    """One row's per-invocation guard inputs, reusable only by clinical context.

    ``identity`` deliberately excludes the observation id, so rows sharing a
    valid clinical context take one deterministic guard decision. The records
    live in caches local to a single :func:`proposed_semantic_buckets` call.
    """

    observation: ClinicalConstructObservation | None
    order: tuple[str, float, float, str]
    identity: tuple[Any, ...]
    supporting: tuple[tuple[bool, str | None], ...]
    wording_unknown: bool


_MISSING = object()


def _domain_key(row_id: str, value: Any) -> Any:
    """Hashable stand-in for ``_domain`` equality; unknown stamps stay row-specific."""
    if value is _MISSING or value is None or isinstance(value, str):
        return value
    # Only equality matters here. A non-primitive stamp cannot be hashed without
    # risking an equality mismatch, so it just disables cross-row reuse.
    return ("row-specific-domain", row_id)


def _supporting_state(row: Mapping[str, Any]) -> tuple[tuple[bool, str | None], ...]:
    """``source_domain``/``source_metric`` as (unknown, known text) pairs."""
    state: list[tuple[bool, str | None]] = []
    for axis in ("source_domain", "source_metric"):
        value = row.get(axis)
        unknown = semantic_value_is_unknown(value)
        state.append((unknown, None if unknown or not isinstance(value, str) else value))
    return tuple(state)


def _supporting_axis_conflict(
    left: tuple[tuple[bool, str | None], ...],
    right: tuple[tuple[bool, str | None], ...],
) -> bool:
    """Replay ``left_axis != right_axis``; unknown or missing text is always a veto."""
    return any(
        left_unknown or right_unknown or left_text != right_text
        for (left_unknown, left_text), (right_unknown, right_text) in zip(
            left, right, strict=True,
        )
    )


def _observation_context(
    observation: ClinicalConstructObservation, rule_id: str,
) -> tuple[Any, ...]:
    """Clinical context every ``compare_clinical_constructs`` read depends on.

    Row identity is excluded: two observations with equal contexts take
    identical deterministic decisions, so one decision covers the whole context
    pair inside a single invocation.
    """
    return (
        observation.clinical_construct, observation.definition, observation.direction,
        observation.unit, observation.estimand, observation.denominator,
        observation.analysis_set, observation.analysis_form,
        observation.instrument_or_scale, observation.actual_timepoint,
        str(observation.actual_timepoint_unit), rule_id,
    )


def _row_semantics(row_id: str, row: Mapping[str, Any]) -> _RowSemantics:
    """Validate one row once and capture everything the pair guard reads from it."""
    try:
        observation = _observation(row)
    except ValueError:
        observation = None
    supporting = _supporting_state(row)
    domain_key = _domain_key(row_id, row.get("_domain", _MISSING))
    if observation is None:
        return _RowSemantics(
            observation=None, supporting=supporting,
            wording_unknown=False,
            order=("unresolved", float("inf"), float("inf"), row_id),
            identity=(domain_key, supporting, None, False),
        )
    wording_unknown = (
        semantic_value_is_unknown(observation.clinical_construct)
        or semantic_value_is_unknown(observation.definition)
    )
    rule_id, distance, weeks = semantic_time_order(observation)
    return _RowSemantics(
        observation=observation, supporting=supporting,
        wording_unknown=wording_unknown,
        order=(rule_id, distance, weeks, row_id),
        identity=(
            domain_key, supporting,
            _observation_context(observation, rule_id), wording_unknown,
        ),
    )


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

    Inside one invocation each row is validated once and one deterministic
    decision is reused for every pair of identical clinical contexts. The
    receipt-bearing pair's own effective state stays in the reuse key, so
    pair-specific acceptance is never applied to a pair without its receipt.
    Nothing is cached across invocations, and no guard, policy, or row is
    added, dropped, or relaxed.
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

    semantics: dict[str, _RowSemantics] = {}

    def semantics_of(row_id: str) -> _RowSemantics:
        cached = semantics.get(row_id)
        if cached is None:
            cached = _row_semantics(row_id, rows[row_id][0])
            semantics[row_id] = cached
        return cached

    digests: dict[str, str] = {}

    def digest_of(row_id: str) -> str:
        if row_id not in digests:
            digests[row_id] = semantic_row_digest(rows[row_id][0])
        return digests[row_id]

    pairs: dict[frozenset[str], SemanticGroupingProposal] = {}
    for proposal in proposals:
        proposal = SemanticGroupingProposal.model_validate(proposal.model_dump(mode="json"))
        for row_id, digest in zip(proposal.row_ids, proposal.row_digests, strict=True):
            if row_id in rows and digest_of(row_id) != digest:
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
            if row_id in rows and digest_of(row_id) != digest:
                raise ValueError("已批准归并的观察摘要不一致，必须重新研究和复核")
        if descriptive_only:
            raise ValueError("描述性域不接受正向语义归并")
        key = frozenset(merge.proposal.row_ids)
        if key in approved_pairs:
            raise ValueError("同一观察对存在重复的已批准归并")
        approved_pairs[key] = merge

    decisions: dict[tuple[Any, ...], bool] = {}
    conflict_calls: dict[tuple[str, str], bool] = {}

    def row_conflict(row_id: str, domain: str) -> bool:
        """Memoize the pair-level source-domain guard for one (row, domain) input.

        The guard is pure in those two arguments, so a repeated context pair may
        reuse it, while the left row's own domain text still drives the right
        row's check exactly as before.
        """
        key = (row_id, domain)
        if key not in conflict_calls:
            conflict_calls[key] = source_domain_conflicts(rows[row_id][0], domain)
        return conflict_calls[key]

    def decide_pair(
        left_id: str, right_id: str, left: _RowSemantics, right: _RowSemantics,
        proposal: SemanticGroupingProposal | None,
        left_conflict: bool, right_conflict: bool,
    ) -> bool:
        left_row, right_row = rows[left_id][0], rows[right_id][0]
        if left_row.get("_domain") != right_row.get("_domain"):
            return False
        if left_conflict or right_conflict:
            return False
        if (
            (left_row.get("_domain") == "supporting" or right_row.get("_domain") == "supporting")
            # Wording equivalence cannot turn different scientific domains or
            # metrics into the same observation, even with a positive receipt.
            and _supporting_axis_conflict(left.supporting, right.supporting)
        ):
            return False
        if proposal is None:
            if descriptive_only:
                return origin[left_id] == origin[right_id]
        elif not proposal.compatible:
            return False
        left_observation, right_observation = left.observation, right.observation
        if left_observation is None or right_observation is None:
            return False
        if left.wording_unknown or right.wording_unknown:
            return False
        if proposal is None:
            return compare_clinical_constructs(left_observation, right_observation).compatible
        if (left_observation.timepoint_weeks != right_observation.timepoint_weeks
                and not proposal.time_window_compatible):
            return False
        # Only wording is proposed equivalent. Original rows remain unchanged.
        right_for_guard = right_observation.model_copy(update={
            "clinical_construct": left_observation.clinical_construct,
            "definition": left_observation.definition,
        })
        return compare_clinical_constructs(left_observation, right_for_guard).compatible

    def compatible(left_id: str, right_id: str) -> bool:
        left, right = semantics_of(left_id), semantics_of(right_id)
        pair = frozenset((left_id, right_id))
        proposal = pairs.get(pair)
        if proposal is not None and proposal.compatible and pair not in approved_pairs:
            # 候选正向提案未经独立复核签发：不作为合并依据，
            # 回退到确定性路径（同桶 + 守卫）或维持分离。
            proposal = None
        if proposal is None:
            state: Any = "deterministic"
        elif proposal.compatible:
            state = ("approved", proposal.time_window_compatible)
        else:
            state = "veto"
        # 与旧实现一致：右行的来源守卫使用左行的域串，因此两者都进复用键。
        left_domain = str(rows[left_id][0].get("_domain", ""))
        left_conflict = row_conflict(left_id, left_domain)
        right_conflict = row_conflict(right_id, left_domain)
        cache_key = (
            left.identity, right.identity, left_conflict, right_conflict, state,
            origin[left_id] == origin[right_id],
        )
        cached = decisions.get(cache_key)
        if cached is not None:
            return cached
        decided = decide_pair(
            left_id, right_id, left, right, proposal, left_conflict, right_conflict,
        )
        decisions[cache_key] = decided
        return decided

    def clinical_order(row_id: str) -> tuple[str, float, float, str]:
        return semantics_of(row_id).order

    groups: list[list[str]] = []
    for row_id in sorted(rows, key=clinical_order):
        for group in groups:
            if all(compatible(row_id, existing) for existing in group):
                group.append(row_id)
                break
        else:
            groups.append([row_id])
    return tuple(tuple(rows[row_id] for row_id in group) for group in groups)
