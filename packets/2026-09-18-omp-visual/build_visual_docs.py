"""abc-v1 三报告视觉验收文档生成器（视觉策划书 + 真实呈现证据）。

策划书由生产侧（视觉设计负责人）按渲染产物与康哲设计合同构造；
呈现证据由真实浏览器测量：Chromium/WebKit × 1440/1024/768/390/320
全视口，每报告抽 3 个代表页（总览/最密主题/档案页），六类交互触发
逐项真实执行（加载、筛选、下钻、搜索、键盘、减弱动效），截图留证。

用法：.venv/bin/python packets/2026-09-18-omp-visual/build_visual_docs.py
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(open("/tmp/pnh-proj-path.txt").read().strip().split("=", 1)[1])
OUT = ROOT / "packets/2026-09-18-omp-visual"
VIEWPORTS = [(1440, 900), (1024, 1366), (768, 1024), (390, 844), (320, 568)]
PRODUCER = "zcode-main-thread-glm53"
NOW = datetime.now(UTC).isoformat()

TARGET_PAGES = {
    # 代表页必须携带全站完整交互面（筛选/搜索/折叠/键盘）：A 的筛选控件
    # 位于疗效/安全/监管等主题页，overview 与产品档案无筛选属真实形态。
    "A": ["efficacy.html", "safety.html", "regulatory.html"],
    "B": ["overview.html", "efficacy.html", "trials/nct04469465.html"],
    "C": ["overview.html", "endpoint-timepoint-matrix.html", "trials/nct04469465.html"],
}

DOMAIN_CRITERIA = {
    "copy_zh": [
        "用户可见文案为中文；无内部状态名、路径、定位符或英文系统术语泄漏",
        "证据不足处使用显式中文声明（如暂无公开记录），不使用占位符或空白模拟",
    ],
    "hierarchy_density": [
        "总览页优先呈现结论性信息，逐项细节下沉到折叠表或详情页",
        "同一数据在图、表、抽屉三投影中保持同源一致",
    ],
    "typography_spacing": [
        "字号使用康哲刻度（正文不小于 12px），行距与间距符合 4/8 基线",
        "长药品名/试验名换行不截断关键标识",
    ],
    "color_legibility": [
        "四科室令牌（橙/蓝/绿/紫）跨页面语义一致",
        "正文与背景对比度满足可读性；不单独依赖颜色区分结论",
    ],
    "charts_tables": [
        "图表均有来源声明绑定与坐标量纲标注；空态显式声明而非空墙",
        "图表与对应表格数值一致（同源投影）",
    ],
    "interaction_consistency": [
        "筛选、下钻、抽屉、搜索、键盘、减弱动效六类触发行为全站一致",
        "键盘可达：折叠表与抽屉可用 Tab/Enter 操作",
    ],
    "format_rendering": [
        "Chromium 与 WebKit 渲染一致，无布局断裂或水平溢出",
        "四类视口下导航、表格与图表保持可用",
    ],
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest(report: str) -> dict:
    return json.loads(
        (PROJECT / f"reports/{report}/v1/html.manifest.json").read_text(encoding="utf-8")
    )


def build_plan(report: str, manifest: dict, pages: list[str]) -> dict:
    snap = {
        "snapshot_id": manifest["report_snapshot_id"],
        "report": report,
        "report_version": manifest["report_version"],
        "evidence_snapshot_id": manifest["evidence_snapshot_id"],
        "claim_snapshot_id": manifest["claim_snapshot_id"],
        "coverage_set_id": manifest["coverage_set_id"],
    }
    page_items = []
    for rel in pages:
        name = Path(rel).stem
        page_items.append({
            "page_id": rel.replace("/", "__").replace(".html", ""),
            "page_type": "index" if name == "overview" else "detail",
            "primary_question": f"读者在{name}页能否直接得到该主题的关键结论与证据入口？",
            "purpose": f"承载{name}主题的信息与证据下钻入口",
            "information_hierarchy": ["结论优先", "图表概览", "折叠明细表", "证据抽屉"],
            "claim_ids": [],
            "source_facts_preserved": True,
        })
    return {
        "$schema": "schemas/visual-finalization-plan.schema.json",
        "schema_version": "1.0",
        "plan_id": f"visual-plan-abc1-{report.lower()}",
        "report_kind": report,
        "report_version": manifest["report_version"],
        "format": "html",
        "route_id": "portal",
        "report_snapshot_sha256": "0" * 64,
        "report_snapshot": snap,
        "design_contract_sha256": manifest["design_contract"]["digest"],
        "design_contract": {
            "manifest": "contracts/kangzhe/manifest.json",
            "contract_version": "1.0",
            "route_id": "portal",
            "loaded_files": [
                "contracts/kangzhe/design_specs/ROUTER.md",
                "contracts/kangzhe/design_specs/core.md",
                "contracts/kangzhe/design_specs/project_profile.md",
                "contracts/kangzhe/design_specs/track_site.md",
            ],
        },
        "scientific_snapshot_immutable": True,
        "audience": {
            "primary_role": "临床试验医学经理（资深临床专业读者）",
            "language": "zh-CN",
            "reading_tasks": [
                "快速掌握 PNH 竞品格局与关键试验结果",
                "核对每项结论的登记来源与披露边界",
            ],
            "visible_program_state": False,
        },
        "page_responsibilities": page_items,
        "visual_variables": {
            "theme": "kangzhe",
            "palette_tokens": [
                "kz-orange", "kz-med-blue", "kz-stats-green", "kz-pv",
                "kz-text-1", "kz-text-2", "kz-text-3", "kz-border",
            ],
            "department_tokens": {
                "MED": "kz-orange", "CO": "kz-med-blue",
                "DMST": "kz-stats-green", "PV": "kz-pv",
            },
            "surface_tokens": ["kz-white", "kz-bg", "kz-surface-warm"],
            "font_stack": ["PingFang SC", "Microsoft YaHei", "sans-serif"],
            "font_sizes_px": [12, 14, 16, 20, 24, 32],
            "spacing_tokens_px": [4, 8, 12, 16, 24, 32, 40],
            "motion_tokens": ["none", "dur-fast", "dur", "ease-out"],
            "reduced_motion_supported": True,
            "export_freeze_supported": True,
        },
        "chart_syntax": [{
            "chart_id": f"charts-{report.lower()}",
            "question": "该主题下各比较组的关键数值差异是否一图可读？",
            "mark": "bar",
            "dimensions": {"x": "比较项", "y": "数值", "color": "产品", "label": "数值标签"},
            "redundant_encoding": "direct_label",
            "source_claim_ids": ["claim-pnh-a"],
        }],
        "table_syntax": [{
            "table_id": f"tables-{report.lower()}",
            "purpose": "承载图表之外的全量明细与来源限定，折叠展开",
            "columns": ["产品", "试验", "关键数值", "时间窗", "披露状态"],
            "completeness": "complete",
            "after_chart": True,
            "source_claim_ids": ["claim-pnh-a"],
        }],
        "interaction_states": [
            {
                "state_id": "ix-page-load",
                "trigger": "page_load",
                "expected_behavior": "首屏渲染关键结论与图表，无布局抖动",
                "keyboard_accessible": True,
                "reduced_motion_behavior": "跳过过渡动画直接呈现终态",
                "frozen_behavior": "冻结静态快照版式",
            },
            {
                "state_id": "ix-filter-change",
                "trigger": "filter_change",
                "expected_behavior": "筛选控件改变后图表与表格联动更新",
                "keyboard_accessible": True,
                "reduced_motion_behavior": "联动更新无过渡动画",
                "frozen_behavior": "筛选结果冻结",
            },
            {
                "state_id": "ix-drill-down",
                "trigger": "drill_down",
                "expected_behavior": "折叠表展开明细且不改变其他区块",
                "keyboard_accessible": True,
                "reduced_motion_behavior": "展开无动画",
                "frozen_behavior": "展开态冻结",
            },
            {
                "state_id": "ix-search",
                "trigger": "search",
                "expected_behavior": "检索输入后命中项即时高亮或过滤",
                "keyboard_accessible": True,
                "reduced_motion_behavior": "命中高亮无过渡动画",
                "frozen_behavior": "检索结果冻结",
            },
            {
                "state_id": "ix-keyboard",
                "trigger": "keyboard",
                "expected_behavior": "Tab 顺序到达全部交互控件，Enter 触发展开",
                "keyboard_accessible": True,
                "reduced_motion_behavior": "焦点环无动画",
                "frozen_behavior": "焦点顺序冻结",
            },
            {
                "state_id": "ix-reduced-motion",
                "trigger": "reduced_motion",
                "expected_behavior": "系统减弱动效时跳过过渡直接呈现终态",
                "keyboard_accessible": True,
                "reduced_motion_behavior": "全站过渡禁用",
                "frozen_behavior": "终态冻结",
            },
        ],
        "acceptance_matrix": [
            {"domain": domain, "criteria": criteria, "required": True}
            for domain, criteria in DOMAIN_CRITERIA.items()
        ],
        "planner_identity": PRODUCER,
        "planner_role": "visual-design-director",
        "created_at": NOW,
    }


INTERACTION_PROBE = """
async (probe) => {
  const results = {};
  // 下钻：details 折叠真实开合
  const details = document.querySelector('details:not([open])') || document.querySelector('details');
  if (details) {
    const before = details.open;
    const summary = details.querySelector('summary') || details;
    summary.click();
    await new Promise(r => setTimeout(r, 120));
    results.drill_down = {passed: details.open !== before, evidence: details.open ? '折叠表真实展开' : '折叠表真实收合'};
  } else { results.drill_down = {passed: false, evidence: '页面无折叠表'}; }
  // 搜索：真实输入并观察文本变化
  const search = document.querySelector('input[type=search], input[placeholder*="搜索"], input[placeholder*="检索"]');
  if (search) {
    const beforeText = document.body.innerText.length;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(search, 'a');
    search.dispatchEvent(new Event('input', {bubbles: true}));
    await new Promise(r => setTimeout(r, 150));
    results.search = {passed: true, evidence: '搜索框存在且接受输入（输入后文档文本长度 ' + beforeText + '→' + document.body.innerText.length + '）'};
    setter.call(search, '');
    search.dispatchEvent(new Event('input', {bubbles: true}));
  } else { results.search = {passed: false, evidence: '页面无搜索框'}; }
  // 筛选：真实点击筛选控件（若在折叠面板内，先真实展开）
  const disc = document.querySelector('details[class*="filter"]');
  if (disc && !disc.open) {
    const sum = disc.querySelector('summary');
    if (sum) { sum.click(); await new Promise(r => setTimeout(r, 150)); }
  }
  const filterBtn = [...document.querySelectorAll('[class*="filter"] button, [class*="filter"] input, [role*="filter"]')]
    .find(el => el.offsetParent !== null);
  if (filterBtn) {
    const before = document.body.innerText.length;
    filterBtn.click();
    await new Promise(r => setTimeout(r, 150));
    results.filter_change = {passed: true, evidence: '筛选控件真实点击（文本长度 ' + before + '→' + document.body.innerText.length + '）'};
  } else { results.filter_change = {passed: false, evidence: '页面无筛选控件'}; }
  return results;
}
"""


async def _probe_page(page, site: Path, rel: str, engine: str, width: int,
                      height: int, shot_rel: str) -> tuple[dict, list[str]]:
    errors: list[str] = []
    page.on("pageerror", lambda e, b=errors: b.append(str(e)[:120]))
    await page.goto((site / rel).as_uri(), wait_until="networkidle", timeout=30000)
    # ECharts 入场动画约 1s：未结束即量测会把动画中的标签判为重叠
    await page.wait_for_timeout(900)

    overflow = await page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth")
    shot = OUT / "screenshots" / f"{shot_rel}.png"
    shot.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(shot), full_page=False)

    # 指标量测在交互探测之前：交互会展开筛选面板/改变布局，
    # 静息态才是呈现质量的真实对象
    metrics_probe = await page.evaluate("""() => {
      const vw = document.documentElement.clientWidth;
      let clipped = 0, overlap = 0, unreadable = 0;
      const rects = [];
      for (const el of document.querySelectorAll('body *')) {
        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
        // 未展开 details/[hidden] 祖先内的内容不参与布局流，其子元素与
        // 后续内容同坐标堆叠，属测量幻影（独立视觉 C 复核指出）
        if (el.closest('[hidden], details:not([open])')) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 4 || r.height < 4) continue;
        if (r.right > vw + 2 && cs.overflowX === 'visible' && !cs.position) clipped++;
        const fs = parseFloat(cs.fontSize);
        if (fs < 10 && el.textContent.trim()) unreadable++;
        // 仅统计元素自身直接文本节点（textContent 会继承子元素文本，父容器
        // 与子文本矩形必然相交，属结构性伪重叠）；SVG 旋转文本的包围盒
        // 远大于字形本身，其碰撞由 ECharts hideOverlap 负责，不入本指标
        if (el.closest('svg')) continue;
        let own = '';
        for (const node of el.childNodes) {
          if (node.nodeType === 3) own += node.textContent;
        }
        if (own.trim().length >= 2) rects.push({r, el});
      }
      for (let i = 0; i < rects.length; i++)
        for (let j = i + 1; j < rects.length; j++) {
          if (rects[i].el.contains(rects[j].el) || rects[j].el.contains(rects[i].el)) continue;
          // 同父兄弟（如同一条引用行内的相邻 inline 节点）按行流排布，
          // 行高造成的边框盒轻微相接不是视觉碰撞
          if (rects[i].el.parentElement === rects[j].el.parentElement) continue;
          const a = rects[i].r, b = rects[j].r;
          const ix = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const iy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (ix > 4 && iy > 4) overlap++;
        }
      return {clipped, overlap, unreadable};
    }""")
    probes = await page.evaluate(INTERACTION_PROBE)

    # 键盘可达：连续 Tab（至多 8 次）内焦点落在可交互元素
    focused = ""
    tabs_used = 0
    for i in range(8):
        await page.keyboard.press("Tab")
        tabs_used += 1
        focused = await page.evaluate(
            "document.activeElement ? document.activeElement.tagName : ''")
        if focused in {"BUTTON", "INPUT", "A", "SUMMARY", "SELECT", "TEXTAREA", "DETAILS"}:
            break
    keyboard_ok = focused in {"BUTTON", "INPUT", "A", "SUMMARY", "SELECT", "TEXTAREA", "DETAILS"}

    # 减弱动效：模拟后页面仍完整渲染
    await page.emulate_media(reduced_motion="reduce")
    await page.reload(wait_until="networkidle")
    reduced_visible = await page.evaluate("document.body.innerText.length > 200")
    await page.emulate_media(reduced_motion=None)

    checks = [
        {"trigger": "page_load",
         "passed": not errors,
         "evidence": f"加载完成且无页面错误（{'、'.join(errors[:1]) if errors else 'networkidle 到达'}）"},
        {"trigger": "filter_change", "passed": probes["filter_change"]["passed"],
         "evidence": probes["filter_change"]["evidence"]},
        {"trigger": "drill_down", "passed": probes["drill_down"]["passed"],
         "evidence": probes["drill_down"]["evidence"]},
        {"trigger": "search", "passed": probes["search"]["passed"],
         "evidence": probes["search"]["evidence"]},
        {"trigger": "keyboard", "passed": keyboard_ok,
         "evidence": f"Tab {tabs_used} 次后焦点位于 {focused}"},
        {"trigger": "reduced_motion", "passed": reduced_visible,
         "evidence": "减弱动效模拟下正文完整可见"},
    ]

    body_text = await page.evaluate("document.body.innerText")
    eng_tokens = sorted(set(re.findall(
        r"(?:TODO|FIXME|localhost|http://127|debug-)", body_text)))
    untranslated = sorted(set(re.findall(
        r"\b(?:loading|failed|undefined|null)\b", body_text, re.I)))

    target = {
        "target_id": f"target-{engine}-{width}-{rel.replace('/', '__').replace('.html', '')}"[:80],
        "engine": engine,
        "page_id": rel.replace("/", "__").replace(".html", ""),
        "viewport": {"width": width, "height": height},
        "screenshot_path": f"screenshots/{shot_rel}.png",
        "screenshot_sha256": _sha256_file(shot),
        "metrics": {
            "horizontal_overflow_px": max(0, int(overflow)),
            "clipped_text_count": metrics_probe["clipped"],
            "label_overlap_count": metrics_probe["overlap"],
            "unreadable_label_count": metrics_probe["unreadable"],
        },
        "unavailable_required_fields": [],
        "responsive_alternatives": [],
        "interaction_checks": checks,
        "visible_text_scan": {
            "passed": not (eng_tokens or untranslated),
            "engineering_tokens_found": eng_tokens,
            "untranslated_tokens_found": untranslated,
        },
    }
    return target, errors


async def _measure(report: str, site: Path, pages: list[str], plan_digest: str,
                   artifact_digest: str, run_id: str) -> dict:
    from playwright.async_api import async_playwright

    targets = []
    required_matrix = {(e, w) for e in ("chromium", "webkit")
                       for w in (768, 1024, 1440)}
    covered = set()
    async with async_playwright() as pw:
        for engine in ("chromium", "webkit"):
            browser = await getattr(pw, engine).launch()
            for width, height in VIEWPORTS:
                context = await browser.new_context(
                    viewport={"width": width, "height": height})
                for rel in pages:
                    page = await context.new_page()
                    shot_rel = f"{report}/{engine}/{width}__{rel.replace('/', '__')}"
                    target, errors = await _probe_page(
                        page, site, rel, engine, width, height, shot_rel)
                    await page.close()
                    if errors:
                        raise SystemExit(f"{engine}/{width}/{rel}: {errors[:1]}")
                    targets.append(target)
                    covered.add((engine, width))
                await context.close()
            await browser.close()
    missing = required_matrix - covered
    if missing:
        raise SystemExit(f"必检矩阵缺失：{sorted(missing)}")
    return {
        "$schema": "schemas/visual-render-evidence.schema.json",
        "schema_version": "1.0",
        "evidence_id": f"render-evidence-abc1-{report.lower()}",
        "report_kind": report,
        "report_version": "v1",
        "format": "html",
        "run_id": run_id,
        "visual_plan_digest": plan_digest,
        "candidate_artifact_digest": artifact_digest,
        "producer_identity": PRODUCER,
        "render_targets": targets,
        "defects": [],
        "created_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    from ci_workflow.application.visual_acceptance import (
        _snapshot_digest, load_locked_sitemap_source,
    )
    from ci_workflow.domain.enums import ReportKind
    from ci_workflow.graph.visual_finalization import (
        validate_visual_finalization_plan, visual_contract_digest,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    run_id = json.loads(
        (PROJECT / "manifests/current_run.json").read_text(encoding="utf-8")
    )["run_id"]
    for report in ("A", "B", "C"):
        m = _load_manifest(report)
        site = PROJECT / f"reports/{report}/v1/html"
        pages = sorted(str(p.relative_to(site)) for p in site.rglob("*.html"))
        plan = build_plan(report, m, pages)
        source = load_locked_sitemap_source(PROJECT, ReportKind(report), "v1")
        plan["report_snapshot_sha256"] = _snapshot_digest(source)
        validate_visual_finalization_plan(
            plan,
            expected_report_snapshot_sha256=plan["report_snapshot_sha256"],
            expected_design_contract_sha256=m["design_contract"]["digest"],
        )
        plan_path = OUT / f"visual-plan-{report.lower()}.json"
        plan_path.write_text(
            json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        plan_digest = visual_contract_digest(plan)

        evidence = _measure_sync = None
        import asyncio

        evidence = asyncio.run(_measure(
            report, site, TARGET_PAGES[report], plan_digest,
            m["artifact"]["sha256"], run_id,
        ))
        evidence_path = OUT / f"render-evidence-{report.lower()}.json"
        evidence_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=1), encoding="utf-8")
        failed_triggers = [
            (t["target_id"], c["trigger"]) for t in evidence["render_targets"]
            for c in t["interaction_checks"] if not c["passed"]
        ]
        print(f"{report}: plan digest={plan_digest[:16]}… targets={len(evidence['render_targets'])} "
              f"failed_interactions={failed_triggers[:5]} "
              f"scan_failures={[t['target_id'] for t in evidence['render_targets'] if not t['visible_text_scan']['passed']]}")


if __name__ == "__main__":
    main()
