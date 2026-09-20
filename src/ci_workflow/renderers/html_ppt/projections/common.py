"""Shared HTML-PPT projection helpers for A/B/C decks."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from ci_workflow.renderers.html_ppt.assemble import assemble_deck, write_deck
from ci_workflow.renderers.html_ppt.assets import REPO_ROOT, load_inline_assets, load_locked_json
from ci_workflow.renderers.html_ppt.components import Slide
from ci_workflow.renderers.html_ppt.notes import han_count, strip_tags, validate_notes_html
from ci_workflow.renderers.html_ppt.projections.speaker_notes import SPEAKER

DISCLOSURE_ZH = {
    "reported_value": "已公开",
    "not_publicly_disclosed": "未公开",
    "reported_zero": "已公开为零",
    "not_applicable": "不适用",
    "comparable": "可比较",
}
FAMILY_ZH = {
    "teae": "治疗期间不良事件",
    "sae": "严重不良事件",
    "aesi": "特别关注不良事件",
    "common_ae": "常见不良事件",
}
ARM_ZH = {"treatment": "治疗组", "control": "对照组"}
_NOTES_DATE = ""
NOTES_ENGINEERING = (
    "请对着屏幕上的数字讲",
    "系统流程",
    "内部日志",
    "证据门槛",
    "系统故障",
    "系统来源",
    "fixture",
    "prompt",
    "workflow",
    "playwright",
    "gate_status",
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def cutoff_zh(raw: object) -> str:
    text = str(raw or "")
    match = re.match(r"(\d{4})-(\d{2})", text)
    if not match:
        raise ValueError("缺少可解析的资料截止年月")
    return f"{match.group(1)}年{int(match.group(2))}月"


def set_notes_date(date_zh: str) -> None:
    global _NOTES_DATE
    _NOTES_DATE = date_zh


def notes(slide_id: str, body: str = "", **kwargs: object) -> str:
    if slide_id not in SPEAKER:
        raise ValueError(f"{slide_id} 缺少页内逐字稿，禁止用套话补足")
    date_zh = str(kwargs.get("date_zh") or _NOTES_DATE or "页眉所示月份")
    text = SPEAKER[slide_id].format(date_zh=date_zh)
    lowered = text.lower()
    for token in NOTES_ENGINEERING:
        if token.lower() in lowered:
            raise ValueError(f"{slide_id} 逐字稿含工程套话 {token}")
    html_out = f"<p>{text}</p>"
    return validate_notes_html(html_out, slide_id=slide_id)


def stat(num: object, label: str) -> str:
    return (
        '<div class="stat-strip__item">'
        f'<div class="stat-strip__num">{esc(num)}</div>'
        f'<div class="stat-strip__label">{esc(label)}</div></div>'
    )


def disclosure_rows(rows: list[tuple[str, str, str]]) -> str:
    dense = " disclosure-list--dense" if len(rows) >= 8 else ""
    parts = [f'<div class="disclosure-list{dense}">']
    for left, mid, state in rows:
        parts.append(
            '<div class="disclosure-row">'
            f"<span>{esc(left)}</span>"
            f"<span>{esc(mid)}</span>"
            f'<span class="state">{esc(state)}</span></div>'
        )
    parts.append("</div>")
    return "".join(parts)


def write_report_deck(
    *,
    report: str,
    slides: list[Slide],
    title: str,
    date_zh: str,
    digest: str,
    output_path: Path,
    root: Path | None = None,
) -> Path:
    base = root or REPO_ROOT
    assets = load_inline_assets(root=base)
    html_text = assemble_deck(
        slides,
        title=title,
        footer_id=f"产品中心-医学部｜{date_zh}",
        assets=assets,
        extra_meta={
            "report": report,
            "input_sha256": digest,
            "slide_ids": ",".join(slide.slide_id for slide in slides),
        },
    )
    path = write_deck(Path(output_path), html_text)
    manifest = {
        "report": report,
        "output": path.name,
        "input_sha256": digest,
        "assets": assets.hashes,
        "slide_ids": [slide.slide_id for slide in slides],
        "notes_han": {
            slide.slide_id: han_count(strip_tags(slide.notes_html)) for slide in slides
        },
    }
    path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def load_report(report: str, *, root: Path | None = None) -> tuple[dict[str, Any], str]:
    return load_locked_json(report, root=root)
