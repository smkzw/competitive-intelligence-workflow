"""Exact selected CT.gov registry observations for scope review, read from local CAS.

The projection is read-only and deterministic. It forwards original registered fields
for trials already linked to this project's candidates; it does not score medical
relevance, rewrite entity attrs, or write the database. Entity attributes are leads,
not source facts: only a registered JSON document whose bytes match the recorded
digest, whose project and official CT.gov URL are current, and whose NCT is exact may
contribute.

Both the exact study endpoint and the official search endpoint are indexed, because a
current search snapshot is evidence in its own right. Sources are never ranked against
each other, and picking the newest stored version at one URL only keeps that source
current; it says nothing about publication or clinical precedence. Observations are
grouped losslessly by their selected raw fields, so repeated values collapse while
every exact study, source version and JSON location is retained. A source dictionary
declares each registered URL once per source_id; every study reference points to it.
Different current values stay in different groups.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlsplit

from ciw2.pipeline.context import RunContext
from ciw2.sources.ctgov import API, NCT_RE
from ciw2.sources.http import source_by_url

KEY = 'registry_observations'
_API = urlsplit(API)
_HOST = _API.hostname
_SEARCH_PATH = _API.path
_STUDY_PATH = re.compile(re.escape(_SEARCH_PATH) + r'/(NCT\d{8})')
_Entry = tuple[dict[str, Any], dict[str, Any]]


def _at(value: Any, *path: str) -> Any:
    for name in path:
        if not isinstance(value, dict) or name not in value:
            return None
        value = value[name]
    return value


def _nct(study: Any) -> str | None:
    nct = _at(study, 'protocolSection', 'identificationModule', 'nctId')
    return nct if isinstance(nct, str) else None


def _endpoint(url: str) -> tuple[str, str | None] | None:
    """('search', None) or ('study', nct) for the current official CT.gov JSON endpoints."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != 'https' or parts.hostname != _HOST or port not in (None, 443):
        return None
    if parts.username or parts.password:
        return None
    if parts.path.rstrip('/') == _SEARCH_PATH:
        return 'search', None
    match = _STUDY_PATH.fullmatch(parts.path)
    return ('study', match.group(1)) if match and not parts.query else None


def _selected(study: dict[str, Any]) -> dict[str, Any]:
    """Literal registered fields only; a missing field stays absent and false stays false."""
    protocol = study.get('protocolSection')
    if not isinstance(protocol, dict):
        return {}
    selected: dict[str, Any] = {}
    conditions = _at(protocol, 'conditionsModule', 'conditions')
    if isinstance(conditions, list) and all(isinstance(item, str) for item in conditions):
        selected['conditions'] = list(conditions)
    for field, path in (('studyType', ('designModule', 'studyType')),
                        ('primaryPurpose', ('designModule', 'designInfo', 'primaryPurpose'))):
        value = _at(protocol, *path)
        if isinstance(value, str):
            selected[field] = value
    healthy = _at(protocol, 'eligibilityModule', 'healthyVolunteers')
    if isinstance(healthy, bool):
        selected['healthyVolunteers'] = healthy
    return selected


def _current(rc: RunContext, url: str) -> tuple[dict[str, Any], Any] | None:
    """Current registered version at this URL; its stored bytes must match its digest."""
    row = source_by_url(rc.tool_ctx(), url)
    if row is None or row.get('kind') != 'ctgov' or row.get('url') != url:
        return None
    try:
        raw = rc.cas.get(row['digest'])
    except (OSError, TypeError, ValueError):
        return None
    if hashlib.sha256(raw).hexdigest() != row['digest']:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return row, payload


def _target_studies(payload: Any, targets: set[str]) -> list[tuple[str, dict[str, Any], str]]:
    """Exact target studies with locators from either official document shape."""
    if not isinstance(payload, dict):
        return []
    if 'protocolSection' in payload:
        nct = _nct(payload)
        return [(nct, payload, 'protocolSection')] if nct in targets else []
    studies = payload.get('studies')
    if not isinstance(studies, list):
        return []
    found: list[tuple[str, dict[str, Any], str]] = []
    for index, item in enumerate(studies):
        if not isinstance(item, dict):
            continue
        nct = _nct(item)
        if nct is not None and nct in targets:
            found.append((nct, item, f'studies[{index}].protocolSection'))
    return found


def _urls(rc: RunContext, targets: set[str]) -> list[str]:
    rows = rc.db.query(
        "SELECT DISTINCT url FROM sources WHERE project_id=? AND kind='ctgov' ORDER BY url",
        (rc.project_id,))
    urls: list[str] = []
    for url in (row['url'] for row in rows):
        endpoint = _endpoint(url) if isinstance(url, str) else None
        if endpoint is None:
            continue
        kind, nct = endpoint
        if kind == 'study' and nct not in targets:
            continue
        urls.append(url)
    return urls


def _index(rc: RunContext, targets: set[str]) -> dict[str, list[_Entry]]:
    """One current CAS parse per official project URL; keep only target entries."""
    index: dict[str, list[_Entry]] = {}
    if not targets:
        return index
    for url in _urls(rc, targets):
        current = _current(rc, url)
        if current is None:
            continue
        row, payload = current
        for nct, study, locator in _target_studies(payload, targets):
            selected = _selected(study)
            if selected:
                entry = {'nct': nct, 'source_id': row['id'], 'json': locator, 'url': url}
                index.setdefault(nct, []).append((entry, selected))
    for entries in index.values():
        entries.sort(key=lambda item: (item[0]['url'], item[0]['source_id'], item[0]['json']))
    return index


def _link_map(rc: RunContext) -> dict[str, list[str]]:
    """This project's drug-trial links, read once per attach."""
    rows = rc.db.query(
        "SELECT l.src, e.name FROM links l JOIN entities e ON e.id=l.dst AND e.project_id=l.project_id "
        "WHERE l.project_id=? AND l.rel='drug-trial' AND e.type='trial' ORDER BY l.src, e.name, e.id",
        (rc.project_id,))
    mapping: dict[str, list[str]] = {}
    for row in rows:
        name = row['name']
        if isinstance(name, str) and NCT_RE.fullmatch(name):
            mapping.setdefault(row['src'], []).append(name)
    return mapping


def _trial_ncts(candidate: dict[str, Any], links: dict[str, list[str]]) -> list[str]:
    """A trial candidate owns only its exact NCT; a drug uses this project's drug-trial links."""
    name = candidate.get('name')
    if candidate.get('type') == 'trial':
        return [name] if isinstance(name, str) and NCT_RE.fullmatch(name) else []
    entity_id = candidate.get('id')
    return links.get(entity_id, []) if isinstance(entity_id, str) else []


def _observations(ncts: list[str], index: dict[str, list[_Entry]]) -> dict[str, Any]:
    """Selected raw fields plus an explicit source dictionary for every provenanced study.

    A current source version has one URL for all of its observations, so the URL is
    declared once per source_id.  Every study reference still names the exact NCT,
    source version and JSON location; the association round-trips without ranking,
    merging or dropping a group.
    """
    groups: dict[str, dict[str, Any]] = {}
    sources: dict[str, str] = {}
    seen: set[tuple[str, str, str, str]] = set()
    for nct in ncts:
        for entry, selected in index.get(nct, ()):
            group = groups.setdefault(json.dumps(selected, ensure_ascii=False, sort_keys=True),
                                      {**selected, 'studies': []})
            mark = (entry['nct'], entry['source_id'], entry['json'], entry['url'])
            if mark not in seen:
                seen.add(mark)
                sources[entry['source_id']] = entry['url']
                group['studies'].append(
                    {'nct': entry['nct'], 'source_id': entry['source_id'], 'json': entry['json']})
    if not groups:
        return {}
    for group in groups.values():
        group['studies'].sort(key=lambda item: (item['nct'], sources[item['source_id']],
                                                item['source_id'], item['json']))
    return {'registry': 'ctgov', 'sources': {sid: sources[sid] for sid in sorted(sources)},
            'groups': [groups[key] for key in sorted(groups)]}


def attach(rc: RunContext, candidates: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return candidates whose attrs carry exact source-bound observations, when available."""
    links = _link_map(rc)
    linked = [(candidate, _trial_ncts(candidate, links)) for candidate in candidates]
    index = _index(rc, {nct for _, ncts in linked for nct in ncts})
    projected: list[dict[str, Any]] = []
    for candidate, ncts in linked:
        observations = _observations(ncts, index)
        attrs = candidate.get('attrs')
        if not observations:
            projected.append(candidate)  # No context keeps the previous candidate shape.
            continue
        projected.append({**candidate, 'attrs': {
            **(attrs if isinstance(attrs, dict) else {}), KEY: observations}})
    return projected
