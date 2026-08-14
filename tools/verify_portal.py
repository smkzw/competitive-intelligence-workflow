#!/usr/bin/env python3
"""Task 4.6 全站浏览器验收 CLI：Chromium/WebKit 多视口遍历 + 原分辨率截图 + 交互 trace。

用法示例（与 Hermes 计划 Task 4.6 验收一致）：

    uv run python tools/verify_portal.py --report A --project .artifacts/a-complete \\
        --version v-fixture-001 --browser chromium --browser webkit --all-routes

流程（失败关闭，验收器只报告与否决，绝不修改被验收项目、站点、清单或快照）：

1. 输入校验：缺少/非法参数以中文说明退出 2。
2. 锁定站点地图来源：从当前报告版本读取 ``reports/<报告>/<版本>/html.manifest.json``
   与清单引用的锁定报告快照，并核对站点目录摘要与清单一致；缺清单、
   缺快照、绑定不一致或站点摘要过期均以中文说明退出 2，且不启动浏览器。
3. 站点地图一一对应：期望站点地图 = 页面注册表全部静态责任页 + 清单记录
   的每一个产品/试验详情页；缺页、多页、Top-N、额外 slug 均失败退出 1。
4. 路由可达性：从首页/总览沿本地 HTML 锚点遍历期望站点地图；任一期望路
   由（尤其每个产品/试验详情页）不可达即失败退出 1，不启动浏览器。
5. 运行时验收：Chromium/WebKit 在 1280/1440/1920 遍历全部路由，静态扫描
   与运行时观察合并后按同一判定模型逐页验收；任一缺陷整体否决。
6. 产物：每页原分辨率视口截图、每浏览器带运行/站点摘要的交互 trace 与
   report.json；写入 --output-dir（默认 <project>/verification/<报告>/<版本>/），
   绝不写入被验收的 ``reports/<报告>/<版本>/html/`` 站点目录。

退出码：0 = 全站通过；1 = 验收失败（站点地图或运行时缺陷）；2 = 输入/环境错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Never

from playwright.sync_api import sync_playwright

from ci_workflow.domain.enums import ReportKind
from ci_workflow.qc.browser import (
    DEFAULT_VIEWPORTS,
    LockedSitemapSourceError,
    SitemapBoundaryError,
    collect_page_runtime_observations,
    derive_sitemap_contract,
    enumerate_site_routes,
    load_locked_sitemap_source,
    merge_page_observations,
    route_to_site_path,
    scan_page_html,
    verify_page_defects,
    verify_route_reachability,
    verify_sitemap_one_to_one,
)
from ci_workflow.reports.common.page_registry import PageRegistry

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

VALID_REPORTS = ("A", "B", "C")
VALID_BROWSERS = ("chromium", "webkit")


class ChineseArgumentParser(argparse.ArgumentParser):
    """将 argparse 的固定交互文案收口为中文，缺失/非法输入给出可操作说明。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "命令"
        self._optionals.title = "选项"
        self.add_argument("-h", "--help", action="help", help="显示帮助并退出")

    def format_help(self) -> str:
        return super().format_help().replace("usage:", "用法:", 1)

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法:", 1)

    def error(self, message: str) -> Never:
        if message.startswith("the following arguments are required:"):
            missing = message.split(":", 1)[1].strip()
            detail = f"缺少必填参数：{missing}"
        elif "invalid choice:" in message:
            detail = "参数值不在允许范围内，请查看 --help"
        elif message.startswith("unrecognized arguments:"):
            unknown = message.split(":", 1)[1].strip()
            detail = f"无法识别的参数：{unknown}"
        elif message.startswith("argument ") and ":" in message:
            detail = message.split(":", 1)[1].strip()
        else:
            detail = "参数不符合要求，请查看 --help"
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}：参数错误：{detail}\n")


def _parse_viewport(value: str) -> tuple[int, int]:
    """把 ``1280x800`` 解析为 (宽度, 高度)；非法格式失败关闭。"""
    parts = value.split("x", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"视口格式必须为 宽度x高度（例如 1280x800）：{value}")
    try:
        width, height = int(parts[0]), int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(f"视口尺寸必须是整数：{value}") from None
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError(f"视口尺寸必须为正数：{value}")
    return width, height


def _build_parser() -> ChineseArgumentParser:
    parser = ChineseArgumentParser(prog="verify_portal.py", description=__doc__)
    parser.add_argument(
        "--report",
        required=True,
        choices=VALID_REPORTS,
        help="报告类型：A / B / C",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="项目根目录（含 reports/<报告>/<版本>/html/ 站点产物）",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="报告版本目录名（例如 v-fixture-001）",
    )
    parser.add_argument(
        "--browser",
        action="append",
        choices=VALID_BROWSERS,
        help="验收浏览器（可重复）；默认 chromium",
    )
    parser.add_argument(
        "--viewport",
        action="append",
        type=_parse_viewport,
        help="视口 宽度x高度（可重复）；默认 1280x800、1440x900、1920x1080",
    )
    parser.add_argument(
        "--all-routes",
        action="store_true",
        help="验证站点地图全部路由（当前版本默认且唯一模式，此选项为显式声明）",
    )
    parser.add_argument(
        "--output-dir",
        help="验收产物目录（截图/trace/report.json）；默认 "
        "<project>/verification/<报告>/<版本>，绝不写入被验收的 html/ 站点目录",
    )
    return parser


def _run_digest(
    *,
    report: str,
    version: str,
    site_digest: str,
    browsers: list[str],
    viewports: list[tuple[int, int]],
    routes: tuple[str, ...],
) -> str:
    """运行摘要：站点摘要 + 验收配置 + 启动时刻，标识本次验收运行。"""
    payload = json.dumps(
        {
            "report": report,
            "version": version,
            "site_digest": site_digest,
            "browsers": browsers,
            "viewports": [list(vp) for vp in viewports],
            "routes": list(routes),
            "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _valid_site_paths(site_root: Path) -> tuple[Path, ...]:
    """站点全部物理文件（HTML 与资源），死链判定与请求归属的依据。"""
    return tuple(
        sorted(path.relative_to(site_root) for path in site_root.rglob("*") if path.is_file())
    )


def _route_slug(route: str) -> str:
    """路由 → 截图文件名安全片段：``/a/products/product-01`` → ``a_products_product-01``。"""
    return route.lstrip("/").replace("/", "_")


def _run_browser_acceptance(
    *,
    site_root: Path,
    contract: Any,
    valid_paths: tuple[Path, ...],
    browsers: list[str],
    viewports: list[tuple[int, int]],
    output_dir: Path,
    run_digest: str,
    site_digest: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    """在 Chromium/WebKit 各视口遍历全部路由并收集逐页验收结果。

    返回 (按路由聚合的页面结果, trace 元数据, 截图数量)。每浏览器一个
    上下文与交互 trace；截图按路由 × 浏览器 × 视口保存原分辨率 PNG。
    """
    page_results: dict[str, list[dict[str, Any]]] = {route: [] for route in contract.routes}
    traces: list[dict[str, str]] = []
    screenshot_count = 0
    screenshots_dir = output_dir / "screenshots"
    traces_dir = output_dir / "traces"
    for browser_name in browsers:
        with sync_playwright() as playwright:
            browser_type = getattr(playwright, browser_name)
            browser = browser_type.launch()
            context = browser.new_context(
                viewport={"width": viewports[0][0], "height": viewports[0][1]},
                device_scale_factor=1,
            )
            context.tracing.start(
                title=f"run:{run_digest} site:{site_digest}",
                screenshots=True,
                snapshots=True,
            )
            try:
                for width, height in viewports:
                    for route in contract.routes:
                        site_file = site_root / route_to_site_path(route)
                        static = scan_page_html(site_file.read_text(encoding="utf-8"), route)
                        page = context.new_page()
                        page.set_viewport_size({"width": width, "height": height})
                        runtime = collect_page_runtime_observations(page, route, site_file.as_uri())
                        inspection = merge_page_observations(static, runtime)
                        verdict = verify_page_defects(inspection, valid_paths)
                        shot = (
                            screenshots_dir
                            / f"{_route_slug(route)}__{browser_name}__{width}x{height}.png"
                        )
                        shot.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(shot))
                        screenshot_count += 1
                        page.close()
                        page_results[route].append(
                            {
                                "browser": browser_name,
                                "viewport": [width, height],
                                "ok": verdict.ok,
                                "violations": [
                                    {"code": v.code.value, "detail_zh": v.detail_zh}
                                    for v in verdict.violations
                                ],
                            }
                        )
            finally:
                trace_path = traces_dir / f"trace__{browser_name}__{run_digest[:12]}.zip"
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                context.tracing.stop(path=str(trace_path))
                context.close()
                browser.close()
            traces.append(
                {
                    "browser": browser_name,
                    "path": f"traces/trace__{browser_name}__{run_digest[:12]}.zip",
                    "run_digest": run_digest,
                    "site_digest": site_digest,
                }
            )
    pages = [
        {"route": route, "ok": all(check["ok"] for check in checks), "checks": checks}
        for route, checks in page_results.items()
    ]
    return pages, traces, screenshot_count


def _format_verdict(
    pages: list[dict[str, Any]],
    *,
    routes: tuple[str, ...],
    browsers: list[str],
    viewports: list[tuple[int, int]],
    output_dir: Path,
    ok: bool,
) -> str:
    """用户可见中文结论：通过或列出存在缺陷的页面（含浏览器与视口）。"""
    if ok:
        viewport_labels = "、".join(f"{width}×{height}" for width, height in viewports)
        return (
            f"全站验收通过：{len(routes)} 个路由在 {'、'.join(browsers)} 的 "
            f"{viewport_labels} 视口下全部无缺陷；每页原分辨率截图与带运行/站点"
            f"摘要的交互 trace 已保存至 {output_dir}。"
        )
    lines: list[str] = []
    for page in pages:
        if page["ok"]:
            continue
        failed = next(check for check in page["checks"] if not check["ok"])
        first = failed["violations"][0]["detail_zh"] if failed["violations"] else "页面验收未通过"
        viewport = failed["viewport"]
        lines.append(
            f"- {page['route']}（{failed['browser']}，{viewport[0]}×{viewport[1]}）：{first}"
        )
    return (
        "全站验收失败：以下页面存在缺陷：\n"
        + "\n".join(lines[:10])
        + "\n请修复上述问题后重新运行验收工具。"
    )


def verify_cli(argv: list[str]) -> int:
    """CLI 主流程：输入校验 → 锁定站点地图来源 → 站点地图一一对应 → 运行时验收。"""
    parser = _build_parser()
    args = parser.parse_args(argv)
    report_kind = ReportKind(args.report)
    # 计划与用户日常调用通常传入相对项目路径；浏览器打开本地页面前必须
    # 先规范为绝对路径，否则 Path.as_uri() 无法生成 file:// 地址。
    project_root = Path(args.project).expanduser().resolve()

    # 锁定站点地图来源：只读读取当前报告版本的产物清单与锁定报告快照，
    # 并核对站点目录摘要与清单一致。缺清单、缺快照、绑定不一致或站点
    # 摘要过期均失败关闭（退出 2），且不启动浏览器。
    try:
        source = load_locked_sitemap_source(project_root, report_kind, args.version)
    except LockedSitemapSourceError as error:
        print(f"{parser.prog}：参数错误：{error}", file=sys.stderr)
        return EXIT_USAGE

    # 期望站点地图：注册表全部静态责任页 + 清单记录的每一个产品/试验详情页。
    try:
        contract = derive_sitemap_contract(
            PageRegistry.load(),
            report_kind,
            product_ids=source.product_ids,
            trial_ids=source.trial_ids,
        )
    except SitemapBoundaryError as error:
        print(f"{parser.prog}：参数错误：{error}", file=sys.stderr)
        return EXIT_USAGE

    site_root = project_root / "reports" / args.report / args.version / "html"

    # 站点地图一一对应：期望与实际一一对应，缺页/多页/Top-N/额外 slug 失败关闭。
    sitemap = verify_sitemap_one_to_one(contract, enumerate_site_routes(site_root, report_kind))
    if not sitemap.ok:
        print(sitemap.message_zh)
        print(f"{args.report}_PORTAL_FAIL routes={len(contract.routes)} browsers=0")
        return EXIT_FAIL

    # 路由可达性：从首页/总览沿本地 HTML 锚点遍历期望站点地图。任一期望
    # 路由（尤其每个产品/试验动态详情页）不可达即失败关闭，且不启动浏览
    # 器、不产出截图；文件存在但门户内无入口的孤儿页在截图前就被否决。
    inspections = tuple(
        scan_page_html(
            (site_root / route_to_site_path(route)).read_text(encoding="utf-8"),
            route,
        )
        for route in contract.routes
    )
    reachability = verify_route_reachability(contract, inspections)
    if not reachability.ok:
        print(reachability.message_zh)
        print(f"{args.report}_PORTAL_FAIL routes={len(contract.routes)} browsers=0")
        return EXIT_FAIL

    browsers = list(dict.fromkeys(args.browser or ["chromium"]))
    viewports = list(dict.fromkeys(args.viewport or list(DEFAULT_VIEWPORTS)))
    output_dir = (
        Path(args.output_dir).expanduser()
        if args.output_dir
        else project_root / "verification" / args.report / args.version
    )
    site_digest = source.manifest.artifact.sha256
    run_digest = _run_digest(
        report=args.report,
        version=args.version,
        site_digest=site_digest,
        browsers=browsers,
        viewports=viewports,
        routes=contract.routes,
    )

    try:
        pages, traces, screenshot_count = _run_browser_acceptance(
            site_root=site_root,
            contract=contract,
            valid_paths=_valid_site_paths(site_root),
            browsers=browsers,
            viewports=viewports,
            output_dir=output_dir,
            run_digest=run_digest,
            site_digest=site_digest,
        )
    except Exception as error:  # noqa: BLE001 - CLI 需要给用户中文环境错误说明
        print(
            f"验收执行失败：{error}。请确认已安装 Chromium/WebKit 浏览器"
            "（python -m playwright install chromium webkit）。",
            file=sys.stderr,
        )
        return EXIT_USAGE

    ok = all(page["ok"] for page in pages)
    message_zh = _format_verdict(
        pages,
        routes=contract.routes,
        browsers=browsers,
        viewports=viewports,
        output_dir=output_dir,
        ok=ok,
    )
    print(message_zh)
    token = f"{args.report}_PORTAL_OK" if ok else f"{args.report}_PORTAL_FAIL"
    print(f"{token} routes={len(contract.routes)} browsers={len(browsers)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    report_payload = {
        "schema_version": "1.0",
        "tool": "verify_portal",
        "ok": ok,
        "report": args.report,
        "version": args.version,
        "manifest_id": source.manifest.manifest_id,
        "report_snapshot_id": source.manifest.report_snapshot_id,
        "run_digest": run_digest,
        "site_digest": site_digest,
        "browsers": browsers,
        "viewports": [list(vp) for vp in viewports],
        "routes": list(contract.routes),
        "sitemap": {
            "ok": sitemap.ok,
            "expected_routes": list(sitemap.expected_routes),
            "actual_routes": list(sitemap.actual_routes),
            "message_zh": sitemap.message_zh,
        },
        "reachability": {
            "ok": reachability.ok,
            "start_route": reachability.start_route,
            "reachable_routes": list(reachability.reachable_routes),
            "unreachable_routes": list(reachability.unreachable_routes),
            "message_zh": reachability.message_zh,
        },
        "pages": pages,
        "screenshots": {"count": screenshot_count, "dir": str(output_dir / "screenshots")},
        "traces": traces,
        "output_dir": str(output_dir),
        "message_zh": message_zh,
    }
    (output_dir / "report.json").write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return EXIT_OK if ok else EXIT_FAIL


def main() -> None:
    raise SystemExit(verify_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
