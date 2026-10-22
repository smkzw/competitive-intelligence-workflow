"""确定性原文核验：替代 v1 的「独立模型签发」作为关键字段的信任根。

规则：
1. quote 规范化后必须是来源全文规范化文本的子串（空白、全半角、引号、连字符统一）。
2. 数值类事实：value 的数字必须出现在 quote 中（防止“片段对、数字编”）。
3. 返回原文中的起止偏移（基于规范化文本），平台可高亮定位。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_TRANS = str.maketrans({
    "“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "−": "-",
    "≥": ">=", "≤": "<=", "\u00a0": " ",
})


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_TRANS)
    text = re.sub(r"<[^>]+>", " ", text)  # 去掉 HTML 标签
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass(frozen=True)
class QuoteCheck:
    ok: bool
    start: int | None
    end: int | None
    reason: str = ""


def _numbers(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        v = float(value)
        return [str(int(v))] if v.is_integer() else [repr(v).rstrip("0").rstrip(".")]
    if isinstance(value, dict):
        out: list[str] = []
        for v in value.values():
            out += _numbers(v)
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            out += _numbers(v)
        return out
    return re.findall(r"-?\d+(?:\.\d+)?", str(value))


def _number_in(num: str, text: str) -> bool:
    pattern = r"(?<![\d.])" + re.escape(num.lstrip("-")) + r"(?:\.0+)?(?![\d])"
    return re.search(pattern, text) is not None


def check_quote(source_text: str, quote: str | None, value: object = None) -> QuoteCheck:
    if not quote or not quote.strip():
        return QuoteCheck(False, None, None, "缺少原文片段")
    src = normalize(source_text)
    q = normalize(quote)
    if len(q) < 4:
        return QuoteCheck(False, None, None, "原文片段过短")
    idx = src.find(q)
    if idx < 0:
        return QuoteCheck(False, None, None, "原文中找不到该片段")
    missing = [n for n in _numbers(value) if not _number_in(n, q)]
    if missing:
        return QuoteCheck(False, idx, idx + len(q), f"数值未出现在片段中：{', '.join(missing)}")
    return QuoteCheck(True, idx, idx + len(q))
