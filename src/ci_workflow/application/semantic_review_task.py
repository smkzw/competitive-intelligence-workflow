"""P3.7 生产者：语义归并复核工作项的发射与提交验证。

对选择与消费端分桶语义一致（Reviewer-E 2026-09-11 终审修订）：
``build_semantic_review_task`` 以渲染端相同的初始分桶为输入，只在同域
内成对；同试验同产品对、未知语义对、硬冲突对跳过；**同桶且确定性可比
的对跳过（消费端会自动合并）**；跨桶近窗对与仅措辞差异对进入工作项。
``validate_semantic_review_submission`` 绑定任务摘要与当前观察、复验
候选资格、执行消费端同等的最终时间窗守卫；伪造、陈旧、任务外、自审
一律拒绝。渲染端合同见 :mod:`ci_workflow.reports.b.semantic_grouping`。
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from ci_workflow.reports.b.semantic_contract import (
    compare_clinical_constructs,
    semantic_value_is_unknown,
    time_policy_identity,
)
from ci_workflow.reports.b.semantic_grouping import (
    SEMANTIC_POLICY_VERSION,
    ApprovedSemanticMerge,
    _observation,
    semantic_row_digest,
)


def semantic_policy_identity() -> str:
    """语义+时间政策的组合身份，供工作项与回执审计绑定。"""
    return f"{SEMANTIC_POLICY_VERSION}+time:{time_policy_identity()}" 

Record = tuple[dict[str, Any], Any]


class SemanticReviewPair(BaseModel):
    """一对需要独立复核的跨试验观察；摘要绑定签发时的观察字节。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    row_ids: tuple[str, str]
    row_digests: tuple[str, str]
    trial_ids: tuple[str, str]
    definitions_zh: tuple[str, str]
    guard_verdict: Literal["undecided"] = "undecided"

    @model_validator(mode="after")
    def _pair_shape(self) -> SemanticReviewPair:
        if len(set(self.row_ids)) != 2:
            raise ValueError("语义复核对必须绑定两个不同观察")
        return self


class SemanticReviewTask(BaseModel):
    """宿主语义复核工作项；不是接受回执。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    task_id: str
    project_id: str
    policy_version: str
    pairs: tuple[SemanticReviewPair, ...]
    state: Literal["awaiting_host_review"] = "awaiting_host_review"
    next_action_zh: str = (
        "生产模型对每对观察给出兼容与否的提案与中文理由；由不同身份、不同会话"
        "的独立上下文复核后，按已批准归并结构（提案+复核回执）提交。提交摘要"
        "必须与工作项逐观察一致；模型与复核者不得为同一身份。"
    )

    @field_validator("task_id", "project_id", "policy_version")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("语义复核工作项标识不能为空")
        return normalized


def _same_trial_product(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_product = str(left.get("product_id") or "").strip()
    right_product = str(right.get("product_id") or "").strip()
    if not left_product or not right_product:
        return False  # 产品未知时不得推定同产品跳过裁决。
    return bool(
        left.get("trial_id")
        and left.get("trial_id") == right.get("trial_id")
        and left_product == right_product
    )


def _wording_unifiable(
    left_row: Mapping[str, Any], right_row: Mapping[str, Any]
) -> bool | None:
    """确定性守卫：True=措辞统一后可比（含近窗）；False=硬冲突；None=语义不完整。"""
    try:
        left = _observation(left_row)
        right = _observation(right_row)
    except ValueError:
        return None
    if any(semantic_value_is_unknown(value) for value in (
        left.clinical_construct, left.definition,
        right.clinical_construct, right.definition,
    )):
        return None
    if compare_clinical_constructs(left, right).compatible:
        return True
    unified = right.model_copy(update={
        "clinical_construct": left.clinical_construct,
        "definition": left.definition,
    })
    return compare_clinical_constructs(left, unified).compatible


def _base_compatible(
    left_row: Mapping[str, Any], right_row: Mapping[str, Any]
) -> bool:
    return compare_clinical_constructs(
        _observation(left_row), _observation(right_row),
    ).compatible


def _is_review_candidate(
    left_row: Mapping[str, Any],
    right_row: Mapping[str, Any],
    *,
    same_bucket: bool,
) -> bool:
    """发射与复验共用的候选判定，与消费端合并语义一致。"""
    if _same_trial_product(left_row, right_row):
        return False
    unifiable = _wording_unifiable(left_row, right_row)
    if unifiable is not True:
        return False  # 未知（保留描述性）或硬冲突（模型不可覆盖）。
    # 确定性可比且同桶 → 消费端自动合并，无需裁决。
    return not (same_bucket and _base_compatible(left_row, right_row))


def build_semantic_review_task(
    project_id: str,
    records: Sequence[Record],
    *,
    buckets: Sequence[Sequence[Record]],
) -> SemanticReviewTask:
    """从完整观察池与其初始分桶构建宿主语义复核工作项。

    ``buckets`` 必须是渲染端消费的同一初始分桶（科学分区/文本桶）；
    候选判定因此与消费端合并语义一致，不出现"裁了必被拒"或"应裁未裁"。
    """
    rows: dict[str, dict[str, Any]] = {}
    origin: dict[str, int] = {}
    domain: dict[str, str] = {}
    for index, bucket in enumerate(buckets):
        for row, _value in bucket:
            row_id = str(row["row_id"])
            if row_id in rows:
                raise ValueError("语义复核输入包含重复观察标识")
            rows[row_id] = row
            origin[row_id] = index
            domain[row_id] = str(row.get("_domain") or "")
    if len(rows) != len(records):
        raise ValueError("初始分桶未覆盖全部观察")

    pairs: list[SemanticReviewPair] = []
    ids = sorted(rows)
    for index, left_id in enumerate(ids):
        for right_id in ids[index + 1:]:
            if domain[left_id] != domain[right_id]:
                continue  # 跨域对不可能被消费端接受，不进入工作项。
            if not _is_review_candidate(
                rows[left_id], rows[right_id],
                same_bucket=origin[left_id] == origin[right_id],
            ):
                continue
            left, right = rows[left_id], rows[right_id]
            pairs.append(SemanticReviewPair(
                row_ids=(left_id, right_id),
                row_digests=(
                    semantic_row_digest(left), semantic_row_digest(right),
                ),
                trial_ids=(
                    str(left.get("trial_id") or ""), str(right.get("trial_id") or ""),
                ),
                definitions_zh=(
                    str(left.get("semantic_definition")
                        or left.get("original_definition") or ""),
                    str(right.get("semantic_definition")
                        or right.get("original_definition") or ""),
                ),
            ))
    task_id = f"semantic-review-{len(pairs)}-{ids[0][:12]}"
    return SemanticReviewTask(
        task_id=task_id,
        project_id=project_id,
        policy_version=semantic_policy_identity(),
        pairs=tuple(pairs),
    )


def validate_semantic_review_submission(
    payloads: Sequence[Mapping[str, Any] | ApprovedSemanticMerge],
    task: SemanticReviewTask,
    *,
    records: Sequence[Record],
    buckets: Sequence[Sequence[Record]],
) -> tuple[ApprovedSemanticMerge, ...]:
    """重验宿主提交的已批准归并；任何不一致或资格失效失败关闭。"""
    rows: dict[str, dict[str, Any]] = {}
    origin: dict[str, int] = {}
    for index, bucket in enumerate(buckets):
        for row, _value in bucket:
            origin[str(row["row_id"])] = index
    for row, _value in records:
        rows[str(row["row_id"])] = row

    expected = {frozenset(pair.row_ids): pair for pair in task.pairs}
    validated: list[ApprovedSemanticMerge] = []
    seen: set[frozenset[str]] = set()
    for payload in payloads:
        merge = (
            payload
            if isinstance(payload, ApprovedSemanticMerge)
            else ApprovedSemanticMerge.model_validate(payload)
        )
        # 边界整体重验，阻止 model_copy(update=...) 伪造绑定。
        merge = ApprovedSemanticMerge.model_validate(merge.model_dump(mode="json"))
        key = frozenset(merge.proposal.row_ids)
        if key not in expected:
            raise ValueError(f"提交了任务之外的观察对归并：{sorted(merge.proposal.row_ids)}")
        if key in seen:
            raise ValueError("同一观察对存在重复的已批准归并提交")
        seen.add(key)
        pair = expected[key]
        task_digests = dict(zip(pair.row_ids, pair.row_digests, strict=True))
        submitted = dict(zip(
            merge.proposal.row_ids, merge.proposal.row_digests, strict=True,
        ))
        if task_digests != submitted:
            raise ValueError("提交摘要与任务摘要不一致，任务已过期，必须重新研究和签发")
        for row_id, digest in submitted.items():
            if row_id not in rows:
                raise ValueError(f"提交引用当前观察池之外的观察：{row_id}")
            if semantic_row_digest(rows[row_id]) != digest:
                raise ValueError("已批准归并的观察摘要与当前观察不一致，必须重新研究和复核")
        left_id, right_id = merge.proposal.row_ids
        if not _is_review_candidate(
            rows[left_id], rows[right_id],
            same_bucket=origin.get(left_id) == origin.get(right_id),
        ):
            raise ValueError("观察已失去候选资格（硬冲突或已确定性可比），必须重新研究和签发")
        # 消费端同等最终守卫：时间窗不兼容的正向提交必然被拒，前置失败。
        left_obs = _observation(rows[left_id])
        right_obs = _observation(rows[right_id])
        if (left_obs.timepoint_weeks != right_obs.timepoint_weeks
                and not merge.proposal.time_window_compatible):
            raise ValueError("提案声明时间窗不兼容，不能作为正向归并提交")
        validated.append(merge)
    return tuple(validated)


def store_semantic_adjudications(
    project_root: Path,
    *,
    report: str,
    payload_digest: str,
    project_id: str,
    task_id: str,
    adjudications: Sequence[ApprovedSemanticMerge],
) -> Path:
    """把已验证裁决按项目/报告/载荷摘要绑定写入项目状态（原子替换）。"""
    import hashlib
    import json
    import os
    import tempfile
    from datetime import UTC, datetime

    record = {
        "schema_version": "1.0",
        "project_id": project_id,
        "report": report,
        "payload_sha256": payload_digest,
        "task_id": task_id,
        "stored_at": datetime.now(UTC).isoformat(),
        "adjudications": [
            merge.model_dump(mode="json") for merge in adjudications
        ],
    }
    path = project_root / "state/semantic-adjudications.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    digest = hashlib.sha256(encoded).hexdigest()
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=f".{digest[:8]}.tmp", dir=path.parent,
    )
    temporary = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return path


def load_semantic_adjudications_for_render(
    project_root: Path,
    *,
    report: str,
    data_path: Path,
    project_id: str,
) -> tuple[ApprovedSemanticMerge, ...]:
    """读取并核验渲染注入用的项目级语义裁决；绑定不一致失败关闭。"""
    import hashlib
    import json

    path = project_root / "state/semantic-adjudications.json"
    if not path.is_file():
        return ()
    if path.is_symlink():
        raise ValueError("项目级语义裁决状态必须是普通文件")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("report") != report:
        raise ValueError(f"项目级语义裁决绑定的报告不符：{record.get('report')!r}")
    if record.get("project_id") != project_id:
        raise ValueError("项目级语义裁决与当前项目合同不一致")
    payload_digest = hashlib.sha256(
        Path(data_path).read_bytes(),
    ).hexdigest()
    if record.get("payload_sha256") != payload_digest:
        raise ValueError(
            "载荷摘要与语义裁决绑定不一致；载荷已变化，必须重新发射与签发"
        )
    return tuple(
        ApprovedSemanticMerge.model_validate(item)
        for item in record.get("adjudications", ())
    )
