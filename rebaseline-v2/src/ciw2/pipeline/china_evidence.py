"""Native CTR design work units; same-run receipts never stand in for new-run checks."""
from __future__ import annotations

import re

from ciw2.pipeline.context import RunContext, work_limit
from ciw2.pipeline.queries import scoped_trials
from ciw2.pipeline.recovery import fingerprint, get_unit, put_unit
from ciw2.sources import china_detail, china_ingest


def collect(rc: RunContext) -> dict:
    trials=sorted((t for t in scoped_trials(rc.db,rc.project_id)
                   if re.fullmatch(r'CTR[0-9]{8}',t['name'])),key=lambda t:t['name'])
    limit=work_limit(rc.cache.get('max_china_trials'))
    started=ingested=0
    pending=[]
    errors=[]
    for trial in trials:
        rc.check_cancelled()
        binding={k:trial['attrs'].get(k) for k in ('registry_detail_id','registry_source_id')}
        key=f'china_trial_ingestion:{china_ingest.EXTRACTOR_VERSION}:{china_detail.code_hash()}:{trial["name"]}:{fingerprint(binding)}'
        info=get_unit(rc,key)
        if info is not None:
            continue
        if limit is not None and started>=limit:
            pending.append({'trial_id':trial['id'],'ctr':trial['name'],'reason':'execution_budget'})
            continue
        started+=1
        try:
            info=china_ingest.ingest_trial(rc.tool_ctx(),trial['name'])
            put_unit(rc,key,info,source_ids=[info['source_id'],*filter(None,[binding['registry_source_id']])])
            ingested+=int(info['facts_added']>0)
            rc.db.log_coverage(rc.run_id,'trial:chinadrugtrials:detail','china',trial['name'],'ok',hits=info['fact_count'])
        except Exception as exc:  # noqa: BLE001 - Isolate a failed external record without losing completed neighbors.
            errors.append(f'{trial["name"]}: {exc}')
            pending.append({'trial_id':trial['id'],'ctr':trial['name'],'reason':'source_ingestion_failed'})
            rc.db.log_coverage(rc.run_id,'trial:chinadrugtrials:detail','china',trial['name'],'failed',note=str(exc)[:300])
    return {'ingested':ingested,'errors':errors,'pending_trials':pending}
