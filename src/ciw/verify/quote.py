"""确定性原文核验。移植自 archive/ciw2:rebaseline-v2/src/ciw2/verify/quote.py（逻辑不变）。

规则：引语规范化后必须是来源全文的子串；数值必须字面出现在引语中；返回规范化文本中的偏移。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_TRANS = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "−": "-",
        "≥": ">=",
        "≤": "<=",
        "\u00a0": " ",
    }
)
_NUMERIC_TOKEN = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+|\.\d+)(?:\.\d+)?(?:e[-+]?\d+)?"
_NUMBER = rf"(?<![A-Za-zα-ωΑ-Ω0-9_.+-]){_NUMERIC_TOKEN}(?!\d|\.\d)"
_UNIT_PARTS = frozenset(
    unicodedata.normalize("NFKC", part).lower()
    for part in (
        "mg",
        "g",
        "kg",
        "µg",
        "ug",
        "mcg",
        "ng",
        "pg",
        "ml",
        "l",
        "dl",
        "ul",
        "µl",
        "mol",
        "mmol",
        "umol",
        "µmol",
        "nmol",
        "pmol",
        "m",
        "cm",
        "mm",
        "m2",
        "cm2",
        "m^2",
        "cm^2",
        "mmhg",
        "bpm",
        "hz",
        "ms",
        "s",
        "min",
        "h",
        "hr",
        "day",
        "days",
        "week",
        "weeks",
        "year",
        "years",
        "u",
        "iu",
        "uln",
        "point",
        "points",
        "score",
    )
)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_TRANS)
    text = "".join("-" if unicodedata.category(char) == "Pd" or char == "\u00ad" else char for char in text)
    # Inputs are source plaintext (HTML is extracted at ingestion). Inequalities
    # and literal markup are evidence, not HTML tags to delete a second time.
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass(frozen=True)
class QuoteCheck:
    ok: bool
    start: int | None
    end: int | None
    reason: str = ""


def _numbers(value: object, quote: str | None = None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [str(value)]  # Preserve integer precision and exponent digits verbatim.
    if (
        isinstance(value, str)
        and quote is not None
        and re.search(r"(?<![\w/+-])" + re.escape(normalize(value)) + r"(?![\w/+-])", quote)
    ):
        # The complete literal text proves its embedded identifiers; do not
        # discard numbers from unmatched prose merely because a suffix is unknown.
        return []
    if _identifier(value):
        return []
    if isinstance(value, dict):
        out: list[str] = []
        for v in value.values():
            out += _numbers(v, quote)
        return out
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            out += _numbers(v, quote)
        return out
    return re.findall(_NUMERIC_TOKEN, normalize(str(value)))


def _identifier(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = normalize(value)
    return (
        re.fullmatch(r"[\w/-]+", text) is not None
        and any(c.isalpha() for c in text)
        and any(c.isdigit() for c in text)
        and re.fullmatch(_NUMERIC_TOKEN, text) is None
    )


def _missing_labels(value: object, quote: str) -> bool:
    if isinstance(value, dict):
        return any(_missing_labels(item, quote) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_missing_labels(item, quote) for item in value)
    return (
        _identifier(value)
        and re.search(r"(?<![A-Za-z0-9_α-ωΑ-Ω/-])" + re.escape(normalize(value)) + r"(?![A-Za-z0-9_α-ωΑ-Ω/-])", quote)
        is None
    )


def _number_in(num: str, text: str, *, exact_scalar: bool = False) -> bool:
    try:
        target = Decimal(num.replace(",", ""))
    except InvalidOperation:
        return False
    if not target.is_finite():
        return False
    if any(
        Decimal(match[0].replace(",", "")) == target
        and _numeric_suffix(text, match.end())
        and (not exact_scalar or not re.search(r"[<>]=?\s*$", text[: match.start()]))
        for match in re.finditer(_NUMBER, text)
    ):
        return True
    # An unsigned upper endpoint is not a negative number or a digit inside 4-1BB.
    ranges = re.finditer(r"(?<![\w.+/-])\d+(?:\.\d+)?\s*-\s*(?P<upper>\d+(?:\.\d+)?)(?![\d.-])", text)
    return any(
        Decimal(match["upper"]) == target
        and _numeric_suffix(text, match.end())
        and (not exact_scalar or not re.search(r"[<>]=?\s*$", text[: match.start()]))
        for match in ranges
    )


def _numeric_suffix(text: str, end: int) -> bool:
    joined = re.match(r"[-_/]\d+(?:\.\d+)?([a-zµα-ω][a-z0-9µα-ω/^]*|[-_/][\w/-]+)", text[end:])
    if joined:
        return all(part in _UNIT_PARTS for part in joined[1].split("/"))
    tail = re.match(r"[a-zµα-ω][a-z0-9µα-ω/^]*|[-_/][a-zα-ω][a-z0-9α-ω_-]*", text[end:])
    if tail is None:
        return True
    # Numeric quantities may touch units; 2F8/5-HT2A are complete identifiers, not counts.
    return all(part in _UNIT_PARTS for part in tail[0].split("/"))


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
    if _missing_labels(value, q):
        return QuoteCheck(False, idx, idx + len(q), "原文片段缺少完整科学标识")
    exact_scalar = (
        (isinstance(value, (int, float)) and not isinstance(value, bool))
        or isinstance(value, str)
        and re.fullmatch(_NUMERIC_TOKEN, normalize(value)) is not None
    )
    numbers = [str(value)] if exact_scalar else _numbers(value, q)
    missing = [n for n in numbers if not _number_in(n, q, exact_scalar=exact_scalar)]
    if missing:
        sample = ", ".join(n[:80] for n in missing[:5])
        extra = f"（另{len(missing) - 5}项）" if len(missing) > 5 else ""
        reason = (
            "原文比较符未保留，不能支持确定数值"
            if exact_scalar and any(_number_in(n, q) for n in missing)
            else "数值未出现在片段中"
        )
        return QuoteCheck(False, idx, idx + len(q), f"{reason}：{sample}{extra}")
    return QuoteCheck(True, idx, idx + len(q))
