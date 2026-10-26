"""Adopt already-proven literal application rows; no fetch, aliases or approval inference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ciw2.harness.tools import ToolContext
from ciw2.sources.cde_review_browser import proven_acceptance_refs

FIELD = 'identity.registration_class'
EXTRACTOR_VERSION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def adopt(ctx: ToolContext, drug_id: str, rows: list[dict]) -> list[str]:
    """Only callers holding reconciled rows from proven_acceptance_refs may adopt."""
    drug = next((d for d in ctx.db.entities(ctx.project_id, 'drug') if d['id'] == drug_id), None)
    if drug is None:
        raise ValueError('CDE类别目标不属于当前项目')
    proven = proven_acceptance_refs(ctx, drug)
    if any(row not in proven for row in rows):
        raise ValueError('CDE类别与药物或原始行不一致')
    ids = []
    with ctx.db.tx():
        for row in rows:
            if not row['registration_class']:
                continue  # Blank original fields remain in the capture, not a fabricated scientific category.
            source = ctx.db.one('SELECT * FROM sources WHERE id=? AND project_id=? AND kind=?',
                                (row['source_id'], ctx.project_id, 'cde'))
            if not source:
                raise ValueError('CDE类别来源不属于当前项目')
            raw = ctx.cas.get(source['digest'])
            text = ctx.cas.get_text(source['text_digest'])
            if (hashlib.sha256(raw).hexdigest() != source['digest'] or
                    hashlib.sha256(text.encode()).hexdigest() != source['text_digest']):
                raise ValueError('CDE类别来源字节已改变')
            payload = json.loads(raw)
            paths = [f'$.pages[{p}].rows[{i}][5]' for p, page in enumerate(payload['pages'])
                     for i, cells in enumerate(page['rows']) if cells == row['raw_cells']]
            quote = json.dumps(row['raw_cells'], ensure_ascii=False)
            start = text.find(quote)
            if len(paths) != 1 or start < 0 or text.count(quote) != 1:
                raise ValueError('CDE类别原始行定位不唯一')
            signature = json.dumps([ctx.project_id, drug_id, source['id'], source['digest'], paths[0],
                                    row['raw_cells'], EXTRACTOR_VERSION], ensure_ascii=False)
            fid = 'fct_' + hashlib.sha256(signature.encode()).hexdigest()[:12]
            if not ctx.db.one('SELECT id FROM facts WHERE id=?', (fid,)):
                ctx.db.add_fact({'id': fid, 'project_id': ctx.project_id, 'entity_id': drug_id,
                    'field': FIELD, 'value': row['registration_class'], 'tier': 'critical', 'status': 'verified',
                    'source_id': source['id'], 'quote': quote, 'quote_start': start, 'quote_end': start + len(quote),
                    'context': {'role': 'registration_class', 'source_snapshot': source['digest'],
                        'json_path': paths[0], 'drug_type': row['drug_type'], 'product_name': row['drug_name'],
                        'acceptance_number': row['acceptance_number'], 'application_type': row['application_type'],
                        'company_text': row['company_text'], 'handled_date_text': row['handled_date_text'],
                        'observed_at': source['fetched_at'], 'extractor_version': EXTRACTOR_VERSION},
                    'extracted_by': 'code:cde'})
            ids.append(fid)
    return ids
