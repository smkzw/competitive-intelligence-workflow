"""Task 4.6 只读浏览器验收：站点地图一一对应枚举合同与只读缺陷检测。

站点地图由冻结页面注册表与锁定快照中的产品/试验身份确定性展开：
每个静态责任页、每个产品详情页、每个试验详情页一一对应。缺页、
多页（重复）、Top-N 截断与额外 slug 均失败关闭；验收器只报告与
否决，绝不修改被验收站点。

本模块是任务 4.6 三件工作项的共享只读判定模型：站点地图集合一一
对应枚举合同（worker_01）、路由可达性合同（P1 修复：从站点入口沿
本地 HTML 锚点遍历期望站点地图，孤儿详情页在浏览器截图前失败关闭）、
死链/控制台与页面错误/非本地请求/页脚唯一性/横向溢出/固定元素遮挡
缺陷检测（worker_02）与 CLI/多浏览器/截图/trace（worker_03）消费本
合同的期望与实际路由及页面观察，不得重写本模块已冻结的语义。

worker_03 的期望站点地图来源是锁定报告产物：CLI 从当前报告版本的
``reports/<报告>/<版本>/html.manifest.json`` 与清单引用的不可变报告
快照读取产品/试验身份，并核对站点目录摘要与清单一致后才构造站点地
图；本模块提供该只读、失败关闭的锁定来源加载器，绝不修改项目文件。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)

from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.reports.common.page_registry import (
    PageRegistry,
    PageRegistryError,
)
from ci_workflow.storage.manifest_store import ArtifactManifest
from ci_workflow.storage.snapshot_store import ReportSnapshotManifest

_SLUG_PATTERN = r"[a-z0-9][a-z0-9-]*"
_HTML_SUFFIX = ".html"


def _text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("文本不能为空")
    return normalized


class SitemapBoundaryError(ValueError):
    """站点地图合同边界拒绝：非法身份、无法归属路由或非法站点布局。"""


class SitemapKind(StrEnum):
    """站点地图条目责任类型封闭集合：静态责任页与两类动态详情页。"""

    STATIC = "static"
    PRODUCT_DETAIL = "product_detail"
    TRIAL_DETAIL = "trial_detail"


class SitemapEntry(BaseModel):
    """站点地图单条路由：注册表静态责任页或快照产品/试验详情页。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    route: str
    kind: SitemapKind
    page_responsibility_id: str
    identity: str | None = None

    @field_validator("route", "page_responsibility_id")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("identity")
    @classmethod
    def _identity_blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _text(value)
        return normalized


class SitemapContract(BaseModel):
    """期望站点地图：注册表全部静态责任页 + 快照每一个产品/试验详情页。

    绝不 Top-N 或固定示例：提供的每一个产品/试验身份都生成详情路由；
    静态与详情责任必须都能归属到冻结目录。路由顺序遵循注册表合同：
    静态责任页在前（按页面标识排序），动态详情路由在后（按身份排序）。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: ReportKind
    entries: tuple[SitemapEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _routes_unique_and_kind_consistent(self) -> SitemapContract:
        routes = [entry.route for entry in self.entries]
        if len(set(routes)) != len(routes):
            raise ValueError("期望站点地图不允许重复路由")
        for entry in self.entries:
            is_static = entry.kind is SitemapKind.STATIC
            if is_static == (entry.identity is not None):
                raise ValueError("静态责任页不得携带身份，动态详情页必须携带身份")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def routes(self) -> tuple[str, ...]:
        return tuple(entry.route for entry in self.entries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def static_routes(self) -> frozenset[str]:
        return frozenset(entry.route for entry in self.entries if entry.kind is SitemapKind.STATIC)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def product_routes(self) -> frozenset[str]:
        return frozenset(
            entry.route for entry in self.entries if entry.kind is SitemapKind.PRODUCT_DETAIL
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def trial_routes(self) -> frozenset[str]:
        return frozenset(
            entry.route for entry in self.entries if entry.kind is SitemapKind.TRIAL_DETAIL
        )

    def kind_for(self, route: str) -> SitemapKind:
        """返回期望路由的责任类型；路由不在期望站点地图中时失败关闭。"""
        for entry in self.entries:
            if entry.route == route:
                return entry.kind
        raise SitemapBoundaryError(f"路由不在期望站点地图中：{route}")


def _compile_dynamic_template(template: str) -> re.Pattern[str]:
    """动态路由模板 → 完整匹配正则：``/a/products/{product_id}`` → 身份 slug。"""
    parts: list[str] = []
    for segment in template.split("/"):
        if segment.startswith("{") and segment.endswith("}"):
            parts.append(_SLUG_PATTERN)
        else:
            parts.append(re.escape(segment))
    return re.compile("^" + "/".join(parts) + "$")


def derive_sitemap_contract(
    registry: PageRegistry,
    report: ReportKind,
    *,
    product_ids: Sequence[str] = (),
    trial_ids: Sequence[str] = (),
) -> SitemapContract:
    """从冻结注册表与快照产品/试验身份确定性展开期望站点地图。

    提供的每一个产品/试验都生成详情路由，绝不 Top-N 或固定示例；
    非法身份（非 slug、重复）在注册表展开时失败关闭并转为本合同的
    边界错误。静态责任与动态详情责任必须归属冻结目录。
    """
    catalog = registry.catalog(report)
    try:
        routes = registry.sitemap(report, product_ids=product_ids, trial_ids=trial_ids)
    except PageRegistryError as error:
        raise SitemapBoundaryError(str(error)) from error

    static_by_route = {page.route: page for page in catalog.pages}
    dynamic_specs = [
        (spec, _compile_dynamic_template(spec.route_template)) for spec in catalog.dynamic_routes
    ]
    entries: list[SitemapEntry] = []
    for route in routes:
        static = static_by_route.get(route)
        if static is not None:
            entries.append(
                SitemapEntry(
                    route=route,
                    kind=SitemapKind.STATIC,
                    page_responsibility_id=static.id,
                    identity=None,
                )
            )
            continue
        for spec, pattern in dynamic_specs:
            if pattern.fullmatch(route) is None:
                continue
            kind = (
                SitemapKind.PRODUCT_DETAIL
                if spec.route_kind == "product_detail"
                else SitemapKind.TRIAL_DETAIL
            )
            entries.append(
                SitemapEntry(
                    route=route,
                    kind=kind,
                    page_responsibility_id=spec.page_responsibility_id,
                    identity=route.rsplit("/", 1)[-1],
                )
            )
            break
        else:
            raise SitemapBoundaryError(f"路由无法归属任何注册责任：{route}")
    return SitemapContract(report=report, entries=tuple(entries))


class SitemapViolationCode(StrEnum):
    """站点地图违例机器码：缺页、多页与额外页面。"""

    MISSING_STATIC_PAGE = "missing_static_page"
    MISSING_PRODUCT_DETAIL = "missing_product_detail"
    MISSING_TRIAL_DETAIL = "missing_trial_detail"
    EXTRA_ROUTE = "extra_route"
    DUPLICATE_ACTUAL_ROUTE = "duplicate_actual_route"


_KIND_LABELS: dict[SitemapKind, str] = {
    SitemapKind.STATIC: "静态责任页",
    SitemapKind.PRODUCT_DETAIL: "产品详情页",
    SitemapKind.TRIAL_DETAIL: "试验详情页",
}

_MISSING_CODE_BY_KIND: dict[SitemapKind, SitemapViolationCode] = {
    SitemapKind.STATIC: SitemapViolationCode.MISSING_STATIC_PAGE,
    SitemapKind.PRODUCT_DETAIL: SitemapViolationCode.MISSING_PRODUCT_DETAIL,
    SitemapKind.TRIAL_DETAIL: SitemapViolationCode.MISSING_TRIAL_DETAIL,
}


class SitemapViolation(BaseModel):
    """单条站点地图违例：机器码 + 路由 + 用户可见中文说明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: SitemapViolationCode
    route: str
    message_zh: str

    @field_validator("route", "message_zh")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)


class SitemapVerification(BaseModel):
    """一一对应验收结果：通过与否决及全部违例；验收器不修改被验收站点。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    expected_routes: tuple[str, ...]
    actual_routes: tuple[str, ...]
    violations: tuple[SitemapViolation, ...]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def message_zh(self) -> str:
        """用户可见中文结论：通过或按违例类型汇总的失败说明。"""
        if self.ok:
            return "站点地图一一对应验收通过：静态责任页、产品详情页与试验详情页全部齐备。"
        groups: dict[SitemapViolationCode, list[str]] = {}
        for violation in self.violations:
            groups.setdefault(violation.code, []).append(violation.route)
        parts: list[str] = []
        for code in SitemapViolationCode:
            routes = groups.get(code)
            if not routes:
                continue
            label = {
                SitemapViolationCode.MISSING_STATIC_PAGE: "缺少静态责任页",
                SitemapViolationCode.MISSING_PRODUCT_DETAIL: "缺少产品详情页",
                SitemapViolationCode.MISSING_TRIAL_DETAIL: "缺少试验详情页",
                SitemapViolationCode.EXTRA_ROUTE: "存在站点地图之外的页面",
                SitemapViolationCode.DUPLICATE_ACTUAL_ROUTE: "站点地图路由重复出现",
            }[code]
            listed = "、".join(routes[:3])
            if len(routes) > 3:
                listed = f"{listed} 等 {len(routes)} 个"
            parts.append(f"{label}：{listed}")
        return "站点地图一一对应验收失败：" + "；".join(parts)


def verify_sitemap_one_to_one(
    contract: SitemapContract,
    actual_routes: Sequence[str],
) -> SitemapVerification:
    """期望与实际站点地图的集合一一对应；缺页、多页、额外 slug 失败关闭。

    缺页（含 Top-N 截断导致的详情页缺失）按责任类型分类否决；
    实际中重复出现与期望之外的页面同样否决。只报告与否决。
    """
    actual = tuple(actual_routes)
    expected = contract.routes
    expected_set = set(expected)
    actual_set = set(actual)
    violations: list[SitemapViolation] = []

    seen: set[str] = set()
    for route in actual:
        if route in seen:
            violations.append(
                SitemapViolation(
                    code=SitemapViolationCode.DUPLICATE_ACTUAL_ROUTE,
                    route=route,
                    message_zh=f"站点地图路由重复出现：{route}",
                )
            )
        seen.add(route)

    entry_by_route = {entry.route: entry for entry in contract.entries}
    for route in expected:
        if route in actual_set:
            continue
        kind = entry_by_route[route].kind
        violations.append(
            SitemapViolation(
                code=_MISSING_CODE_BY_KIND[kind],
                route=route,
                message_zh=f"缺少{_KIND_LABELS[kind]}：{route}",
            )
        )

    for route in sorted(actual_set - expected_set):
        violations.append(
            SitemapViolation(
                code=SitemapViolationCode.EXTRA_ROUTE,
                route=route,
                message_zh=f"发现站点地图之外的页面：{route}",
            )
        )

    return SitemapVerification(
        ok=not violations,
        expected_routes=expected,
        actual_routes=actual,
        violations=tuple(violations),
    )


def route_to_site_path(route: str) -> Path:
    """路由 → 站点相对物理文件：静态平铺、动态按类目目录。

    ``/a/overview`` → ``overview.html``；``/a/products/product-01`` →
    ``products/product-01.html``；``/c/trials/trial-01`` →
    ``trials/trial-01.html``。非法路由失败关闭。
    """
    segments = [segment for segment in route.split("/") if segment]
    if len(segments) == 2:
        return Path(f"{segments[1]}{_HTML_SUFFIX}")
    if len(segments) == 3:
        return Path(segments[1]) / f"{segments[2]}{_HTML_SUFFIX}"
    raise SitemapBoundaryError(f"无法将路由映射为站点物理文件：{route}")


def enumerate_site_routes(site_root: Path, report: ReportKind) -> tuple[str, ...]:
    """从产物站点物理文件确定性枚举实际路由（含报告前缀）。

    布局：静态责任页为 ``<page-id>.html``，动态详情为
    ``<kind-path>/<slug>.html``。所有 ``*.html`` 都映射为完整路由
    （``index.html`` 等布局外文件同样计入），交由一一对应检查判定
    缺页或额外页面；非 HTML 资源（CSS/JS/Logo）不计入站点地图。
    """
    prefix = f"/{report.value.casefold()}"
    routes: list[str] = []
    for path in sorted(site_root.rglob(f"*{_HTML_SUFFIX}")):
        relative = path.relative_to(site_root)
        parts = [
            part[: -len(_HTML_SUFFIX)] if part.endswith(_HTML_SUFFIX) else part
            for part in relative.parts
        ]
        routes.append(f"{prefix}/{'/'.join(parts)}")
    return tuple(routes)


# ===========================================================================
# 路由可达性合同（P1 修复）：从站点入口沿本地 HTML 锚点遍历期望站点地图。
# 每个期望路由（尤其每个产品/试验动态详情页）都必须能从入口经站点内链接
# 到达；文件存在但门户内没有任何入口的孤儿页，在浏览器截图前失败关闭。
# 链接解析与死链判定共用 ``resolve_local_link``，不另设一套更弱的 URL 规则；
# 站外、页内锚点、mailto/tel/脚本等不可验证链接不构成站点入口。验收器只
# 消费页面观察并报告与否决，绝不修改被验收站点。
# ===========================================================================


def site_path_to_route(path: Path, report: ReportKind) -> str | None:
    """站点相对物理文件 → 路由（``route_to_site_path`` 的逆映射）。

    非 HTML 文件（CSS/JS/Logo 等资源）不产生路由，返回 None。
    """
    parts = path.parts
    if not parts or not parts[-1].endswith(_HTML_SUFFIX):
        return None
    stem = parts[-1][: -len(_HTML_SUFFIX)]
    segments = (*parts[:-1], stem)
    return f"/{report.value.casefold()}/{'/'.join(segments)}"


class ReachabilityViolationCode(StrEnum):
    """路由可达性违例机器码：期望路由不可达。"""

    UNREACHABLE_ROUTE = "unreachable_route"


class ReachabilityViolation(BaseModel):
    """单条可达性违例：机器码 + 路由 + 用户可见中文说明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: ReachabilityViolationCode
    route: str
    message_zh: str

    @field_validator("route", "message_zh")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)


class ReachabilityVerification(BaseModel):
    """可达性验收结果：从入口沿链接遍历后的通过与否决及不可达路由。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    start_route: str
    reachable_routes: tuple[str, ...]
    unreachable_routes: tuple[str, ...]
    violations: tuple[ReachabilityViolation, ...]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def message_zh(self) -> str:
        """用户可见中文结论：通过或点名不可达路由并给出修复指引。"""
        if self.ok:
            return (
                f"全站可达性验收通过：全部 {len(self.reachable_routes)} 个路由"
                f"均可从站点入口（{self.start_route}）通过页面链接到达。"
            )
        listed = "、".join(self.unreachable_routes[:5])
        if len(self.unreachable_routes) > 5:
            listed = f"{listed} 等 {len(self.unreachable_routes)} 个路由"
        return (
            "全站可达性验收失败：以下页面无法从站点入口（"
            f"{self.start_route}）通过页面链接到达，用户无法导航进入："
            f"{listed}。请在产品总览、临床开发组合或首页等页面为这些"
            "页面添加可见的中文入口链接。"
        )


def _overview_start_route(contract: SitemapContract) -> str:
    """可达性遍历入口：首页/总览静态责任页（页面标识为 overview）。"""
    for entry in contract.entries:
        if entry.kind is SitemapKind.STATIC and entry.page_responsibility_id == "overview":
            return entry.route
    raise SitemapBoundaryError("期望站点地图缺少首页/总览静态责任页，无法进行可达性验收")


def verify_route_reachability(
    contract: SitemapContract,
    inspections: Sequence[PageInspection],
) -> ReachabilityVerification:
    """从入口沿站点内 HTML 锚点遍历期望站点地图；不可达路由失败关闭。

    广度优先、确定性遍历：每个页面的本地链接经 ``resolve_local_link``
    解析为站点物理文件，再映射回路由；只有落在期望站点地图内的链接
    才构成边。站外、页内锚点、mailto/tel/脚本链接不构成入口。文件
    存在但无任何入边的期望路由（孤儿页）按类型逐条否决。只读验收，
    绝不修改站点。
    """
    start = _overview_start_route(contract)
    expected = set(contract.routes)
    by_route = {inspection.route: inspection for inspection in inspections}
    visited: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        route = queue.popleft()
        if route in visited:
            continue
        visited.add(route)
        inspection = by_route.get(route)
        if inspection is None:
            continue
        for link in inspection.links:
            target_path = resolve_local_link(route, link.href)
            if target_path is None:
                continue
            target_route = site_path_to_route(target_path, contract.report)
            if target_route is None or target_route not in expected:
                continue
            if target_route not in visited:
                queue.append(target_route)

    unreachable = tuple(route for route in contract.routes if route not in visited)
    violations = tuple(
        ReachabilityViolation(
            code=ReachabilityViolationCode.UNREACHABLE_ROUTE,
            route=route,
            message_zh=(
                f"页面缺少可见入口：{route} 只能通过直接打开文件访问，门户内没有任何页面链接到它"
            ),
        )
        for route in unreachable
    )
    return ReachabilityVerification(
        ok=not violations,
        start_route=start,
        reachable_routes=tuple(sorted(visited)),
        unreachable_routes=unreachable,
        violations=violations,
    )


# ===========================================================================
# 只读缺陷检测（worker_02）：死链、控制台/页面错误、非本地请求、页脚唯一
# 性、横向溢出与固定元素遮挡。验收器只消费观察并报告与否决，绝不修改被
# 验收站点；运行时观察（控制台、页面错误、视口与矩形）由真实浏览器收集，
# 静态 HTML 扫描补充链接、请求与页脚数量，两者共用同一判定模型。
# ===========================================================================

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})
_OVERFLOW_TOLERANCE_PX = 1.0
_OCCLUSION_MIN_OVERLAP_PX = 1.0


class Rect(BaseModel):
    """内容/固定元素矩形：几何判定输入，倒置坐标失败关闭。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    top: float
    left: float
    right: float
    bottom: float

    @model_validator(mode="after")
    def _rect_ordered(self) -> Rect:
        if self.top > self.bottom or self.left > self.right:
            raise ValueError("矩形坐标必须满足 top≤bottom 且 left≤right")
        return self


class LinkObservation(BaseModel):
    """页面锚点链接观察：原始 href 与可见文本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    href: str
    text: str = ""

    @field_validator("href")
    @classmethod
    def _href_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("text")
    @classmethod
    def _text_blank_to_empty(cls, value: str) -> str:
        return " ".join(value.split())


class ConsoleObservation(BaseModel):
    """控制台消息观察：类型封闭集合 + 消息文本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    message_type: str
    text: str

    @field_validator("message_type")
    @classmethod
    def _message_type_closed(cls, value: str) -> str:
        if value not in ("error", "warning", "log", "info", "debug"):
            raise ValueError("控制台消息类型不在封闭集合内")
        return value

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)


class PageErrorObservation(BaseModel):
    """未捕获页面异常观察：异常文本。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str

    @field_validator("text")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)


class RequestObservation(BaseModel):
    """网络请求观察：请求 URL 与资源类型封闭集合。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    resource_type: str = "other"

    @field_validator("url")
    @classmethod
    def _url_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("resource_type")
    @classmethod
    def _resource_type_closed(cls, value: str) -> str:
        if value not in (
            "document",
            "stylesheet",
            "script",
            "image",
            "font",
            "fetch",
            "xhr",
            "other",
        ):
            raise ValueError("请求资源类型不在封闭集合内")
        return value


class OcclusionObservation(BaseModel):
    """固定元素遮挡候选：固定元素与内容矩形各一对，几何判定在验收器。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fixed_label: str
    fixed_rect: Rect
    covered_label: str
    covered_rect: Rect

    @field_validator("fixed_label", "covered_label")
    @classmethod
    def _label_not_blank(cls, value: str) -> str:
        return _text(value)


class LayoutObservation(BaseModel):
    """视口与文档宽度观察：横向溢出判定输入。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    viewport_width: float
    document_scroll_width: float

    @model_validator(mode="after")
    def _widths_sane(self) -> LayoutObservation:
        if self.viewport_width <= 0 or self.document_scroll_width < 0:
            raise ValueError("视口宽度必须为正数，文档滚动宽度不能为负")
        return self


class PageInspection(BaseModel):
    """单页只读观察集合：链接、控制台/页面错误、请求、遮挡、页脚与布局。

    观察由静态 HTML 扫描与真实浏览器运行时收集；缺省字段表示未观察，
    验收器不据此做任何判定（页脚数与布局宽度同时齐备才检查）。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    route: str
    links: tuple[LinkObservation, ...] = ()
    console_messages: tuple[ConsoleObservation, ...] = ()
    page_errors: tuple[PageErrorObservation, ...] = ()
    requests: tuple[RequestObservation, ...] = ()
    occlusions: tuple[OcclusionObservation, ...] = ()
    footer_count: int | None = None
    layout: LayoutObservation | None = None

    @field_validator("route")
    @classmethod
    def _route_not_blank(cls, value: str) -> str:
        return _text(value)

    @field_validator("footer_count")
    @classmethod
    def _footer_count_non_negative(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("页脚数量不能为负")
        return value


class DefectViolationCode(StrEnum):
    """只读缺陷机器码：死链、控制台/页面错误、非本地请求、页脚、溢出遮挡。"""

    DEAD_LINK = "dead_link"
    CONSOLE_ERROR = "console_error"
    PAGE_ERROR = "page_error"
    REMOTE_REQUEST = "remote_request"
    MISSING_FOOTER = "missing_footer"
    DUPLICATE_FOOTER = "duplicate_footer"
    HORIZONTAL_OVERFLOW = "horizontal_overflow"
    CONTENT_OCCLUSION = "content_occlusion"


class DefectViolation(BaseModel):
    """单条只读缺陷：机器码 + 路由 + 用户可见中文说明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: DefectViolationCode
    route: str
    detail_zh: str

    @field_validator("route", "detail_zh")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        return _text(value)


class PageDefectVerification(BaseModel):
    """单页只读缺陷验收结果：通过与否决及全部缺陷；只报告，不改站点。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    route: str
    ok: bool
    violations: tuple[DefectViolation, ...]

    @field_validator("route")
    @classmethod
    def _route_not_blank(cls, value: str) -> str:
        return _text(value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def message_zh(self) -> str:
        """用户可见中文结论：通过或按缺陷汇总的失败说明。"""
        if self.ok:
            return (
                "页面只读验收通过：未发现死链、控制台错误、页面错误、"
                "非本地请求、页脚缺失或重复、横向溢出或内容遮挡。"
            )
        listed = "；".join(v.detail_zh for v in self.violations[:3])
        if len(self.violations) > 3:
            listed = f"{listed} 等 {len(self.violations)} 处问题"
        return f"页面只读验收失败：{listed}"


class PortalDefectVerification(BaseModel):
    """全站只读缺陷验收结果：任一页面失败即整体否决。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    pages: tuple[PageDefectVerification, ...]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def message_zh(self) -> str:
        """用户可见中文结论：通过或列出存在缺陷的页面。"""
        if self.ok:
            return "全站只读验收通过：所有页面均未发现缺陷。"
        failed = [page for page in self.pages if not page.ok]
        named = "、".join(page.route for page in failed[:3])
        if len(failed) > 3:
            named = f"{named} 等 {len(failed)} 个页面"
        return f"全站只读验收失败：{named} 存在缺陷。"


def _is_loopback_host(host: str) -> bool:
    return host.casefold() in _LOCAL_HOSTS


def is_local_request_url(url: str) -> bool:
    """请求 URL 是否为本地资源：相对路径、内联 data/blob 与回环地址。

    协议相对 URL（``//host/…``）视为站外；file 视为本地。非空校验由
    观察模型完成，本函数只做分类。
    """
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.casefold()
    if scheme in ("data", "blob"):
        return True
    if scheme == "":
        return not parsed.netloc
    if scheme in ("http", "https", "ws", "wss"):
        return _is_loopback_host(parsed.hostname or "")
    return scheme == "file"


def _normalize_segments(parts: Sequence[str]) -> tuple[str, ...]:
    """规范化 URL 路径段：合并 ``.`` 与 ``..``，逃出根时保留 ``..``。"""
    result: list[str] = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if result:
                result.pop()
            else:
                result.append("..")
        else:
            result.append(part)
    return tuple(result)


def resolve_local_link(page_route: str, href: str) -> Path | None:
    """把页面链接解析为站点相对物理文件；非本地/不可验证链接返回 None。

    - 页内锚点、mailto/tel/javascript/data/blob、协议相对与站外 http(s)
      链接返回 None，不做死链判定。
    - 相对链接按页面所在目录解析；``..`` 逃出站点根目录时返回含 ``..``
      的越界路径，由站点文件集合判定为死链。
    - 站内绝对路径（``/overview.html``）与回环 http(s) 链接按站点根解析。
    """
    raw = href.strip()
    if not raw or raw.startswith("#"):
        return None
    target = raw.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    parsed = urlsplit(target)
    scheme = parsed.scheme.casefold()
    if scheme in ("mailto", "tel", "javascript", "data", "blob"):
        return None
    if scheme in ("http", "https"):
        if not _is_loopback_host(parsed.hostname or ""):
            return None
        segments = [unquote(part) for part in parsed.path.split("/")]
        return Path(*_normalize_segments(segments))
    if scheme == "file":
        return None
    if scheme != "":
        return None
    if parsed.netloc:
        return None
    if target.startswith("/"):
        segments = [unquote(part) for part in target.split("/")]
        return Path(*_normalize_segments(segments))
    page_dir = route_to_site_path(page_route).parent
    segments = [*page_dir.parts, *[unquote(part) for part in target.split("/")]]
    return Path(*_normalize_segments(segments))


def _rects_overlap(first: Rect, second: Rect) -> bool:
    overlap_width = min(first.right, second.right) - max(first.left, second.left)
    overlap_height = min(first.bottom, second.bottom) - max(first.top, second.top)
    return overlap_width > _OCCLUSION_MIN_OVERLAP_PX and overlap_height > _OCCLUSION_MIN_OVERLAP_PX


def verify_page_defects(
    inspection: PageInspection,
    valid_site_paths: Sequence[Path],
) -> PageDefectVerification:
    """单页只读缺陷验收：死链、控制台/页面错误、非本地请求、页脚唯一性、
    横向溢出与固定元素遮挡全部失败关闭。只报告与否决，绝不修改站点。
    """
    valid = frozenset(Path(path) for path in valid_site_paths)
    violations: list[DefectViolation] = []
    route = inspection.route

    for link in inspection.links:
        target = resolve_local_link(route, link.href)
        if target is None or target in valid:
            continue
        label = f"「{link.text}」" if link.text else ""
        violations.append(
            DefectViolation(
                code=DefectViolationCode.DEAD_LINK,
                route=route,
                detail_zh=f"死链：链接{label}指向不存在的页面 {target}",
            )
        )

    for message in inspection.console_messages:
        if message.message_type != "error":
            continue
        violations.append(
            DefectViolation(
                code=DefectViolationCode.CONSOLE_ERROR,
                route=route,
                detail_zh=f"控制台错误：{message.text}",
            )
        )

    for error in inspection.page_errors:
        violations.append(
            DefectViolation(
                code=DefectViolationCode.PAGE_ERROR,
                route=route,
                detail_zh=f"页面错误：{error.text}",
            )
        )

    for request in inspection.requests:
        if is_local_request_url(request.url):
            continue
        violations.append(
            DefectViolation(
                code=DefectViolationCode.REMOTE_REQUEST,
                route=route,
                detail_zh=f"非本地请求（{request.resource_type}）：{request.url}",
            )
        )

    if inspection.footer_count == 0:
        violations.append(
            DefectViolation(
                code=DefectViolationCode.MISSING_FOOTER,
                route=route,
                detail_zh="页面缺少唯一全局页脚",
            )
        )
    elif inspection.footer_count is not None and inspection.footer_count > 1:
        violations.append(
            DefectViolation(
                code=DefectViolationCode.DUPLICATE_FOOTER,
                route=route,
                detail_zh=f"页面发现 {inspection.footer_count} 个全局页脚，每页必须唯一",
            )
        )

    if inspection.layout is not None:
        overflow = inspection.layout.document_scroll_width - inspection.layout.viewport_width
        if overflow > _OVERFLOW_TOLERANCE_PX:
            violations.append(
                DefectViolation(
                    code=DefectViolationCode.HORIZONTAL_OVERFLOW,
                    route=route,
                    detail_zh=f"页面横向溢出 {overflow:.0f}px",
                )
            )

    for occlusion in inspection.occlusions:
        if not _rects_overlap(occlusion.fixed_rect, occlusion.covered_rect):
            continue
        violations.append(
            DefectViolation(
                code=DefectViolationCode.CONTENT_OCCLUSION,
                route=route,
                detail_zh=(
                    f"固定元素「{occlusion.fixed_label}」遮挡内容「{occlusion.covered_label}」"
                ),
            )
        )

    return PageDefectVerification(
        route=route,
        ok=not violations,
        violations=tuple(violations),
    )


def verify_portal_defects(
    inspections: Sequence[PageInspection],
    valid_site_paths: Sequence[Path],
) -> PortalDefectVerification:
    """全站只读缺陷验收：任一页面失败即整体否决；只报告与否决。"""
    pages = tuple(verify_page_defects(inspection, valid_site_paths) for inspection in inspections)
    return PortalDefectVerification(ok=all(page.ok for page in pages), pages=pages)


class _PageScanner(HTMLParser):
    """静态 HTML 只读扫描：锚点链接、样式/脚本/图片请求与全局页脚数量。

    不执行 JavaScript；控制台/页面错误、视口宽度与固定元素矩形需真实
    浏览器运行时观察补充到 PageInspection。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[LinkObservation] = []
        self.requests: list[RequestObservation] = []
        self.footer_count = 0
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "a":
            href = attributes.get("href", "")
            self._anchor_href = href or None
            self._anchor_text = []
        elif tag == "footer":
            if "site-footer" in attributes.get("class", "").split():
                self.footer_count += 1
        elif tag == "link":
            href = attributes.get("href", "")
            if not href:
                return
            rel = attributes.get("rel", "").casefold().split()
            if "stylesheet" in rel:
                self.requests.append(RequestObservation(url=href, resource_type="stylesheet"))
            elif any(token in rel for token in ("icon", "preload", "modulepreload")):
                self.requests.append(RequestObservation(url=href, resource_type="other"))
        elif tag == "script":
            src = attributes.get("src", "")
            if src:
                self.requests.append(RequestObservation(url=src, resource_type="script"))
        elif tag == "img":
            src = attributes.get("src", "")
            if src:
                self.requests.append(RequestObservation(url=src, resource_type="image"))
        elif tag == "source":
            src = attributes.get("src", "")
            if src:
                self.requests.append(RequestObservation(url=src, resource_type="other"))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            self.links.append(
                LinkObservation(
                    href=self._anchor_href,
                    text=" ".join(" ".join(self._anchor_text).split()),
                )
            )
            self._anchor_href = None
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._anchor_href is not None:
            self._anchor_text.append(data)


def scan_page_html(html: str, route: str) -> PageInspection:
    """对页面 HTML 做只读静态扫描，返回可验收的部分观察。

    静态可确认：链接、样式/脚本/图片请求与全局页脚数量。控制台/页面
    错误、视口宽度与固定元素遮挡由真实浏览器运行时观察补充；验收器
    只消费观察，绝不修改被验收站点。
    """
    scanner = _PageScanner()
    scanner.feed(html)
    return PageInspection(
        route=route,
        links=tuple(scanner.links),
        requests=tuple(scanner.requests),
        footer_count=scanner.footer_count,
    )


# ===========================================================================
# 运行时观察收集（worker_03）：真实浏览器（Chromium/WebKit）按视口收集
# 控制台消息、页面错误、网络请求、横向溢出与固定元素遮挡候选。静态扫描
# 已覆盖链接/请求/页脚数量；运行时收集与静态扫描合并为同一
# PageInspection 交 worker_02 判定模型验收。验收器只消费观察并报告与否
# 决，绝不修改被验收站点。
# ===========================================================================

DEFAULT_VIEWPORTS: tuple[tuple[int, int], ...] = ((1280, 800), (1440, 900), (1920, 1080))

_RUNTIME_RESOURCE_TYPES: Mapping[str, str] = {
    "document": "document",
    "stylesheet": "stylesheet",
    "script": "script",
    "image": "image",
    "font": "font",
    "fetch": "fetch",
    "xhr": "xhr",
}

_RUNTIME_LAYOUT_JS = """() => ({
  viewport_width: window.innerWidth,
  document_scroll_width: document.documentElement.scrollWidth,
})"""

_RUNTIME_OCCLUSION_JS = """() => {
  const MIN_OVERLAP = 1.0;
  const visible = (el) => {
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    return el.getClientRects().length > 0;
  };
  const fixed = Array.from(document.querySelectorAll("*")).filter((el) => {
    const position = getComputedStyle(el).position;
    return (position === "fixed" || position === "sticky") && visible(el);
  });
  const covered = Array.from(
    document.querySelectorAll("h1, h2, h3, main section, main article, main p, main li")
  ).filter(visible);
  const rectOf = (el) => {
    const rect = el.getBoundingClientRect();
    return { top: rect.top, left: rect.left, right: rect.right, bottom: rect.bottom };
  };
  const labelOf = (el) => {
    const raw = String(el.getAttribute("aria-label") || el.id || el.className || "").trim();
    return (raw || el.tagName.toLowerCase()).slice(0, 40);
  };
  const textOf = (el) => (el.textContent || "").trim().slice(0, 24) || el.tagName.toLowerCase();
  const out = [];
  for (const fixedEl of fixed) {
    const fixedRect = fixedEl.getBoundingClientRect();
    for (const coveredEl of covered) {
      const coveredRect = coveredEl.getBoundingClientRect();
      const overlapWidth =
        Math.min(fixedRect.right, coveredRect.right) - Math.max(fixedRect.left, coveredRect.left);
      const overlapHeight =
        Math.min(fixedRect.bottom, coveredRect.bottom) - Math.max(fixedRect.top, coveredRect.top);
      if (overlapWidth > MIN_OVERLAP && overlapHeight > MIN_OVERLAP) {
        out.push({
          fixed_label: labelOf(fixedEl),
          fixed_rect: rectOf(fixedEl),
          covered_label: textOf(coveredEl),
          covered_rect: rectOf(coveredEl),
        });
      }
    }
  }
  return out;
}"""


def collect_page_runtime_observations(
    page: Any,
    route: str,
    url: str,
    *,
    settle_ms: int = 250,
) -> PageInspection:
    """在真实浏览器页面收集单次导航的运行时观察并返回 PageInspection。

    ``page`` 必须是已启动的 Playwright 同步页面；本函数负责挂载监听、
    导航与收集，不负责页面/浏览器生命周期。控制台/页面错误/网络请求在
    导航前挂载；视口宽度与固定元素遮挡在页面稳定后求值。页面保持打开
    由调用方管理（用于原分辨率截图等后续动作）。
    """
    console_messages: list[ConsoleObservation] = []
    page_errors: list[PageErrorObservation] = []
    requests: list[RequestObservation] = []

    def _on_console(message: Any) -> None:
        if message.type not in ("error", "warning", "log", "info", "debug"):
            return
        console_messages.append(ConsoleObservation(message_type=message.type, text=message.text))

    def _on_page_error(error: Any) -> None:
        page_errors.append(PageErrorObservation(text=str(error)))

    def _on_request(request: Any) -> None:
        resource_type = _RUNTIME_RESOURCE_TYPES.get(request.resource_type, "other")
        requests.append(RequestObservation(url=request.url, resource_type=resource_type))

    page.on("console", _on_console)
    page.on("pageerror", _on_page_error)
    page.on("request", _on_request)
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(settle_ms)
        layout_data = cast(dict[str, float], page.evaluate(_RUNTIME_LAYOUT_JS))
        occlusion_data = cast(list[dict[str, Any]], page.evaluate(_RUNTIME_OCCLUSION_JS))
    finally:
        page.remove_listener("console", _on_console)
        page.remove_listener("pageerror", _on_page_error)
        page.remove_listener("request", _on_request)

    occlusions: list[OcclusionObservation] = []
    for item in occlusion_data:
        occlusions.append(
            OcclusionObservation(
                fixed_label=_text(item["fixed_label"]),
                fixed_rect=Rect(
                    top=float(item["fixed_rect"]["top"]),
                    left=float(item["fixed_rect"]["left"]),
                    right=float(item["fixed_rect"]["right"]),
                    bottom=float(item["fixed_rect"]["bottom"]),
                ),
                covered_label=_text(item["covered_label"]),
                covered_rect=Rect(
                    top=float(item["covered_rect"]["top"]),
                    left=float(item["covered_rect"]["left"]),
                    right=float(item["covered_rect"]["right"]),
                    bottom=float(item["covered_rect"]["bottom"]),
                ),
            )
        )
    return PageInspection(
        route=route,
        console_messages=tuple(console_messages),
        page_errors=tuple(page_errors),
        requests=tuple(requests),
        occlusions=tuple(occlusions),
        layout=LayoutObservation(
            viewport_width=layout_data["viewport_width"],
            document_scroll_width=layout_data["document_scroll_width"],
        ),
    )


def merge_page_observations(
    static: PageInspection,
    runtime: PageInspection,
) -> PageInspection:
    """合并同一路由的静态扫描与运行时观察为一份 PageInspection。

    静态贡献链接、请求与页脚数量；运行时贡献控制台/页面错误、请求、
    遮挡与布局；请求按 (URL, 资源类型) 去重。路由不一致失败关闭。
    """
    if static.route != runtime.route:
        raise ValueError(f"静态扫描与运行时观察路由不一致：{static.route} != {runtime.route}")
    seen: set[tuple[str, str]] = set()
    requests: list[RequestObservation] = []
    for request in (*static.requests, *runtime.requests):
        key = (request.url, request.resource_type)
        if key in seen:
            continue
        seen.add(key)
        requests.append(request)
    return PageInspection(
        route=static.route,
        links=static.links,
        console_messages=runtime.console_messages,
        page_errors=runtime.page_errors,
        requests=tuple(requests),
        occlusions=runtime.occlusions,
        footer_count=static.footer_count,
        layout=runtime.layout,
    )


# ===========================================================================
# 锁定站点地图来源（worker_03 修订）：从当前报告版本的产物清单与不可变
# 报告快照读取期望站点地图的产品/试验身份。验收器只读：只核验与读取，
# 绝不修改被验收项目、站点、清单或快照。缺清单、缺快照、绑定不一致或
# 站点摘要过期均在启动浏览器前失败关闭，防止旧清单或被改写站点假通过。
# ===========================================================================


class LockedSitemapSourceError(ValueError):
    """锁定站点地图来源拒绝：清单/快照缺失、绑定不一致或站点摘要过期。"""


@dataclass(frozen=True)
class LockedSitemapSource:
    """已核验的锁定站点地图来源：产物清单、报告快照与清单记录的产品/试验。"""

    manifest: ArtifactManifest
    snapshot: ReportSnapshotManifest
    product_ids: tuple[str, ...]
    trial_ids: tuple[str, ...]


def _canonical_json(value: object) -> bytes:
    """与 SnapshotStore/ManifestStore 同一规范 JSON：排序、紧凑、中文不转义。"""
    try:
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
    except (TypeError, ValueError) as error:
        raise LockedSitemapSourceError("锁定站点地图来源必须是有限、可序列化的 JSON") from error


def site_directory_digest(site_root: Path) -> tuple[str, int]:
    """站点目录确定性摘要与汇总字节数；与产物清单 artifact 绑定同一合同。

    摘要 = 按路径排序后，对每个文件依次更新 POSIX 相对路径、NUL 与字节
    内容的整体 SHA-256；字节数 = 全部文件字节之和。只读，不修改站点。
    """
    digest = hashlib.sha256()
    total = 0
    for path in sorted(site_root.rglob("*")):
        if not path.is_file():
            continue
        content = path.read_bytes()
        digest.update(path.relative_to(site_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        total += len(content)
    return digest.hexdigest(), total


def load_locked_sitemap_source(
    project_root: Path,
    report: ReportKind,
    version: str,
) -> LockedSitemapSource:
    """读取并核验当前报告版本的锁定站点地图来源（只读，失败关闭）。

    核验链：

    1. ``reports/<报告>/<版本>/html.manifest.json`` 存在且符合
       ``ArtifactManifest``；报告类型与版本匹配；状态不是 failed/superseded；
       产物相对路径正是 ``reports/<报告>/<版本>/html``。
    2. 清单引用的 ``snapshots/reports/<报告>/<report_snapshot_id>.json``
       存在且符合 ``ReportSnapshotManifest``；其报告、版本、项目、合同
       版本、数据截止时间、证据/声明/覆盖集绑定与产物清单一致。
    3. 按 SnapshotStore 同一规范 JSON 重算摘要与
       ``stable_id("report-snapshot", 报告, 摘要)``，与清单身份及文件名
       一致。
    4. 站点目录当前摘要与汇总字节数与清单 ``artifact.sha256``/``byte_size``
       一致；不一致时在启动浏览器前失败关闭。

    全部通过后返回清单记录的产品/试验标识作为期望站点地图来源。
    """
    report_value = report.value
    project_root = project_root.expanduser().resolve()
    expected_rel = f"reports/{report_value}/{version}/html"
    manifest_path = project_root / "reports" / report_value / version / "html.manifest.json"

    # 1. 产物清单：存在、解析、报告/版本匹配、状态可用、路径正是站点目录。
    if not manifest_path.is_file():
        raise LockedSitemapSourceError(
            f"报告站点清单不存在：{manifest_path}。请确认 --project 与 --version "
            f"指向已生成的门户产物（应存在 reports/{report_value}/{version}/html.manifest.json）。"
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LockedSitemapSourceError(
            f"报告站点清单无法读取：{manifest_path}（{error}）。请重新生成该报告版本。"
        ) from error
    if not isinstance(payload, dict):
        raise LockedSitemapSourceError(f"报告站点清单顶层必须是对象：{manifest_path}")
    try:
        manifest = ArtifactManifest.model_validate(payload)
    except ValidationError as error:
        raise LockedSitemapSourceError(
            f"报告站点清单校验失败：{error}。请重新生成该报告版本。"
        ) from error
    if manifest.report != report_value:
        raise LockedSitemapSourceError(
            f"报告站点清单的报告类型不一致：清单为 {manifest.report}，请求为 {report_value}。"
        )
    if manifest.report_version != version:
        raise LockedSitemapSourceError(
            f"报告站点清单的版本不一致：清单为 {manifest.report_version}，请求为 {version}。"
        )
    if manifest.status in ("failed", "superseded"):
        raise LockedSitemapSourceError(
            f"报告站点清单状态为 {manifest.status}，不可用于验收；请重新生成该报告版本。"
        )
    if manifest.artifact.relative_path != expected_rel:
        raise LockedSitemapSourceError(
            f"报告站点清单的产物路径不一致：{manifest.artifact.relative_path} != {expected_rel}。"
        )

    # 2. 报告快照：存在、符合模型。
    snapshot_path = (
        project_root
        / "snapshots"
        / "reports"
        / report_value
        / f"{manifest.report_snapshot_id}.json"
    )
    if not snapshot_path.is_file():
        raise LockedSitemapSourceError(
            f"报告快照文件不存在：{snapshot_path}。请确认项目内存在清单引用的"
            "锁定报告快照（snapshots/reports/<报告>/<report_snapshot_id>.json）。"
        )
    try:
        snapshot_bytes = snapshot_path.read_bytes()
        snapshot_payload = json.loads(snapshot_bytes)
    except (OSError, json.JSONDecodeError) as error:
        raise LockedSitemapSourceError(
            f"报告快照无法读取：{snapshot_path}（{error}）。请重新锁定报告快照。"
        ) from error
    if not isinstance(snapshot_payload, dict):
        raise LockedSitemapSourceError(f"报告快照顶层必须是对象：{snapshot_path}")
    try:
        snapshot = ReportSnapshotManifest.model_validate(snapshot_payload)
    except ValidationError as error:
        raise LockedSitemapSourceError(
            f"报告快照校验失败：{error}。请重新锁定报告快照。"
        ) from error

    # 3. 规范 JSON 重算摘要与稳定身份，与清单及文件名一致。
    encoded = _canonical_json(snapshot.model_dump(mode="json"))
    digest = hashlib.sha256(encoded).hexdigest()
    expected_id = stable_id("report-snapshot", report_value, digest)
    if expected_id != manifest.report_snapshot_id:
        raise LockedSitemapSourceError(
            "报告快照身份与站点清单不一致：按锁定内容重算为 "
            f"{expected_id}，清单记录 {manifest.report_snapshot_id}；"
            "请重新生成并锁定该报告版本。"
        )
    if snapshot_path.name != f"{expected_id}.json":
        raise LockedSitemapSourceError(
            f"报告快照文件名与锁定身份不一致：{snapshot_path.name}；请重新锁定报告快照。"
        )
    if len(snapshot_bytes) != len(encoded):
        raise LockedSitemapSourceError("报告快照字节数与锁定内容不一致；请重新锁定报告快照。")

    # 4. 绑定一致：报告/版本/项目/合同版本/数据截止/证据/声明/覆盖集。
    bindings = (
        ("报告类型", snapshot.report, manifest.report),
        ("报告版本", snapshot.report_version, manifest.report_version),
        ("项目标识", snapshot.project_id, manifest.project_id),
        ("合同版本", str(snapshot.contract_version), str(manifest.contract_version)),
        ("数据截止时间", snapshot.data_cutoff, manifest.data_cutoff),
        ("证据快照", snapshot.evidence_snapshot_id, manifest.evidence_snapshot_id),
        ("声明快照", snapshot.claim_snapshot_id, manifest.claim_snapshot_id),
        ("覆盖集", snapshot.coverage_set_id, manifest.coverage_set_id),
    )
    for label, snapshot_value, manifest_value in bindings:
        if snapshot_value == manifest_value:
            continue
        raise LockedSitemapSourceError(
            f"报告快照与站点清单的{label}不一致：快照为 {snapshot_value}，"
            f"清单为 {manifest_value}；请重新生成并锁定该报告版本。"
        )
    if set(snapshot.claim_ids) != set(manifest.claim_ids):
        raise LockedSitemapSourceError(
            "报告快照与站点清单的声明集合不一致；请重新生成并锁定该报告版本。"
        )

    # 5. 站点目录当前摘要与字节数必须与清单一致（启动浏览器前失败关闭）。
    site_root = project_root.joinpath(*expected_rel.split("/"))
    if not site_root.is_dir():
        raise LockedSitemapSourceError(f"报告站点目录不存在：{site_root}。请确认产物已生成。")
    actual_digest, actual_bytes = site_directory_digest(site_root)
    if actual_digest != manifest.artifact.sha256:
        raise LockedSitemapSourceError(
            "报告站点摘要与清单不一致：站点产物可能已被改写，请重新生成该报告版本后重试。"
        )
    if actual_bytes != manifest.artifact.byte_size:
        raise LockedSitemapSourceError(
            "报告站点字节数与清单不一致：站点产物可能已被改写，请重新生成该报告版本后重试。"
        )

    return LockedSitemapSource(
        manifest=manifest,
        snapshot=snapshot,
        product_ids=manifest.product_ids,
        trial_ids=manifest.trial_ids,
    )
