"""Recheck already-discovered certificates, then adopt exact source identities."""
from __future__ import annotations

import json

from ciw2.pipeline.context import RunContext
from ciw2.sources import nmpa_detail, nmpa_ingest


def _close_names(rc: RunContext, unresolved: list[dict], pending: list[dict], errors: list[str]) -> tuple[list[dict],int]:
    """Finite same-source fixed point: each useful pass removes a pending identity."""
    added=0
    while unresolved:
        remaining=[]
        for previous in unresolved:
            rc.check_cancelled()
            try:
                info=nmpa_ingest.activate_source(rc.tool_ctx(),previous['source_id'])
                added+=int(info.get('facts_added',0)>0)
                if info['status']=='unresolved':remaining.append(info)
            except Exception as exc:  # noqa: BLE001 - A broken proof does not erase accepted neighbors.
                pending.append({'source_id':previous['source_id'],'reason':'source_identity_failed'})
                errors.append(f"{previous['source_id']}: {exc}")
        if len(remaining)==len(unresolved):
            return remaining,added
        unresolved=remaining
    return [],added


def collect(rc: RunContext) -> dict:
    requests={}
    errors=[]
    pending=[]
    for source in rc.db.query("SELECT id,url,meta FROM sources WHERE project_id=? AND kind='nmpa'",
                              (rc.project_id,)):
        try:
            meta=json.loads(source['meta'])
            if not isinstance(meta,dict) or not isinstance(meta.get('request_context'),dict):
                raise TypeError('许可来源请求结构无效')
            scope=meta['request_context']
            if scope.get('tool')!='nmpa_product_detail' or scope.get('project_id')!=rc.project_id:
                raise ValueError('许可来源请求不属于当前项目')
            key=(source['url'],scope['registration_number'],scope['category'])
            nmpa_detail._record(source['url'])
            requests[key]=None
        except (ValueError,KeyError,TypeError) as exc:
            pending.append({'source_id':source['id'],'reason':'source_request_invalid'})
            errors.append(f"{source['id']}: {exc}")
    adopted=0
    made_progress=False
    unresolved=[]
    source_ids=[]
    for url,number,category in sorted(requests):
        rc.check_cancelled()
        try:
            result=nmpa_detail.browser_detail(rc.tool_ctx(),url,number,category)
            info=nmpa_ingest.activate_source(rc.tool_ctx(),result['source_id'])
            source_ids.append(result['source_id'])
            adopted+=int(info.get('facts_added',0)>0)
            made_progress=made_progress or info['status']=='adopted'
            if info['status']=='unresolved':
                unresolved.append(info)
            rc.db.log_coverage(rc.run_id,'identity:nmpa:certificate','china',number,'ok',
                hits=info.get('facts_added',0),note=info['status'])
        except Exception as exc:  # noqa: BLE001 - A failed certificate cannot erase other completed records.
            pending.append({'registration_number':number,'reason':'source_identity_failed'})
            errors.append(f'{number}: {exc}')
            rc.db.log_coverage(rc.run_id,'identity:nmpa:certificate','china',number,'failed',note=str(exc)[:300])
    if made_progress and unresolved:
        unresolved,closed=_close_names(rc,unresolved,pending,errors)
        adopted+=closed
    return {'adopted':adopted,'source_ids':source_ids,'unresolved':unresolved,'pending_records':pending,'errors':errors}
