"""Task 3.7 独立科学质控判定模型与审查输入包。

不可变、extra=forbid、确定性可摘要的判定模型；审查输入包只含
候选快照/事实/声明、标准、覆盖与证据/来源/定位引用；不含构建者
思维链、草稿、提示词、日志或任务上下文。

结论显式区分接受与否决处置：accepted 不得携带否决处置或阻断性问题；
veto 必须且只能声明 recoverable/exhausted 之一并携带至少一个阻断性问题。
结论的来源引用与精确定位必须与审查输入包逐字一致；问题的来源/片段
必须存在于已复核引用中。
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import ReportKind

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _not_blank(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


def _sha256_digest(value: str) -> str:
    """严格小写 SHA-256：非十六进制、大小写错误或长度错误一律拒绝。"""
    normalized = _not_blank(value)
    if _SHA256_RE.fullmatch(normalized) is None:
        raise ValueError("摘要必须是小写 SHA-256（64 位十六进制）")
    return normalized


def _has_chinese_context(value: str) -> bool:
    return _CJK_RE.search(value) is not None


def candidate_content_digest(snapshot: Any) -> str:
    """确定性计算候选快照内容摘要。"""
    if hasattr(snapshot, "model_dump"):
        return _sha256_hex(snapshot.model_dump(mode="json"))
    return _sha256_hex(snapshot)


# ─── 来源定位引用 ────────────────────────────────────────────────────────────


class LocatorDetail(BaseModel):
    """精确来源定位：字段路径、页、表、链接等。

    必须至少包含一个真实可检索维度（字段路径/标题/页/表/行/列/段落/链接），
    且该维度文本非空、页码 >= 1；仅有 document_role 不构成精确定位。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_role: str
    field_path: str | None = None
    heading: str | None = None
    page: int | None = Field(default=None, ge=1)
    table: str | None = None
    row: str | None = None
    column: str | None = None
    paragraph: str | None = None
    url: str | None = None

    @field_validator("document_role")
    @classmethod
    def _doc_role_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator(
        "field_path", "heading", "table", "row", "column", "paragraph", "url"
    )
    @classmethod
    def _dimension_text_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _not_blank(value)

    @model_validator(mode="after")
    def _has_precise_anchor(self) -> LocatorDetail:
        if not any(
            (
                self.field_path,
                self.heading,
                self.page,
                self.table,
                self.row,
                self.column,
                self.paragraph,
                self.url,
            )
        ):
            raise ValueError("来源定位必须包含字段、页、表、段落或链接等真实维度")
        return self


class LocatorRef(BaseModel):
    """精确来源定位条目：片段标识 + 定位详情。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fragment_id: str
    locator: LocatorDetail

    @field_validator("fragment_id")
    @classmethod
    def _frag_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class SourceRef(BaseModel):
    """已复核来源版本/片段/声明引用。

    片段/声明/事实版本引用与定位都不得为空：无声明/事实谱系的来源
    不能支撑接受结论。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_version_id: str
    fragment_ids: tuple[str, ...] = Field(min_length=1)
    claim_ids: tuple[str, ...] = Field(min_length=1)
    fact_version_ids: tuple[str, ...] = Field(min_length=1)
    locators: tuple[LocatorRef, ...] = Field(min_length=1)

    @field_validator("source_version_id")
    @classmethod
    def _ref_text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("fragment_ids", "claim_ids", "fact_version_ids")
    @classmethod
    def _ids_unique_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(v) for v in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("引用标识不得重复")
        return normalized

    @model_validator(mode="after")
    def _at_least_one_locator(self) -> SourceRef:
        if not self.locators:
            raise ValueError("来源必须至少包含一个精确来源定位")
        # 嵌套定位片段必须唯一且属于本来源片段
        seen: set[str] = set()
        for loc in self.locators:
            if loc.fragment_id in seen:
                raise ValueError("来源定位片段标识不得重复")
            seen.add(loc.fragment_id)
            if loc.fragment_id not in self.fragment_ids:
                raise ValueError("来源定位片段必须属于本来源片段")
        return self


# ─── 审查问题 ────────────────────────────────────────────────────────────────


class ScientificIssue(BaseModel):
    """质控审查发现的单项问题。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issue_id: str
    severity: Literal["blocking", "non_blocking"]
    category: str
    description_zh: str
    source_version_id: str
    fragment_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("issue_id", "source_version_id", "category")
    @classmethod
    def _issue_text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("fragment_ids")
    @classmethod
    def _issue_fragments_unique_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_not_blank(v) for v in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("问题片段标识不得重复")
        return normalized

    @field_validator("description_zh")
    @classmethod
    def _desc_has_chinese(cls, value: str) -> str:
        normalized = _not_blank(value)
        if not _has_chinese_context(normalized):
            raise ValueError("问题描述必须包含中文语境")
        return normalized


# ─── 审查输入包 ──────────────────────────────────────────────────────────────


class ScientificQcReviewBundle(BaseModel):
    """封闭不可变审查输入包：只含候选快照/事实/声明、标准、覆盖与证据/来源/
    定位引用。不含构建者推理、思维链、草稿、提示词、日志、任务上下文或可变回调。
    来源引用与精确定位是审查者唯一可见的证据锚点。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    producer_id: str
    project_id: str
    report_kind: ReportKind
    report_version: str
    report_object_id: str
    candidate_snapshot_id: str
    candidate_content_digest: str
    criteria_version: str
    gate_result_key: str
    coverage_set_id: str
    coverage_digest: str
    source_refs: tuple[SourceRef, ...]
    locators: tuple[LocatorRef, ...]

    @field_validator(
        "producer_id", "project_id", "report_version", "report_object_id",
        "candidate_snapshot_id", "criteria_version", "gate_result_key",
        "coverage_set_id",
    )
    @classmethod
    def _bundle_text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("candidate_content_digest", "coverage_digest")
    @classmethod
    def _bundle_digests_are_sha256(cls, value: str) -> str:
        return _sha256_digest(value)

    @model_validator(mode="after")
    def _bundle_consistent(self) -> ScientificQcReviewBundle:
        if not self.source_refs:
            raise ValueError("审查包必须至少包含一个已复核来源引用")
        if not self.locators:
            raise ValueError("审查包必须至少包含一个精确来源定位")
        ids = [r.source_version_id for r in self.source_refs]
        if len(set(ids)) != len(ids):
            raise ValueError("来源引用标识不得重复")
        loc_ids = [loc.fragment_id for loc in self.locators]
        if len(set(loc_ids)) != len(loc_ids):
            raise ValueError("定位条目标识不得重复")
        # 定位必须引用已声明的来源片段
        all_fragments = {
            frag for ref in self.source_refs for frag in ref.fragment_ids
        }
        for loc in self.locators:
            if loc.fragment_id not in all_fragments:
                raise ValueError("审查包定位必须引用已声明的来源片段")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def input_digest(self) -> str:
        """审阅输入内容摘要：内容变化 → 摘要变化。"""
        return _sha256_hex(self._digest_payload())

    def _digest_payload(self) -> dict[str, Any]:
        data = self.model_dump(mode="json", exclude={"input_digest"})
        return data


# ─── 质控结论 ────────────────────────────────────────────────────────────────


class ScientificQcVerdict(BaseModel):
    """独立科学质控结论：只接受或否决；绑定当前候选快照内容摘要、
    GateSpec 结果键、覆盖范围、来源定位与审查输入摘要。不可变、
    extra=forbid、规范确定性可摘要。

    - ``accepted``：不得携带否决处置（veto_disposition=None），不得有阻断性问题；
    - ``veto``：必须且只能声明 ``recoverable``/``exhausted`` 之一，且至少一个阻断性问题。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    criteria_version: str
    verdict_id: str
    verdict: Literal["accepted", "veto"]
    veto_disposition: Literal["recoverable", "exhausted"] | None = None
    project_id: str
    contract_version: str
    report_kind: ReportKind
    report_version: str
    report_object_id: str
    candidate_snapshot_id: str
    candidate_content_digest: str
    gate_result_key: str
    coverage_set_id: str
    coverage_digest: str
    source_refs: tuple[SourceRef, ...]
    locators: tuple[LocatorRef, ...]
    issues: tuple[ScientificIssue, ...] = ()
    reviewer_id: str
    review_input_digest: str
    reviewed_at: datetime
    valid_until: datetime

    @field_validator(
        "criteria_version", "verdict_id", "project_id", "contract_version",
        "report_version", "report_object_id", "candidate_snapshot_id",
        "gate_result_key", "coverage_set_id", "reviewer_id",
        "review_input_digest",
    )
    @classmethod
    def _verdict_text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("reviewed_at", "valid_until")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("日期时间必须包含明确时区偏移")
        return value

    @field_validator("candidate_content_digest", "coverage_digest", "review_input_digest")
    @classmethod
    def _verdict_digests_are_sha256(cls, value: str) -> str:
        return _sha256_digest(value)

    @model_validator(mode="after")
    def _verdict_consistent(self) -> ScientificQcVerdict:
        if self.verdict == "accepted":
            if self.veto_disposition is not None:
                raise ValueError("接受结论不得携带否决处置")
            if self.has_blocking_issues():
                raise ValueError("接受结论不允许携带阻断性问题")
        else:
            if self.veto_disposition not in ("recoverable", "exhausted"):
                raise ValueError("否决结论必须且只能声明可修复或已穷尽之一")
            if not self.has_blocking_issues():
                raise ValueError("否决结论必须携带至少一个阻断性问题")
        if not self.source_refs:
            raise ValueError("结论必须至少包含一个已复核来源引用")
        if not self.locators:
            raise ValueError("结论必须至少包含一个精确来源定位")
        # 来源引用身份唯一
        ref_ids = [r.source_version_id for r in self.source_refs]
        if len(set(ref_ids)) != len(ref_ids):
            raise ValueError("来源引用标识不得重复")
        # 定位条目身份唯一且引用已声明片段
        all_fragments = {
            frag for ref in self.source_refs for frag in ref.fragment_ids
        }
        loc_ids = [loc.fragment_id for loc in self.locators]
        if len(set(loc_ids)) != len(loc_ids):
            raise ValueError("定位条目标识不得重复")
        for loc in self.locators:
            if loc.fragment_id not in all_fragments:
                raise ValueError("定位必须引用已声明的来源片段")
        # 问题身份唯一；问题来源/片段必须存在于已复核引用中
        issue_ids = [i.issue_id for i in self.issues]
        if len(set(issue_ids)) != len(issue_ids):
            raise ValueError("问题标识不得重复")
        ref_by_source = {r.source_version_id: r for r in self.source_refs}
        for issue in self.issues:
            ref = ref_by_source.get(issue.source_version_id)
            if ref is None:
                raise ValueError("问题来源必须属于已复核来源引用")
            missing = [
                frag for frag in issue.fragment_ids if frag not in ref.fragment_ids
            ]
            if missing:
                raise ValueError("问题片段必须属于其来源的已复核片段")
        return self

    def has_blocking_issues(self) -> bool:
        return any(issue.severity == "blocking" for issue in self.issues)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict_digest(self) -> str:
        """确定性可摘要内容摘要。"""
        return _sha256_hex(self._digest_payload())

    def _digest_payload(self) -> dict[str, Any]:
        data = self.model_dump(mode="json", exclude={"verdict_digest"})
        return data


# ─── 当前科学质控上下文（编排层创建） ──────────────────────────────────────────


class ScientificQcCurrentContext(BaseModel):
    """编排层创建的当前质控上下文：唯一权威的候选/门槛/覆盖/标准/来源/身份。

    由编排层从当前候选快照、GateSpec 结果、覆盖集合、标准版本与生产者身份
    组装并摘要；公共边界只接受该类型上下文，绝不接受调用方自由传入的
    分离 criteria/coverage 字符串。model_copy/dict 漂移在公共边界被原始
    内容重验证拒绝。持久化部署时该上下文应由权威记录加载；当前 Phase 3
    以编排层显式构造为真源（持久化推迟，见报告）。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    context_id: str
    producer_id: str
    project_id: str
    report_kind: ReportKind
    report_version: str
    report_object_id: str
    candidate_snapshot_id: str
    candidate_content_digest: str
    criteria_version: str
    gate_result_key: str
    contract_version: str
    coverage_set_id: str
    coverage_digest: str
    source_refs: tuple[SourceRef, ...]
    locators: tuple[LocatorRef, ...]

    @field_validator(
        "context_id", "producer_id", "project_id", "report_version",
        "report_object_id", "candidate_snapshot_id", "criteria_version",
        "gate_result_key", "contract_version", "coverage_set_id",
    )
    @classmethod
    def _context_text_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("candidate_content_digest", "coverage_digest")
    @classmethod
    def _context_digests_are_sha256(cls, value: str) -> str:
        return _sha256_digest(value)

    @model_validator(mode="after")
    def _context_consistent(self) -> ScientificQcCurrentContext:
        if not self.source_refs:
            raise ValueError("当前上下文必须至少包含一个已复核来源引用")
        if not self.locators:
            raise ValueError("当前上下文必须至少包含一个精确来源定位")
        ref_ids = [r.source_version_id for r in self.source_refs]
        if len(set(ref_ids)) != len(ref_ids):
            raise ValueError("来源引用标识不得重复")
        loc_ids = [loc.fragment_id for loc in self.locators]
        if len(set(loc_ids)) != len(loc_ids):
            raise ValueError("定位条目标识不得重复")
        all_fragments = {
            frag for ref in self.source_refs for frag in ref.fragment_ids
        }
        for loc in self.locators:
            if loc.fragment_id not in all_fragments:
                raise ValueError("当前上下文定位必须引用已声明的来源片段")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def context_digest(self) -> str:
        """当前上下文内容摘要：内容变化 → 摘要变化。"""
        return _sha256_hex(self._digest_payload())

    def _digest_payload(self) -> dict[str, Any]:
        data = self.model_dump(mode="json", exclude={"context_digest"})
        return data


# ─── JSON Schema 语义校验（Draft 2020-12 无法表达的跨数组引用/语义唯一） ────────


def check_scientific_qc_verdict_semantics(payload: dict[str, Any]) -> list[str]:
    """校验 JSON Schema 无法表达的结构语义；返回全部违例描述（空 = 通过）。

    - 来源引用 source_version_id 语义唯一；
    - 定位 fragment_id 语义唯一；
    - 问题 issue_id 语义唯一；
    - 每个定位条目必须引用已声明的来源片段；
    - 每个问题的来源/片段必须属于已复核引用；
    - 定位必须包含至少一个真实可检索维度（与运行时一致）；
    - 问题片段非空。
    """
    violations: list[str] = []

    def nonblank(v: object) -> bool:
        return isinstance(v, str) and bool(v.strip())

    source_refs = payload.get("source_refs")
    if isinstance(source_refs, list):
        seen: set[str] = set()
        for i, ref in enumerate(source_refs):
            if not isinstance(ref, dict):
                violations.append(f"source_refs[{i}] 必须是对象")
                continue
            sid = ref.get("source_version_id")
            if not isinstance(sid, str) or not nonblank(sid):
                violations.append(f"source_refs[{i}].source_version_id 非空")
            elif sid in seen:
                violations.append(f"source_refs[{i}].source_version_id 重复: {sid}")
            else:
                seen.add(sid)
            for field in ("fragment_ids", "claim_ids", "fact_version_ids"):
                ids = ref.get(field)
                if not isinstance(ids, list) or not ids:
                    violations.append(f"source_refs[{i}].{field} 非空")
            # 嵌套定位片段唯一 + 属于本来源片段（P1-2 攻击：同 fragment_id
            # 但定位字段不同的嵌套重复也必须拒绝）
            violations.extend(_check_source_ref_semantics(ref, i))
    else:
        violations.append("source_refs 必须是数组")

    locators = payload.get("locators")
    if isinstance(locators, list):
        seen_loc: set[str] = set()
        declared_fragments: set[str] = set()
        if isinstance(source_refs, list):
            for ref in source_refs:
                if not isinstance(ref, dict):
                    continue
                frags = ref.get("fragment_ids")
                if isinstance(frags, list):
                    declared_fragments.update(
                        frag for frag in frags if isinstance(frag, str)
                    )
        for i, loc in enumerate(locators):
            if not isinstance(loc, dict):
                violations.append(f"locators[{i}] 必须是对象")
                continue
            fid = loc.get("fragment_id")
            if not isinstance(fid, str) or not nonblank(fid):
                violations.append(f"locators[{i}].fragment_id 非空")
            elif fid in seen_loc:
                violations.append(f"locators[{i}].fragment_id 重复: {fid}")
            else:
                seen_loc.add(fid)
            detail = loc.get("locator")
            if isinstance(detail, dict):
                dims = {
                    "field_path", "heading", "page", "table",
                    "row", "column", "paragraph", "url",
                }
                present = {
                    name for name in dims
                    if detail.get(name) is not None
                }
                if not present:
                    violations.append(
                        f"locators[{i}].locator 缺少真实可检索维度"
                    )
                for name in present:
                    value = detail.get(name)
                    if name == "page":
                        if not isinstance(value, int) or value < 1:
                            violations.append(
                                f"locators[{i}].locator.page 必须 >= 1"
                            )
                    elif not nonblank(value):
                        violations.append(
                            f"locators[{i}].locator.{name} 非空"
                        )
            if fid and fid not in declared_fragments:
                violations.append(
                    f"locators[{i}].fragment_id 未声明: {fid}"
                )
    else:
        violations.append("locators 必须是数组")

    issues = payload.get("issues") or []
    if isinstance(issues, list):
        seen_issue: set[str] = set()
        for i, issue in enumerate(issues):
            if not isinstance(issue, dict):
                violations.append(f"issues[{i}] 必须是对象")
                continue
            iid = issue.get("issue_id")
            if not isinstance(iid, str) or not nonblank(iid):
                violations.append(f"issues[{i}].issue_id 非空")
            elif iid in seen_issue:
                violations.append(f"issues[{i}].issue_id 重复: {iid}")
            else:
                seen_issue.add(iid)
            frags = issue.get("fragment_ids")
            if not isinstance(frags, list) or not frags:
                violations.append(f"issues[{i}].fragment_ids 非空")
            elif len(set(frags)) != len(frags):
                violations.append(f"issues[{i}].fragment_ids 重复")
            src = issue.get("source_version_id")
            ref = next(
                (
                    r for r in source_refs
                    if isinstance(r, dict) and r.get("source_version_id") == src
                ),
                None,
            ) if isinstance(source_refs, list) else None
            if ref is None:
                violations.append(
                    f"issues[{i}].source_version_id 未声明: {src}"
                )
            else:
                declared = set(ref.get("fragment_ids") or [])
                for frag in (frags or []):
                    if frag not in declared:
                        violations.append(
                            f"issues[{i}].fragment_ids 未声明: {frag}"
                        )
    return violations


def _check_source_ref_semantics(ref: dict[str, Any], index: int) -> list[str]:
    """单个来源引用的语义校验：嵌套定位片段唯一且必须属于本引用片段。"""
    violations: list[str] = []

    def nonblank(v: object) -> bool:
        return isinstance(v, str) and bool(v.strip())

    frags = ref.get("fragment_ids")
    if not isinstance(frags, list) or not frags:
        violations.append(f"source_refs[{index}].fragment_ids 非空")
        return violations
    declared = {frag for frag in frags if isinstance(frag, str) and nonblank(frag)}
    locators = ref.get("locators")
    if not isinstance(locators, list) or not locators:
        violations.append(f"source_refs[{index}].locators 非空")
        return violations
    seen_nested: set[str] = set()
    for j, loc in enumerate(locators):
        if not isinstance(loc, dict):
            violations.append(f"source_refs[{index}].locators[{j}] 必须是对象")
            continue
        fid = loc.get("fragment_id")
        if not isinstance(fid, str) or not nonblank(fid):
            violations.append(
                f"source_refs[{index}].locators[{j}].fragment_id 非空"
            )
            continue
        if fid in seen_nested:
            violations.append(
                f"source_refs[{index}].locators[{j}].fragment_id 重复: {fid}"
            )
        else:
            seen_nested.add(fid)
        if fid not in declared:
            violations.append(
                f"source_refs[{index}].locators[{j}].fragment_id "
                f"未声明于本来源片段: {fid}"
            )
        detail = loc.get("locator")
        if isinstance(detail, dict):
            dims = {
                "field_path", "heading", "page", "table",
                "row", "column", "paragraph", "url",
            }
            present = {
                name for name in dims if detail.get(name) is not None
            }
            if not present:
                violations.append(
                    f"source_refs[{index}].locators[{j}].locator "
                    "缺少真实可检索维度"
                )
            for name in present:
                value = detail.get(name)
                if name == "page":
                    if not isinstance(value, int) or value < 1:
                        violations.append(
                            f"source_refs[{index}].locators[{j}].locator.page "
                            "必须 >= 1"
                        )
                elif not nonblank(value):
                    violations.append(
                        f"source_refs[{index}].locators[{j}].locator.{name} 非空"
                    )
    return violations


def check_scientific_qc_review_bundle_semantics(payload: dict[str, Any]) -> list[str]:
    """审查包/当前上下文语义校验（JSON Schema 无法表达的部分）。

    - 来源引用 source_version_id 语义唯一；
    - 嵌套定位片段唯一且属于本来源片段；
    - 顶层定位 fragment_id 唯一且引用已声明片段；
    - 定位精度：至少一个真实维度、非空文本、page >= 1。
    """
    violations: list[str] = []

    def nonblank(v: object) -> bool:
        return isinstance(v, str) and bool(v.strip())

    source_refs = payload.get("source_refs")
    seen: set[str] = set()
    if isinstance(source_refs, list):
        for i, ref in enumerate(source_refs):
            if not isinstance(ref, dict):
                violations.append(f"source_refs[{i}] 必须是对象")
                continue
            sid = ref.get("source_version_id")
            if not isinstance(sid, str) or not nonblank(sid):
                violations.append(f"source_refs[{i}].source_version_id 非空")
            elif sid in seen:
                violations.append(f"source_refs[{i}].source_version_id 重复: {sid}")
            else:
                seen.add(sid)
            violations.extend(_check_source_ref_semantics(ref, i))
    else:
        violations.append("source_refs 必须是数组")

    locators = payload.get("locators")
    if isinstance(locators, list):
        declared_fragments: set[str] = set()
        if isinstance(source_refs, list):
            for ref in source_refs:
                if not isinstance(ref, dict):
                    continue
                frags = ref.get("fragment_ids")
                if isinstance(frags, list):
                    declared_fragments.update(
                        frag for frag in frags if isinstance(frag, str)
                    )
        seen_loc: set[str] = set()
        for i, loc in enumerate(locators):
            if not isinstance(loc, dict):
                violations.append(f"locators[{i}] 必须是对象")
                continue
            fid = loc.get("fragment_id")
            if not isinstance(fid, str) or not nonblank(fid):
                violations.append(f"locators[{i}].fragment_id 非空")
            elif fid in seen_loc:
                violations.append(f"locators[{i}].fragment_id 重复: {fid}")
            else:
                seen_loc.add(fid)
            if fid and fid not in declared_fragments:
                violations.append(f"locators[{i}].fragment_id 未声明: {fid}")
            detail = loc.get("locator")
            if isinstance(detail, dict):
                dims = {
                    "field_path", "heading", "page", "table",
                    "row", "column", "paragraph", "url",
                }
                present = {
                    name for name in dims if detail.get(name) is not None
                }
                if not present:
                    violations.append(
                        f"locators[{i}].locator 缺少真实可检索维度"
                    )
                for name in present:
                    value = detail.get(name)
                    if name == "page":
                        if not isinstance(value, int) or value < 1:
                            violations.append(
                                f"locators[{i}].locator.page 必须 >= 1"
                            )
                    elif not nonblank(value):
                        violations.append(
                            f"locators[{i}].locator.{name} 非空"
                        )
    return violations
