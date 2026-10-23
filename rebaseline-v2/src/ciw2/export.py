"""Read-only current-fact downloads; never a backup, raw-source or log bundle."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from ciw2.domain.availability import require_supported_cutoff
from ciw2.store.db import DB


def fact_export(db: DB, pid: str, field_prefix: str = '', status: str = '') -> dict[str, Any]:
    # One SQLite snapshot, including exact source versions, without model setup.
    with db.tx():
        project = db.project(pid)
        if project is None:
            raise KeyError(pid)
        require_supported_cutoff(project['cutoff_date'])
        sources = {row['id']: row for row in db.query(
            'SELECT id,kind,url,title,digest,text_digest,published_date,fetched_at '
            'FROM sources WHERE project_id=?', (pid,))}
        entities = {row['id']: row for row in db.query(
            'SELECT id,name,name_zh,type FROM entities WHERE project_id=?', (pid,))}
        facts = [{**fact, 'source': sources.get(fact['source_id']), 'entity': entities.get(fact['entity_id'])}
                 for fact in db.current_facts(pid) if fact['field'].startswith(field_prefix)
                 and (not status or fact['status'] == status)]
    return {'schema_version': 'ciw2-facts-v1', 'scope': 'current_project_facts', 'project_id': pid,
            'indication': project['indication'], 'selection': {'field_prefix': field_prefix, 'status': status},
            'fact_count': len(facts), 'facts': facts}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def _csv_text(value: Any, key: str, escaped: list[str]) -> str:
    text = '' if value is None else str(value)
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        escaped.append(key)
        return "'" + text
    return text


def encode_export(payload: dict[str, Any], file_format: str) -> bytes:
    if file_format == 'json':
        return (_json(payload) + '\n').encode('utf-8')
    if file_format != 'csv':
        raise ValueError('Unsupported export format')
    output = io.StringIO(newline='')
    columns = ['id', 'project_id', 'entity_id', 'entity_name', 'field', 'value_json', 'status', 'tier',
               'unit', 'source_id', 'source_url', 'source_digest', 'quote', 'context_json', 'csv_escaped_fields']
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for fact in payload['facts']:
        entity, source = fact['entity'] or {}, fact['source'] or {}
        flat = {key: fact[key] for key in ('id', 'project_id', 'entity_id', 'field', 'status', 'tier', 'source_id', 'quote')}
        flat.update(entity_name=entity.get('name_zh') or entity.get('name'), unit=fact['context'].get('unit'),
                    source_url=source.get('url'), source_digest=source.get('digest'))
        escaped: list[str] = []
        row = {key: _csv_text(value, key, escaped) for key, value in flat.items()}
        # Valid JSON strings start with quotes; valid negative numeric literals
        # remain numbers. Neither can start an executable spreadsheet formula.
        row.update(value_json=_json(fact['value']), context_json=_json(fact['context']),
                   csv_escaped_fields=_json(escaped))
        writer.writerow(row)
    return output.getvalue().encode('utf-8-sig')
