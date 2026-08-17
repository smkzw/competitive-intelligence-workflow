"""Task 4.1 页面注册表：从冻结 A/B/C 页面目录加载静态责任与动态详情责任。

静态页面逐项读取冻结目录，不重复维护页面清单；动态产品/试验详情路由
责任在代码中显式声明，与静态页分离。站点地图由全部提供的快照产品/试验
确定性展开，绝不 Top-N 或固定示例。

目录解析支持两种布局：仓库根 ``docs/architecture/page-catalogs/`` 与
包内数据副本 ``reports/common/page-catalogs/``（随轮分发，逐字一致由
合同测试保证）；生产 ``load()`` 自动按源码树 → 包内数据顺序解析，
不接受调用方选择生产路径。

加载器分离：生产 ``load()`` 只经专用私有路径 ``_load_frozen_catalogs``
加载内部解析的冻结目录；测试/内部目录走独立覆盖点 ``_load_from_dir``。
两者共享 ``_build_registry_from_dir`` 的解析/校验语义，但生产调用链
绝不经过测试覆盖点（monkeypatch 该辅助不影响生产验证）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)

from ci_workflow.domain.enums import ReportKind

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_STATIC_ROUTE_RE = re.compile(r"^/[abc]/[a-z0-9-]+$")
_DYNAMIC_ROUTE_RE = re.compile(r"^/[abc]/[a-z0-9-]+/\{[a-z0-9_]+\}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_REPORT_LETTERS = ("A", "B", "C")


class PageRegistryError(ValueError):
    """页面注册表边界拒绝：未知报告类型、重复或自由路由、非法站点地图输入。"""


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


def _has_chinese(value: str) -> bool:
    return _CJK_RE.search(value) is not None


class StaticPage(BaseModel):
    """目录中的一个静态页面：路由是页面 ID 的确定性身份，不是自由文本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    route: str
    title_zh: str
    navigation_group_zh: str
    responsibility_zh: str
    visuals: tuple[str, ...] = Field(min_length=1)
    complete_table: bool
    filter_profiles: tuple[str, ...] = Field(min_length=1)
    evidence_drawer_profile: str
    empty_numeric_fallback: str | None = None

    @field_validator("id", "route", "evidence_drawer_profile")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("title_zh", "navigation_group_zh", "responsibility_zh")
    @classmethod
    def _copy_has_chinese(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized or not _has_chinese(normalized):
            raise ValueError("用户可见页面文案必须为原生中文（不能为空）")
        return normalized

    @field_validator("visuals", "filter_profiles")
    @classmethod
    def _entries_unique_nonblank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_text(v) for v in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("页面清单条目不能重复")
        return normalized

    @field_validator("empty_numeric_fallback")
    @classmethod
    def _fallback_blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _text(value)
        if not _has_chinese(normalized):
            raise ValueError("空数值回退文案必须为原生中文")
        return normalized


class DynamicRouteSpec(BaseModel):
    """动态详情路由责任：产品详情或试验详情，与静态页面责任分离。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    route_kind: str
    route_template: str
    page_responsibility_id: str
    identity_field: str

    @field_validator("route_kind")
    @classmethod
    def _route_kind_closed(cls, value: str) -> str:
        if value not in ("product_detail", "trial_detail"):
            raise ValueError("动态路由类型必须为 product_detail 或 trial_detail")
        return value

    @field_validator("identity_field")
    @classmethod
    def _identity_field_closed(cls, value: str) -> str:
        if value not in ("product_id", "trial_id"):
            raise ValueError("动态路由身份字段必须为 product_id 或 trial_id")
        return value

    @field_validator("route_template", "page_responsibility_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _template_and_kind_consistent(self) -> DynamicRouteSpec:
        if (self.route_kind == "product_detail") != (self.identity_field == "product_id"):
            raise ValueError("动态路由类型与身份字段不一致")
        if not _DYNAMIC_ROUTE_RE.fullmatch(self.route_template):
            raise ValueError(f"动态路由模板不是合法身份路由：{self.route_template}")
        if "{" + self.identity_field + "}" not in self.route_template:
            raise ValueError("动态路由模板必须包含对应身份占位符")
        return self


# 报告类型 -> 动态详情路由责任（与冻结目录静态页分离，页面责任必须在目录内）。
_DYNAMIC_ROUTE_DEFS: Mapping[ReportKind, tuple[dict[str, str], ...]] = {
    ReportKind.A: (
        {
            "route_kind": "product_detail",
            "path": "products",
            "identity_field": "product_id",
            "page_responsibility_id": "product-overview",
        },
    ),
    ReportKind.B: (
        {
            "route_kind": "product_detail",
            "path": "products",
            "identity_field": "product_id",
            "page_responsibility_id": "product-trial-profiles",
        },
        {
            "route_kind": "trial_detail",
            "path": "trials",
            "identity_field": "trial_id",
            "page_responsibility_id": "product-trial-profiles",
        },
    ),
    ReportKind.C: (
        {
            "route_kind": "trial_detail",
            "path": "trials",
            "identity_field": "trial_id",
            "page_responsibility_id": "trial-profile",
        },
    ),
}

_PAGE_FIELD_ALIASES: Mapping[str, str] = {
    "title": "title_zh",
    "navigation_group": "navigation_group_zh",
    "responsibility": "responsibility_zh",
}


class ReportCatalog(BaseModel):
    """一份冻结报告目录：静态页 + 动态详情路由责任。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportKind
    contract_version: str
    pages: tuple[StaticPage, ...] = Field(min_length=1)
    dynamic_routes: tuple[DynamicRouteSpec, ...] = Field(min_length=1)

    @field_validator("contract_version")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @model_validator(mode="after")
    def _routes_are_deterministic_identities(self) -> ReportCatalog:
        page_ids = [p.id for p in self.pages]
        if len(set(page_ids)) != len(page_ids):
            raise ValueError("目录页面 ID 重复，必须失败关闭")
        for page in self.pages:
            expected = f"/{self.report.value.casefold()}/{page.id}"
            if page.route != expected:
                raise ValueError(
                    f"路由必须是页面 ID 的确定性身份：{page.route} != {expected}"
                )
        templates = [spec.route_template for spec in self.dynamic_routes]
        if len(set(templates)) != len(templates):
            raise ValueError("动态路由模板重复，必须失败关闭")
        for spec in self.dynamic_routes:
            if spec.route_template.startswith(f"/{self.report.value.casefold()}/"):
                continue
            raise ValueError(f"动态路由模板报告前缀与目录不一致：{spec.route_template}")
        known_pages = set(page_ids)
        for spec in self.dynamic_routes:
            if spec.page_responsibility_id not in known_pages:
                raise ValueError(
                    f"动态责任引用了目录外页面：{spec.page_responsibility_id}"
                )
        return self


class PageRegistry(BaseModel):
    """A/B/C 三个冻结目录的只读注册表，提供确定性站点地图展开。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    catalogs: tuple[ReportCatalog, ...]

    @classmethod
    def _search_paths(cls) -> tuple[Path, ...]:
        """目录解析顺序：仓库根冻结目录 → 包内数据副本（随轮分发）。

        安装布局不存在仓库根 ``docs/architecture``，因此必须回退到模块
        同目录的包内数据副本；两者逐字一致由合同测试保证。
        """
        module_dir = Path(__file__).resolve().parent
        return (
            Path(__file__).resolve().parents[4]
            / "docs" / "architecture" / "page-catalogs",
            module_dir / "page-catalogs",
        )

    @classmethod
    def load(cls) -> PageRegistry:
        """从冻结 A/B/C 页面目录加载注册表（生产公开 API）。

        不接受调用方选择目录：按源码树 → 包内数据顺序自动解析，两处均
        缺失时失败关闭。生产只走专用私有路径 ``_load_frozen_catalogs``，
        绝不经过测试覆盖点 ``_load_from_dir``（monkeypatch 该辅助不影响
        生产加载或任何生产验证器）。
        """
        for candidate in cls._search_paths():
            if candidate.is_dir():
                return cls._load_frozen_catalogs(candidate)
        raise PageRegistryError(
            "冻结页面目录缺失：源码树与包内数据布局均不可用"
        )

    @classmethod
    def _load_frozen_catalogs(cls, catalog_dir: Path) -> PageRegistry:
        """生产专用私有路径：从内部解析的冻结目录构建注册表。

        与测试辅助 ``_load_from_dir`` 严格分离：生产调用链
        （``load`` → ``_load_frozen_catalogs`` → ``_build_registry_from_dir``）
        不经过测试覆盖点；对 ``_load_from_dir`` 的 monkeypatch 不影响生产。
        """
        return _build_registry_from_dir(catalog_dir)

    @classmethod
    def _load_from_dir(cls, catalog_dir: Path) -> PageRegistry:
        """测试/内部专用：从调用方提供的目录加载 A/B/C；生产绝不调用。

        与生产路径共享 ``_build_registry_from_dir`` 的解析/校验语义，
        但作为独立覆盖点存在，生产调用链不引用本方法。
        """
        return _build_registry_from_dir(catalog_dir)

    def catalog(self, report: ReportKind) -> ReportCatalog:
        for catalog in self.catalogs:
            if catalog.report is report:
                return catalog
        raise PageRegistryError(f"未知报告类型：{report.value}")

    def page_responsibility_ids(self, report: ReportKind) -> frozenset[str]:
        """报告的全部页面责任：静态页 ID 与动态详情责任（两者都来自目录）。"""
        catalog = self.catalog(report)
        ids = {page.id for page in catalog.pages}
        ids.update(spec.page_responsibility_id for spec in catalog.dynamic_routes)
        return frozenset(ids)

    def sitemap(
        self,
        report: ReportKind,
        *,
        product_ids: Sequence[str] = (),
        trial_ids: Sequence[str] = (),
    ) -> tuple[str, ...]:
        """静态路由 + 全部提供快照产品/试验的详情路由，确定性展开。

        绝不 Top-N 或固定示例：提供的每一个产品/试验都生成路由；
        提供集合为空时只返回静态路由。
        """
        catalog = self.catalog(report)
        static = tuple(page.route for page in sorted(catalog.pages, key=lambda p: p.id))
        dynamic: list[str] = []
        for spec in catalog.dynamic_routes:
            ids = (
                product_ids if spec.identity_field == "product_id" else trial_ids
            )
            _assert_slug_ids(ids, spec.identity_field)
            for slug in sorted(ids):
                dynamic.append(spec.route_template.format(**{spec.identity_field: slug}))
        return (*static, *dynamic)


def _build_registry_from_dir(catalog_dir: Path) -> PageRegistry:
    """从单个目录解析并构建 A/B/C 注册表（共享核心，非覆盖点）。

    生产（``_load_frozen_catalogs``）与测试（``_load_from_dir``）共用本
    函数以避免复制解析/校验语义；它不是被 monkeypatch 的测试覆盖点。
    """
    catalogs: list[ReportCatalog] = []
    for path in sorted(catalog_dir.glob("*.yaml")):
        payload = _load_catalog_file(path)
        catalogs.append(payload)
    by_report = {catalog.report: catalog for catalog in catalogs}
    missing = [
        letter
        for letter in _REPORT_LETTERS
        if ReportKind(letter) not in by_report
    ]
    if missing:
        raise PageRegistryError(f"冻结页面目录缺失报告类型：{'、'.join(missing)}")
    ordered = tuple(by_report[ReportKind(letter)] for letter in _REPORT_LETTERS)
    return PageRegistry(catalogs=ordered)


def _load_catalog_file(path: Path) -> ReportCatalog:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise PageRegistryError(f"页面目录 YAML 损坏：{path.name}") from error
    if not isinstance(raw, dict):
        raise PageRegistryError(f"页面目录必须是映射：{path.name}")
    try:
        report = ReportKind(cast(str, raw["report"]))
    except (KeyError, ValueError) as error:
        raise PageRegistryError(
            f"未知报告类型：{raw.get('report')!r}（{path.name}）"
        ) from error
    if path.stem.upper() != report.value:
        raise PageRegistryError(
            f"目录文件与报告类型不一致：{path.name} 声明 {report.value}"
        )
    pages = cast(list[Any], raw.get("pages", []))
    page_payloads = [
        {
            **{_PAGE_FIELD_ALIASES.get(key, key): value for key, value in page.items()},
        }
        for page in pages
    ]
    static_pages = tuple(StaticPage.model_validate(page) for page in page_payloads)
    dynamic_routes = tuple(
        DynamicRouteSpec.model_validate(
            {
                "route_kind": definition["route_kind"],
                "route_template": (
                    f"/{report.value.casefold()}/{definition['path']}"
                    f"/{{{definition['identity_field']}}}"
                ),
                "page_responsibility_id": definition["page_responsibility_id"],
                "identity_field": definition["identity_field"],
            }
        )
        for definition in _DYNAMIC_ROUTE_DEFS[report]
    )
    try:
        return ReportCatalog(
            report=report,
            contract_version=cast(str, raw["contract_version"]),
            pages=static_pages,
            dynamic_routes=dynamic_routes,
        )
    except (PydanticValidationError, KeyError, TypeError) as error:
        raise PageRegistryError(
            f"页面目录校验失败：{path.name}：{error}"
        ) from error


def _assert_slug_ids(ids: Sequence[str], field: str) -> None:
    seen: set[str] = set()
    for value in ids:
        if not isinstance(value, str) or not _SLUG_RE.fullmatch(value):
            raise PageRegistryError(
                f"站点地图{field}必须是稳定标识 slug（含路径或空白被拒绝）：{value!r}"
            )
        if value in seen:
            raise PageRegistryError(f"站点地图{field}重复：{value}")
        seen.add(value)
