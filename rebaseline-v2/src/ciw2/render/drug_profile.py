"""Shared-source identity projection for drug profiles.

Only verified current facts of this project with a nonempty quote count; discovery
attributes never certify a target, company, holder group or development status.
Values are returned as plain data for autoescaped templates, and the projection is
strictly read-only: entities, attrs, facts and sources are never mutated.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from typing import Any

from ciw2.domain.identity import name_key
from ciw2.domain.profile_evidence import FIELDS, holder_role, indication_qualifies
from ciw2.render.drug_identity import web_url
from ciw2.render.labels import PHASE_ZH
from ciw2.store.db import DB

ROLES = {'identity.developer': '研发方', 'identity.rights_holder': '研发权益方'}
HOLDER_FIELD = 'status.china_mah'
HOLDER_JURISDICTIONS = frozenset({None, 'CN', 'China', '中国'})
CHINA_JURISDICTIONS = frozenset({'cn', 'china', '中国'})
GLOBAL_JURISDICTIONS = frozenset({'global'})
GROUP_RELATIONSHIPS = frozenset({'wholly_owned', 'controlled', 'subsidiary'})
DEVELOPMENT_FIELDS = {'status.china.development': 'china', 'status.global.development': 'global'}

_FIELD_ORDER = {field: index for index, field in enumerate(FIELDS)}
_PHASE_CODES = {code: code for code in PHASE_ZH}
_PHASE_LABELS = {label: code for code, label in PHASE_ZH.items()}
_PHASE_LABELS.update({'批准上市':'approved','获批上市':'approved'})
_ROMAN = {'I': 'phase1', 'II': 'phase2', 'III': 'phase3', 'IV': 'phase4'}
_ROMAN_PAIRS = {('I', 'II'): 'phase1_2', ('II', 'III'): 'phase2_3'}
_TRANSLIT = str.maketrans({'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV'})
_PHASE_PATTERN = re.compile(r'(IV|I{1,3})(?:\s*/\s*(IV|I{1,3}))?\s*期?', re.IGNORECASE)
_DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}')


def _text(value: Any) -> str | None:
    """Keep the source string verbatim; blank, None and non-strings never become text."""
    return value if isinstance(value, str) and value.strip() else None


def _context(fact: dict[str, Any]) -> dict[str, Any]:
    value = fact.get('context')
    return value if isinstance(value, dict) else {}


def _verified(fact: dict[str, Any], sources: dict[str, dict[str, Any]]) -> bool:
    quote = fact.get('quote')
    return (fact.get('status') == 'verified' and fact.get('source_id') in sources
            and isinstance(quote, str) and bool(quote.strip()))


def _jurisdiction(context: dict[str, Any]) -> str | None:
    value = context.get('jurisdiction')
    return value.strip().casefold() if isinstance(value, str) else None


def _dated(value: Any) -> str | None:
    """Valid YYYY-MM-DD calendar dates only, and never in the future."""
    if not isinstance(value, str) or _DATE_PATTERN.fullmatch(value.strip()) is None:
        return None
    try:
        day = date.fromisoformat(value.strip())
    except ValueError:
        return None
    return value.strip() if day <= date.today() else None


def _canonical_phase(value: Any) -> str:
    """One canonical Phase code from an exact code/label or an explicit Roman numeral."""
    text = _text(value)
    if text is None:
        return 'unknown'
    code = _PHASE_CODES.get(text) or _PHASE_LABELS.get(text)
    if code is not None:
        return code
    word = re.sub(r'^phase\s*', '', text.translate(_TRANSLIT), flags=re.IGNORECASE).strip()
    if re.fullmatch(r'[1-4](?:\s*/\s*[1-4])?\s*期?',word):
        word=word.translate(str.maketrans({'1':'I','2':'II','3':'III','4':'IV'}))
    match = _PHASE_PATTERN.fullmatch(word)
    if match is None:
        return 'unknown'
    first, second = match.group(1).upper(), (match.group(2) or '').upper()
    return _ROMAN[first] if not second else _ROMAN_PAIRS.get((first, second), 'unknown')


def _group_qualifies(fact: dict[str, Any], holder_keys: set[str]) -> bool:
    context = _context(fact)
    legal_entity = _text(context.get('legal_entity'))
    if legal_entity is None or name_key(legal_entity) not in holder_keys:
        return False
    if _jurisdiction(context) not in CHINA_JURISDICTIONS:
        return False
    if context.get('relationship') not in GROUP_RELATIONSHIPS:
        return False
    return _dated(context.get('as_of')) is not None


def _development_qualifies(fact: dict[str, Any], indication_keys: set[str], region: str) -> bool:
    context = _context(fact)
    indication = _text(context.get('indication'))
    if not indication_qualifies(indication,indication_keys):
        return False
    allowed = CHINA_JURISDICTIONS if region == 'china' else GLOBAL_JURISDICTIONS
    if _jurisdiction(context) not in allowed:
        return False
    return _dated(context.get('as_of')) is not None


def _holder_keys(facts: list[dict[str, Any]], sources: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    """Verified current China holder names per drug; the only anchor a group may name."""
    keys: dict[str, set[str]] = defaultdict(set)
    for fact in facts:
        if fact['field'] != HOLDER_FIELD or not _verified(fact, sources):
            continue
        name = _text(fact['value'])
        if name is None or _context(fact).get('jurisdiction') not in HOLDER_JURISDICTIONS:
            continue
        keys[fact['entity_id']].add(name_key(name))
    return keys


def _ref(fact: dict[str, Any], value: str, sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {'field': fact['field'], 'value': value, 'context': dict(_context(fact)),
            'fact_id': fact['id'], 'source_id': fact['source_id'], 'quote': fact['quote'],
            'source_kind':sources[fact['source_id']]['kind'],
            **({'phase_code':_canonical_phase(value)} if fact['field'] in DEVELOPMENT_FIELDS else {}),
            'url': web_url(sources[fact['source_id']]['url'])}


def _ref_order(ref: dict[str, Any]) -> tuple[int, str, str, str]:
    return (_FIELD_ORDER[ref['field']], name_key(ref['value']), ref['source_id'], ref['fact_id'])


def _company(ref: dict[str, Any]) -> dict[str, Any]:
    context = ref['context']
    return {'role': ROLES[ref['field']], 'name': ref['value'], 'fact_id': ref['fact_id'],
            'source_id': ref['source_id'], 'url': ref['url'], 'quote': ref['quote'],
            'as_of': _text(context.get('as_of')), 'jurisdiction': _text(context.get('jurisdiction'))}


def _group(ref: dict[str, Any],current_holders: set[str]) -> dict[str, Any]:
    context = ref['context']
    role='中国MAH所属集团' if name_key(context['legal_entity']) in current_holders else '许可记录持有人所属集团'
    return {'role': role, 'name': ref['value'], 'fact_id': ref['fact_id'],
            'source_id': ref['source_id'], 'url': ref['url'], 'quote': ref['quote'],
            'as_of': _dated(context.get('as_of')), 'jurisdiction': _text(context.get('jurisdiction')),
            'legal_entity': _text(context.get('legal_entity')),
            'relationship': _text(context.get('relationship'))}


def _one_phase(refs: list[dict[str, Any]]) -> str:
    phases = {_canonical_phase(ref['value']) for ref in refs}
    return phases.pop() if len(phases) == 1 else 'unknown'


def _distinct(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(values), key=name_key)


def _profile(rows: list[dict[str, Any]], sources: dict[str, dict[str, Any]],
             indication_keys: set[str], holder_keys: set[str]) -> dict[str, Any]:
    current_holders={name_key(f['value']) for f in rows if f['field']==HOLDER_FIELD
                     and isinstance(f['value'],str) and holder_role(_context(f))=='中国MAH'}
    qualified: list[dict[str, Any]] = []
    for fact in rows:
        field = fact['field']
        if field not in FIELDS:
            continue
        value = _text(fact['value'])
        if value is None:
            continue
        if field == 'status.china_mah_group' and not _group_qualifies(fact, holder_keys):
            continue
        region = DEVELOPMENT_FIELDS.get(field)
        if region is not None and not _development_qualifies(fact, indication_keys, region):
            continue
        qualified.append(_ref(fact, value, sources))
    qualified.sort(key=_ref_order)
    phase_china_refs = [ref for ref in qualified if ref['field'] == 'status.china.development']
    phase_global_refs = [ref for ref in qualified if ref['field'] == 'status.global.development']
    modalities = _distinct([ref['value'] for ref in qualified if ref['field'] == 'identity.modality'])
    return {
        'targets': _distinct([ref['value'] for ref in qualified if ref['field'] == 'identity.target']),
        'modality': ' / '.join(modalities) or None,
        'companies': [_company(ref) for ref in qualified if ref['field'] in ROLES],
        'group_refs': [_group(ref,current_holders) for ref in qualified if ref['field'] == 'status.china_mah_group'],
        'phase_china': _one_phase(phase_china_refs),
        'phase_global': _one_phase(phase_global_refs),
        'profile_refs': qualified,
        'phase_china_refs': phase_china_refs,
        'phase_global_refs': phase_global_refs,
    }


def drug_profiles(db: DB, pid: str) -> dict[str, dict[str, Any]]:
    """Project every drug of the project, including candidates excluded from reports."""
    project = db.project(pid)
    assert project is not None
    indication_keys = {name_key(_text(name)) for name in (project['indication'], *project['indication_aliases'])}
    indication_keys.discard('')
    sources = {row['id']: row for row in db.query('SELECT id,url,kind FROM sources WHERE project_id=?', (pid,))}
    facts = [fact for fact in db.current_facts(pid) if _verified(fact, sources)]
    holders = _holder_keys(facts, sources)
    by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        by_entity[fact['entity_id']].append(fact)
    profiles: dict[str, dict[str, Any]] = {}
    for drug in db.entities(pid, 'drug'):
        profiles[drug['id']] = _profile(by_entity.get(drug['id'], []), sources, indication_keys,
                                        holders.get(drug['id'], set()))
    return profiles
