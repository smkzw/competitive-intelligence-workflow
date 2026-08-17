"""A 类报告独立验收中对旧版失败样本的确定性判定。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReportAAcceptanceIssue:
    code: str
    message_zh: str


def _balanced_parentheses(text: str) -> bool:
    depth = 0
    quote: str | None = None
    escaped = False
    for character in text:
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if quote is not None:
            if character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and quote is None


def inspect_legacy_report_a_sample(sample_root: Path) -> tuple[ReportAAcceptanceIssue, ...]:
    """读取最小脱敏样本；任一历史假阳性特征都必须明确否决。"""
    metadata = json.loads((sample_root / "sample.json").read_text(encoding="utf-8"))
    issues: list[ReportAAcceptanceIssue] = []
    sample_kind = metadata["sample_kind"]
    payload_path = sample_root / metadata["payload_file"]

    if sample_kind == "five_products_zero_trials":
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        counts = payload.get("entity_counts", {})
        if int(counts.get("drugs", 0)) > 0 and int(counts.get("trials", 0)) == 0:
            issues.append(
                ReportAAcceptanceIssue(
                    "products_without_trials",
                    "已有竞品却没有任何临床试验，不能生成 A 类报告。",
                )
            )
    elif sample_kind == "malformed_stylesheet":
        stylesheet = payload_path.read_text(encoding="utf-8")
        if not _balanced_parentheses(stylesheet):
            issues.append(
                ReportAAcceptanceIssue(
                    "malformed_stylesheet",
                    "页面样式括号不闭合，站点视觉验收不能通过。",
                )
            )
    elif sample_kind == "zero_card_false_green":
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        zero_card_passes = [
            item
            for item in payload.get("results", [])
            if item.get("status") == "pass" and "0 张卡" in str(item.get("detail", ""))
        ]
        if zero_card_passes:
            issues.append(
                ReportAAcceptanceIssue(
                    "zero_card_false_green",
                    "零张证据卡不能通过来源、快照、结构或追溯检查。",
                )
            )
    elif sample_kind == "unanchored_ad_shell":
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        if payload.get("verdict") != "PASS" or any(
            item.get("status") == "fail" for item in payload.get("results", [])
        ):
            issues.append(
                ReportAAcceptanceIssue(
                    "unanchored_report_shell",
                    "页面数量或卡片数量不能替代关键事实锚定，旧版特应性皮炎报告不能交付。",
                )
            )
    else:
        issues.append(
            ReportAAcceptanceIssue(
                "unknown_negative_sample",
                "负例类型未登记，验收失败关闭。",
            )
        )
    return tuple(issues)
