"""Medical-manager adversarial attack on C portal (worker_03).

Writes screenshots and machine-readable observations under this reviews folder.
Does not patch renderer/templates/assets/fixtures.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
SHOTS = ROOT / "screenshots"
OBS = ROOT / "observations"
SHOTS.mkdir(parents=True, exist_ok=True)
OBS.mkdir(parents=True, exist_ok=True)

STATIC_PAGES = [
    "overview",
    "design-map",
    "trial-profile",
    "population-disease-definition",
    "inclusion-criteria",
    "exclusion-criteria",
    "treatment-arms",
    "endpoint-timepoint-matrix",
    "visit-duration-followup",
    "sample-analysis-statistics",
    "design-patterns",
    "evidence-versions-limitations",
]
WIDTHS = (1024, 1280, 1440, 1920)
BROWSERS = ("chromium", "webkit")

LEAKS = [
    "field_family",
    "source_role",
    "not_publicly_disclosed",
    "registry_result_or_primary_report",
    "c_missing_",
    "candidate_paths",
    "工作流",
    "后端",
    "提示词",
    "evidence-gate",
    "EvidenceGate",
    "ReportKind",
    "worker_",
    "Codex",
    "pytest",
    "render_report",
    "FactDisclosureState",
    "DesignFieldFamily",
    "pipeline",
    "fixture",
]
FORBIDDEN_UX = [
    "唯一最佳",
    "最佳方案",
    "推荐唯一",
    "Click",
    "Loading...",
    "undefined",
    "null",
    "NaN",
    "TODO",
    "FIXME",
    "占位",
    "示例数据",
]

metrics: dict = {
    "schema_version": "c-attack-metrics.v1",
    "role": "worker_03",
    "site_root": str(SITE),
    "engines": [],
    "pages": [],
    "defects": [],
    "passed_checks": [],
    "screenshots": [],
}


def note(
    kind: str,
    severity: str,
    page_id: str,
    engine: str,
    width: int,
    detail: str,
    evidence: dict | None = None,
) -> None:
    item = {
        "kind": kind,
        "severity": severity,
        "page_id": page_id,
        "engine": engine,
        "width": width,
        "detail": detail,
        "evidence": evidence or {},
    }
    metrics["defects"].append(item)


def ok(
    check: str,
    page_id: str | None = None,
    engine: str | None = None,
    width: int | None = None,
    detail: str = "",
) -> None:
    metrics["passed_checks"].append(
        {
            "check": check,
            "page_id": page_id,
            "engine": engine,
            "width": width,
            "detail": detail,
        }
    )


def attack_page(page, engine: str, page_id: str, rel: str, width: int, *, is_trial: bool = False) -> dict:
    uri = (SITE / rel).as_uri()
    page.set_viewport_size({"width": width, "height": 900})
    errors: list[str] = []
    remote: list[str] = []

    def on_console(message) -> None:
        if message.type == "error":
            errors.append(f"console:{message.type}:{message.text}")

    def on_pageerror(error) -> None:
        errors.append(f"page:{error}")

    def on_request(request) -> None:
        if request.url.startswith(("http://", "https://")):
            remote.append(request.url)

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    page.on("request", on_request)
    page.goto(uri, wait_until="load")
    page.wait_for_function("document.readyState === 'complete'")
    page.wait_for_timeout(120)

    body = page.locator("body").inner_text()
    html_lang = page.locator("html").get_attribute("lang")
    row: dict = {
        "engine": engine,
        "page_id": page_id,
        "width": width,
        "rel": rel,
        "lang": html_lang,
        "title": page.title(),
        "has_chart_module": page.locator("#kz-chart-module").count() == 1,
        "chart_types": page.locator("[data-chart-type]").evaluate_all(
            "ns => ns.map(n => n.getAttribute('data-chart-type'))"
        ),
        "row_count": page.locator(".kz-chart-table__row[data-row-id]").count(),
        "evidence_triggers": page.locator("[data-evidence-open]").count(),
        "path_cards": page.locator("[data-path-id]").count() if page_id == "design-patterns" else None,
        "overflow": page.evaluate(
            """() => ({doc: document.documentElement.scrollWidth, body: document.body.scrollWidth, vw: window.innerWidth})"""
        ),
        "chart_box": page.locator("#kz-chart-module").bounding_box()
        if page.locator("#kz-chart-module").count()
        else None,
        "console_errors": list(errors),
        "remote_http": [u for u in remote if u.startswith(("http://", "https://"))],
    }

    table_y = page.evaluate(
        """() => {
      const chart = document.querySelector('#kz-chart-module');
      const table = document.querySelector('.kz-chart-table')
        || document.querySelector('[data-complete-table]')
        || document.querySelector('table');
      if (!chart || !table) return null;
      const c = chart.getBoundingClientRect();
      const t = table.getBoundingClientRect();
      return {
        chartTop: c.top + window.scrollY,
        tableTop: t.top + window.scrollY,
        chartHeight: c.height,
        tableHeight: t.height
      };
    }"""
    )
    row["chart_table_order"] = table_y

    core_visible = page.evaluate(
        """() => {
      const chart = document.querySelector('#kz-chart-module');
      if (!chart) return {ok:false, reason:'missing'};
      const r = chart.getBoundingClientRect();
      const vh = window.innerHeight;
      const visibleHeight = Math.min(r.bottom, vh) - Math.max(r.top, 0);
      return {
        ok: r.top < vh && visibleHeight > 40,
        top: r.top,
        bottom: r.bottom,
        vh: vh,
        visibleHeight: visibleHeight,
        width: r.width,
        height: r.height
      };
    }"""
    )
    row["core_chart_in_viewport"] = core_visible

    ids = page.evaluate(
        """() => {
      const chartIds = [...document.querySelectorAll('#kz-chart-module [data-row-id]')]
        .map(n => n.getAttribute('data-row-id'));
      const tableIds = [...document.querySelectorAll('.kz-chart-table__row[data-row-id]')]
        .map(n => n.getAttribute('data-row-id'));
      const uniq = a => [...new Set(a)];
      return {chart: uniq(chartIds), table: uniq(tableIds)};
    }"""
    )
    row["row_ids"] = ids

    leaks_hit = [token for token in LEAKS if token in body]
    forbidden_hit = [token for token in FORBIDDEN_UX if token in body]
    row["leaks"] = leaks_hit
    row["forbidden_ux"] = forbidden_hit
    eng_phrases = re.findall(
        r"\b(?:worker|fixture|pipeline|schema|endpoint_family|source_locator|disclosure_state|field_family)\b",
        body,
        flags=re.I,
    )
    row["eng_phrases"] = sorted(set(eng_phrases))

    should_shot = (
        width in (1024, 1920)
        and page_id
        in {
            "overview",
            "trial-profile",
            "inclusion-criteria",
            "treatment-arms",
            "design-patterns",
            "endpoint-timepoint-matrix",
            "sample-analysis-statistics",
        }
    ) or (is_trial and width == 1280 and page_id == "nct02260986")
    if should_shot:
        shot_name = f"{engine}_{page_id}_{width}.png"
        page.screenshot(path=str(SHOTS / shot_name), full_page=False)
        metrics["screenshots"].append(shot_name)
        row["screenshot"] = shot_name

    if html_lang != "zh-CN":
        note("lang", "high", page_id, engine, width, f"html lang={html_lang}")
    else:
        ok("lang_zh_CN", page_id, engine, width)

    if not row["has_chart_module"]:
        note("missing_chart", "critical", page_id, engine, width, "缺少 #kz-chart-module")
    if row["row_count"] <= 0:
        note("empty_table", "critical", page_id, engine, width, "完整表无 data-row-id 行")
    if leaks_hit:
        note("internal_leak", "high", page_id, engine, width, f"泄露: {leaks_hit}")
    if forbidden_hit:
        note("forbidden_ux", "high", page_id, engine, width, f"禁用表达: {forbidden_hit}")
    if row["eng_phrases"]:
        note(
            "english_engineering",
            "medium",
            page_id,
            engine,
            width,
            f"工程英文: {row['eng_phrases']}",
        )

    overflow = row["overflow"]
    if overflow["doc"] > width + 1 or overflow["body"] > width + 1:
        note("horizontal_overflow", "high", page_id, engine, width, f"横向溢出 {overflow}")
    else:
        ok("no_horizontal_drag", page_id, engine, width)

    chart_box = row["chart_box"]
    if chart_box:
        if chart_box["x"] < -1 or chart_box["x"] + chart_box["width"] > width + 1:
            note("chart_clip", "high", page_id, engine, width, f"核心图越界 {chart_box}")
        else:
            ok("chart_within_viewport_x", page_id, engine, width)

    if not core_visible.get("ok"):
        note(
            "core_chart_not_default_visible",
            "high",
            page_id,
            engine,
            width,
            f"首屏核心图不可见: {core_visible}",
        )
    else:
        ok(
            "core_chart_default_visible",
            page_id,
            engine,
            width,
            str(core_visible.get("visibleHeight")),
        )

    if table_y and table_y["tableTop"] + 1 < table_y["chartTop"]:
        note("table_before_chart", "high", page_id, engine, width, f"表在图前: {table_y}")
    elif table_y:
        ok("chart_before_table", page_id, engine, width)

    chart_set = set(ids["chart"])
    table_set = set(ids["table"])
    if chart_set and table_set:
        if chart_set != table_set:
            if not chart_set.issubset(table_set) and not table_set.issubset(chart_set):
                note(
                    "chart_table_id_mismatch",
                    "critical",
                    page_id,
                    engine,
                    width,
                    f"chart={sorted(chart_set)} table={sorted(table_set)}",
                )
            else:
                note(
                    "chart_table_id_unequal_subset",
                    "medium",
                    page_id,
                    engine,
                    width,
                    f"chart={sorted(chart_set)} table={sorted(table_set)}",
                )
        else:
            ok("chart_table_ids_equal", page_id, engine, width)

    if errors:
        note("console_or_page_error", "high", page_id, engine, width, str(errors[:5]))
    if row["remote_http"]:
        note(
            "remote_runtime_request",
            "critical",
            page_id,
            engine,
            width,
            str(row["remote_http"][:5]),
        )
    if page_id == "design-patterns" and (row["path_cards"] or 0) < 2:
        note(
            "paths_lt_2",
            "critical",
            page_id,
            engine,
            width,
            f"path cards={row['path_cards']}",
        )
    if "康哲药业" not in body:
        note("missing_brand", "medium", page_id, engine, width, "缺少康哲药业品牌")

    if page_id == "overview":
        for bad in (
            "C 类报告",
            "C类报告",
            "系统工作方式",
            "证据门槛",
            "工作流",
            "程序状态",
            "报告类型 C",
        ):
            if bad in body:
                note(
                    "overview_system_explainer",
                    "high",
                    page_id,
                    engine,
                    width,
                    f"首页泄露系统说明: {bad}",
                )
        for need in ("适应症", "观察截止"):
            if need not in body:
                note(
                    "overview_missing_meta",
                    "high",
                    page_id,
                    engine,
                    width,
                    f"首页缺少 {need}",
                )

    metrics["pages"].append(row)
    return row


def attack_filters(page, engine: str) -> None:
    width = 1280
    page.set_viewport_size({"width": width, "height": 900})
    page.goto((SITE / "overview.html").as_uri(), wait_until="load")
    page.wait_for_timeout(100)
    panel = page.locator("#kz-filter-panel")
    if panel.count() and not panel.evaluate("node => node.open"):
        page.locator("#kz-filter-panel > summary").click()
    buttons = page.locator('button[data-filter-dimension="trial"][data-filter-value]')
    if buttons.count() < 2:
        note(
            "filter_trial_buttons",
            "critical",
            "overview",
            engine,
            width,
            f"trial buttons={buttons.count()}",
        )
        return
    before = page.locator(".kz-chart-table__row[data-row-id]").evaluate_all(
        "ns => ns.filter(n => n.style.display !== 'none').map(n => n.getAttribute('data-row-id'))"
    )
    val = buttons.nth(0).get_attribute("data-filter-value")
    buttons.nth(0).click()
    page.wait_for_timeout(80)
    after = page.locator(".kz-chart-table__row[data-row-id]").evaluate_all(
        "ns => ns.filter(n => n.style.display !== 'none').map(n => n.getAttribute('data-row-id'))"
    )
    if not after or not (set(after) < set(before)):
        note(
            "page_filter_not_narrowing",
            "critical",
            "overview",
            engine,
            width,
            f"before={len(before)} after={len(after)}",
        )
    else:
        ok("page_filter_narrows", "overview", engine, width, f"{len(before)}->{len(after)}")
    if not val or val not in page.url:
        note("url_missing_trial_filter", "high", "overview", engine, width, page.url)
    else:
        ok("url_restores_trial_filter", "overview", engine, width, page.url)

    sync = page.evaluate(
        """() => {
      const visibleTable = [...document.querySelectorAll('.kz-chart-table__row[data-row-id]')]
        .filter(n => n.style.display !== 'none')
        .map(n => n.getAttribute('data-row-id'));
      const visibleChart = window.__C_VISIBLE_CHART_ROW_IDS__ || [];
      return {visibleTable, visibleChart};
    }"""
    )
    if sync["visibleChart"] and set(sync["visibleChart"]) - set(sync["visibleTable"]):
        note("filter_chart_table_desync", "high", "overview", engine, width, str(sync))
    else:
        ok("filter_chart_table_sync", "overview", engine, width)

    page_url = page.url
    mod = page.locator('button[data-filter-scope="module"][data-filter-value]')
    if mod.count() >= 1:
        panel = page.locator("#kz-filter-panel")
        if panel.count() and not panel.evaluate("node => node.open"):
            page.locator("#kz-filter-panel > summary").click()
        mod.first.click()
        page.wait_for_timeout(80)
        if val and val not in page.url:
            note("module_filter_clears_page", "high", "overview", engine, width, page.url)
        else:
            ok("module_filter_keeps_page", "overview", engine, width, page.url)
        if page.url == page_url:
            note("module_filter_no_url_change", "medium", "overview", engine, width, page.url)
    else:
        note("module_filter_missing", "medium", "overview", engine, width, "无模块筛选按钮")


def attack_evidence(page, engine: str) -> None:
    width = 1280
    page.emulate_media(reduced_motion="reduce")
    page.set_viewport_size({"width": width, "height": 900})
    page.goto((SITE / "inclusion-criteria.html").as_uri(), wait_until="load")
    page.wait_for_timeout(100)
    trigger = page.locator("[data-evidence-open]").first
    if trigger.count() == 0:
        note(
            "evidence_trigger_missing",
            "critical",
            "inclusion-criteria",
            engine,
            width,
            "无证据下钻入口",
        )
        return
    trigger.focus()
    trigger.click()
    page.wait_for_timeout(80)
    panel = page.locator("#kz-evidence-drawer-panel")
    if panel.count() == 0 or not panel.is_visible():
        note(
            "evidence_drawer_not_open",
            "critical",
            "inclusion-criteria",
            engine,
            width,
            "抽屉未打开",
        )
        return
    text = panel.inner_text()
    page.screenshot(
        path=str(SHOTS / f"{engine}_evidence_drawer_open_{width}.png"),
        full_page=False,
    )
    metrics["screenshots"].append(f"{engine}_evidence_drawer_open_{width}.png")
    for need in ("来源", "原始"):
        if need not in text:
            note(
                "evidence_drawer_missing_label",
                "high",
                "inclusion-criteria",
                engine,
                width,
                f"缺少 {need}",
            )
    for bad in ("source_role", "field_family", "not_publicly_disclosed", "EvidenceView"):
        if bad in text:
            note(
                "evidence_drawer_leak",
                "high",
                "inclusion-criteria",
                engine,
                width,
                f"抽屉泄露 {bad}",
            )
    clinical_bits = ["版本", "定位", "试验", "字段", "量表", "时间", "运算符", "阈值", "单位"]
    hit = [bit for bit in clinical_bits if bit in text]
    if len(hit) < 2:
        note(
            "evidence_drawer_thin_clinical",
            "medium",
            "inclusion-criteria",
            engine,
            width,
            f"临床下钻词过少: {hit}; snippet={text[:240]}",
        )
    else:
        ok("evidence_drawer_clinical_terms", "inclusion-criteria", engine, width, str(hit))
    page.keyboard.press("Escape")
    page.wait_for_timeout(80)
    if panel.is_visible():
        note("escape_does_not_close", "high", "inclusion-criteria", engine, width, "Esc 未关闭")
    else:
        ok("escape_closes_drawer", "inclusion-criteria", engine, width)
    active = page.evaluate(
        """() => document.activeElement && document.activeElement.hasAttribute('data-evidence-open')"""
    )
    if not active:
        note("focus_not_returned", "high", "inclusion-criteria", engine, width, "焦点未回到触发器")
    else:
        ok("focus_returns", "inclusion-criteria", engine, width)


def attack_trial_nav(page, engine: str) -> None:
    width = 1280
    page.goto((SITE / "trial-profile.html").as_uri(), wait_until="load")
    page.wait_for_timeout(80)
    links = page.locator('a[href*="trials/"]').evaluate_all(
        "ns => ns.map(n => n.getAttribute('href'))"
    )
    if len(set(links)) < 4:
        note(
            "trial_index_links",
            "high",
            "trial-profile",
            engine,
            width,
            f"试验详情链接不足: {links}",
        )
    else:
        ok("trial_index_links", "trial-profile", engine, width, str(sorted(set(links))))
    page.goto((SITE / "trials/nct02260986.html").as_uri(), wait_until="load")
    crumb = page.locator(".kz-c-breadcrumb a")
    if crumb.count() < 1:
        note("trial_breadcrumb_missing", "medium", "nct02260986", engine, width, "无面包屑")
    else:
        crumb.first.click()
        page.wait_for_timeout(80)
        if page.url.endswith("trial-profile.html"):
            ok("breadcrumb_back", "nct02260986", engine, width)
        else:
            note("breadcrumb_nav_fail", "medium", "nct02260986", engine, width, page.url)


def attack_disclosure_labels(page, engine: str) -> None:
    width = 1440
    page.goto((SITE / "sample-analysis-statistics.html").as_uri(), wait_until="load")
    page.wait_for_timeout(80)
    body = page.locator("body").inner_text()
    if not any(token in body for token in ("未公开", "未公开披露", "未公开发布")):
        note(
            "missing_unpublished_label",
            "high",
            "sample-analysis-statistics",
            engine,
            width,
            "统计页未见“未公开”类标签",
        )
    else:
        ok("unpublished_label_present", "sample-analysis-statistics", engine, width)
    for bad in ("NOT_PUBLICLY_DISCLOSED", "NOT_APPLICABLE", "MISSING"):
        if bad in body:
            note(
                "raw_disclosure_enum",
                "high",
                "sample-analysis-statistics",
                engine,
                width,
                bad,
            )


def main() -> None:
    with sync_playwright() as playwright:
        for engine in BROWSERS:
            browser = getattr(playwright, engine).launch()
            metrics["engines"].append(engine)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            for width in WIDTHS:
                for page_id in STATIC_PAGES:
                    attack_page(page, engine, page_id, f"{page_id}.html", width)
            for width in (1024, 1280, 1920):
                for trial in (
                    "nct02260986",
                    "nct04178967",
                    "nct03985943",
                    "nct05149313",
                ):
                    attack_page(
                        page,
                        engine,
                        trial,
                        f"trials/{trial}.html",
                        width,
                        is_trial=True,
                    )
            attack_filters(page, engine)
            attack_evidence(page, engine)
            attack_trial_nav(page, engine)
            attack_disclosure_labels(page, engine)
            context.close()
            browser.close()

    summary = {
        "defect_count": len(metrics["defects"]),
        "by_severity": dict(Counter(item["severity"] for item in metrics["defects"])),
        "by_kind": dict(Counter(item["kind"] for item in metrics["defects"])),
    }
    seen: set[tuple] = set()
    unique: list[dict] = []
    for item in metrics["defects"]:
        detail = item["detail"] if isinstance(item["detail"], str) else str(item["detail"])
        signature = (
            item["severity"],
            item["kind"],
            item["page_id"],
            item["engine"],
            re.sub(r"\d+(?:\.\d+)?", "N", detail)[:180],
        )
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(item)
    summary["unique_defect_signatures"] = len(unique)
    summary["unique_defects"] = unique
    metrics["summary"] = summary

    out = OBS / "medical-manager-attack.json"
    out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print("pages_checked", len(metrics["pages"]))
    print(
        "defects",
        summary["defect_count"],
        "unique",
        summary["unique_defect_signatures"],
        summary["by_severity"],
    )
    print("by_kind", summary["by_kind"])
    print("screenshots", len(metrics["screenshots"]))
    print("passed", len(metrics["passed_checks"]))
    for item in unique[:60]:
        print(
            f"- [{item['severity']}/{item['kind']}] {item['engine']} "
            f"{item['page_id']}@{item['width']}: {item['detail'][:220]}"
        )


if __name__ == "__main__":
    main()
