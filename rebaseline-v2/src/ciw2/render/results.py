"""Complete measurement instances and bounded, queryable result figures."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from typing import Any

from ciw2.domain.identity import name_key
from ciw2.domain.outcomes import DOMAIN_LABELS

VISIT = re.compile(r'(?:at\s+)?(week|day|month)s?\s*(\d+)|第\s*(\d+)\s*(周|天|月)', re.IGNORECASE)


def _visit(text: Any) -> tuple[str, int, str] | None:
    if not isinstance(text, str):
        return None
    raw = ' '.join(text.split()).strip()
    if name_key(raw) == 'baseline':
        return 'days', 0, '基线'
    match = VISIT.fullmatch(raw)
    if not match:
        return None
    unit = (match[1] or {'周': 'week', '天': 'day', '月': 'month'}[match[4]]).lower()
    value = int(match[2] or match[3])
    return ('months' if unit == 'month' else 'days', value * (7 if unit == 'week' else 1),
            f"第{value}{ {'week': '周', 'day': '天', 'month': '月'}[unit]}")


def _measurement(row: dict[str, Any]) -> tuple[tuple, tuple[str, int, str] | None]:
    visits = {name: _visit(row.get(name)) for name in ('class_title', 'category', 'timepoint')}
    available = [value for value in visits.values() if value]
    unique = {(value[0], value[1]) for value in available}
    visit = available[0] if len(unique) == 1 else None
    facets = tuple(name_key(row.get(name)) if not visits[name] or len(unique) > 1 else ''
                   for name in ('class_title', 'category', 'timepoint'))
    # Missing population/statistics/unit cannot silently qualify unrelated studies.
    incomplete = not all(row.get(name) for name in ('population', 'stat_type', 'unit'))
    frame = (name_key(row['endpoint']), row.get('stat_type'), name_key(row.get('unit')),
             row.get('param_type'), row.get('dispersion_type'), name_key(row.get('population')),
             visit[0] if visit else None, facets,
             (row['entity_id'], row['source_id']) if incomplete else None,
             row.get('domain', 'unresolved'))
    return frame, visit


def _point(row: dict[str, Any], visit: tuple | None) -> dict[str, Any]:
    identity = row.get('identity') or {}
    trial_label = identity.get('label') or row.get('entity') or ''
    context_label = trial_label
    if identity.get('drug_label') == ' / '.join(row.get('display_drugs', [])):
        context_label = trial_label[len(identity['drug_label']):].strip(' ·')
    phase = identity.get('phase_label') or ''
    drug_label = row.get('arm_drug_label') or row.get('arm_drug') or ''
    axis_label = ' · '.join(filter(None, (drug_label, phase))) if drug_label else (
        '研究：' + identity['axis_label'] if identity.get('axis_label') else row.get('arm') or '研究观察')
    label = ' · '.join(str(value) for value in (row.get('arm_drug_label') or row.get('arm_drug'), context_label, row.get('arm')) if value)
    series = json.dumps([row['entity_id'], row['source_id'], row.get('source_snapshot'),
                         row.get('group_id'), row.get('arm')], ensure_ascii=False)
    return {'fact_id': row['id'], 'value': row['value'], 'x': visit[1] if visit else None,
            'drug_label': drug_label, 'phase_label': phase, 'axis_label': axis_label,
            'visit': visit[2] if visit else (row.get('class_title') or row.get('category') or row.get('timepoint') or ''),
            'series_key': series, 'series_name': label, 'label': label,
            'trial': row.get('entity') or '', 'trial_label': trial_label,
            'arm': row.get('arm') or ''}


def _group(frame: tuple, items: list[tuple[dict, tuple | None]], positions: set[int]) -> dict[str, Any]:
    rows = [item[0] for item in items]
    points = [_point(row, visit) for row, visit in items]
    pairs = Counter((point['series_key'], point['x']) for point in points)
    collision = any(count > 1 for count in pairs.values())
    line = not collision and all(point['x'] is not None for point in points) and len({p['x'] for p in points}) > 1
    axes = frame[6]
    group_id = hashlib.sha256(json.dumps(frame, ensure_ascii=False).encode()).hexdigest()[:16]
    return {'id': group_id, 'title': rows[0]['endpoint'], 'subtitle': rows[0].get('timepoint') or '',
            'domain': frame[-1],
            'population': rows[0].get('population') or '', 'unit': rows[0].get('unit') or '',
            'stat_type': rows[0].get('stat_type') or '', 'primary': any(row['field'].startswith('result.primary') for row in rows),
            'kind': 'line' if line else 'bar', 'axis_unit': axes, 'collision': collision, 'positions': sorted(positions),
            'display_axis': 'weeks' if axes == 'days' and all(p['x'] is not None and p['x'] % 7 == 0 for p in points) else axes,
            'points': points, 'labels': [point['label'] for point in points], 'values': [point['value'] for point in points],
            'trials': len({row['entity_id'] for row in rows})}


def result_groups(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    groups: dict[tuple, list[tuple[dict, tuple | None]]] = defaultdict(list)
    positions: dict[tuple, set[int]] = defaultdict(set)
    exclusions = {}
    for row in rows:
        frame, visit = _measurement(row)
        if visit:
            positions[frame].add(visit[1])
        value = row['value']
        reason = ('unverified' if row['status'] != 'verified' else 'non_numeric'
                  if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) else None)
        if reason:
            exclusions[row['id']] = reason
            continue
        groups[frame].append((row, visit))
    figures = [_group(frame, items, positions[frame]) for frame, items in groups.items()]
    return sorted(figures, key=lambda group: (list(DOMAIN_LABELS).index(group['domain']),
                                             not group['primary'], group['kind'] != 'line',
                                             name_key(group['title']), group['id'])), exclusions
