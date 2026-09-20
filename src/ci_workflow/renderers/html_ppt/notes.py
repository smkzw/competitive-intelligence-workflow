"""Speaker-note length gates and audience-copy sanitizers."""

from __future__ import annotations

import re

HAN_RE = re.compile(r"[\u4e00-\u9fff]")
TAG_RE = re.compile(r"<[^>]+>")
NOTES_PADDING = (
    "请对着屏幕上的数字讲",
    "不要改口成系统流程或内部日志",
    "系统流程",
    "内部日志",
    "证据门槛",
    "系统故障",
    "系统来源",
)
FORBIDDEN = (
    "schema_version",
    "gate_status",
    "route_attempts",
    "snapshot-",
    "v-fixture",
    "reported_value",
    "not_publicly_disclosed",
    "higher_is_better",
    "workflow",
    "prompt",
    "playwright",
    "chromium",
    "RENDERER_",
    "traceback",
    "TODO",
    "fixture run",
    "scientific_review",
    "content_text",
)


def han_count(text: str) -> int:
    return len(HAN_RE.findall(text))


def strip_tags(html: str) -> str:
    return TAG_RE.sub("", html)


def validate_notes_html(html: str, *, slide_id: str) -> str:
    if "<strong>" not in html.lower():
        raise ValueError(f"{slide_id} 逐字稿缺少 strong 提示")
    n = han_count(strip_tags(html))
    if not 150 <= n <= 300:
        raise ValueError(f"{slide_id} 逐字稿汉字数为 {n}，要求 150–300")
    lowered = html.lower()
    for token in FORBIDDEN:
        if token.lower() in lowered:
            raise ValueError(f"{slide_id} 逐字稿含禁用词 {token}")
    for token in NOTES_PADDING:
        if token.lower() in lowered:
            raise ValueError(f"{slide_id} 逐字稿含套话或工程用语 {token}")
    plain = strip_tags(html)
    if re.search(r"(.{16,})\1", plain):
        raise ValueError(f"{slide_id} 逐字稿重复套句")
    return html


def audience_is_clean(text: str, *, slide_id: str) -> None:
    if han_count(text) < 1:
        raise ValueError(f"{slide_id} 观众页缺少汉字")
    lowered = text.lower()
    for token in FORBIDDEN:
        if token.lower() in lowered:
            raise ValueError(f"{slide_id} 观众页含禁用词 {token}")
