"""Event field checks: an announcement date is not a regulatory action date."""

import re

from ciw.verify.crosscheck import _date_in_quote
from ciw.verify.quote import check_quote, normalize

_ACTION = {
    "approval": r"获批|批准|approv|authori[sz]",
    "filing": r"受理|递交|提交|submit|accept|filing|filed",
    "topline": r"顶线|揭盲|主要终点|top[- ]?line|primary endpoint|results",
    "phase_start": r"入组|启动|enroll|enrol|initiated|first patient",
    "licensing": r"签署|授权|许可|签约|修订|修正|sign|licens|agreement|amend|revis",
}
_ANNOUNCEMENT = re.compile(r"宣布|发布|公告|announc|issued|press release", re.I)
_TOPLINE = re.compile(
    r"top[- ]?line|顶线|揭盲|(?:宣布|公布|披露).{0,100}(?:结果|主要终点)|"
    r"(?:announc|release).{0,100}(?:results|primary endpoint)",
    re.I | re.S,
)
_FIRST_ENROLLED = re.compile(
    r"(?:已(?:经)?|完成|成功).{0,30}首(?:例|位|名).{0,20}入组|"
    r"首(?:例|位|名).{0,15}(?:已(?:经)?|完成|成功).{0,20}入组|"
    r"\bfirst\s+(?:patient|participant|subject)\s+(?:has\s+been|was|is)\s+"
    r"(?:successfully\s+)?(?:enrolled|recruited)\b|"
    r"\b(?:enrolled|recruited)\s+(?:(?:its|the)\s+)?first\s+(?:patient|participant|subject)\b",
    re.I,
)


def _literal(quote: str, value: str) -> bool:
    value = normalize(value)
    if not value:
        return True
    left = r"(?<![a-z0-9])" if value[0].isascii() and value[0].isalnum() else ""
    right = r"(?![a-z0-9])" if value[-1].isascii() and value[-1].isalnum() else ""
    return re.search(left + re.escape(value) + right, normalize(quote)) is not None


def _first_enrolment(quote: str) -> bool:
    for sentence in re.split(r"[。；;.!?\n]", quote):
        for match in _FIRST_ENROLLED.finditer(sentence):
            before = sentence[:match.start()]
            if not re.search(r"计划|预计|预期|拟|将|尚未|未|没有|没|不能|无法|"
                             r"\b(?:will|expected|plans?|aims?|no|not|never|cannot)\b", before, re.I):
                return True
    return False


def _filing_only_planned(quote):
    found = False
    for clause in re.split(r"[。；;!?\n]|\.(?!\d)", quote):
        for action in re.finditer(r"递交|提交|受理|\b(?:submit|submitted|accept|accepted|file|filed)\b", clause, re.I):
            found = True
            before = clause[:action.start()]
            planned = re.search(r"(?:计划|预计|预期|拟|将)[^，,。；;]{0,100}$|"
                                r"\b(?:will|expected|plans?|planned|aims?|intends?)\b[^,;]{0,100}$", before, re.I)
            negated = re.search(r"(?:尚未|未|没有|无法)\s*$|"
                                r"\b(?:not|never|cannot)(?:\s+(?:yet|been|be|have)){0,3}\s*$", before, re.I)
            if not planned and not negated:
                return False
    return found


def _patient_scopes(quote):
    part = r"(?:[^.!?。;；\n]|\.(?=\d))"
    pattern = (r"\b(?:patients?|adults?|children|adolescents?)\b" + part + r"{0,200}?"
               r"\b((?:for whom|whose|in whom)\b" + part + r"*)")
    return [m[1].strip() for m in re.finditer(pattern, quote, re.I)]


def validate_event_item(item: dict) -> tuple[bool, str]:
    kind, quote = item["event_type"], item["quote"]
    for field in ("product_mention", "indication"):
        if not _literal(quote, item.get(field, "")):
            return False, f"{field}未在所选引文中保留完整原文，不能借用片段外先行词"
    detail = item.get("detail", "")
    if detail:
        anchor = item.get("detail_quote") or detail
        if not check_quote(quote, anchor, detail).ok:
            return False, "detail缺少所选引文内支持其信息与数值的连续原文"
        for scope in _patient_scopes(quote):
            if normalize(scope) not in normalize(anchor):
                return False, "detail与detail_quote须保留本条适用人群的完整条件，可用中文概括但不能扩大范围：" + scope
    if kind == "filing" and _filing_only_planned(quote):
        return False, "引语仅为计划或否定，未支持实际递交或受理"
    if kind == "phase_start" and not _first_enrolment(quote):
        return False, "引语未明确首例已经入组，计划或仅试验启动不能代替首例入组"
    if kind == "topline" and not _TOPLINE.search(quote):
        return False, "引语未支持顶线结果披露，不能把结果回顾当作新顶线事件"
    if not item.get("date"):
        return True, ""
    evidence = item.get("event_date_quote") or ""
    if not check_quote(quote, evidence).ok or not _date_in_quote(item["date"], evidence):
        return False, "缺少事件日期与实际动作相连的原文"
    if (kind in {"approval", "filing"} and "\n" in evidence) or not re.search(
        _ACTION.get(kind, r"(?!)"), evidence, re.I
    ):
        return False, "新闻头部日期不能代替事件日期"
    if kind == "licensing":
        amendment = re.compile(r"修订|修正|amend|revis", re.I)
        if amendment.search(item.get("detail", "")) and not amendment.search(evidence):
            return False, "原合作签署日期不能用于修订后条款"
    if kind in {"approval", "filing"} and _ANNOUNCEMENT.search(evidence):
        return False, "宣布已经获批/受理不证明该日就是批准/受理日"
    return True, ""
