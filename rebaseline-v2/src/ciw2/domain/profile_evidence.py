"""One bounded, source-literal profile check for adoption, recovery and requalification.

Natural-language expressions outside the explicit claim forms remain unverified;
name/date co-occurrence is not treated as a relationship or jurisdiction proof.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from ciw2.domain.identity import name_key

FIELDS=('identity.target','identity.modality','identity.developer','identity.rights_holder',
        'status.china_mah_group','status.china.development','status.global.development')
SOURCE_CONTEXT=('legal_entity','relationship','as_of','jurisdiction','indication')
_NEGATED=re.compile(r'\b(?:not|never|neither|no longer|without)\b|并非|並非|不是|不属于|不屬於|尚未|未获|未獲|不在',re.IGNORECASE)


def contains(quote: str,value: str) -> bool:
    return re.search(r'(?<![a-z0-9])'+re.escape(name_key(value))+r'(?![a-z0-9])',name_key(quote)) is not None


def drug_names(db: Any,pid: str,eid: str) -> list[str]:
    entity=next((d for d in db.entities(pid,'drug') if d['id']==eid),None)
    if entity is None:return []
    sources={row['id'] for row in db.query('SELECT id FROM sources WHERE project_id=?',(pid,))}
    return [entity['name'],*(f['value'] for f in db.current_facts(pid,eid)
        if f['field'] in {'identity.name_zh','identity.name_en'} and f['status']=='verified'
        and f['source_id'] in sources and isinstance(f['value'],str) and f['value'].strip() and f['quote'])]


def holder_role(context: dict[str,Any]) -> str:
    try:
        expired=date.fromisoformat(context.get('valid_until'))<datetime.fromisoformat(context.get('observed_at')).date()
    except (ValueError,TypeError):
        expired=False
    return '许可记录持有人' if expired else '中国MAH'


def dated(value: Any) -> date | None:
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return None
    try:
        day=date.fromisoformat(value)
        return day if day<=date.today() else None
    except ValueError:
        return None


def _date_present(text: str,day: date) -> bool:
    formats={day.isoformat(),f'{day.year}年{day.month}月{day.day}日',day.strftime('%Y年%m月%d日')}
    for fmt in ('%B %d, %Y','%d %B %Y','%B %d %Y','%d %b %Y'):
        label=day.strftime(fmt)
        formats.update({label,re.sub(r'\b0(?=\d\b)','',label)})
    markers=list(re.finditer(r'\bas of\b|截至|截止',text,re.IGNORECASE))
    if len(markers)>1:return False
    tail=text[markers[0].end():].lstrip(' :：') if markers else text.lstrip(' \t“"')
    return any(re.match(re.escape(name_key(label))+r'(?!\d)',name_key(tail)) for label in formats)


def _claims(quote: str) -> list[str]:
    return re.split(r'(?<=[。；;!?])\s*|(?<=\.)\s+(?=[A-Z\u4e00-\u9fff])',quote)


def _region_bound(text: str,names: list[str],indication: str,value: str,china: bool) -> bool:
    region=r'(?:中国|china|cn)' if china else r'(?:全球|global|globally|worldwide)'
    drug='(?:'+'|'.join(re.escape(name_key(n)) for n in names)+')'
    disease,raw=re.escape(name_key(indication)),re.escape(name_key(value))
    gap=r'[ \t,，:：-]*'
    patterns=[drug+gap+region+gap+disease+gap+raw,
              region+gap+drug+gap+disease+gap+raw,
              drug+gap+disease+gap+raw+gap+r'(?:is\s+)?(?:in\s+|在|于|於)'+region]
    return any(re.search(pattern,name_key(text)) for pattern in patterns)


def _ownership(text: str,parent: str,child: str,relation: str) -> bool:
    parent,child=re.escape(name_key(parent)),re.escape(name_key(child))
    text=name_key(text)
    qualifier={'wholly_owned':r'(?:wholly[- ]owned|全资|全資)',
               'controlled':r'(?:controlled|控股|控制)',
               'subsidiary':r'(?:(?:wholly[- ]owned|controlled|全资|全資|控股)\s*)?'}[relation]
    subsidiary=qualifier+r'\s*(?:subsidiary|子公司|附屬公司|附属公司)'
    end=r'(?=[ \t]*(?:as of\b|截至|截止|[,，。.；;]|$))'
    patterns=[parent+r'\s+owns\s+'+child+r'\s+as\s+(?:its|a)\s+'+subsidiary+end,
              child+r'\s*(?:is|was|became|,)\s*(?:a\s+|the\s+)?'+subsidiary+r'\s+of\s+'+parent+end,
              parent+r'\s*的\s*'+subsidiary+r'\s*'+child+end,
              child+r'\s*(?:为|為|是|系)\s*'+parent+r'\s*的\s*'+subsidiary+end]
    if relation=='wholly_owned':patterns.append(parent+r'\s+owns\s+100\s*%\s+of\s+'+child+end)
    return any(re.search(pattern,text) for pattern in patterns)


def _property(text: str,names: list[str],value: str,field: str) -> bool:
    if field not in {'identity.target','identity.modality'}:return True
    value=re.escape(name_key(value));text=name_key(text)
    for name in names:
        subject=re.escape(name_key(name))
        if field=='identity.target':
            predicate=r'\s*(?:targets?\s+|binds\s+|has (?:the )?target (?:of )?|靶向|特异性靶向|作用于|的靶点为)\s*'
        else:predicate=r'\s*(?:is (?:a |an |the )?|是(?:一种|一款)?|为(?:一种|一款)?)\s*'
        if re.search(subject+predicate+value,text):return True
    return False


def _deictic(quote: str,names: list[str],value: str,field: str) -> list[str]:
    if field!='identity.target' or re.search(r'\n\s*\n',quote):return []
    clauses=_claims(quote)
    if len(clauses)!=2:return []
    first=name_key(clauses[0]).rstrip('.')
    if not any(first==name_key(n)+' is the source full name' for n in names):return []
    second=name_key(clauses[1])
    return [clauses[1]] if re.fullmatch(r'its target is\s+'+re.escape(name_key(value))+r'[.]?',second) else []


def issue(db: Any,pid: str,eid: str,field: str,value: Any,quote: str,context: dict[str,Any]) -> str | None:
    if field not in FIELDS:return None
    names=drug_names(db,pid,eid)
    if not names:return '身份事实需要已存在的药物实体'
    if not isinstance(value,str) or not value.strip() or not contains(quote,value):return '原文缺少完整身份值'
    if field=='status.china_mah_group':
        legal=context.get('legal_entity');relation=context.get('relationship')
        if (not isinstance(legal,str) or relation not in {'wholly_owned','controlled','subsidiary'}
                or context.get('jurisdiction') not in {'CN','China','中国'}):return '集团关系范围未成立'
        sources={s['id'] for s in db.query('SELECT id FROM sources WHERE project_id=?',(pid,))}
        holder=any(f['field']=='status.china_mah' and f['status']=='verified' and f['source_id'] in sources
                   and isinstance(f['value'],str) and name_key(f['value'])==name_key(legal)
                   for f in db.current_facts(pid,eid))
        claims=[text for text in _claims(quote) if contains(text,legal) and contains(text,value)
                and not _NEGATED.search(text) and _ownership(text,value,legal,relation)]
        if not holder or not claims:return '原文未明确绑定该持有人与集团的控制关系'
    else:
        claims=[text for text in _claims(quote) if contains(text,value) and any(contains(text,name) for name in names)
                and not _NEGATED.search(text) and _property(text,names,value,field)]
        if not claims:claims=_deictic(quote,names,value,field)
        if not claims:return '原文未支持该药物的身份值'
    if field=='identity.rights_holder' and not any(re.search(r'权益|许可|授权|独家|rights|licen[cs]',c,re.IGNORECASE) for c in claims):
        return '自主研发或销售不能单独证明研发权益或许可关系'
    if field.endswith('.development'):
        indication=context.get('indication');project=db.project(pid)
        keys={name_key(n) for n in [project['indication'],*project['indication_aliases']]}
        if not isinstance(indication,str) or name_key(indication) not in keys:return '项目适应症范围未匹配'
        china=field=='status.china.development'
        if context.get('jurisdiction') not in ({'CN','China','中国'} if china else {'global'}):return '地域范围未匹配'
        claims=[c for c in claims if contains(c,indication) and _region_bound(c,names,indication,value,china)]
        if not claims:return '原文没有绑定该适应症与地域的开发状态'
    if field.startswith('status.'):
        day=dated(context.get('as_of'))
        if day is None or not any(_date_present(c,day) for c in claims):return '截至日期未绑定到该声明'
    return None
