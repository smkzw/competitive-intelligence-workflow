"""门户疗效行→科学视图层的策略驱动分区适配。

渲染器消费本模块的分区作为跨试验可比性的唯一初始裁决来源：
命中版本化终点/时间窗政策的观察按 ``build_efficacy_views`` 的科学
分组进入兼容桶；缺少必要语义或未命中政策的观察保留给调用方的
描述性路径，不丢弃、不伪装可比。本模块不做任何呈现决策。
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ci_workflow.domain.evidence import EvidenceLocator
from ci_workflow.reports.b.contracts import (
    EndpointCompatibilityResult,
    EndpointDirection,
    EndpointObservation,
    match_endpoint_compatibility,
)
from ci_workflow.reports.b.efficacy import (
    EfficacyArmRole,
    EfficacyFactRow,
    build_efficacy_views,
)
from ci_workflow.reports.b.semantic_grouping import ApprovedSemanticMerge

Record = tuple[dict[str, Any], Any]


def _text(row: Mapping[str, object], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@dataclass(frozen=True)
class SciencePartition:
    """策略命中的科学分桶与未裁决观察。"""

    buckets: tuple[tuple[Record, ...], ...]
    bucket_keys: tuple[tuple[str, ...], ...]
    unmatched: tuple[Record, ...]
    difference_labels: Mapping[str, tuple[str, ...]]

    @property
    def matched_row_ids(self) -> frozenset[str]:
        return frozenset(
            str(row["row_id"]) for bucket in self.buckets for row, _ in bucket
        )


def _observation(row: Mapping[str, object]) -> EndpointObservation | None:
    direction_text = _text(row, "semantic_direction", "direction").lower()
    try:
        direction = EndpointDirection(direction_text)
    except ValueError:
        return None
    endpoint_id = _text(row, "original_endpoint", "endpoint_id", "clinical_concept")
    definition = _text(row, "semantic_definition", "original_definition")
    if not endpoint_id or not definition:
        return None
    timepoint = row.get("actual_timepoint")
    time_unit = _text(row, "actual_timepoint_unit")
    if timepoint is None or isinstance(timepoint, bool) or not time_unit:
        return None
    return EndpointObservation.model_validate(
        {
            "observation_id": str(row["row_id"]),
            "trial_id": _text(row, "trial_id") or "trial-unspecified",
            "endpoint_id": endpoint_id,
            "endpoint_definition": definition,
            "endpoint_role": _text(row, "endpoint_role", "role") or "not_classified",
            "unit": _text(row, "unit") or "unit-unspecified",
            "direction": direction.value,
            "analysis_form": _text(row, "analysis_form", "statistical_form_family")
            or "form-unspecified",
            "timepoint": timepoint,
            "time_unit": time_unit,
        }
    )


def _fact_row(
    row: Mapping[str, object],
    value: object,
    match: EndpointCompatibilityResult,
) -> tuple[EfficacyFactRow | None, tuple[str, ...]]:
    arm_role_text = _text(row, "arm_role").lower()
    try:
        arm_role = EfficacyArmRole(arm_role_text)
    except ValueError:
        return None, ("组别角色不支持疗效比较视图",)
    locator_raw = None
    if isinstance(value, Mapping):
        locator_raw = value.get("source_locator", value.get("locator"))
    if isinstance(locator_raw, EvidenceLocator):
        locator = locator_raw
    elif isinstance(locator_raw, Mapping):
        try:
            locator = EvidenceLocator.model_validate(locator_raw)
        except (TypeError, ValueError):
            locator = EvidenceLocator(document_role="registry", heading="登记结果")
    else:
        locator = EvidenceLocator(document_role="registry", heading="登记结果")
    assert match.compatibility_key is not None
    try:
        return EfficacyFactRow.model_validate(
            {
                "row_id": str(row["row_id"]),
                "source_row_id": str(row["row_id"]),
                "observation_id": str(row["row_id"]),
                "product_id": _text(row, "product_id") or "product-unspecified",
                "trial_id": _text(row, "trial_id") or "trial-unspecified",
                "endpoint_family_id": match.endpoint_rule_id,
                "endpoint_family_label_zh": None,
                "compatibility_key": match.compatibility_key,
                "original_endpoint": _text(
                    row, "original_endpoint", "endpoint_id", "clinical_concept"
                ),
                "original_definition": _text(
                    row, "semantic_definition", "original_definition"
                ),
                "endpoint_role": _text(row, "endpoint_role", "role") or "not_classified",
                "direction": match.observation.direction.value,
                "unit": match.observation.unit,
                "analysis_form": match.observation.analysis_form,
                "actual_timepoint": match.observation.timepoint,
                "actual_timepoint_unit": match.observation.time_unit,
                "analysis_population": _text(
                    row, "analysis_population", "population_context", "population"
                )
                or None,
                "arm_role": arm_role.value,
                "arm_id": _text(row, "group_id", "arm_id", "arm") or str(row["row_id"]),
                "arm_label": _text(row, "arm_label", "group", "arm") or "组别未列示",
                "value": row.get("numeric_value"),
                "numerator": row.get("numerator"),
                "denominator": row.get("denominator"),
                "compatibility_difference_labels_zh": match.difference_labels_zh,
                "source_version_id": _text(row, "source_version_id")
                or "portal-unspecified",
                "source_locator": {
                    "document_role": locator.document_role,
                    "field_path": locator.field_path,
                    "heading": locator.heading,
                    "page": locator.page,
                    "table": locator.table,
                    "row": locator.row,
                    "column": locator.column,
                    "paragraph": locator.paragraph,
                    "url": locator.url,
                },
            }
        ), ("科学事实行校验失败",)
    except (TypeError, ValueError):
        return None, ("科学事实行校验失败",)


def efficacy_science_partition(
    records: Sequence[Record],
) -> SciencePartition:
    """把门户疗效记录分为政策命中的科学桶与未裁决的描述性观察。"""

    fact_rows: list[EfficacyFactRow] = []
    by_row_id: dict[str, Record] = {}
    unmatched: list[Record] = []
    labels: dict[str, tuple[str, ...]] = {}
    for record in records:
        row, value = record
        row_id = str(row["row_id"])
        if row_id in by_row_id:
            raise ValueError(f"科学分区收到重复观察标识：{row_id}")
        by_row_id[row_id] = record
        observation = _observation(row)
        match = (
            None if observation is None else match_endpoint_compatibility(observation)
        )
        if match is None or match.compatibility_key is None:
            unmatched.append(record)
            labels[row_id] = (
                ("语义信息不完整",)
                if observation is None
                else match.difference_labels_zh  # type: ignore[union-attr]
            )
            continue
        fact, fact_label = _fact_row(row, value, match)
        if fact is None:
            unmatched.append(record)
            labels[row_id] = fact_label
            continue
        fact_rows.append(fact)
    if not fact_rows:
        return SciencePartition((), (), tuple(unmatched), labels)

    view_set = build_efficacy_views(fact_rows)
    buckets: list[tuple[Record, ...]] = []
    bucket_keys: list[tuple[str, ...]] = []
    seen: set[str] = set()
    for view in view_set.single_timepoint_views:
        members = tuple(
            by_row_id[row.row_id] for row in view.rows if row.row_id in by_row_id
        )
        if not members:
            continue
        buckets.append(members)
        key = view.compatibility_key or view.compatibility_keys[0]
        bucket_keys.append(
            (
                str(view.endpoint_family_id),
                "/".join(str(item) for item in key),
                str(view.actual_timepoint),
                str(view.actual_timepoint_unit),
            )
        )
        seen.update(row.row_id for row in view.rows)
    # ponytail: view 集合未覆盖的命中行按科学分组键的兜底桶；正常路径为空。
    leftover = tuple(
        by_row_id[row.row_id] for row in view_set.fact_rows if row.row_id not in seen
    )
    for record in leftover:
        buckets.append((record,))
        bucket_keys.append(("uncovered", str(record[0]["row_id"])))
    return SciencePartition(tuple(buckets), tuple(bucket_keys), tuple(unmatched), labels)


_POOL_DOMAINS: dict[str, str] = {
    "efficacy": "efficacy",
    "safety": "safety",
    "baseline": "baseline-overview",
    "disposition": "disposition-overview",
    "matrix": "efficacy-safety-matrix",
    "supporting": "subgroups-supporting-evidence",
}


def validate_full_pool_inputs(
    records: Sequence[Record],
    *,
    semantic_proposals: Sequence[Any],
    semantic_adjudications: Sequence[ApprovedSemanticMerge],
) -> None:
    """完整观察池的入口校验：域白名单、孤儿提案/归并、跨域、摘要绑定。"""
    from ci_workflow.reports.b.semantic_grouping import (
        SemanticGroupingProposal,
        semantic_row_digest,
    )

    seen: set[str] = set()
    by_domain: dict[str, dict[str, Any]] = {}
    for row, _value in records:
        row_id = str(row["row_id"])
        if row_id in seen:
            raise ValueError(f"完整观察池包含重复观察标识：{row_id}")
        seen.add(row_id)
        domain = str(row.get("_domain") or "").strip()
        if domain not in _POOL_DOMAINS:
            raise ValueError(f"完整观察池包含未支持域：{domain or '未标注'}")
        by_domain[row_id] = row

    for proposal in semantic_proposals:
        if not isinstance(proposal, SemanticGroupingProposal):
            continue
        missing = [rid for rid in proposal.row_ids if rid not in by_domain]
        if missing:
            raise ValueError(f"语义提案引用完整观察池之外的观察：{missing}")
        left, right = (by_domain[rid] for rid in proposal.row_ids)
        if left.get("_domain") != right.get("_domain"):
            raise ValueError("跨域语义提案不受支持，必须拆分研究问题")

    for merge in semantic_adjudications:
        # 边界整体重验，阻止 model_copy(update=...) 伪造的外层绑定。
        merge = ApprovedSemanticMerge.model_validate(merge.model_dump(mode="json"))
        missing = [rid for rid in merge.proposal.row_ids if rid not in by_domain]
        if missing:
            raise ValueError(f"已批准归并引用完整观察池之外的观察：{missing}")
        left_id, right_id = merge.proposal.row_ids
        left, right = by_domain[left_id], by_domain[right_id]
        if left.get("_domain") != right.get("_domain"):
            raise ValueError("跨域语义归并不受支持，必须拆分研究问题")
        if (semantic_row_digest(left) != merge.proposal.row_digests[0]
                or semantic_row_digest(right) != merge.proposal.row_digests[1]):
            raise ValueError("已批准归并的观察摘要与完整观察池不一致")


def adjudicate_comparable_membership(
    domain: str,
    records: Sequence[Record],
    *,
    bucket_key_fn: Any,
    semantic_proposals: Sequence[Any],
    semantic_adjudications: Sequence[ApprovedSemanticMerge],
) -> tuple[tuple[Record, ...], ...]:
    """跨试验可比域（efficacy/safety）的成员裁决唯一真源。

    桶构建键由调用方注入（渲染端展示语义键）；裁决语义——初始桶、
    候选否决、已批准归并、complete-link——全部在本科学层完成。
    返回按组内 row_id 排序的成员组。
    """
    from ci_workflow.reports.b.semantic_grouping import (
        SemanticGroupingProposal,
        proposed_semantic_buckets,
    )

    if domain not in {"efficacy", "safety"}:
        raise ValueError(f"不支持的跨试验裁决域：{domain}")
    proposals = tuple(
        item for item in semantic_proposals
        if isinstance(item, SemanticGroupingProposal)
    )
    if domain == "efficacy":
        partition = efficacy_science_partition(records)
        buckets: list[tuple[Record, ...]] = [
            tuple(bucket) for bucket in partition.buckets
        ]
        fallback: dict[Any, list[Record]] = {}
        for record in partition.unmatched:
            fallback.setdefault(bucket_key_fn(record[0]), []).append(record)
        buckets.extend(tuple(group) for group in fallback.values())
    else:
        keyed: dict[Any, list[Record]] = {}
        for record in records:
            keyed.setdefault(bucket_key_fn(record[0]), []).append(record)
        buckets = [tuple(group) for group in keyed.values()]

    merged = proposed_semantic_buckets(
        tuple(buckets), proposals, approved_merges=semantic_adjudications,
    )
    return tuple(
        tuple(sorted(group, key=lambda item: str(item[0]["row_id"])))
        for group in merged
    )
