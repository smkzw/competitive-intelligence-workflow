"""Task 4.1 规范覆盖集合与格式覆盖投影合同。

``CoverageSet`` 是绑定项目/合同/报告/版本/数据截止/证据快照/声明快照的
不可变规范覆盖项集合；``CoverageProjection`` 绑定恰好一个覆盖集合、
快照与输出格式，记录已覆盖项与版本化结构化例外。

合同边界（诚实声明）：Draft 2020-12 Schema 只表达可表示结构；跨数组的
逐项身份唯一、集合闭合、覆盖/例外重叠、等价行集绑定、HTML 完整表
不可省略、页面责任目录权威（生产验证器始终加载冻结 PageRegistry，
不接受调用方注入注册表），以及确定性身份/摘要重算，全部由生产验证器
语义层强制执行（``validate_*_payload``）。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)

from ci_workflow.domain.enums import OutputFormat, ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.reports.common.page_registry import PageRegistry

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# HTML 首版冻结合同：完整表不可省略，不支持格式例外。
_TABLE_OMISSION_FORBIDDEN_FORMATS = frozenset({OutputFormat.HTML})


class CoverageBoundaryError(ValueError):
    """覆盖合同边界拒绝：绑定失败、集合不闭合、重叠或摘要不一致。"""


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


def _has_chinese(value: str) -> bool:
    return _CJK_RE.search(value) is not None


def _offset_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("覆盖合同日期时间必须包含明确时区")
    return value


class CoverageItemKind(StrEnum):
    """覆盖项责任类型封闭集合：章节/页面/产品/试验/声明/图表/表格/证据/附录。"""

    CHAPTER = "chapter"
    PAGE = "page"
    PRODUCT = "product"
    TRIAL = "trial"
    CLAIM = "claim"
    CHART = "chart"
    TABLE = "table"
    EVIDENCE = "evidence"
    APPENDIX = "appendix"


class CoverageExceptionKind(StrEnum):
    """版本化格式例外类型：只有已批准的图表等价例外。"""

    CHART_EQUIVALENCE = "chart_equivalence"


def derive_coverage_item_id(
    report: ReportKind,
    kind: CoverageItemKind,
    page_responsibility_id: str,
    referenced_ids: Sequence[str],
) -> str:
    """覆盖项确定性身份：报告类型 + 责任类型 + 页面责任 + 规范化引用。"""
    return stable_id(
        "coverage-item",
        report.value,
        kind.value,
        _text(page_responsibility_id),
        *sorted(_text(ref) for ref in referenced_ids),
    )


def derive_coverage_set_id(
    project_id: str,
    contract_version: int,
    report: ReportKind,
    report_version: str,
    data_cutoff: str,
    evidence_snapshot_id: str,
    claim_snapshot_id: str,
    item_ids: Sequence[str],
) -> str:
    """覆盖集合确定性身份：全部绑定字段 + 排序后的条目身份。"""
    return stable_id(
        "coverage-set",
        _text(project_id),
        str(contract_version),
        report.value,
        _text(report_version),
        _text(data_cutoff),
        _text(evidence_snapshot_id),
        _text(claim_snapshot_id),
        *sorted(_text(item_id) for item_id in item_ids),
    )


def derive_coverage_exception_id(
    version: int,
    omitted_item_id: str,
    kind: CoverageExceptionKind,
    replacement_expression: str,
    row_set_digest: str,
) -> str:
    """版本化例外确定性身份：版本、省略项、例外类型、替代表达与行集摘要。"""
    return stable_id(
        "coverage-exception",
        str(version),
        _text(omitted_item_id),
        kind.value,
        _text(replacement_expression),
        _text(row_set_digest),
    )


def _exception_key(exception: CoverageException | Mapping[str, Any]) -> str:
    """例外投影键：版本 + 省略项 + 已校验例外身份。

    例外身份由版本/省略项/类型/替代表达/行集摘要确定性推导并被语义层
    强制，因此投影身份经此键绑定到已校验的例外身份；篡改例外内容要么
    改变例外身份（被拒绝）、要么改变本键（投影 ID 重算不一致）。
    """
    if isinstance(exception, Mapping):
        return (
            f"{exception['version']}:{exception['omitted_item_id']}:"
            f"{exception['exception_id']}"
        )
    return (
        f"{exception.version}:{exception.omitted_item_id}:"
        f"{exception.exception_id}"
    )


def derive_coverage_projection_id(
    coverage_set_id: str,
    format: OutputFormat,
    covered_item_ids: Sequence[str],
    exceptions: Sequence[CoverageException | Mapping[str, Any]],
) -> str:
    """投影确定性身份：绑定集合 + 格式 + 排序后的覆盖项与例外键。"""
    return stable_id(
        "coverage-projection",
        _text(coverage_set_id),
        format.value,
        *sorted(_text(item_id) for item_id in covered_item_ids),
        *sorted(_exception_key(exception) for exception in exceptions),
    )


def compute_coverage_set_content_digest(payload: Mapping[str, Any]) -> str:
    """覆盖集合规范内容摘要：按条目身份规范化排序，换序不改变摘要。"""
    data = dict(payload)
    data.pop("content_digest", None)
    items = data.get("items")
    if isinstance(items, list):
        data["items"] = sorted(items, key=lambda item: str(item["item_id"]))
    return _sha256_hex(data)


def compute_coverage_projection_content_digest(payload: Mapping[str, Any]) -> str:
    """投影规范内容摘要：覆盖项与例外按身份规范化排序。"""
    data = dict(payload)
    data.pop("content_digest", None)
    covered = data.get("covered_item_ids")
    if isinstance(covered, list):
        data["covered_item_ids"] = sorted(covered)
    exceptions = data.get("exceptions")
    if isinstance(exceptions, list):
        data["exceptions"] = sorted(
            exceptions, key=lambda exception: str(exception["exception_id"])
        )
    return _sha256_hex(data)


class CoverageItem(BaseModel):
    """规范覆盖项：稳定条目身份 + 封闭责任类型 + 页面责任 + 稳定引用。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    item_id: str
    kind: CoverageItemKind
    page_responsibility_id: str
    referenced_ids: tuple[str, ...] = Field(min_length=1)
    label_zh: str

    @field_validator("item_id", "page_responsibility_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("referenced_ids")
    @classmethod
    def _refs_unique_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("覆盖项引用身份不能重复")
        return normalized

    @field_validator("label_zh")
    @classmethod
    def _label_has_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("覆盖项中文标签必须包含中文")
        return normalized


class CoverageSet(BaseModel):
    """不可变规范覆盖集合，绑定项目/合同/报告/版本/截止/证据/声明快照。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    coverage_set_id: str
    project_id: str
    contract_version: int = Field(ge=1)
    report: ReportKind
    report_version: str
    data_cutoff: datetime
    evidence_snapshot_id: str
    claim_snapshot_id: str
    items: tuple[CoverageItem, ...] = Field(min_length=1)
    created_at: datetime
    content_digest: str

    @field_validator(
        "coverage_set_id", "project_id", "report_version",
        "evidence_snapshot_id", "claim_snapshot_id",
    )
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("data_cutoff", "created_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("content_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        normalized = _text(value)
        if not _SHA256_RE.fullmatch(normalized):
            raise ValueError("覆盖集合内容摘要必须是 64 位小写 SHA-256")
        return normalized


class EquivalenceEvidence(BaseModel):
    """图表等价证据：等价图表项 + 共享行集摘要 + 中文等价说明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    equivalent_item_id: str
    row_set_digest: str
    basis_zh: str

    @field_validator("equivalent_item_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("row_set_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        normalized = _text(value)
        if not _SHA256_RE.fullmatch(normalized):
            raise ValueError("等价行集摘要必须是 64 位小写 SHA-256")
        return normalized

    @field_validator("basis_zh")
    @classmethod
    def _basis_has_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("等价说明必须为原生中文")
        return normalized


class CoverageException(BaseModel):
    """版本化结构例外：省略项、替代表达、简洁中文理由与等价证据。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exception_id: str
    version: int = Field(ge=1)
    omitted_item_id: str
    exception_kind: CoverageExceptionKind
    replacement_expression: str
    rationale_zh: str
    equivalence_evidence: EquivalenceEvidence

    @field_validator("exception_id", "omitted_item_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("replacement_expression")
    @classmethod
    def _replacement_has_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("替代表达必须为原生中文")
        return normalized

    @field_validator("rationale_zh")
    @classmethod
    def _rationale_has_chinese(cls, value: str) -> str:
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("例外理由必须为简洁原生中文")
        return normalized


class CoverageProjection(BaseModel):
    """不可变格式覆盖投影：绑定一个覆盖集合、快照与输出格式。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0"
    coverage_projection_id: str
    coverage_set_id: str
    coverage_set_digest: str
    report: ReportKind
    report_version: str
    evidence_snapshot_id: str
    claim_snapshot_id: str
    format: OutputFormat
    covered_item_ids: tuple[str, ...]
    exceptions: tuple[CoverageException, ...]
    created_at: datetime
    content_digest: str

    @field_validator(
        "coverage_projection_id", "coverage_set_id", "report_version",
        "evidence_snapshot_id", "claim_snapshot_id",
    )
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("covered_item_ids")
    @classmethod
    def _covered_unique_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(value) for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("覆盖项不能重复")
        return normalized

    @field_validator("created_at")
    @classmethod
    def _time_has_offset(cls, value: datetime) -> datetime:
        return _offset_datetime(value)

    @field_validator("coverage_set_digest", "content_digest")
    @classmethod
    def _digest_is_sha256(cls, value: str) -> str:
        normalized = _text(value)
        if not _SHA256_RE.fullmatch(normalized):
            raise ValueError("投影摘要必须是 64 位小写 SHA-256")
        return normalized


# ─── 语义校验（Draft 2020-12 无法表达的跨数组规则） ────────────────────────


def check_coverage_set_semantics(
    model: CoverageSet,
    *,
    registry: PageRegistry,
) -> list[str]:
    """校验 Schema/模型无法表达的结构语义；返回全部违例（空 = 通过）。

    页面责任目录权威不可关闭：registry 必填，每个覆盖项的页面责任必须
    属于同一报告类型的冻结目录或动态详情责任。
    """
    violations: list[str] = []
    item_ids = [item.item_id for item in model.items]
    if len(set(item_ids)) != len(item_ids):
        duplicates = sorted(
            {item_id for item_id in item_ids if item_ids.count(item_id) > 1}
        )
        violations.append(f"覆盖项身份重复：{'、'.join(duplicates)}")
    for item in model.items:
        expected = derive_coverage_item_id(
            model.report,
            item.kind,
            item.page_responsibility_id,
            item.referenced_ids,
        )
        if item.item_id != expected:
            violations.append(
                f"覆盖项 {item.item_id} 身份与科学身份字段不一致（应为 {expected}）"
            )
    expected_set_id = derive_coverage_set_id(
        model.project_id,
        model.contract_version,
        model.report,
        model.report_version,
        model.data_cutoff.isoformat(),
        model.evidence_snapshot_id,
        model.claim_snapshot_id,
        item_ids,
    )
    if model.coverage_set_id != expected_set_id:
        violations.append(
            "覆盖集合 ID 与绑定内容不一致（自由身份替换被拒绝）"
        )
    expected_digest = compute_coverage_set_content_digest(
        _canonical_set_dump(model.model_dump(mode="json"))
    )
    if model.content_digest != expected_digest:
        violations.append("覆盖集合内容摘要与规范内容不一致")
    known = registry.page_responsibility_ids(model.report)
    for item in model.items:
        if item.page_responsibility_id not in known:
            violations.append(
                f"覆盖项 {item.item_id} 引用未知页面责任："
                f"{item.page_responsibility_id}（{model.report.value} 目录外）"
            )
    return violations


def check_coverage_projection_semantics(
    model: CoverageProjection,
    coverage_set: CoverageSet,
) -> list[str]:
    """校验投影的集合闭合、重叠、格式例外与确定性身份/摘要。"""
    violations: list[str] = []
    set_ids = {item.item_id for item in coverage_set.items}
    covered = list(model.covered_item_ids)
    omitted = [exception.omitted_item_id for exception in model.exceptions]
    exception_ids = [exception.exception_id for exception in model.exceptions]
    if len(set(exception_ids)) != len(exception_ids):
        violations.append("例外身份重复")
    for exception in model.exceptions:
        expected_exception_id = derive_coverage_exception_id(
            exception.version,
            exception.omitted_item_id,
            exception.exception_kind,
            exception.replacement_expression,
            exception.equivalence_evidence.row_set_digest,
        )
        if exception.exception_id != expected_exception_id:
            violations.append(
                f"例外身份不一致：{exception.exception_id}"
                f"（应为 {expected_exception_id}，自由替换被拒绝）"
            )
    if len(set(omitted)) != len(omitted):
        violations.append("省略项重复")
    overlap = set(covered) & set(omitted)
    if overlap:
        violations.append(f"覆盖与例外重叠：{'、'.join(sorted(overlap))}")
    unknown = [item_id for item_id in (*covered, *omitted) if item_id not in set_ids]
    if unknown:
        violations.append(f"投影引用规范集合外项：{'、'.join(sorted(unknown))}")
    unexplained = set_ids - set(covered) - set(omitted)
    if unexplained:
        violations.append(f"未解释差异：{'、'.join(sorted(unexplained))}")
    # 绑定：恰好一个覆盖集合与同一快照。
    if model.coverage_set_id != coverage_set.coverage_set_id:
        violations.append("投影绑定的覆盖集合 ID 与校验对象不一致")
    if model.coverage_set_digest != coverage_set.content_digest:
        violations.append("投影绑定的覆盖集合摘要不一致")
    if model.report is not coverage_set.report:
        violations.append("投影报告类型与覆盖集合不一致")
    if model.report_version != coverage_set.report_version:
        violations.append("投影报告版本与覆盖集合不一致")
    if model.evidence_snapshot_id != coverage_set.evidence_snapshot_id:
        violations.append("投影证据快照与覆盖集合不一致（跨快照混用）")
    if model.claim_snapshot_id != coverage_set.claim_snapshot_id:
        violations.append("投影声明快照与覆盖集合不一致（跨快照混用）")
    # 确定性身份与摘要。
    expected_id = derive_coverage_projection_id(
        model.coverage_set_id,
        model.format,
        model.covered_item_ids,
        model.exceptions,
    )
    if model.coverage_projection_id != expected_id:
        violations.append("投影 ID 与内容不一致（自由身份替换被拒绝）")
    expected_digest = compute_coverage_projection_content_digest(
        _canonical_projection_dump(model.model_dump(mode="json"))
    )
    if model.content_digest != expected_digest:
        violations.append("投影内容摘要与规范内容不一致")
    # HTML-only 首版不接受省略完整表格或其他格式投影。
    if model.format not in _TABLE_OMISSION_FORBIDDEN_FORMATS:
        violations.append("覆盖投影格式必须是 html")
        return violations
    if model.exceptions:
        violations.append(
            f"{model.format.value} 禁止省略完整表格，例外必须为空"
        )
    return violations


def _canonical_set_dump(dump: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(dump)
    data.pop("content_digest", None)
    data["items"] = sorted(data["items"], key=lambda item: str(item["item_id"]))
    return data


def _canonical_projection_dump(dump: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(dump)
    data.pop("content_digest", None)
    data["covered_item_ids"] = sorted(data["covered_item_ids"])
    data["exceptions"] = sorted(
        data["exceptions"], key=lambda exception: str(exception["exception_id"])
    )
    return data


# ─── Schema 解析与生产验证器 ────────────────────────────────────────────────


def _coverage_set_schema() -> dict[str, Any]:
    return _load_schema("coverage-set", "覆盖集合")


def _coverage_projection_schema() -> dict[str, Any]:
    return _load_schema("coverage-projection", "格式覆盖投影")


def _load_schema(name: str, label: str) -> dict[str, Any]:
    """解析打包 Schema（Draft 2020-12），不接受调用方选择路径。

    同时支持两种布局：
    - 源码树/目录安装包：仓库根 ``schemas/``；
    - 打包安装布局：``ci_workflow/schemas/``（随包数据携带）。

    两处均缺失时以确定性的 ``CoverageBoundaryError`` 失败关闭。
    """
    candidates: tuple[Path, ...] = (
        Path(__file__).resolve().parents[4] / "schemas" / f"{name}.schema.json",
        Path(__file__).resolve().parents[2] / "schemas" / f"{name}.schema.json",
    )
    for candidate in candidates:
        try:
            return cast(dict[str, Any], json.loads(candidate.read_text(encoding="utf-8")))
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as error:
            raise CoverageBoundaryError(f"打包的{label} Schema 损坏：{candidate}") from error
    raise CoverageBoundaryError(
        f"无法定位打包的{label} Schema（源码树与安装布局均缺失）"
    )


def _validate_coverage_set_payload_with_registry(
    raw: dict[str, Any],
    registry: PageRegistry,
) -> CoverageSet:
    """内部/测试专用：以给定注册表校验覆盖集合；公开边界必须使用冻结注册表。"""
    schema = _coverage_set_schema()
    try:
        Draft202012Validator(schema).validate(raw)
    except JsonSchemaValidationError as error:
        raise CoverageBoundaryError(
            f"覆盖集合不符合打包 Schema（{schema.get('$id', 'coverage-set')}）："
            f"{error.message}"
        ) from error
    try:
        model = CoverageSet.model_validate(raw)
    except PydanticValidationError as error:
        raise CoverageBoundaryError(f"覆盖集合模型校验失败：{error}") from error
    violations = check_coverage_set_semantics(model, registry=registry)
    if violations:
        raise CoverageBoundaryError("覆盖集合语义校验失败：" + "；".join(violations))
    return model


def validate_coverage_set_payload(raw: dict[str, Any]) -> CoverageSet:
    """生产覆盖集合验证器：打包 Schema → Pydantic 模型 → 语义校验。

    页面责任权威：始终加载冻结 PageRegistry（源码树或包内数据布局），
    每个覆盖项的页面责任必须属于同一报告类型的冻结目录或动态详情责任；
    公开边界不接受调用方注入注册表（自定义注册表只允许内部/测试专用
    路径 ``_validate_coverage_set_payload_with_registry``）。
    """
    return _validate_coverage_set_payload_with_registry(raw, PageRegistry.load())


def validate_coverage_projection_payload(
    raw: dict[str, Any],
    coverage_set: CoverageSet,
) -> CoverageProjection:
    """生产投影验证器：打包 Schema → Pydantic 模型 → 与给定覆盖集合的语义绑定。"""
    schema = _coverage_projection_schema()
    try:
        Draft202012Validator(schema).validate(raw)
    except JsonSchemaValidationError as error:
        raise CoverageBoundaryError(
            f"格式覆盖投影不符合打包 Schema（{schema.get('$id', 'coverage-projection')}）："
            f"{error.message}"
        ) from error
    try:
        model = CoverageProjection.model_validate(raw)
    except PydanticValidationError as error:
        raise CoverageBoundaryError(f"格式覆盖投影模型校验失败：{error}") from error
    violations = check_coverage_projection_semantics(model, coverage_set)
    if violations:
        raise CoverageBoundaryError("格式覆盖投影语义校验失败：" + "；".join(violations))
    return model
