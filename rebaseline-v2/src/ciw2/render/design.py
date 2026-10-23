"""Source-backed design comparison; display projections never alter stored facts."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any
from urllib.parse import urlsplit

from ciw2.domain.semantics import parse_timepoint
from ciw2.pipeline.queries import scoped_trials
from ciw2.render.drug_identity import drug_identities
from ciw2.render.eligibility import eligibility_reading
from ciw2.render.labels import phase_label
from ciw2.render.trial_identity import trial_identities
from ciw2.store.db import DB


def thresholds(criteria: str) -> list[dict[str, Any]]:
    """Compatibility projection from the single source-span reader."""
    return eligibility_reading(criteria)['rules']


def source_ref(fact: dict[str, Any], sources: dict[str, dict[str, Any]], *, historical: bool = False) -> dict[str, Any]:
    source = sources.get(fact['source_id'], {})
    url = source.get('url') or fact['context'].get('source_url')
    if url and urlsplit(url).scheme not in {'http', 'https'}:
        url = None
    return {'fact_id': fact['id'], 'source_id': fact['source_id'], 'url': url,
            'quote': fact['quote'], 'status': fact['status'],
            'stored_status': fact.get('stored_status', fact['status']), 'historical': historical,
            'verdict_note': fact.get('verdict_note'),
            'locator': fact['context'].get('json_path'), 'value': fact['value'], 'context': fact['context']}


def scalar_observations(row: dict[str, Any]) -> None:
    """One unambiguous verified scientific observation, never database-order truth."""
    for key, refs in row['observations'].items():
        verified = [r for r in refs if r['status'] == 'verified']
        signatures = {json.dumps([r['value'], {k: r['context'][k] for k in (
            'enrollment_type', 'arm', 'timepoint', 'population', 'unit', 'stat_type', 'denominator')
            if r['context'].get(k) is not None}], sort_keys=True, ensure_ascii=False) for r in verified}
        selected = verified[0] if len(signatures) == 1 else (refs[0] if not verified and len(refs) == 1 else None)
        if selected:
            row[key] = selected['value']
            row[f'{key}_status'] = selected['status']
            if key == 'sample_size':
                row['sample_size_type'] = selected['context'].get('enrollment_type')
    criteria = row.get('eligibility_criteria')
    reading = eligibility_reading(criteria) if isinstance(criteria, str) else {'rules': [], 'segments': []}
    row['eligibility_thresholds'] = reading['rules']
    row['eligibility_reading'] = reading
    clauses: dict[tuple[str, str, int], dict[str, Any]] = {}
    for rule in reading['rules']:
        key = (rule['section'], rule['section_title'], rule['clause_start'])
        clause = clauses.setdefault(key, {'section': rule['section'], 'labels': [],
            'section_title': rule['section_title'],
            'segments': eligibility_reading(rule['rule_text'])['segments']})
        clause['labels'].append(rule['label'])
    row['eligibility_clauses'] = list(clauses.values())


def endpoint_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        endpoints = [(kind, endpoint) for kind in ('primary', 'secondary')
                     for endpoint in row.get(f'{kind}_endpoints', [])]
        for kind, endpoint in endpoints:
            name = endpoint.get('measure') or ''
            visit = endpoint.get('time_frame') or ''
            time = parse_timepoint(visit)
            if not re.fullmatch(r'(?:at\s+)?(?:(?:week|day|month)\s*\d+|\d+\s*(?:weeks?|days?|months?)|第\s*\d+\s*[周天月])', visit.strip(), re.IGNORECASE):
                time = parse_timepoint('')
            frame = ('days', time.days) if time.days is not None else (
                ('months', time.months) if time.months is not None else ('raw', visit.casefold().strip()))
            key = (kind, ' '.join(name.casefold().split()), endpoint.get('description'), *frame)
            group = groups.setdefault(key, {'kind': kind, 'measure': name, 'timepoint': visit, 'entries': []})
            group['entries'].append({**endpoint, 'trial': row['trial'], 'drugs': row['drugs'],
                                     'identity': row['identity']})
    return list(groups.values())


def design_data(db: DB, pid: str, phase_zh: dict[str, str]) -> dict[str, Any]:
    trials = {t['id']: t for t in scoped_trials(db,pid)}
    identities = trial_identities(db, pid)
    drugs = {d['id']: d['name_zh'] or d['name'] for d in drug_identities(db,pid).values()}
    sources = {s['id']: s for s in db.query('SELECT id, url FROM sources WHERE project_id=?', (pid,))}
    names: dict[str, list[str]] = defaultdict(list)
    for link in db.query("SELECT src, dst FROM links WHERE project_id=? AND rel='drug-trial'", (pid,)):
        if link['src'] in drugs:
            names[link['dst']].append(drugs[link['src']])
    rows: dict[str, dict[str, Any]] = {}
    for fact in sorted(db.current_facts(pid), key=lambda f: (f['entity_id'], f['field'], f['id'])):
        tid, field = fact['entity_id'], fact['field']
        if tid not in trials or not field.startswith(('design.', 'trial.', 'status.trial')):
            continue
        trial = trials[tid]
        row = rows.setdefault(tid, {'trial': trial['name'], 'title': trial['attrs'].get('title'),
            'identity': identities[tid],
            'url': trial['attrs'].get('url'), 'drugs': names[tid], 'primary_endpoints': [], 'secondary_endpoints': [],
            'unverified': [], 'sources': {}, 'observations': {}, 'eligibility_thresholds': []})
        ref = source_ref(fact, sources)
        history, seen = [], {fact['id']}
        prior = fact.get('supersedes')
        while prior and prior not in seen:
            seen.add(prior)
            old = db.one('SELECT * FROM facts WHERE project_id=? AND id=?', (pid, prior))
            if old is None:
                break
            old['value'], old['context'] = json.loads(old['value']), json.loads(old['context'])
            history.append(source_ref(old, sources, historical=True))
            prior = old['supersedes']
        if history:
            ref['supersedes'], ref['history'] = history[0], history
        key = 'trial_status' if field == 'status.trial' else field.split('.', 1)[1].replace('.', '_')
        row['sources'].setdefault(key, []).append(ref)
        if field in {'design.primary_endpoint', 'design.secondary_endpoint'}:
            value = fact['value'] if isinstance(fact['value'], dict) else {'measure': fact['value']}
            row[f'{key}s'].append({**value, **ref})
        else:
            row['observations'].setdefault(key, []).append(ref)
        if fact['tier'] == 'critical' and fact['status'] != 'verified':
            row['unverified'].append(field)
    for row in rows.values():
        scalar_observations(row)
    ordered = sorted(rows.values(), key=lambda r: (r.get('phase') or '', r.get('start_date') or '', r['trial']), reverse=True)
    sized = [r for r in ordered if type(r.get('sample_size')) in (int, float)
             and r.get('sample_size_status') == 'verified']
    counts: dict[str, int] = defaultdict(int)
    for row in ordered:
        if row.get('phase_status') == 'verified':
            counts[phase_label(row.get('phase'))] += 1
    return {'rows': ordered, 'endpoint_groups': endpoint_groups(ordered), 'charts': {
        'size': {'labels': [r['trial'] for r in sized], 'values': [r['sample_size'] for r in sized],
                 'identities': [{k: r['identity'][k] for k in ('registry_id', 'axis_label', 'label')} for r in sized]},
        'phase': [{'name': key, 'value': count} for key, count in counts.items()]}}
