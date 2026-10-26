"""Versioned source-class facets; they do not establish China indication or core membership."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from ciw2.render.drug_identity import web_url

FIELD = 'identity.registration_class'
LABELS = {'innovative': '创新药', 'biosimilar': '生物类似药', 'modified': '改良型', 'unknown': '类别待核'}
RULE_VERSION = 'cde-registration-2020-literal-v1'
CHEMICAL_RULE = 'https://english.nmpa.gov.cn/2020-06/30/c_528659.htm'
BIOLOGICAL_RULE = 'https://www.nmpa.gov.cn/directory/web/nmpa/images/1707039824076019627.pdf'
EFFECTIVE_DATE_SOURCE = 'https://english.nmpa.gov.cn/2020-06/30/c_528660.htm'


def _category(fact: dict) -> tuple[str, str | None]:
    ctx = fact['context']
    try:
        day = date.fromisoformat(ctx.get('handled_date_text', ''))
    except (ValueError, TypeError):
        return 'unknown', None
    if not date(2020, 7, 1) <= day <= date.today():
        return 'unknown', None
    code, kind = fact['value'], ctx.get('drug_type')
    if kind in {'化药', '化学药品'}:
        if code == '1':
            return 'innovative', CHEMICAL_RULE
        if code in {'2', '2.1', '2.2', '2.3', '2.4'}:
            return 'modified', CHEMICAL_RULE
    if kind == '治疗用生物制品':
        if code == '1':
            return 'innovative', BIOLOGICAL_RULE
        if code == '3.3':
            return 'biosimilar', BIOLOGICAL_RULE
        if code in {'2', '2.1', '2.2', '2.3', '2.4'}:
            return 'modified', BIOLOGICAL_RULE
    return 'unknown', None


def _ref(fact: dict, source: dict) -> dict:
    category, definition = _category(fact)
    ctx = fact['context']
    return {'fact_id': fact['id'], 'source_id': source['id'], 'quote': fact['quote'],
            'url': web_url(source['url']), 'field': FIELD, 'role': '注册分类', 'value': fact['value'],
            'context': ctx, 'category': category, 'category_label': LABELS[category],
            'definition_url': definition, 'rule_version': RULE_VERSION,
            'observed_at': source['fetched_at'], 'registration_number': ctx['acceptance_number']}


def registrations(db, pid: str) -> dict[str, dict]:
    sources = {s['id']: s for s in db.query('SELECT * FROM sources WHERE project_id=? AND kind=?', (pid, 'cde'))}
    by_drug = defaultdict(list)
    names = {d['id']: d['name'] for d in db.entities(pid, 'drug')}
    for fact in db.current_facts(pid):
        source = sources.get(fact['source_id'])
        ctx = fact['context']
        if (fact['field'] != FIELD or fact['status'] != 'verified' or fact['extracted_by'] != 'code:cde'
                or not source or not fact['quote'] or ctx.get('role') != 'registration_class'
                or ctx.get('source_snapshot') != source['digest'] or not ctx.get('acceptance_number')
                or names.get(fact['entity_id']) != ctx.get('product_name')):
            continue
        by_drug[fact['entity_id']].append(_ref(fact, source))
    out = {}
    for eid in names:
        refs = sorted(by_drug[eid], key=lambda r: (r['registration_number'], r['observed_at'], r['fact_id']))
        # Compare current observations of each filing; preserve equal-time conflicts, never first-wins.
        latest = {}
        for ref in refs:
            number = ref['registration_number']
            latest[number] = max(latest.get(number, ''), ref['observed_at'])
        current = [r for r in refs if r['observed_at'] == latest[r['registration_number']]]
        categories = {r['category'] for r in current}
        category = next(iter(categories)) if len(categories) == 1 else 'unknown'
        out[eid] = {'category': category, 'label': LABELS[category], 'refs': refs,
                    'rule_version': RULE_VERSION, 'core_membership': None}
    return out
