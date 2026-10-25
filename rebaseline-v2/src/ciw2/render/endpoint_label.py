"""Source-defined abbreviations and fully parsed change labels for expert reading.

This is a display projection only. Unknown clauses stay verbatim; original
endpoints, population, units, measurements and scientific grouping never change.
No indication/drug dictionary, inferred improvement direction, or translation API.
"""
from __future__ import annotations

import re

_ABBREVIATION = r'[a-z]?[A-Z]{2,}[a-z0-9]?(?:[ -](?:[A-Z]{2,}|[0-9]+))*'
_SCOPED = re.compile(
    r'\b(?:without|with|except|not|versus|vs|participants|patients|subjects|placebo|only|subgroups?'
    r'|during|before|after|rescue|treatment|grade|stage|among|when|until'
    r'|percent(?:age|ile)?|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve'
    r'|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty'
    r'|sixty|seventy|eighty|ninety|hundred|thousand|improvements?|responses?|reductions?)\b|[0-9<>=≤≥]', re.IGNORECASE)
_CHANGE = (('Absolute Change From Baseline in ', '较基线绝对变化'),
           ('Percent Change From Baseline in ', '较基线百分比变化'),
           ('Change From Baseline in ', '较基线变化'))
_OP = {'>=':'≥','<=':'≤','>':'>','<':'<','≥':'≥','≤':'≤','Less Than (<)':'<'}
_UNIT = {'week':'周','day':'天','month':'月'}


def _measure(text: str) -> str | None:
    weekly = re.fullmatch(r'Weekly Average of (.+)', text, re.IGNORECASE)
    if weekly:
        # One explicit averaging layer only; do not normalize nested operations.
        inner = _atomic_measure(weekly[1])
        return inner+'（每周均值）' if inner else None
    return _atomic_measure(text)


def _atomic_measure(text: str) -> str | None:
    text = re.sub(r' Scores?$', '', text, flags=re.IGNORECASE)
    nrs = re.fullmatch(r'(?:(Average|Peak|Worst) )?(Pruritus|Pain|Sleep Disturbance) '
                       r'(?:NRS|Numeric Rating Scale(?: \(NRS\))?)', text, re.IGNORECASE)
    if nrs:
        intensity = {'average': '平均', 'peak': '峰值', 'worst': '最严重', '': ''}[(nrs[1] or '').lower()]
        symptom = {'pruritus': '瘙痒', 'pain': '疼痛', 'sleep disturbance': '睡眠障碍'}[nrs[2].lower()]
        return intensity + symptom + 'NRS'
    expanded = re.fullmatch(r'([^()]+)\(('+_ABBREVIATION+r')\)', text)
    if expanded:
        if _SCOPED.search(expanded[1]) or expanded[2] == 'NRS':
            return None
        return expanded[2]
    return text if re.fullmatch(_ABBREVIATION, text) else None


def endpoint_label(value: object) -> str:
    if not isinstance(value, str) or not value:
        return '—'
    raw = value
    if len(raw)>2000:
        return raw
    text=' '.join(raw.split())
    for prefix, change in _CHANGE:
        if not text.casefold().startswith(prefix.casefold()):
            continue
        body=text[len(prefix):]
        qualifiers=[]
        visit=re.fullmatch(r'(.+) at Each Visit up to (Week|Day|Month)s? ([0-9]+(?:\.[0-9]+)?)',body,re.IGNORECASE)
        if visit:
            body=visit[1]
            qualifiers.append(f'各访视至第{visit[3]}{_UNIT[visit[2].lower()]}')
        age=re.fullmatch(r'(.+) For Participants (Less Than \(<\)|>=|<=|>|<|≥|≤)\s*([0-9]+(?:\.[0-9]+)?) Years of Age',body)
        if age:
            body=age[1]
            qualifiers.insert(0,f'{_OP[age[2]]}{age[3]}岁')
        name=_measure(body)
        return ' · '.join([name,change,*qualifiers]) if name else raw
    return raw
