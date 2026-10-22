"""Source-backed design comparison; display projections never alter stored facts."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any
from urllib.parse import urlsplit

from ciw2.domain.semantics import parse_timepoint
from ciw2.store.db import DB


def thresholds(criteria: str) -> list[dict[str, Any]]:
    """Only copy explicit named-scale inequalities; no inferred clinical criteria."""
    pattern = r'\b(EASI|IGA|SCORAD|BSA|PP[- ]?NRS|WI[- ]?NRS|NRS)\s*(>=|<=|≥|≤|>|<|=)\s*(\d+(?:\.\d+)?)\s*(%)?'
    headers = [(m.end(), 'inclusion' if m[1].lower().startswith(('inclusion', '入')) else 'exclusion')
               for m in re.finditer(r'^\s*(?:key\s+)?(inclusion\s+criteria|exclusion\s+criteria|入选标准|排除标准)\s*[:：]?',
                                    criteria, re.IGNORECASE | re.MULTILINE)]
    result = []
    for match in re.finditer(pattern, criteria, re.IGNORECASE):
        section = next((role for end, role in reversed(headers) if end <= match.start()), 'unspecified')
        start = criteria.rfind('\n', 0, match.start()) + 1
        end = criteria.find('\n', match.end())
        rule = criteria[start:end if end >= 0 else len(criteria)].strip()
        result.append({'measure': match[1].upper(), 'operator': match[2].replace('≥', '>=').replace('≤', '<='),
                       'value': float(match[3]), 'unit': match[4] or None, 'quote': match[0],
                       'section': section, 'rule_text': rule})
    return result


def source_ref(fact: dict[str, Any], sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source = sources.get(fact['source_id'], {})
    url = source.get('url') or fact['context'].get('source_url')
    if url and urlsplit(url).scheme not in {'http', 'https'}:
        url = None
    return {'fact_id': fact['id'], 'source_id': fact['source_id'], 'url': url,
            'quote': fact['quote'], 'status': fact['status'],
            'locator': fact['context'].get('json_path'), 'value': fact['value']}


def endpoint_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        for endpoint in row['primary_endpoints']:
            name = endpoint.get('measure') or ''
            visit = endpoint.get('time_frame') or ''
            time = parse_timepoint(visit)
            if not re.fullmatch(r'(?:at\s+)?(?:(?:week|day|month)\s*\d+|\d+\s*(?:weeks?|days?|months?)|第\s*\d+\s*[周天月])', visit.strip(), re.IGNORECASE):
                time = parse_timepoint('')
            frame = ('days', time.days) if time.days is not None else (
                ('months', time.months) if time.months is not None else ('raw', visit.casefold().strip()))
            key = (' '.join(name.casefold().split()), *frame)
            group = groups.setdefault(key, {'measure': name, 'timepoint': visit, 'entries': []})
            group['entries'].append({**endpoint, 'trial': row['trial'], 'drugs': row['drugs']})
    return list(groups.values())


def design_data(db: DB, pid: str, phase_zh: dict[str, str]) -> dict[str, Any]:
    trials = {t['id']: t for t in db.entities(pid, 'trial')}
    drugs = {d['id']: d['name_zh'] or d['name'] for d in db.entities(pid, 'drug')}
    sources = {s['id']: s for s in db.query('SELECT id, url FROM sources WHERE project_id=?', (pid,))}
    names: dict[str, list[str]] = defaultdict(list)
    for link in db.query("SELECT src, dst FROM links WHERE project_id=? AND rel='drug-trial'", (pid,)):
        if link['src'] in drugs:
            names[link['dst']].append(drugs[link['src']])
    rows: dict[str, dict[str, Any]] = {}
    for fact in db.current_facts(pid):
        tid, field = fact['entity_id'], fact['field']
        if tid not in trials or not field.startswith(('design.', 'trial.', 'status.trial')):
            continue
        trial = trials[tid]
        row = rows.setdefault(tid, {'trial': trial['name'], 'title': trial['attrs'].get('title'),
            'url': trial['attrs'].get('url'), 'drugs': names[tid], 'primary_endpoints': [],
            'unverified': [], 'sources': {}, 'eligibility_thresholds': []})
        ref = source_ref(fact, sources)
        key = 'trial_status' if field == 'status.trial' else field.split('.', 1)[1].replace('.', '_')
        row['sources'].setdefault(key, []).append(ref)
        if field == 'design.primary_endpoint':
            value = fact['value'] if isinstance(fact['value'], dict) else {'measure': fact['value']}
            row['primary_endpoints'].append({**value, **ref})
        else:
            row[key] = fact['value']
        if field == 'design.sample_size':
            row['sample_size_status'] = fact['status']
            row['sample_size_type'] = fact['context'].get('enrollment_type')
        if field == 'design.phase':
            row['phase_status'] = fact['status']
        if field == 'design.eligibility.criteria' and isinstance(fact['value'], str):
            row['eligibility_thresholds'] = thresholds(fact['value'])
        if fact['tier'] == 'critical' and fact['status'] != 'verified':
            row['unverified'].append(field)
    ordered = sorted(rows.values(), key=lambda r: (r.get('phase') or '', r.get('start_date') or '', r['trial']), reverse=True)
    sized = [r for r in ordered if type(r.get('sample_size')) in (int, float)
             and r.get('sample_size_status') == 'verified']
    counts: dict[str, int] = defaultdict(int)
    for row in ordered:
        if row.get('phase_status') == 'verified':
            counts[phase_zh.get(row.get('phase') or 'unknown', '未知')] += 1
    return {'rows': ordered, 'endpoint_groups': endpoint_groups(ordered), 'charts': {
        'size': {'labels': [r['trial'] for r in sized], 'values': [r['sample_size'] for r in sized]},
        'phase': [{'name': key, 'value': count} for key, count in counts.items()]}}
