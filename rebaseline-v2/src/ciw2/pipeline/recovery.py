"""Source-bound same-run work receipts, using the existing stages table only."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from ciw2.pipeline.context import RunContext
from ciw2.sources.http import public_url, source_by_url


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _version(row: dict[str, Any] | None, url: str) -> dict[str, Any]:
    version = {'url': url, **{key: row.get(key) if row else None for key in ('id', 'digest', 'text_digest')}}
    context = json.loads(row['meta']).get('request_context') if row else None
    if context is not None:
        version['request_context'] = context
    return version


def _representation_current(rc: RunContext,row: dict[str,Any] | None) -> bool:
    if row is None:return True
    meta=json.loads(row['meta'])
    if 'pdf' not in meta.get('content_type','').casefold() and not meta.get('text_parser_id'):
        return True
    from ciw2.sources.pdf_text import PDFTextError, parser_identity
    try:
        if not row.get('text_digest') or meta.get('text_parser_id')!=parser_identity():return False
        raw=rc.cas.get(row['digest']);text=rc.cas.get(row['text_digest'])
    except (PDFTextError,OSError):return False
    return hashlib.sha256(raw).hexdigest()==row['digest'] and hashlib.sha256(text).hexdigest()==row['text_digest']


def get_unit(rc: RunContext, key: str) -> Any:
    cached = rc.db.stage_output(rc.run_id, key)
    if cached is None:
        return None
    ctx = rc.tool_ctx()
    for source in cached['sources']:
        row=source_by_url(ctx,source['url'],request_context=source.get('request_context'))
        if _version(row,source['url'])!=source or not _representation_current(rc,row):return None
    rc.db.log_step(rc.run_id, rc.stage, rc.stage, 0, 'cache', {'reused_stage': key})
    return cached['result']


def put_unit(rc: RunContext, key: str, result: Any, *, source_ids: Iterable[str] = (),
             urls: Iterable[str] = ()) -> None:
    sources = []
    for sid in sorted(set(source_ids)):
        row = rc.db.one('SELECT * FROM sources WHERE project_id=? AND id=?', (rc.project_id, sid))
        if row:
            sources.append(_version(row, row['url']))
    ctx = rc.tool_ctx()
    for url in sorted({public_url(url) for url in urls} - {source['url'] for source in sources}):
        sources.append(_version(source_by_url(ctx, url), url))
    rc.db.set_stage(rc.run_id, key, 'succeeded', output={'result': result, 'sources': sources})
