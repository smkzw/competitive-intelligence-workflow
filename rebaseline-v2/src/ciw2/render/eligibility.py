"""Source-span eligibility reading projection.

Only explicit named-scale/laboratory comparisons and score choices are recognised. The
projection never decides eligibility, never rewrites the source, and never
supplies a missing threshold or unit.  Unrecognised language is returned
unchanged as plain text.  Callers must HTML-escape every returned string; this
module never emits markup and never escapes source text itself.

Documented limits: this is a phrase reader, not a clinical parser.  It handles
the common ``EASI/IGA/SCORAD/BSA/PP-NRS/WI-NRS/NRS`` scale forms and explicit
``ALT/AST/eGFR/platelets/neutrophils/hemoglobin`` laboratory inequalities,
including ``x ULN`` units, percentage units and adjacent ``ALT or AST``
conditions, parenthesized lab pairs, explicit Chinese ULN, discrete score choices
and immediately joined bounds. ``one_of`` keeps a list of literal scores, not
a continuous range. Joined bounds inherit the explicitly adjacent metric, not
an omitted unit; they never cross a clause, line or another named measure.
Timing, visit, negation and other qualifiers stay in ``rule_text``;
they are never turned into additional rules.  ``label`` is only the explicit
comparison, so callers that show it should keep ``rule_text`` visible for those
qualifiers.  List markers are trimmed from ``rule_text`` only; the ``segments``
side keeps every source character.  Free text, doses, dates and unknown
measures remain ordinary segments.  ``source_start``/``source_end`` delimit
``quote`` in the original string, and emphasis roles are exactly ``None``,
``threshold``, ``logic``, ``negation`` and ``heading``.
"""
from __future__ import annotations

import re
from itertools import pairwise
from typing import Any

_HEADING = "heading"
_THRESHOLD = "threshold"
_LOGIC = "logic"
_NEGATION = "negation"

_SCORE = r"EASI|vIGA|IGA|SCORAD|BSA|PP[-\s]?NRS|WI[-\s]?NRS|NRS"
_LAB = r"ALT|AST|SCr|eGFR|platelets?|neutrophils?|h[ae]moglobin"
_LAB_WORD = _LAB
_METRIC = rf"(?:{_SCORE}|{_LAB})(?![A-Za-z0-9])"

_METRIC_PHRASE = (
    r"[\(\uff08]?"
    rf"(?P<measure>{_METRIC})"
    r"(?![-\u2010-\u2015]\s*\d)"
    r"\s*[\)\uff09]?"
    r"(?:\s*(?:score|count|level|levels|\u8bc4\u5206|\u8ba1\u6570))?"
)
_NUMBER = r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"

_SYMBOL = r"(?:\\?>=|\\?<=|\\?>|\\?<|\\?=|\u2265|\u2264|\uff1e|\uff1c|\u2267|\u2266)"
_WORD = (
    r"(?:greater\s+than\s+or\s+equal\s+to|greater\s+than\s+and\s+equal\s+to|"
    r"less\s+than\s+or\s+equal\s+to|no\s+less\s+than|not\s+less\s+than|"
    r"no\s+greater\s+than|not\s+more\s+than|at\s+least|at\s+most|"
    r"more\s+than|less\s+than|greater\s+than|above|below|"
    r"\u5927\u4e8e\u7b49\u4e8e|\u5c0f\u4e8e\u7b49\u4e8e|\u4e0d\u4f4e\u4e8e|\u4e0d\u9ad8\u4e8e|"
    r"\u4e0d\u5c11\u4e8e|\u4e0d\u8d85\u8fc7|\u81f3\u5c11|\u81f3\u591a|\u5927\u4e8e|\u5c0f\u4e8e)"
)
_CMP = rf"(?:{_SYMBOL}|{_WORD})"

_UNIT = (
    r"(?:%|percent(?:\s*\(%\))?|"
    r"(?:\u00d7|x|times|\u500d)\s*(?:the\s+)?(?:ULN|upper\s+limit\s+of\s+normal|正常(?:值|范围)?上限)(?:\s*\(ULN\))?|"
    r"(?:the\s+)?(?:ULN|upper\s+limit\s+of\s+normal)(?:\s*\(ULN\))?|"
    r"[\u00d7x]?\s*10\s*\^?\s*9\s*/\s*[Ll]|"
    r"(?:mg|g|\u00b5g|ng|mmol|\u00b5mol|umol|U|mEq)\s*/\s*(?:dL|dl|L|mL)|"
    r"mL\s*/\s*min(?:\s*/\s*1\.73\s*m(?:\^?2|\u00b2))?|"
    r"/\s*(?:\u00b5L|\u03bcL|uL|mcL|mcl|mm\^?3|mm\u00b3)|"
    r"U\s*/\s*L)"
)
_SUFFIX = rf"\s*(?:of\s+)?(?P<cmp>{_CMP})\s*(?P<num>{_NUMBER})(?:\s*(?P<unit>{_UNIT}))?"

_PREFIX = re.compile(r"(?<![A-Za-z-])" + _METRIC_PHRASE + _SUFFIX, re.IGNORECASE)
_AVERAGE = r'(?P<average>weekly[ \t]+(?:mean|average)|(?:的)?(?:周平均(?:值|分)|平均(?:值|评分|分))|mean|average)'
_AVERAGE_MEASURE = rf'(?P<measure>(?:{_SCORE})(?![A-Za-z0-9-]))[ \t]*(?:scores?|评分)?'
_AVERAGES = [re.compile(r'(?<![A-Za-z-])'+pattern+_SUFFIX,re.IGNORECASE) for pattern in (
    _AVERAGE_MEASURE+r'[ \t]*'+_AVERAGE,
    _AVERAGE+r'[ \t]+'+_AVERAGE_MEASURE)]
_LAB_ONE = rf"(?:{_LAB_WORD})(?![A-Za-z0-9])"
_COMPOUND = re.compile(
    r"(?<![A-Za-z-])(?:[（(][ \t]*)?(?P<measure>"
    + _LAB_ONE
    + rf"(?:\s*/\s*{_LAB_ONE}|\s*,\s*{_LAB_ONE}"
      rf"|\s+(?:or|and)\s*{_LAB_ONE}|\s*(?:\u6216|\u548c|\u4ee5\u53ca)\s*{_LAB_ONE})+)(?:[ \t]*[）)])?"
    + _SUFFIX,
    re.IGNORECASE,
)
_DISCRETE = re.compile(
    rf'(?<![A-Za-z-])(?P<measure>{_SCORE})(?![A-Za-z0-9-])'
    rf'[ \t]*(?:评分|score)?[ \t]*(?:为|等于|is|=)[ \t]*'
    rf'(?P<choices>{_NUMBER}(?:[ \t]*(?:或|or)[ \t]*{_NUMBER})+)(?:[ \t]*分)?'
    r'(?!\.\d)(?=$|[，,；;。.\r\n)）]|且|并且)',re.IGNORECASE)
_CONTINUATION = re.compile(
    rf'(?P<link>[ \t]*(?:并且|且|或|and/or|and|or)[ \t]*)'
    rf'(?P<cmp>{_CMP})[ \t]*(?P<num>{_NUMBER})(?:[ \t]*(?P<unit>{_UNIT}))?',re.IGNORECASE)
_BSA_REVERSE = re.compile(
    rf"(?P<cmp>{_CMP})\s*(?P<num>{_NUMBER})\s*(?P<unit>percent(?:\s*\(%\))?|%)"
    r"\s*(?:of\s+|in\s+)?(?:the\s+)?(?:body\s+surface\s+area(?:\s*\(BSA\))?|BSA)(?![A-Za-z0-9])",
    re.IGNORECASE,
)

_HEADING_EN = re.compile(
    r"^[ \t]*(?:\d+[.)]\s*)?"
    r"(?P<label>(?:(?:key|main|general|other)\s+)?(?:inclusion|exclusion)\s+criteria"
    r"(?:\s+for\s+[^:\r\n]+)?)"
    r"(?P<colon>\s*[:\uff1a])?",
    re.IGNORECASE,
)
_HEADING_ZH = re.compile(
    r"^[ \t]*(?:\d+[.)]\s*)?"
    r"(?P<label>\u5165\u9009\u6807\u51c6|\u7eb3\u5165\u6807\u51c6|\u5165\u7ec4\u6807\u51c6|"
    r"\u6392\u9664\u6807\u51c6|\u5254\u9664\u6807\u51c6)"
    r"(?P<colon>\s*[:\uff1a])?"
)
_BULLET = re.compile(r"^[ \t]*(?:[-\u2022\u00b7\u2013*]|\d+[.)])\s+")
_LOGIC_RE = re.compile(r"\b(?:and/or|and|or|but)\b|\u4ee5\u53ca|\u548c|\u6216|\u4e14", re.IGNORECASE)
_NEGATION_RE = re.compile(
    r"\b(?:no|not|without|unless|except|excluding|excluded|failure|failed|unable|free\s+of|negative\s+for)\b|"
    r"\u672a|\u65e0|\u975e|\u4e0d\u5f97|\u4e0d\u80fd|\u7981\u7528|\u9664\u5916|\u6392\u9664",
    re.IGNORECASE,
)

_MEASURE_NAMES = {
    "easi": "EASI", "iga": "IGA", "viga": "vIGA", "scorad": "SCORAD", "bsa": "BSA",
    "ppnrs": "PP-NRS", "winrs": "WI-NRS", "nrs": "NRS",
    "alt": "ALT", "ast": "AST", "scr": "SCr", "egfr": "eGFR",
    "platelet": "platelets", "platelets": "platelets",
    "neutrophil": "neutrophils", "neutrophils": "neutrophils",
    "hemoglobin": "hemoglobin", "haemoglobin": "hemoglobin",
}
_SCORE_NAMES = {"EASI", "IGA", "vIGA", "SCORAD", "BSA", "PP-NRS", "WI-NRS", "NRS"}
_LABEL_NAMES = {"platelets": "\u8840\u5c0f\u677f", "neutrophils": "\u4e2d\u6027\u7c92\u7ec6\u80de",
                "hemoglobin": "\u8840\u7ea2\u86cb\u767d"}
_OPERATOR_SYMBOL = {">=": "\u2265", "<=": "\u2264", ">": ">", "<": "<", "=": "="}
_PRIORITY = {_HEADING: 4, _THRESHOLD: 3, _LOGIC: 2, _NEGATION: 2}


def eligibility_reading(text: str) -> dict[str, Any]:
    """Return source-verbatim ``rules`` and lossless emphasis ``segments``."""
    if not isinstance(text, str):
        raise TypeError("eligibility text must be a string")
    headings = _headings(text)
    rules: list[dict[str, Any]] = []
    spans = [(heading["start"], heading["end"], _HEADING) for heading in headings]
    for rule in _ordered(_candidates(text)):
        rule["section"] = _section_at(rule["source_start"], headings)
        rule["section_title"] = next((h['title'] for h in reversed(headings)
                                      if h['end'] <= rule['source_start']), '')
        rule['clause_start'] = text.rfind('\n', 0, rule['source_start']) + 1
        rule["rule_text"] = _rule_text(text, rule["source_start"], headings)
        gaps = rule.pop("_logic", [])
        spans.extend(_rule_spans(rule, gaps))
        rules.append(rule)
    spans.extend(_role_spans(text, _LOGIC, _LOGIC_RE))
    spans.extend(_role_spans(text, _NEGATION, _NEGATION_RE))
    return {"rules": rules, "segments": _segments(text, spans)}


def _candidates(text: str) -> list[dict[str, Any]]:
    found = []
    for pattern in _AVERAGES:
        for match in pattern.finditer(text):
            measure=_canonical(match['measure'])
            found.append(_average(_rule(text,match,measure,'score',measure),match['average']))
    for match in _COMPOUND.finditer(text):
        rule = _rule(text, match, *_compound(match.group("measure")))
        rule["_logic"] = _connector_spans(match)
        found.append(rule)
    for match in _PREFIX.finditer(text):
        measure = _canonical(match.group("measure"))
        found.append(_rule(text, match, measure, _kind(measure), measure))
    for match in _BSA_REVERSE.finditer(text):
        found.append(_rule(text, match, "BSA", "score", "BSA"))
    for rule in list(found):
        end=rule['source_end']
        while match:=_CONTINUATION.match(text,end):
            tail=_rule(text,match,rule['measure'],rule['kind'],rule['measure'])
            if rule.get('aggregation_text'):tail=_average(tail,rule['aggregation_text'])
            tail['_logic']=[(match.start('link'),match.end('link'),_LOGIC)]
            found.append(tail)
            end=match.end()
    for match in _DISCRETE.finditer(text):
        measure=_canonical(match['measure'])
        numbers=re.findall(_NUMBER,match['choices'])
        found.append({'kind':'score','measure':measure,'operator':'one_of',
            'value':[float(n.replace(',','')) for n in numbers],'unit':None,
            'source_start':match.start(),'source_end':match.end(),'quote':match.group(),
            'label':f'{_display(measure)} 评分 = '+ ' 或 '.join(numbers),
            '_logic':[(m.start()+match.start('choices'),m.end()+match.start('choices'),_LOGIC)
                      for m in re.finditer(r'或|or',match['choices'],re.IGNORECASE)]})
    return found


def _average(rule: dict[str,Any],raw: str) -> dict[str,Any]:
    weekly=re.search(r'weekly|周',raw,re.IGNORECASE) is not None
    head=_display(rule['measure'])+(' 评分' if rule['measure']!='BSA' else '')
    rule['label']=rule['label'].replace(head,head+('（周平均）' if weekly else '（平均）'),1)
    rule.update(aggregation='weekly_mean' if weekly else 'mean',aggregation_text=raw)
    return rule


def _connector_spans(match: re.Match[str]) -> list[tuple[int, int, str]]:
    base = match.start("measure")
    return [(base + found.start(), base + found.end(), _LOGIC)
            for found in re.finditer(r"\b(?:or|and)\b|\u6216|\u548c|\u4ee5\u53ca|/", match.group("measure"),
                                      re.IGNORECASE)]


def _rule_spans(rule: dict[str, Any], gaps: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    cursor = rule["source_start"]
    for start, end, _ in gaps:
        if start > cursor:
            spans.append((cursor, start, _THRESHOLD))
        spans.append((start, end, _LOGIC))
        cursor = end
    if cursor < rule["source_end"]:
        spans.append((cursor, rule["source_end"], _THRESHOLD))
    return spans


def _rule(text: str, match: re.Match[str], measure: str, kind: str, label_measure: str) -> dict[str, Any]:
    operator = _operator(match.group("cmp"))
    unit = _unit(match.group("unit"))
    number = match.group("num")
    return {
        "kind": kind, "measure": measure, "operator": operator, "value": float(number.replace(",", "")),
        "unit": unit, "source_start": match.start(), "source_end": match.end(),
        "quote": text[match.start():match.end()],
        "label": _label(label_measure, kind, operator, number, unit),
    }


def _ordered(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates.sort(key=lambda rule: (rule["source_start"], -rule["source_end"]))
    kept: list[dict[str, Any]] = []
    last_end = -1
    for rule in candidates:
        if rule["source_start"] >= last_end:
            kept.append(rule)
            last_end = rule["source_end"]
    return kept


def _compound(raw: str) -> tuple[str, str, str]:
    # Normalise each connector independently; '/' is not evidence of OR.
    matches = list(re.finditer(_LAB_WORD, raw, re.IGNORECASE))
    names, labels = [], []
    end = 0
    for match in matches:
        connector = raw[end:match.start()].strip().casefold()
        if names:
            connectors = {'and': (' and ', ' 且 '), '和': (' and ', ' 且 '),
                          '以及': (' and ', ' 且 '), 'or': (' or ', ' 或 '),
                          '或': (' or ', ' 或 '), ',': (', ', '、')}
            source, label = connectors.get(connector, (connector, connector))
            names.append(source)
            labels.append(label)
        name = _canonical(match.group())
        names.append(name)
        labels.append(_display(name))
        end = match.end()
    return ''.join(names), 'lab', ''.join(labels)


def _canonical(raw: str) -> str:
    return _MEASURE_NAMES.get(re.sub(r"[^a-z]", "", raw.casefold()), raw.strip())


def _kind(measure: str) -> str:
    return "score" if measure in _SCORE_NAMES else "lab"


def _display(measure: str) -> str:
    return _LABEL_NAMES.get(measure, measure)


def _operator(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw.casefold().replace("\\", "")).strip()
    if any(token in text for token in (
            ">=", "\u2265", "\u2267", "\u5927\u4e8e\u7b49\u4e8e", "\u4e0d\u4f4e\u4e8e", "\u4e0d\u5c11\u4e8e",
            "\u81f3\u5c11", "at least", "no less", "not less", "greater than or equal", "greater than and equal")):
        return ">="
    if any(token in text for token in (
            "<=", "\u2264", "\u2266", "\u5c0f\u4e8e\u7b49\u4e8e", "\u4e0d\u9ad8\u4e8e", "\u4e0d\u8d85\u8fc7",
            "\u81f3\u591a", "at most", "no greater", "not more", "less than or equal")):
        return "<="
    if any(token in text for token in (">", "\uff1e", "\u5927\u4e8e", "more than", "greater than", "above")):
        return ">"
    if any(token in text for token in ("<", "\uff1c", "\u5c0f\u4e8e", "less than", "below")):
        return "<"
    return "="


def _unit(raw: str | None) -> str | None:
    if not raw:
        return None
    value = re.sub(r"\s+", " ", raw).strip()
    low = value.casefold()
    if value == "%" or low.startswith("percent"):
        return "%"
    if "uln" in low or "upper limit" in low or re.search(r'正常(?:值|范围)?上限',value):
        return "\u00d7 ULN" if re.search(r"[\u00d7x]|times|\u500d", value, re.IGNORECASE) else "ULN"
    if re.fullmatch(r"[\u00d7x]?\s*10\s*\^?\s*9\s*/\s*[Ll]", value):
        return "\u00d7 10^9/L" if value[0] in "\u00d7xX" else "10^9/L"
    return re.sub(r"\s*/\s*", "/", value)


def _label(measure: str, kind: str, operator: str, number: str, unit: str | None) -> str:
    head = _display(measure)
    if kind == "score" and measure != "BSA":
        head = f"{head} \u8bc4\u5206"
    text = f"{head} {_OPERATOR_SYMBOL[operator]} {number}"
    if unit:
        text += unit if unit == "%" or unit.startswith("/") else f" {unit}"
    return text


def _line_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    offset = 0
    for line in text.splitlines(keepends=True):
        spans.append((offset, offset + len(line.rstrip("\r\n"))))
        offset += len(line)
    return spans


def _headings(text: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for start, end in _line_spans(text):
        line = text[start:end]
        for pattern in (_HEADING_EN, _HEADING_ZH):
            match = pattern.match(line)
            if not match:
                continue
            if not match.group("colon") and line[match.end():].strip():
                continue
            label = match.group("label")
            section = "exclusion" if re.search(
                r"exclusion|\u6392\u9664|\u5254\u9664", label, re.IGNORECASE) else "inclusion"
            title = label.strip()
            if title.casefold().startswith('other ') and found and found[-1]['section'] == section:
                title = found[-1]['title'] + ' · ' + title
            found.append({"start": start + match.start("label"), "end": start + match.end(),
                          "section": section, "line_start": start, 'title': title})
            break
    return found


def _section_at(position: int, headings: list[dict[str, Any]]) -> str:
    section = "unspecified"
    for heading in headings:
        if heading["end"] <= position:
            section = heading["section"]
    return section


def _rule_text(text: str, start: int, headings: list[dict[str, Any]]) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end < 0:
        line_end = len(text)
    begin = line_start
    for heading in headings:
        if heading["line_start"] == line_start and heading["end"] <= start:
            begin = heading["end"]
    bullet = _BULLET.match(text[begin:line_end])
    if bullet:
        begin += bullet.end()
    return text[begin:line_end].strip()


def _role_spans(text: str, role: str, pattern: re.Pattern[str]) -> list[tuple[int, int, str]]:
    return [(match.start(), match.end(), role) for match in pattern.finditer(text)]


def _segments(text: str, spans: list[tuple[int, int, str]]) -> list[dict[str, str | None]]:
    if not text:
        return []
    chosen: list[tuple[int, int, str]] = []
    for span in sorted(spans, key=lambda item: (-_PRIORITY[item[2]], item[0], -(item[1] - item[0]))):
        start, end, _ = span
        if end > start and all(end <= left or start >= right for left, right, _ in chosen):
            chosen.append(span)
    chosen.sort()
    points = {0, len(text)}
    for start, end, _ in chosen:
        points.update((start, end))
    result: list[dict[str, str | None]] = []
    for start, end in pairwise(sorted(points)):
        role = next((role for left, right, role in chosen if left <= start and end <= right), None)
        chunk = text[start:end]
        if result and result[-1]["emphasis"] == role:
            result[-1]["text"] += chunk
        else:
            result.append({"text": chunk, "emphasis": role})
    return result
