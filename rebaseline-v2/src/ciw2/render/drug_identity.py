"""Source-backed formal names shared by every report, without mutating discovery."""
from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlsplit

from ciw2.domain.identity import name_key
from ciw2.store.db import DB


def web_url(value: Any) -> str | None:
    if not isinstance(value,str):
        return None
    try:
        url=urlsplit(value)
        return value if url.scheme in {'http','https'} and url.hostname else None
    except ValueError:
        return None


def drug_identities(db: DB, pid: str) -> dict[str, dict[str, Any]]:
    sources={s['id']:s for s in db.query('SELECT id,url FROM sources WHERE project_id=?',(pid,))}
    refs: dict[str,list[dict[str,Any]]]=defaultdict(list)
    for fact in db.current_facts(pid):
        if (fact['field'] not in {'identity.name_zh','identity.name_en'} or fact['status']!='verified'
                or fact['source_id'] not in sources or not isinstance(fact['value'],str)
                or not fact['value'].strip()):
            continue
        refs[fact['entity_id']].append({'name':fact['value'],'field':fact['field'],'fact_id':fact['id'],
            'source_id':fact['source_id'],'url':web_url(sources[fact['source_id']]['url']),
            'quote':fact['quote'],**{key:fact['context'].get(key) for key in (
                'registration_number','strength','observed_at','issue_date','approval_date','valid_until')}})
    out={}
    for drug in db.entities(pid,'drug'):
        name_refs=sorted(refs[drug['id']],key=lambda r:(name_key(r['name']),r['fact_id']))
        name_zh=' / '.join(dict.fromkeys(r['name'] for r in name_refs if r['field']=='identity.name_zh')) or None
        aliases=sorted(set(drug['aliases'])|{r['name'] for r in name_refs},key=name_key)
        out[drug['id']]={**drug,'name_zh':name_zh,'name_refs':name_refs,'aliases':aliases}
    return out


def china_trial_sites(db: DB, pid: str) -> dict[str, bool | None]:
    sources={s['id'] for s in db.query('SELECT id FROM sources WHERE project_id=?',(pid,))}
    observed: dict[str,set[bool]]=defaultdict(set)
    for fact in db.current_facts(pid):
        if fact['status']!='verified' or fact['source_id'] not in sources:
            continue
        if (fact['field']=='trial.china_site' and type(fact['value']) is bool
                and fact['context'].get('geographic_scope')=='mainland_china'):
            observed[fact['entity_id']].add(fact['value'])
        elif fact['field']=='trial.countries' and isinstance(fact['value'],list):
            if 'China' in fact['value']:
                observed[fact['entity_id']].add(True)
            elif fact['value'] and fact['context'].get('locations_complete') is True:
                observed[fact['entity_id']].add(False)
        elif fact['field']=='design.trial_scope' and fact['value']=='国内试验':
            observed[fact['entity_id']].add(True)
    return {tid:next(iter(values)) if len(values)==1 else None for tid,values in observed.items()}
