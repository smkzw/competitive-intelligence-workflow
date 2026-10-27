"""Event field checks: an announcement date is not a regulatory action date."""

import re

from ciw.verify.crosscheck import _date_in_quote
from ciw.verify.quote import check_quote

_ACTION = {
    "approval": r"获批|批准|approv|authori[sz]",
    "filing": r"受理|递交|提交|submit|accept|filing|filed",
    "topline": r"顶线|揭盲|主要终点|top[- ]?line|primary endpoint|results",
    "phase_start": r"入组|启动|enroll|enrol|initiated|first patient",
    "licensing": r"签署|授权|许可|签约|sign|licens|agreement",
}
_ANNOUNCEMENT = re.compile(r"宣布|发布|公告|announc|issued|press release", re.I)
_TOPLINE = re.compile(
    r"top[- ]?line|顶线|揭盲|(?:宣布|公布|披露).{0,100}(?:结果|主要终点)|"
    r"(?:announc|release).{0,100}(?:results|primary endpoint)",
    re.I | re.S,
)


def validate_event_item(item: dict) -> tuple[bool, str]:
    kind, quote = item["event_type"], item["quote"]
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
    if kind in {"approval", "filing"} and _ANNOUNCEMENT.search(evidence):
        return False, "宣布已经获批/受理不证明该日就是批准/受理日"
    return True, ""
