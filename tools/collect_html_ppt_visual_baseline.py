#!/usr/bin/env python3
"""Task 8.6：全页多视口 Chromium/WebKit 原图与诊断收集器。

只读取当前锁定的 A/B/C 单文件 HTML-PPT，写出截图与中文台账。不改医学数据，
不重渲染，不代替 Codex 终验。

Usage::

    uv run python tools/collect_html_ppt_visual_baseline.py
    uv run python tools/collect_html_ppt_visual_baseline.py \\
        --output-dir docs/acceptance/runs/8.6/visual-baseline
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserType, Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

LOCKED_DECKS: dict[str, dict[str, Any]] = {
    "A": {
        "path": "output/html-ppt/report-a.html",
        "sha256": "718705c6d1aa1347907b600e27a9753230f8ad93afb17a0cfa73f44eb164d7a6",
        "page_count": 20,
        "slide_ids": [
            "a-cover",
            "a-toc",
            "a-summary",
            "a-landscape",
            "a-products",
            "a-clinical",
            "a-efficacy",
            "a-efficacy-2",
            "a-efficacy-3",
            "a-efficacy-4",
            "a-efficacy-5",
            "a-safety",
            "a-matrix",
            "a-matrix-2",
            "a-regulatory",
            "a-companies",
            "a-patents",
            "a-history",
            "a-limitations",
            "a-ending",
        ],
        "watch_ids": ["a-matrix-2"],
    },
    "B": {
        "path": "output/html-ppt/report-b.html",
        "sha256": "2bf6a334fd484f1df99bca363f1425503f83e9aa9727a73986a6fcd846c3a406",
        "page_count": 24,
        "slide_ids": [
            "b-cover",
            "b-toc",
            "b-summary",
            "b-efficacy",
            "b-longitudinal",
            "b-safety",
            "b-matrix",
            "b-baseline-overview",
            "b-demographics",
            "b-disease-context",
            "b-severity",
            "b-disposition-overview",
            "b-flow",
            "b-adherence",
            "b-loss-exit",
            "b-screen-failure",
            "b-rescue",
            "b-prohibited",
            "b-deviation",
            "b-exposure",
            "b-subgroups",
            "b-profiles",
            "b-limitations",
            "b-ending",
        ],
        "watch_ids": ["b-efficacy"],
    },
    "C": {
        "path": "output/html-ppt/report-c.html",
        "sha256": "e284dec451cc8355a5ebdd376a903785b3a10e984a9a6bae9bc3c73a61a8f342",
        "page_count": 18,
        "slide_ids": [
            "c-cover",
            "c-toc",
            "c-summary",
            "c-design-map",
            "c-population",
            "c-inclusion",
            "c-exclusion",
            "c-arms",
            "c-endpoints",
            "c-visits",
            "c-stats",
            "c-dossiers",
            "c-identity",
            "c-patterns",
            "c-path-1",
            "c-path-2",
            "c-limitations",
            "c-ending",
        ],
        "watch_ids": ["c-endpoints"],
    },
}

VIEWPORTS: tuple[tuple[str, int, int, str], ...] = (
    ("1280x800", 1280, 800, "CFORCE CSS 最大化基线"),
    ("1920x1080", 1920, 1080, "Mi Monitor CSS 最大化基线"),
    ("2048x1024", 2048, 1024, "非 16:9 压力视口"),
    ("1280x720", 1280, 720, "逻辑画布回归视口"),
)
BROWSERS = ("chromium", "webkit")
REMOTE_SCHEMES = ("http://", "https://", "ws://", "wss://")
DEFAULT_SETTLE_MS = 900
WATCH_SETTLE_MS = 1200

DIAGNOSTIC_JS = """() => {
  const slide = document.querySelector('.slide.is-active');
  const deck = document.querySelector('.deck');
  if (!slide || !deck) {
    return { error: 'missing-slide-or-deck' };
  }
  const box = slide.getBoundingClientRect();
  const deckBox = deck.getBoundingClientRect();
  const issues = [];
  const sel = [
    'h1', 'h2', 'h3', 'p', 'li', 'td', 'th',
    '.disclosure-row', '.kz-card', '.stat-strip', '.content-conclusion',
    '.slide-number', '.kz-label', '.chart-label', 'figcaption', 'svg text'
  ].join(',');
  const nodes = slide.querySelectorAll(sel);
  for (const el of nodes) {
    if (el.closest('aside.notes')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const label = (el.getAttribute('data-slide-id')
      || el.className || el.tagName || 'node').toString().slice(0, 80);
    const text = (el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 48);
    if (r.right > box.right + 2.5 || r.bottom > box.bottom + 2.5
        || r.left < box.left - 2.5 || r.top < box.top - 2.5) {
      issues.push({
        kind: 'overflow',
        severity: 'high',
        node: label,
        text,
      });
    }
    if (el.scrollWidth > el.clientWidth + 4 && !el.closest('svg')) {
      issues.push({
        kind: 'clip',
        severity: 'high',
        node: label,
        text,
      });
    }
  }
  const svgTexts = Array.from(slide.querySelectorAll('svg text'))
    .map((el) => {
      const r = el.getBoundingClientRect();
      return {
        r,
        text: (el.textContent || '').replace(/\\s+/g, ' ').trim(),
      };
    })
    .filter((item) => item.r.width >= 2 && item.r.height >= 2 && item.text);
  for (let i = 0; i < svgTexts.length; i += 1) {
    for (let j = i + 1; j < svgTexts.length; j += 1) {
      const a = svgTexts[i].r;
      const b = svgTexts[j].r;
      const overlapW = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const overlapH = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (overlapW > 4 && overlapH > 3) {
        issues.push({
          kind: 'svg-label-overlap',
          severity: 'medium',
          node: 'svg text',
          text: svgTexts[i].text.slice(0, 24) + ' × ' + svgTexts[j].text.slice(0, 24),
        });
      }
    }
  }
  const bodyText = (slide.innerText || '').replace(/\\s+/g, ' ');
  const hasEasi = /EASI/.test(bodyText) && /75/.test(bodyText);
  if (hasEasi && /75\\s+%/.test(bodyText)) {
    issues.push({
      kind: 'cjk-percent-spacing',
      severity: 'medium',
      node: 'body',
      text: 'EASI 数字与百分号之间存在多余空格',
    });
  }
  const scaleActual = document.documentElement.style.getPropertyValue('--deck-scale').trim();
  const scaleExpectedNumber = Math.min(
    document.documentElement.clientWidth / 1280,
    document.documentElement.clientHeight / 720,
  );
  const scaleExpected = String(scaleExpectedNumber);
  if (Math.abs(Number(scaleActual) - scaleExpectedNumber) > 0.001) {
    issues.push({
      kind: 'scale-mismatch',
      severity: 'blocker',
      node: ':root --deck-scale',
      text: scaleActual + ' != ' + scaleExpected,
    });
  }
  const centerErrorX = Math.abs(deckBox.left + deckBox.width / 2 - innerWidth / 2);
  const centerErrorY = Math.abs(deckBox.top + deckBox.height / 2 - innerHeight / 2);
  if (centerErrorX > 0.5 || centerErrorY > 0.5) {
    issues.push({
      kind: 'centering',
      severity: 'medium',
      node: '.deck',
      text: 'dx=' + centerErrorX.toFixed(2) + ' dy=' + centerErrorY.toFixed(2),
    });
  }
  if (deck.offsetWidth !== 1280 || slide.offsetHeight !== 720) {
    issues.push({
      kind: 'logical-canvas',
      severity: 'blocker',
      node: '.deck/.slide',
      text: deck.offsetWidth + 'x' + slide.offsetHeight,
    });
  }
  const h1 = slide.querySelector('h1');
  return {
    slideId: slide.dataset.slideId || '',
    title: h1 ? (h1.textContent || '').trim() : '',
    pageNumber: (slide.querySelector('.slide-number') || {}).textContent || '',
    logicalWidth: deck.offsetWidth,
    logicalHeight: slide.offsetHeight,
    scaleActual,
    scaleExpected,
    centerErrorX,
    centerErrorY,
    svgTextCount: svgTexts.length,
    bodyChars: bodyText.length,
    issues,
  };
}"""

SEVERITY_RANK = {"blocker": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_ZH = {
    "blocker": "阻断",
    "high": "高",
    "medium": "中",
    "low": "低",
}
KIND_ZH = {
    "overflow": "节点溢出画布",
    "clip": "文本横向裁切",
    "svg-label-overlap": "SVG 标签重叠",
    "cjk-percent-spacing": "中文百分号留白",
    "scale-mismatch": "缩放公式不一致",
    "centering": "双轴居中偏差",
    "logical-canvas": "逻辑画布尺寸异常",
    "remote-request": "出现远程请求",
    "page-error": "页面脚本错误",
    "console-error": "控制台错误",
    "slide-id-mismatch": "页标识与锁定清单不符",
    "page-count-mismatch": "页数与锁定清单不符",
    "hash-mismatch": "HTML 哈希与锁定值不符",
}


@dataclass
class PageAudit:
    remote: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)

    def attach(self, page: Page) -> None:
        page.on(
            "request",
            lambda request: self.remote.append(request.url)
            if request.url.startswith(REMOTE_SCHEMES)
            else None,
        )
        page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: self.console_errors.append(message.text)
            if message.type == "error"
            else None,
        )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_viewports(raw: str | None) -> tuple[tuple[str, int, int, str], ...]:
    if not raw:
        return VIEWPORTS
    wanted = {item.strip() for item in raw.split(",") if item.strip()}
    selected = tuple(item for item in VIEWPORTS if item[0] in wanted)
    missing = wanted - {item[0] for item in selected}
    if missing:
        raise ValueError(f"未知视口：{', '.join(sorted(missing))}")
    return selected


def parse_browsers(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return BROWSERS
    wanted = tuple(item.strip() for item in raw.split(",") if item.strip())
    unknown = [item for item in wanted if item not in BROWSERS]
    if unknown:
        raise ValueError(f"未知浏览器：{', '.join(unknown)}")
    return wanted


def bind_decks(root: Path) -> list[dict[str, Any]]:
    bound: list[dict[str, Any]] = []
    for report, spec in LOCKED_DECKS.items():
        path = root / str(spec["path"])
        if not path.is_file():
            raise FileNotFoundError(f"缺少锁定 HTML：{path}")
        digest = sha256_file(path)
        bound.append(
            {
                "report": report,
                "path": path,
                "relpath": spec["path"],
                "expected_sha256": spec["sha256"],
                "actual_sha256": digest,
                "page_count": spec["page_count"],
                "slide_ids": list(spec["slide_ids"]),
                "watch_ids": list(spec["watch_ids"]),
                "hash_ok": digest == spec["sha256"],
            }
        )
    return bound


def issue_record(
    *,
    report: str,
    slide_id: str,
    browser: str,
    viewport: str,
    kind: str,
    severity: str,
    detail: str,
    screenshot: str = "",
) -> dict[str, Any]:
    return {
        "report": report,
        "slide_id": slide_id,
        "browser": browser,
        "viewport": viewport,
        "kind": kind,
        "kind_zh": KIND_ZH.get(kind, kind),
        "severity": severity,
        "severity_zh": SEVERITY_ZH[severity],
        "detail": detail,
        "screenshot": screenshot,
    }


def collect_deck(
    page: Page,
    audit: PageAudit,
    deck: dict[str, Any],
    *,
    browser: str,
    viewport_name: str,
    screenshot_dir: Path,
    settle_ms: int,
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pages: list[dict[str, Any]] = []
    defects: list[dict[str, Any]] = []
    page.goto(deck["path"].as_uri() + "#/1")
    page.locator(".slide.is-active").wait_for()
    href = page.evaluate("location.href")
    if not str(href).startswith("file:"):
        raise RuntimeError(f"{deck['report']} 未以 file:// 打开：{href}")

    expected_ids: list[str] = deck["slide_ids"]
    seen: list[str] = []
    for index, expected_id in enumerate(expected_ids, start=1):
        page.wait_for_function(
            "id => document.querySelector('.slide.is-active')?.dataset.slideId === id",
            arg=expected_id,
        )
        wait_ms = WATCH_SETTLE_MS if expected_id in deck["watch_ids"] else settle_ms
        page.wait_for_timeout(wait_ms)
        diagnostic = page.evaluate(DIAGNOSTIC_JS)
        slide_id = str(diagnostic.get("slideId") or "")
        rel_shot = (
            Path("screenshots")
            / browser
            / viewport_name
            / f"{deck['report'].lower()}-{index:02d}-{slide_id or expected_id}.png"
        )
        shot_path = screenshot_dir / rel_shot.relative_to("screenshots")
        shot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(shot_path), full_page=False, animations="disabled")
        shot_rel = str(shot_path.relative_to(root))
        if slide_id != expected_id:
            defects.append(
                issue_record(
                    report=deck["report"],
                    slide_id=slide_id or expected_id,
                    browser=browser,
                    viewport=viewport_name,
                    kind="slide-id-mismatch",
                    severity="blocker",
                    detail=f"期望 {expected_id}，实际 {slide_id}",
                    screenshot=shot_rel,
                )
            )
        for raw_issue in diagnostic.get("issues") or []:
            kind = str(raw_issue.get("kind") or "unknown")
            severity = str(raw_issue.get("severity") or "low")
            if severity not in SEVERITY_RANK:
                severity = "low"
            detail = " / ".join(
                part
                for part in (
                    str(raw_issue.get("node") or ""),
                    str(raw_issue.get("text") or ""),
                )
                if part
            )
            defects.append(
                issue_record(
                    report=deck["report"],
                    slide_id=slide_id or expected_id,
                    browser=browser,
                    viewport=viewport_name,
                    kind=kind,
                    severity=severity,
                    detail=detail,
                    screenshot=shot_rel,
                )
            )
        pages.append(
            {
                "report": deck["report"],
                "index": index,
                "slide_id": slide_id or expected_id,
                "title": diagnostic.get("title") or "",
                "page_number": diagnostic.get("pageNumber") or "",
                "browser": browser,
                "viewport": viewport_name,
                "screenshot": shot_rel,
                "screenshot_sha256": sha256_file(shot_path),
                "screenshot_bytes": shot_path.stat().st_size,
                "logical_width": diagnostic.get("logicalWidth"),
                "logical_height": diagnostic.get("logicalHeight"),
                "scale_actual": diagnostic.get("scaleActual"),
                "scale_expected": diagnostic.get("scaleExpected"),
                "center_error_x": diagnostic.get("centerErrorX"),
                "center_error_y": diagnostic.get("centerErrorY"),
                "svg_text_count": diagnostic.get("svgTextCount"),
                "body_chars": diagnostic.get("bodyChars"),
                "watch": expected_id in deck["watch_ids"],
                "issue_count": len(diagnostic.get("issues") or []),
            }
        )
        seen.append(slide_id or expected_id)
        if index < len(expected_ids):
            page.keyboard.press("ArrowRight")
            page.locator(".slide.is-active").wait_for()

    if len(seen) != deck["page_count"]:
        defects.append(
            issue_record(
                report=deck["report"],
                slide_id="*",
                browser=browser,
                viewport=viewport_name,
                kind="page-count-mismatch",
                severity="blocker",
                detail=f"期望 {deck['page_count']} 页，实际走过 {len(seen)} 页",
            )
        )
    for url in audit.remote:
        defects.append(
            issue_record(
                report=deck["report"],
                slide_id="*",
                browser=browser,
                viewport=viewport_name,
                kind="remote-request",
                severity="blocker",
                detail=url,
            )
        )
    for message in audit.page_errors:
        defects.append(
            issue_record(
                report=deck["report"],
                slide_id="*",
                browser=browser,
                viewport=viewport_name,
                kind="page-error",
                severity="blocker",
                detail=message,
            )
        )
    for message in audit.console_errors:
        defects.append(
            issue_record(
                report=deck["report"],
                slide_id="*",
                browser=browser,
                viewport=viewport_name,
                kind="console-error",
                severity="high",
                detail=message,
            )
        )
    return pages, defects


def render_markdown(
    *,
    recorded_at: str,
    decks: list[dict[str, Any]],
    browsers: tuple[str, ...],
    viewports: tuple[tuple[str, int, int, str], ...],
    pages: list[dict[str, Any]],
    defects: list[dict[str, Any]],
    screenshot_count: int,
) -> str:
    hash_rows = "\n".join(
        (
            f"| {item['report']} | `{item['relpath']}` | {item['page_count']} |"
            f" `{item['expected_sha256']}` | `{item['actual_sha256']}` |"
            f" {'匹配' if item['hash_ok'] else '**不匹配**'} |"
        )
        for item in decks
    )
    viewport_rows = "\n".join(
        f"| `{name}` | {width}×{height} | {note} |"
        for name, width, height, note in viewports
    )
    unique_defects: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    for item in sorted(defects, key=lambda row: SEVERITY_RANK[row["severity"]]):
        key = (item["report"], item["slide_id"], item["kind"], item["detail"])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_defects.append(item)
    counts = Counter(item["severity_zh"] for item in unique_defects)
    summary = "、".join(
        f"{label} {counts.get(label, 0)}" for label in ("阻断", "高", "中", "低")
    )
    if unique_defects:
        defect_lines = [
            "| 严重度 | 类型 | 报告 | 页 | 详情 | 代表原图 |",
            "|---|---|---|---|---|---|",
        ]
        for item in unique_defects[:200]:
            detail = item["detail"].replace("|", "\\|")
            shot = f"`{item['screenshot']}`" if item["screenshot"] else "—"
            defect_lines.append(
                f"| {item['severity_zh']} | {item['kind_zh']} | {item['report']} |"
                f" `{item['slide_id']}` | {detail} | {shot} |"
            )
        if len(unique_defects) > 200:
            defect_lines.append(
                f"| — | — | — | — | 其余 {len(unique_defects) - 200} 条见 JSON | — |"
            )
        defect_table = "\n".join(defect_lines)
    else:
        defect_table = "本轮自动诊断未发现溢出、裁切、远程请求或缩放合同失败。"

    watch_ids = {
        "a-matrix-2": "A 矩阵第二页标签留白/引线",
        "b-efficacy": "B 疗效页 92.2 与图例间距",
        "c-endpoints": "C 终点页 EASI ≥ 75 % 中文排版",
    }
    watch_rows = []
    for slide_id, note in watch_ids.items():
        hits = [item for item in unique_defects if item["slide_id"] == slide_id]
        shots = [
            item["screenshot"]
            for item in pages
            if item["slide_id"] == slide_id and item["browser"] == "chromium"
        ]
        status = "有自动缺陷" if hits else "自动诊断未报警（仍须人工看原图）"
        shot = f"`{shots[0]}`" if shots else "—"
        watch_rows.append(f"| `{slide_id}` | {note} | {status} | {shot} |")
    page_index_lines = [
        "| 报告 | 序号 | 页标识 | 标题 | Chromium 1920×1080 原图 |",
        "|---|---:|---|---|---|",
    ]
    for item in pages:
        if item["browser"] != "chromium" or item["viewport"] != "1920x1080":
            continue
        title = str(item["title"]).replace("|", "\\|")
        page_index_lines.append(
            f"| {item['report']} | {item['index']} | `{item['slide_id']}` |"
            f" {title} | `{item['screenshot']}` |"
        )
    return "\n".join(
        [
            "# Task 8.6 HTML-PPT 全页多视口原图与诊断台账",
            "",
            f"记录时间：{recorded_at}",
            "收集器：`tools/collect_html_ppt_visual_baseline.py`",
            "状态：**非终验**。本文件是首轮真实渲染证据和自动缺陷基线；",
            "Codex 仍是视觉、医学与监管结论的最终权威。",
            "",
            "## 绑定哈希",
            "",
            "| 报告 | 路径 | 页数 | 锁定 SHA-256 | 实测 SHA-256 | 结果 |",
            "|---|---|---:|---|---|---|",
            hash_rows,
            "",
            "## 采集矩阵",
            "",
            f"- 浏览器：{', '.join(browsers)}",
            (
                f"- 截图张数：{screenshot_count}"
                f"（62 页 × {len(viewports)} 视口 × {len(browsers)} 浏览器）"
            ),
            "- 协议：`file://`；设备像素比 1；视口原图（非整页文档滚动、非元素裁切）",
            "- 入场动效：截图时 `animations=disabled`，翻页后等待稳定再拍",
            "",
            "| 视口 | CSS 像素 | 用途 |",
            "|---|---|---|",
            viewport_rows,
            "",
            "## 自动缺陷汇总",
            "",
            f"去重视图（跨浏览器/视口合并同类）：{summary}。完整逐次命中见 JSON。",
            "",
            defect_table,
            "",
            "## 首轮重点页",
            "",
            "| 页标识 | 移交问题 | 自动诊断 | 代表原图 |",
            "|---|---|---|---|",
            *watch_rows,
            "",
            "## 62 页索引（Chromium 1920×1080）",
            "",
            *page_index_lines,
            "",
            "## 复跑",
            "",
            "```text",
            "uv run python tools/collect_html_ppt_visual_baseline.py",
            "```",
            "",
            "哈希不匹配时收集器以退出码 2 失败关闭，不生成误绑原图。",
            "",
        ]
    )


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="采集 HTML-PPT 全页多视口原图与中文诊断台账"
    )
    parser.add_argument("--root", default=str(REPO_ROOT), help="仓库根目录")
    parser.add_argument(
        "--output-dir",
        default="docs/acceptance/runs/8.6/visual-baseline",
        help="台账与截图输出目录（相对 --root）",
    )
    parser.add_argument("--browsers", default="chromium,webkit")
    parser.add_argument(
        "--viewports", default="1280x800,1920x1080,2048x1024,1280x720"
    )
    parser.add_argument("--settle-ms", type=int, default=DEFAULT_SETTLE_MS)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output_dir = (root / args.output_dir).resolve()
    screenshot_dir = output_dir / "screenshots"
    try:
        browsers = parse_browsers(args.browsers)
        viewports = parse_viewports(args.viewports)
        decks = bind_decks(root)
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return EXIT_USAGE
    except ValueError as error:
        print(error, file=sys.stderr)
        return EXIT_USAGE

    hash_defects = [
        issue_record(
            report=item["report"],
            slide_id="*",
            browser="*",
            viewport="*",
            kind="hash-mismatch",
            severity="blocker",
            detail=f"期望 {item['expected_sha256']}，实际 {item['actual_sha256']}",
        )
        for item in decks
        if not item["hash_ok"]
    ]
    if hash_defects:
        output_dir.mkdir(parents=True, exist_ok=True)
        fail_path = output_dir / "hash-mismatch.json"
        fail_path.write_text(
            json.dumps(hash_defects, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"HTML 哈希与 Task 8.6 锁定值不符，已写入 {fail_path}", file=sys.stderr)
        return EXIT_USAGE

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    pages: list[dict[str, Any]] = []
    defects: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        for browser_name in browsers:
            browser_type: BrowserType = getattr(playwright, browser_name)
            browser = browser_type.launch()
            try:
                for viewport_name, width, height, _note in viewports:
                    for deck in decks:
                        page = browser.new_page(
                            viewport={"width": width, "height": height},
                            device_scale_factor=1,
                        )
                        audit = PageAudit()
                        audit.attach(page)
                        try:
                            deck_pages, deck_defects = collect_deck(
                                page,
                                audit,
                                deck,
                                browser=browser_name,
                                viewport_name=viewport_name,
                                screenshot_dir=screenshot_dir,
                                settle_ms=args.settle_ms,
                                root=root,
                            )
                            pages.extend(deck_pages)
                            defects.extend(deck_defects)
                        finally:
                            page.close()
            finally:
                browser.close()

    recorded_at = datetime.now(UTC).isoformat()
    ledger = {
        "task": "8.6",
        "collector": "tools/collect_html_ppt_visual_baseline.py",
        "not_acceptance": True,
        "recorded_at": recorded_at,
        "worker": "worker_01",
        "locked_medical_data_unchanged": True,
        "browsers": list(browsers),
        "viewports": [
            {"name": name, "width": width, "height": height, "note": note}
            for name, width, height, note in viewports
        ],
        "decks": [
            {
                "report": item["report"],
                "path": item["relpath"],
                "sha256": item["actual_sha256"],
                "page_count": item["page_count"],
                "slide_ids": item["slide_ids"],
            }
            for item in decks
        ],
        "screenshot_count": len(pages),
        "pages": pages,
        "defects": defects,
        "defect_count": len(defects),
    }
    json_path = output_dir / "visual-baseline-ledger.json"
    md_path = output_dir / "visual-baseline-ledger.md"
    json_path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(
        render_markdown(
            recorded_at=recorded_at,
            decks=decks,
            browsers=browsers,
            viewports=viewports,
            pages=pages,
            defects=defects,
            screenshot_count=len(pages),
        ),
        encoding="utf-8",
    )
    unique_count = len(
        {
            (item["report"], item["slide_id"], item["kind"], item["detail"])
            for item in defects
        }
    )
    print(json_path)
    print(md_path)
    print(f"screenshots={len(pages)} defect_hits={len(defects)} unique={unique_count}")
    return EXIT_FAIL if defects else EXIT_OK


if __name__ == "__main__":
    sys.exit(run())
