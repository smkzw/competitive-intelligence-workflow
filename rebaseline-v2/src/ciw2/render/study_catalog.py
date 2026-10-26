"""Read-only related-study inventory; numeric availability never defines membership."""
from __future__ import annotations

import hashlib
import json
from collections import Counter

from ciw2.pipeline.queries import scoped_trials
from ciw2.render.drug_identity import web_url


def _source(db, pid: str, trial_id: str, sources: dict) -> tuple[dict | None, dict]:
    link = db.one("SELECT dst,attrs FROM links WHERE project_id=? AND src=? AND rel='ctgov-current'",
                  (pid, trial_id))
    if not link:
        return None, {}
    try:
        context = json.loads(link['attrs'])
    except (TypeError, ValueError):
        return None, {}
    source = sources.get(link['dst'])
    if not isinstance(context, dict) or not source or source['kind'] != 'ctgov':
        return None, {}
    version = context.get('extractor_version')
    expected = hashlib.sha256(f'{source["id"]}:{version}'.encode()).hexdigest()
    if (not isinstance(version, str) or not version or context.get('source_id') != source['id']
            or context.get('source_digest') != source['digest'] or context.get('snapshot') != expected):
        return None, {}
    return source, context


def _published(trial: dict, context: dict) -> bool | None:
    flag, modules = trial['attrs'].get('has_results'), context.get('input_result_modules')
    if type(flag) is not bool or not isinstance(modules, list) or any(not isinstance(m, str) for m in modules):
        return None
    return flag if flag == bool(modules) else None


def study_catalog(db, pid: str, results: list[dict], identities: dict) -> dict:
    sources = {s['id']: s for s in db.query('SELECT * FROM sources WHERE project_id=?', (pid,))}
    result_counts = Counter(r['entity_id'] for r in results)
    rows = []
    for trial in scoped_trials(db, pid):
        source, context = _source(db, pid, trial['id'], sources)
        published = _published(trial, context) if source else None
        rows.append({'entity_id': trial['id'], 'registry_id': trial['name'],
            'identity': identities.get(trial['id']), 'result_count': result_counts[trial['id']],
            'published_results': published, 'published_label': {True: '登记已发布结果', False: '尚无登记结果',
                None: '—'}[published], 'source_url': web_url(source['url']) if source else None,
            'source_id': source['id'] if source else None})
    rows.sort(key=lambda row: row['registry_id'])
    return {'rows': rows, 'counts': {'all': len(rows),
        'with_results': sum(r['published_results'] is True for r in rows),
        'without_results': sum(r['published_results'] is False for r in rows),
        'unknown': sum(r['published_results'] is None for r in rows),
        'adopted': sum(r['result_count'] > 0 for r in rows)}}
