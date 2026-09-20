"""PPT Master 的中文来源包投影。

该模块只把已经锁定的报告数据投影为 PPT Master 可读取的 Markdown
和机器可核验的摘要清单。它不创建逐页 SVG，也不创建 PPTX。

来源包的身份边界是 ``(project_id, report, report_version, snapshot_id)``。
快照、覆盖集合、页面策略和项目内康哲 PPTX 设计合同均在生成前绑定；
任何跨报告、跨版本或跨快照组合都会失败关闭。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id

ReportKey = Literal["A", "B", "C"]
JsonObject = dict[str, Any]

_SCHEMA_FILENAME = "pptx-source-pack.schema.json"
_SCHEMA_VERSION = "1.0"
_CONTRACT_VERSION = "8.7"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")

# The source pack is intentionally ordered like the report data contract. Unknown
# keys are appended in lexical order, so a new report field is never silently lost.
_DATA_SECTION_ORDER = (
    "products",
    "trials",
    "observations",
    "efficacy",
    "safety",
    "baseline",
    "baseline_views",
    "disposition",
    "disposition_views",
    "efficacy_views",
    "safety_views",
    "matrix_view",
    "regulatory",
    "companies",
    "patents",
    "history",
    "sources",
)
_METADATA_KEYS = frozenset(
    {
        "schema_version",
        "report",
        "report_kind",
        "report_version",
        "indication",
        "indication_id",
        "data_cutoff",
        "report_snapshot_id",
    }
)


class SourcePackBuildError(ValueError):
    """来源包输入或绑定不符合锁定快照合同。"""


@dataclass(frozen=True)
class SourcePack:
    """来源包构建结果；写文件是单独的显式动作。"""

    markdown: str
    summary: SourcePackSummary

    @property
    def source_pack_sha256(self) -> str:
        """Markdown 来源包的 SHA-256。"""

        return self.summary.source_pack_sha256

    @property
    def manifest(self) -> SourcePackSummary:
        """与 ``summary`` 等价的清单别名，便于调用方交接给作业收据。"""

        return self.summary


class SourcePackPage(BaseModel):
    """一个静态页面策略摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_id: str = Field(min_length=1)
    route: str = Field(min_length=1)
    title_zh: str = Field(min_length=1)
    responsibility_zh: str = Field(min_length=1)
    visuals: tuple[str, ...]
    complete_table: bool
    filter_profiles: tuple[str, ...]
    evidence_drawer_profile: str = Field(min_length=1)


class SourcePackCoverage(BaseModel):
    """覆盖集合摘要，不复制覆盖事实正文。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    coverage_set_id: str = Field(min_length=1)
    content_sha256: str
    item_count: int = Field(ge=0)
    item_ids: tuple[str, ...]
    item_kind_counts: dict[str, int]

    @staticmethod
    def _validate_sha(value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("覆盖集合摘要必须是 64 位小写 SHA-256")
        return value

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> SourcePackCoverage:
        result = super().model_validate(obj, *args, **kwargs)
        cls._validate_sha(result.content_sha256)
        if len(result.item_ids) != len(set(result.item_ids)):
            raise ValueError("覆盖项身份不得重复")
        if sum(result.item_kind_counts.values()) != result.item_count:
            raise ValueError("覆盖项分类计数与总数不一致")
        return result


class SourcePackContractFile(BaseModel):
    """设计合同中被摘要绑定的单个文件。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    sha256: str

    @staticmethod
    def _validate_sha(value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("合同文件摘要必须是 64 位小写 SHA-256")
        return value

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> SourcePackContractFile:
        result = super().model_validate(obj, *args, **kwargs)
        _relative_path(result.path, field="合同文件路径")
        cls._validate_sha(result.sha256)
        return result


class SourcePackDesignContract(BaseModel):
    """项目内康哲 PPTX 轨摘要。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest_path: str = Field(min_length=1)
    route: Literal["pptx"]
    contract_version: str = Field(min_length=1)
    sha256: str
    files: tuple[SourcePackContractFile, ...]

    @staticmethod
    def _validate_sha(value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("设计合同摘要必须是 64 位小写 SHA-256")
        return value

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> SourcePackDesignContract:
        result = super().model_validate(obj, *args, **kwargs)
        _relative_path(result.manifest_path, field="设计合同 manifest 路径")
        cls._validate_sha(result.sha256)
        paths = [item.path for item in result.files]
        if len(paths) != len(set(paths)):
            raise ValueError("设计合同文件路径不得重复")
        return result


class SourcePackSummary(BaseModel):
    """PPTX 来源包机器摘要；Markdown 本体由 ``SourcePack.markdown`` 保存。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    contract_version: Literal["8.7"] = "8.7"
    source_pack_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    report: ReportKey
    report_version: str = Field(min_length=1)
    indication: str = Field(min_length=1)
    data_cutoff: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    snapshot_sha256: str
    claim_snapshot_id: str = Field(min_length=1)
    evidence_snapshot_id: str = Field(min_length=1)
    coverage_set_id: str = Field(min_length=1)
    coverage_set_sha256: str
    report_data_sha256: str
    page_strategy_sha256: str
    design_contract_sha256: str
    source_pack_path: str = Field(min_length=1)
    source_pack_sha256: str
    source_pack_byte_size: int = Field(ge=1)
    summary_path: str = Field(min_length=1)
    summary_sha256: str
    page_count: int = Field(ge=1)
    pages: tuple[SourcePackPage, ...] = Field(min_length=1)
    coverage: SourcePackCoverage
    fact_counts: dict[str, int]
    source_keys: tuple[str, ...] = Field(min_length=1)
    design_contract: SourcePackDesignContract
    no_svg: Literal[True] = True

    @staticmethod
    def _validate_sha(value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("来源包摘要必须是 64 位小写 SHA-256")
        return value

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> SourcePackSummary:
        result = super().model_validate(obj, *args, **kwargs)
        for field_name in (
            "snapshot_sha256",
            "coverage_set_sha256",
            "report_data_sha256",
            "page_strategy_sha256",
            "design_contract_sha256",
            "source_pack_sha256",
            "summary_sha256",
        ):
            cls._validate_sha(getattr(result, field_name))
        _relative_path(result.source_pack_path, field="来源包路径")
        _relative_path(result.summary_path, field="摘要路径")
        if result.page_count != len(result.pages):
            raise ValueError("页面数量摘要与页面清单不一致")
        if len(result.source_keys) != len(set(result.source_keys)):
            raise ValueError("来源顶层字段不得重复")
        if any(value < 0 for value in result.fact_counts.values()):
            raise ValueError("事实计数不得为负")
        return result


@dataclass(frozen=True)
class _SnapshotBinding:
    project_id: str
    report: ReportKey
    report_version: str
    snapshot_id: str
    snapshot_sha256: str
    claim_snapshot_id: str
    evidence_snapshot_id: str
    coverage_set_id: str
    locked_at: str


@dataclass(frozen=True)
class _CoverageBinding:
    coverage_set_id: str
    content_sha256: str
    item_ids: tuple[str, ...]
    item_kind_counts: dict[str, int]
    items: tuple[JsonObject, ...]


@dataclass(frozen=True)
class _PageBinding:
    payload: JsonObject
    pages: tuple[SourcePackPage, ...]
    digest: str


@dataclass(frozen=True)
class _DesignBinding:
    summary: SourcePackDesignContract
    digest: str


# ─── Deterministic primitives ──────────────────────────────────────────────


def _canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SourcePackBuildError(f"来源包输入不是可规范化 JSON：{exc}") from exc
    return (text + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _text(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise SourcePackBuildError(f"{field} 必须是非空文本")
    normalized = " ".join(value.split())
    if not normalized:
        raise SourcePackBuildError(f"{field} 不能为空")
    return normalized


def _sha(value: Any, *, field: str) -> str:
    normalized = _text(value, field=field)
    if not _SHA256_RE.fullmatch(normalized):
        raise SourcePackBuildError(f"{field} 必须是 64 位小写 SHA-256")
    return normalized
def _relative_path(value: Any, *, field: str) -> str:
    normalized = _text(value, field=field)
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or "\\" in normalized:
        raise SourcePackBuildError(f"{field} 必须是项目内 POSIX 相对路径")
    return normalized



def _json_mapping(value: Any, *, field: str) -> JsonObject:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if not isinstance(value, Mapping):
        raise SourcePackBuildError(f"{field} 必须是对象")
    try:
        # Make a detached, JSON-only copy. This also normalizes enum values and
        # prevents a caller mutating the payload after the source pack is built.
        detached = json.loads(json.dumps(dict(value), ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise SourcePackBuildError(f"{field} 不是可规范化 JSON：{exc}") from exc
    if not isinstance(detached, dict):  # pragma: no cover - guarded by Mapping above
        raise SourcePackBuildError(f"{field} 必须是对象")
    return cast(JsonObject, detached)


def _report_key(value: Any, *, field: str = "报告类型") -> ReportKey:
    if isinstance(value, ReportKind):
        value = value.value
    if not isinstance(value, str):
        raise SourcePackBuildError(f"{field} 必须为 A、B 或 C")
    normalized = value.strip().upper()
    if normalized not in {"A", "B", "C"}:
        raise SourcePackBuildError(f"{field} 必须为 A、B 或 C，收到 {value!r}")
    return cast(ReportKey, normalized)


def _resolve_report_data(
    report: str | ReportKind,
    report_data: Mapping[str, Any] | BaseModel,
) -> tuple[ReportKey, JsonObject]:
    report_key = _report_key(report)
    data = _json_mapping(report_data, field="锁定报告数据")
    embedded_report = data.get("report", data.get("report_kind"))
    if (
        embedded_report is not None
        and _report_key(embedded_report, field="报告数据类型") != report_key
    ):
        raise SourcePackBuildError("报告数据类型与请求的报告类型不一致")
    if not _text(data.get("report_version"), field="报告版本"):
        raise SourcePackBuildError("锁定报告数据缺少 report_version")
    if not _text(data.get("indication"), field="适应症"):
        raise SourcePackBuildError("锁定报告数据缺少 indication")
    if not _text(data.get("data_cutoff"), field="数据截止时间"):
        raise SourcePackBuildError("锁定报告数据缺少 data_cutoff")
    return report_key, data


def _resolve_snapshot(
    snapshot: Mapping[str, Any] | BaseModel,
    *,
    report: ReportKey,
    report_data: JsonObject,
) -> _SnapshotBinding:
    payload = _json_mapping(snapshot, field="锁定报告快照")
    if isinstance(payload.get("snapshot"), dict) and "snapshot_id" not in payload:
        payload = cast(JsonObject, payload["snapshot"])
    required = (
        "project_id",
        "report",
        "report_version",
        "snapshot_id",
        "snapshot_sha256",
        "claim_snapshot_id",
        "evidence_snapshot_id",
        "coverage_set_id",
        "locked_at",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise SourcePackBuildError(f"锁定报告快照缺少字段：{'、'.join(missing)}")
    snapshot_report = _report_key(payload["report"], field="锁定快照报告类型")
    if snapshot_report != report:
        raise SourcePackBuildError("锁定快照报告类型与来源包报告不一致")
    report_version = _text(payload["report_version"], field="锁定快照报告版本")
    if report_version != _text(report_data["report_version"], field="报告版本"):
        raise SourcePackBuildError("锁定快照报告版本与报告数据不一致")
    report_snapshot_id = report_data.get("report_snapshot_id")
    snapshot_id = _text(payload["snapshot_id"], field="锁定快照标识")
    if (
        report_snapshot_id is not None
        and _text(report_snapshot_id, field="报告数据快照标识") != snapshot_id
    ):
        raise SourcePackBuildError("报告数据 report_snapshot_id 与锁定快照不一致")
    return _SnapshotBinding(
        project_id=_text(payload["project_id"], field="项目标识"),
        report=report,
        report_version=report_version,
        snapshot_id=snapshot_id,
        snapshot_sha256=_sha(payload["snapshot_sha256"], field="锁定快照摘要"),
        claim_snapshot_id=_text(payload["claim_snapshot_id"], field="声明快照标识"),
        evidence_snapshot_id=_text(payload["evidence_snapshot_id"], field="证据快照标识"),
        coverage_set_id=_text(payload["coverage_set_id"], field="覆盖集标识"),
        locked_at=_text(payload["locked_at"], field="锁定时间"),
    )


def _coverage_payload(value: Mapping[str, Any] | BaseModel) -> JsonObject:
    payload = _json_mapping(value, field="覆盖集合")
    nested = payload.get("coverage_set")
    if isinstance(nested, dict):
        payload = cast(JsonObject, nested)
    return payload


def _resolve_coverage(
    coverage_set: Mapping[str, Any] | BaseModel,
    *,
    snapshot: _SnapshotBinding,
    report: ReportKey,
    report_data: JsonObject,
) -> _CoverageBinding:
    payload = _coverage_payload(coverage_set)
    coverage_id = _text(payload.get("coverage_set_id"), field="覆盖集标识")
    if coverage_id != snapshot.coverage_set_id:
        raise SourcePackBuildError("覆盖集标识与锁定快照不一致")
    if (
        payload.get("report") is not None
        and _report_key(payload["report"], field="覆盖集报告类型") != report
    ):
        raise SourcePackBuildError("覆盖集报告类型与来源包报告不一致")
    for field_name, expected in (
        ("report_version", snapshot.report_version),
        ("evidence_snapshot_id", snapshot.evidence_snapshot_id),
        ("claim_snapshot_id", snapshot.claim_snapshot_id),
    ):
        actual = payload.get(field_name)
        if actual is not None and _text(actual, field=field_name) != expected:
            raise SourcePackBuildError(f"覆盖集 {field_name} 与锁定快照不一致")

    raw_items = payload.get("items")
    if raw_items is None:
        raw_items = payload.get("covered_items")
    if raw_items is None:
        raw_items = []
    if not isinstance(raw_items, list):
        raise SourcePackBuildError("覆盖集 items 必须是数组")
    items: list[JsonObject] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, Mapping):
            raise SourcePackBuildError(f"覆盖项 #{index + 1} 必须是对象")
        item_payload = _json_mapping(item, field=f"覆盖项 #{index + 1}")
        item_id = _text(item_payload.get("item_id"), field=f"覆盖项 #{index + 1} 标识")
        item_payload["item_id"] = item_id
        items.append(item_payload)
    declared_ids = payload.get("covered_item_ids")
    if declared_ids is not None:
        if not isinstance(declared_ids, list) or not all(
            isinstance(item, str) for item in declared_ids
        ):
            raise SourcePackBuildError("covered_item_ids 必须是字符串数组")
        declared = tuple(_text(item, field="covered_item_ids") for item in declared_ids)
        if items and declared != tuple(item["item_id"] for item in items):
            raise SourcePackBuildError("covered_item_ids 与覆盖项清单不一致")
    item_ids = tuple(item["item_id"] for item in items)
    if len(item_ids) != len(set(item_ids)):
        raise SourcePackBuildError("覆盖项标识不得重复")
    if not item_ids and isinstance(declared_ids, list):
        item_ids = tuple(_text(item, field="covered_item_ids") for item in declared_ids)
    # A production CoverageSet always has items. Keep this boundary explicit,
    # while permitting a minimal covered_item_ids fixture for contract tests.
    if not item_ids:
        raise SourcePackBuildError("覆盖集合必须包含至少一个覆盖项")

    content_digest = payload.get("content_digest", payload.get("coverage_set_sha256"))
    digest_payload = dict(payload)
    digest_payload.pop("content_digest", None)
    digest_payload.pop("coverage_set_sha256", None)
    if isinstance(digest_payload.get("items"), list):
        digest_payload["items"] = sorted(
            digest_payload["items"], key=lambda item: str(item.get("item_id", ""))
        )
    computed_content_sha256 = _sha256_json(digest_payload)
    if content_digest is None:
        content_sha256 = computed_content_sha256
    else:
        content_sha256 = _sha(content_digest, field="覆盖集内容摘要")
        # Full CoverageSet payloads use this canonical content digest. Minimal
        # fixture payloads may provide only an externally locked digest.
        required_digest_fields = {
            "schema_version",
            "project_id",
            "contract_version",
            "report",
            "report_version",
            "data_cutoff",
            "evidence_snapshot_id",
            "claim_snapshot_id",
            "items",
            "created_at",
        }
        if (
            "content_digest" in payload
            and required_digest_fields.issubset(payload)
            and content_sha256 != computed_content_sha256
        ):
            raise SourcePackBuildError("覆盖集内容摘要与覆盖项内容不一致")

    kind_counts: dict[str, int] = {}
    for item in items:
        kind = str(item.get("kind", item.get("item_kind", "other")))
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    # covered_item_ids-only payloads do not carry kinds; count them under a
    # neutral category so the summary remains arithmetically closed.
    if not items:
        kind_counts = {"declared": len(item_ids)}
    return _CoverageBinding(
        coverage_set_id=coverage_id,
        content_sha256=content_sha256,
        item_ids=item_ids,
        item_kind_counts=dict(sorted(kind_counts.items())),
        items=tuple(items),
    )


def _catalog_payload_from_model(value: Any) -> JsonObject:
    if hasattr(value, "catalogs"):
        catalogs = value.catalogs
        if not catalogs:
            raise SourcePackBuildError("页面注册表不含目录")
        value = catalogs[0]
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return _json_mapping(value, field="页面策略")


def load_page_strategy(report: str | ReportKind, *, root: Path | None = None) -> JsonObject:
    """读取项目内冻结 A/B/C 页面策略 YAML。"""

    report_key = _report_key(report)
    base = root or Path(__file__).resolve().parents[4]
    candidates = (
        base
        / "src"
        / "ci_workflow"
        / "reports"
        / "common"
        / "page-catalogs"
        / f"{report_key}.yaml",
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise SourcePackBuildError(f"页面策略读取失败：{path}") from exc
        if not isinstance(payload, dict):
            raise SourcePackBuildError(f"页面策略顶层必须是对象：{path}")
        payload = cast(JsonObject, payload)
        if _report_key(payload.get("report"), field="页面策略报告类型") != report_key:
            raise SourcePackBuildError("页面策略报告类型不一致")
        return payload
    raise SourcePackBuildError(f"页面策略缺失：报告 {report_key}")


def _resolve_pages(
    page_strategy: Mapping[str, Any] | BaseModel | None,
    *,
    report: ReportKey,
) -> _PageBinding:
    if page_strategy is None:
        payload = load_page_strategy(report)
    elif hasattr(page_strategy, "catalogs"):
        # PageRegistry -> select the requested catalog without relying on its
        # private loader internals.
        catalogs = page_strategy.catalogs
        selected = None
        for catalog in catalogs:
            catalog_report = getattr(catalog, "report", None)
            catalog_key = _report_key(catalog_report, field="页面目录报告类型")
            if catalog_key == report:
                selected = catalog
                break
        if selected is None:
            raise SourcePackBuildError(f"页面注册表缺少报告 {report}")
        payload = _catalog_payload_from_model(selected)
    elif hasattr(page_strategy, "pages") and hasattr(page_strategy, "report"):
        payload = _catalog_payload_from_model(page_strategy)
    else:
        payload = _json_mapping(page_strategy, field="页面策略")
        nested = payload.get("catalog")
        if isinstance(nested, dict):
            payload = cast(JsonObject, nested)
    if (
        payload.get("report") is not None
        and _report_key(payload["report"], field="页面策略报告类型") != report
    ):
        raise SourcePackBuildError("页面策略报告类型与来源包报告不一致")
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        raise SourcePackBuildError("页面策略必须包含非空 pages")
    pages: list[SourcePackPage] = []
    normalized_pages: list[JsonObject] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_pages):
        if not isinstance(raw, Mapping):
            raise SourcePackBuildError(f"页面策略第 {index + 1} 项必须是对象")
        item = _json_mapping(raw, field=f"页面策略第 {index + 1} 项")
        page_id = _text(item.get("id", item.get("page_id")), field="页面 ID")
        if page_id in seen:
            raise SourcePackBuildError(f"页面策略存在重复 ID：{page_id}")
        seen.add(page_id)
        route = _text(item.get("route", f"/{report.casefold()}/{page_id}"), field="页面路由")
        title = _text(item.get("title_zh", item.get("title")), field="页面标题")
        responsibility = _text(
            item.get("responsibility_zh", item.get("responsibility")),
            field="页面责任",
        )
        visuals_raw = item.get("visuals", [])
        if not isinstance(visuals_raw, list):
            raise SourcePackBuildError(f"页面 {page_id} visuals 必须是数组")
        visuals = tuple(_text(visual, field=f"页面 {page_id} visual") for visual in visuals_raw)
        filters_raw = item.get("filter_profiles", [])
        if not isinstance(filters_raw, list):
            raise SourcePackBuildError(f"页面 {page_id} filter_profiles 必须是数组")
        filter_profiles = tuple(
            _text(profile, field=f"页面 {page_id} filter_profile") for profile in filters_raw
        )
        evidence_profile = _text(
            item.get("evidence_drawer_profile", "common-clinical"),
            field=f"页面 {page_id} evidence_drawer_profile",
        )
        complete_table = item.get("complete_table", True)
        if not isinstance(complete_table, bool):
            raise SourcePackBuildError(f"页面 {page_id} complete_table 必须是布尔值")
        page = SourcePackPage(
            page_id=page_id,
            route=route,
            title_zh=title,
            responsibility_zh=responsibility,
            visuals=visuals,
            complete_table=complete_table,
            filter_profiles=filter_profiles,
            evidence_drawer_profile=evidence_profile,
        )
        pages.append(page)
        normalized_pages.append(
            {
                "page_id": page_id,
                "route": route,
                "title_zh": title,
                "responsibility_zh": responsibility,
                "visuals": list(visuals),
                "complete_table": complete_table,
                "filter_profiles": list(filter_profiles),
                "evidence_drawer_profile": evidence_profile,
            }
        )
    normalized_payload = dict(payload)
    normalized_payload["pages"] = normalized_pages
    return _PageBinding(
        payload=normalized_payload,
        pages=tuple(pages),
        digest=_sha256_json(normalized_payload),
    )


def load_design_contract(path: Path | None = None, *, root: Path | None = None) -> JsonObject:
    """读取项目内康哲设计合同 manifest。"""

    base = root or Path(__file__).resolve().parents[4]
    candidate = path or (base / "contracts" / "kangzhe" / "manifest.json")
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourcePackBuildError(f"设计合同 manifest 读取失败：{candidate}") from exc
    if not isinstance(payload, dict):
        raise SourcePackBuildError("设计合同 manifest 顶层必须是对象")
    return cast(JsonObject, payload)


def _resolve_design_contract(
    design_contract: Mapping[str, Any] | Path | None,
    *,
    report: ReportKey,
) -> _DesignBinding:
    if design_contract is None:
        payload = load_design_contract()
    elif isinstance(design_contract, Path):
        payload = load_design_contract(design_contract)
    else:
        payload = _json_mapping(design_contract, field="设计合同")
    nested = payload.get("design_contract")
    if isinstance(nested, dict):
        # Callers may pass a report manifest's design_contract binding. Preserve
        # its explicit digest while still recording the project PPTX route.
        payload = cast(JsonObject, nested)
    route = payload.get("route", payload.get("route_id", "pptx"))
    if route != "pptx":
        raise SourcePackBuildError(f"PPTX 来源包只能绑定 pptx 设计轨，收到 {route!r}")
    explicit_digest = payload.get(
        "design_contract_sha256",
        payload.get("sha256", payload.get("digest")),
    )
    runtime = payload.get("runtime")
    source = payload.get("source")
    runtime_mapping = runtime if isinstance(runtime, dict) else {}
    source_mapping = source if isinstance(source, dict) else {}
    digest_value = (
        explicit_digest
        or runtime_mapping.get("collection_sha256")
        or source_mapping.get("stable_collection_sha256")
    )
    if digest_value is None:
        digest_value = _sha256_json(payload)
    digest = _sha(digest_value, field="设计合同摘要")
    contract_version = _text(
        payload.get("contract_version", payload.get("schema_version", "1.0")),
        field="设计合同版本",
    )
    manifest_path = _text(
        payload.get("manifest_path", payload.get("manifest", "contracts/kangzhe/manifest.json")),
        field="设计合同 manifest 路径",
    )
    raw_files: Any = payload.get("files")
    if raw_files is None:
        raw_files = runtime_mapping.get("files", source_mapping.get("design_specs_files", {}))
    files: list[SourcePackContractFile] = []
    if isinstance(raw_files, Mapping):
        for path, sha256 in sorted(raw_files.items(), key=lambda item: str(item[0])):
            files.append(
                SourcePackContractFile(
                    path=_text(path, field="设计合同文件路径"),
                    sha256=_sha(sha256, field="设计合同文件摘要"),
                )
            )
    elif isinstance(raw_files, list):
        for index, item in enumerate(raw_files):
            if not isinstance(item, Mapping):
                raise SourcePackBuildError(f"设计合同文件 #{index + 1} 必须是对象")
            item_payload = _json_mapping(item, field=f"设计合同文件 #{index + 1}")
            files.append(
                SourcePackContractFile(
                    path=_text(item_payload.get("path"), field="设计合同文件路径"),
                    sha256=_sha(item_payload.get("sha256"), field="设计合同文件摘要"),
                )
            )
    summary = SourcePackDesignContract(
        manifest_path=manifest_path,
        route="pptx",
        contract_version=contract_version,
        sha256=digest,
        files=tuple(files),
    )
    return _DesignBinding(summary=summary, digest=digest)


# ─── Markdown projection ───────────────────────────────────────────────────


def _format_scalar(value: Any) -> str:
    if value is None:
        return "未披露"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
    if isinstance(value, (list, tuple)):
        return "、".join(_format_scalar(item) for item in value)
    if isinstance(value, Mapping):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    header_values = [str(header).replace("|", "\\|") for header in headers]
    lines = [
        "| " + " | ".join(header_values) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = [_format_scalar(value) for value in row]
        if len(values) < len(headers):
            values.extend("未披露" for _ in range(len(headers) - len(values)))
        lines.append("| " + " | ".join(values[: len(headers)]) + " |")
    return lines


def _row_sort_key(row: Mapping[str, Any]) -> tuple[str, str]:
    for key in ("row_id", "id", "observation_id", "fact_id", "product_id", "trial_id"):
        value = row.get(key)
        if value is not None:
            return key, str(value)
    return "", json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _render_list_section(title: str, values: list[Any], *, level: int = 3) -> list[str]:
    lines = [f"{'#' * level} {title}", ""]
    if not values:
        lines.append("> 本字段在锁定快照中没有记录；不得将未披露解释为零。")
        lines.append("")
        return lines
    if all(isinstance(value, Mapping) for value in values):
        rows = [cast(Mapping[str, Any], value) for value in values]
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        # Keep stable source order for columns while making row order deterministic.
        rows = sorted(rows, key=_row_sort_key)
        lines.extend(_markdown_table(keys, [[row.get(key) for key in keys] for row in rows]))
        lines.append("")
        return lines
    lines.extend(f"- {_format_scalar(value)}" for value in values)
    lines.append("")
    return lines


def _render_mapping_section(title: str, value: Mapping[str, Any], *, level: int = 3) -> list[str]:
    lines = [f"{'#' * level} {title}", ""]
    scalar_rows: list[tuple[str, Any]] = []
    nested: list[tuple[str, Any]] = []
    for key in sorted(value):
        child = value[key]
        if isinstance(child, (Mapping, list)):
            nested.append((str(key), child))
        else:
            scalar_rows.append((str(key), child))
    if scalar_rows:
        lines.extend(_markdown_table(("字段", "值"), scalar_rows))
        lines.append("")
    if not scalar_rows and not nested:
        lines.append("> 本字段为空；不得据此推断医学事实。")
        lines.append("")
    for key, child in nested:
        if isinstance(child, list):
            lines.extend(_render_list_section(key, child, level=min(level + 1, 6)))
        else:
            lines.extend(
                _render_mapping_section(
                    key,
                    cast(Mapping[str, Any], child),
                    level=min(level + 1, 6),
                )
            )
    return lines


def _render_report_data(data: JsonObject) -> tuple[list[str], dict[str, int]]:
    lines: list[str] = ["## 5. 锁定报告结构化事实", ""]
    fact_counts: dict[str, int] = {}
    keys = [key for key in _DATA_SECTION_ORDER if key in data]
    keys.extend(sorted(key for key in data if key not in _METADATA_KEYS and key not in keys))
    for key in keys:
        value = data[key]
        if isinstance(value, list):
            fact_counts[key] = len(value)
            lines.extend(_render_list_section(key, value))
        elif isinstance(value, Mapping):
            child_counts = _nested_list_counts(value, prefix=key)
            fact_counts.update(child_counts)
            lines.extend(_render_mapping_section(key, value))
        else:
            # Unknown scalar fields are retained rather than dropped.
            fact_counts[key] = 1
            lines.extend(_render_mapping_section(key, {"值": value}))
    if not keys:
        lines.append("> 锁定报告没有可投影的业务字段。")
        lines.append("")
    return lines, dict(sorted(fact_counts.items()))


def _nested_list_counts(value: Mapping[str, Any], *, prefix: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, child in value.items():
        child_prefix = f"{prefix}.{key}"
        if isinstance(child, list):
            counts[child_prefix] = len(child)
        elif isinstance(child, Mapping):
            counts.update(_nested_list_counts(child, prefix=child_prefix))
    return counts


def _build_markdown(
    *,
    report: ReportKey,
    report_data: JsonObject,
    snapshot: _SnapshotBinding,
    coverage: _CoverageBinding,
    pages: _PageBinding,
    design: _DesignBinding,
) -> tuple[str, dict[str, int]]:
    indication = _text(report_data["indication"], field="适应症")
    report_version = _text(report_data["report_version"], field="报告版本")
    data_cutoff = _text(report_data["data_cutoff"], field="数据截止时间")
    lines: list[str] = [
        f"# PPT Master 来源包｜报告 {report}｜{indication}",
        "",
        "> 本文件由锁定报告快照、规范覆盖集合、冻结页面策略和项目内康哲 PPTX 设计合同确定性生成。",
        "> 仅供 PPT Master 内容策略与设计锁定阶段使用；不包含逐页 SVG，不生成或替代 PPTX。",
        "",
        "## 1. 快照与合同绑定",
        "",
    ]
    binding_rows = (
        ("报告类型", report),
        ("报告版本", report_version),
        ("适应症", indication),
        ("数据截止时间", data_cutoff),
        ("项目标识", snapshot.project_id),
        ("锁定快照", snapshot.snapshot_id),
        ("锁定快照摘要", snapshot.snapshot_sha256),
        ("声明快照", snapshot.claim_snapshot_id),
        ("证据快照", snapshot.evidence_snapshot_id),
        ("覆盖集合", snapshot.coverage_set_id),
        ("覆盖集合摘要", coverage.content_sha256),
        ("页面策略摘要", pages.digest),
        ("PPTX 设计合同摘要", design.digest),
    )
    lines.extend(_markdown_table(("绑定字段", "锁定值"), binding_rows))
    lines.extend(
        [
            "",
            "## 2. 页面策略（图表与完整表格责任）",
            "",
            "> 页面顺序、责任、可视化类型和证据抽屉均来自冻结页面策略；来源包不自行新增页面。",
            "",
        ]
    )
    page_rows = [
        (
            index,
            page.page_id,
            page.route,
            page.title_zh,
            page.responsibility_zh,
            "、".join(page.visuals) or "未指定",
            "是" if page.complete_table else "否",
            "、".join(page.filter_profiles) or "未指定",
            page.evidence_drawer_profile,
        )
        for index, page in enumerate(pages.pages, start=1)
    ]
    lines.extend(
        _markdown_table(
            (
                "序号",
                "页面 ID",
                "路由",
                "标题",
                "页面责任",
                "可视化",
                "完整表格",
                "筛选配置",
                "证据抽屉",
            ),
            page_rows,
        )
    )
    lines.extend(
        [
            "",
            "## 3. 覆盖集合摘要",
            "",
            "> 覆盖项只记录稳定身份和责任摘要；医学数值以锁定报告事实为准。",
            "",
        ]
    )
    coverage_rows = []
    for item in coverage.items:
        coverage_rows.append(
            (
                item.get("item_id"),
                item.get("kind", item.get("item_kind", "未分类")),
                item.get("page_responsibility_id", item.get("page_id", "未指定")),
                item.get("label_zh", item.get("label", "未命名覆盖项")),
                item.get("referenced_ids", item.get("references", "未指定")),
            )
        )
    if coverage_rows:
        lines.extend(
            _markdown_table(
                ("覆盖项 ID", "类型", "页面责任", "中文标签", "引用身份"),
                coverage_rows,
            )
        )
    else:
        lines.append("> 覆盖集仅提供 covered_item_ids；未携带逐项标签。")
    lines.extend(["", "## 4. PPTX 设计合同摘要", ""])
    lines.extend(
        _markdown_table(
            ("合同字段", "值"),
            (
                ("manifest", design.summary.manifest_path),
                ("路线", design.summary.route),
                ("合同版本", design.summary.contract_version),
                ("合同摘要", design.summary.sha256),
                ("锁定规则", "只使用项目内冻结合同；不依赖外部 Skill 软链接"),
                ("PPTX 边界", "图表、文字、图形和必要表格保持可编辑；禁止截图或整页图片"),
            ),
        )
    )
    lines.append("")
    data_lines, fact_counts = _render_report_data(report_data)
    lines.extend(data_lines)
    lines.extend(
        [
            "## 6. 生成边界与交接",
            "",
            "- 本来源包只承载锁定快照中的中文结构化事实、页面责任和合同绑定。",
            "- 数值、单位、分母、治疗组/对照组、时间点和披露状态不得在 PPT Master 中自行改写。",
            "- 未披露不解释为零；跨试验比较不得池化或生成综合评分。",
            "- 本任务不生成 SVG，不生成 PPTX；确认结果覆盖设计推荐值后方可进入 PPT Master "
            "串行作业。",
            "",
        ]
    )
    markdown = "\n".join(lines)
    if not markdown.endswith("\n"):
        markdown += "\n"
    if "<svg" in markdown.casefold():
        raise SourcePackBuildError("来源包 Markdown 不得包含 SVG 内容")
    return markdown, fact_counts


# ─── Public builder and persistence API ────────────────────────────────────


def _summary_digest(summary: SourcePackSummary) -> str:
    payload = summary.model_dump(mode="json")
    payload["summary_sha256"] = "0" * 64
    return _sha256_json(payload)


def build_source_pack(
    report: str | ReportKind,
    report_data: Mapping[str, Any] | BaseModel,
    snapshot: Mapping[str, Any] | BaseModel,
    coverage_set: Mapping[str, Any] | BaseModel,
    page_strategy: Mapping[str, Any] | BaseModel | None = None,
    design_contract: Mapping[str, Any] | Path | None = None,
    *,
    source_pack_path: str | None = None,
    summary_path: str | None = None,
) -> SourcePack:
    """从锁定报告数据构建一个中文 PPTX Markdown 来源包。

    ``page_strategy`` 和 ``design_contract`` 缺省时读取项目内冻结副本。
    函数只返回内存对象，不写任何文件；调用 ``write_source_pack`` 才会
    创建 Markdown 与摘要清单。
    """

    report_key, data = _resolve_report_data(report, report_data)
    snapshot_binding = _resolve_snapshot(snapshot, report=report_key, report_data=data)
    coverage_binding = _resolve_coverage(
        coverage_set,
        snapshot=snapshot_binding,
        report=report_key,
        report_data=data,
    )
    page_binding = _resolve_pages(page_strategy, report=report_key)
    design_binding = _resolve_design_contract(design_contract, report=report_key)
    markdown, fact_counts = _build_markdown(
        report=report_key,
        report_data=data,
        snapshot=snapshot_binding,
        coverage=coverage_binding,
        pages=page_binding,
        design=design_binding,
    )
    source_sha256 = _sha256_bytes(markdown.encode("utf-8"))
    source_path = source_pack_path or f"report-{report_key.casefold()}.md"
    summary_file_path = summary_path or f"report-{report_key.casefold()}.summary.json"
    source_pack_id = stable_id(
        "pptx-source-pack",
        snapshot_binding.project_id,
        report_key,
        snapshot_binding.report_version,
        snapshot_binding.snapshot_id,
    )
    summary = SourcePackSummary(
        source_pack_id=source_pack_id,
        project_id=snapshot_binding.project_id,
        report=report_key,
        report_version=snapshot_binding.report_version,
        indication=_text(data["indication"], field="适应症"),
        data_cutoff=_text(data["data_cutoff"], field="数据截止时间"),
        snapshot_id=snapshot_binding.snapshot_id,
        snapshot_sha256=snapshot_binding.snapshot_sha256,
        claim_snapshot_id=snapshot_binding.claim_snapshot_id,
        evidence_snapshot_id=snapshot_binding.evidence_snapshot_id,
        coverage_set_id=coverage_binding.coverage_set_id,
        coverage_set_sha256=coverage_binding.content_sha256,
        report_data_sha256=_sha256_json(data),
        page_strategy_sha256=page_binding.digest,
        design_contract_sha256=design_binding.digest,
        source_pack_path=_text(source_path, field="来源包路径"),
        source_pack_sha256=source_sha256,
        source_pack_byte_size=len(markdown.encode("utf-8")),
        summary_path=_text(summary_file_path, field="摘要路径"),
        summary_sha256="0" * 64,
        page_count=len(page_binding.pages),
        pages=page_binding.pages,
        coverage=SourcePackCoverage(
            coverage_set_id=coverage_binding.coverage_set_id,
            content_sha256=coverage_binding.content_sha256,
            item_count=len(coverage_binding.item_ids),
            item_ids=coverage_binding.item_ids,
            item_kind_counts=coverage_binding.item_kind_counts,
        ),
        fact_counts=fact_counts,
        source_keys=tuple(data.keys()),
        design_contract=design_binding.summary,
    )
    summary = summary.model_copy(update={"summary_sha256": _summary_digest(summary)})
    return SourcePack(markdown=markdown, summary=summary)


def build_pptx_source_pack(*args: Any, **kwargs: Any) -> SourcePack:
    """明确的 PPTX 命名别名。"""

    return build_source_pack(*args, **kwargs)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SourcePackBuildError(f"拒绝覆盖既有来源包产物：{path}")
    path.write_bytes(payload)


def write_source_pack(
    source_pack: SourcePack | None = None,
    output_dir: Path | None = None,
    *,
    report: str | ReportKind | None = None,
    report_data: Mapping[str, Any] | BaseModel | None = None,
    snapshot: Mapping[str, Any] | BaseModel | None = None,
    coverage_set: Mapping[str, Any] | BaseModel | None = None,
    page_strategy: Mapping[str, Any] | BaseModel | None = None,
    design_contract: Mapping[str, Any] | Path | None = None,
) -> tuple[Path, Path]:
    """写入 ``report-{a|b|c}.md`` 和对应摘要清单，返回两条路径。

    可直接传入已构建的 ``source_pack``，或传入 builder 所需的关键字参数。
    写入采用“不覆盖既有产物”策略，避免 PPT Master 误读旧快照来源包。
    """

    if source_pack is None:
        if report is None or report_data is None or snapshot is None or coverage_set is None:
            raise SourcePackBuildError(
                "写入来源包需要 source_pack，或完整的 "
                "report/report_data/snapshot/coverage_set"
            )
        source_pack = build_source_pack(
            report,
            report_data,
            snapshot,
            coverage_set,
            page_strategy,
            design_contract,
        )
    if output_dir is None:
        raise SourcePackBuildError("写入来源包需要 output_dir")
    output_dir = Path(output_dir)
    source_path = output_dir / Path(source_pack.summary.source_pack_path)
    summary_path = output_dir / Path(source_pack.summary.summary_path)
    source_bytes = source_pack.markdown.encode("utf-8")
    _write_bytes(source_path, source_bytes)
    summary_bytes = _canonical_bytes(source_pack.summary.model_dump(mode="json"))
    try:
        _write_bytes(summary_path, summary_bytes)
    except Exception:
        # Do not leave a source file if the paired summary cannot be written.
        source_path.unlink(missing_ok=True)
        raise
    return source_path, summary_path


def write_pptx_source_pack(*args: Any, **kwargs: Any) -> tuple[Path, Path]:
    """明确的 PPTX 命名写入别名。"""

    return write_source_pack(*args, **kwargs)


def load_source_pack_summary(path: Path) -> SourcePackSummary:
    """读取并验证来源包摘要清单。"""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourcePackBuildError(f"来源包摘要读取失败：{path}") from exc
    try:
        summary = SourcePackSummary.model_validate(payload)
    except PydanticValidationError as exc:
        raise SourcePackBuildError(f"来源包摘要不符合类型合同：{path}") from exc
    validate_source_pack_summary(summary)
    return summary


def _load_schema() -> JsonObject:
    module_path = Path(__file__).resolve()
    candidates = (
        module_path.parents[4] / "schemas" / _SCHEMA_FILENAME,
        module_path.parents[2] / "schemas" / _SCHEMA_FILENAME,
    )
    for candidate in candidates:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except (OSError, json.JSONDecodeError) as exc:
            raise SourcePackBuildError(f"来源包 Schema 损坏：{candidate}") from exc
        if not isinstance(payload, dict):
            raise SourcePackBuildError("来源包 Schema 顶层必须是对象")
        return cast(JsonObject, payload)
    raise SourcePackBuildError("无法定位 PPTX 来源包 Schema")


def validate_source_pack_summary(
    summary: SourcePackSummary | Mapping[str, Any],
    *,
    markdown: str | bytes | Path | None = None,
) -> SourcePackSummary:
    """执行 Schema、摘要自洽和可选 Markdown 字节摘要校验。"""

    try:
        model = (
            summary
            if isinstance(summary, SourcePackSummary)
            else SourcePackSummary.model_validate(summary)
        )
    except PydanticValidationError as exc:
        raise SourcePackBuildError("来源包摘要不符合类型合同") from exc
    schema = _load_schema()
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
                model.model_dump(mode="json")
            ),
            key=lambda error: list(error.path),
        )
    except Exception as exc:
        raise SourcePackBuildError("来源包 Schema 校验失败") from exc
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise SourcePackBuildError(f"来源包摘要不符合 Schema：{details}")
    if _summary_digest(model) != model.summary_sha256:
        raise SourcePackBuildError("来源包摘要自身摘要不一致")
    if markdown is not None:
        if isinstance(markdown, Path):
            try:
                markdown_bytes = markdown.read_bytes()
            except OSError as exc:
                raise SourcePackBuildError(f"来源包 Markdown 读取失败：{markdown}") from exc
        elif isinstance(markdown, str):
            markdown_bytes = markdown.encode("utf-8")
        else:
            markdown_bytes = markdown
        actual = _sha256_bytes(markdown_bytes)
        if actual != model.source_pack_sha256:
            raise SourcePackBuildError(
                f"来源包 Markdown 摘要不一致：实际 {actual}，清单 {model.source_pack_sha256}"
            )
        if b"<svg" in markdown_bytes.lower():
            raise SourcePackBuildError("来源包 Markdown 不得包含逐页 SVG")
    return model


__all__ = [
    "SourcePack",
    "SourcePackBuildError",
    "SourcePackCoverage",
    "SourcePackDesignContract",
    "SourcePackPage",
    "SourcePackSummary",
    "build_pptx_source_pack",
    "build_source_pack",
    "load_design_contract",
    "load_page_strategy",
    "load_source_pack_summary",
    "validate_source_pack_summary",
    "write_pptx_source_pack",
    "write_source_pack",
]
