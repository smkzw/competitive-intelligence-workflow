"""Batch already-proven application IDs against the four observed public scopes."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ciw2.pipeline.context import RunContext
from ciw2.pipeline.queries import scoped_drugs
from ciw2.pipeline.recovery import fingerprint, get_unit, put_unit
from ciw2.sources import cde_priority, cde_review_browser
from ciw2.sources.cde_review_capture import SCOPES, parse_review_capture


def _applications(rc: RunContext, ctx, pending: list[dict]) -> list[dict]:
    refs=[]
    for drug in scoped_drugs(rc):
        claimed=drug['attrs'].get('cde_acceptance_refs',[])
        proven=cde_review_browser.proven_acceptance_refs(ctx,drug)
        refs.extend({'drug_id':drug['id'],**ref} for ref in proven)
        accepted={(r['source_id'],r['acceptance_number']) for r in proven}
        if any(not isinstance(r,dict) or (r.get('source_id'),r.get('acceptance_number')) not in accepted for r in claimed):
            pending.append({'kind':'cde_application','drug_id':drug['id'],'reason':'unproven_application_binding'})
    return sorted(refs,key=lambda r:(r['drug_id'],r['acceptance_number'],r['source_id']))


def _directory(ctx, section: str) -> dict:
    if section in cde_priority.SECTIONS:
        pages,sid=cde_priority._scope(ctx,section=section)
        parsed=cde_priority.parse_capture(pages,section=section)
    else:
        filters=dict(SCOPES[section]);pages,sid=cde_review_browser._scope(ctx,filters)
        parsed=parse_review_capture(pages,filters=filters)
    return {**parsed,'source_id':sid,'results':[{**r,'source_id':sid} for r in parsed['results']]}


def collect(rc: RunContext) -> dict:
    ctx=rc.tool_ctx();pending=[];errors=[];completed=[]
    refs=_applications(rc,ctx,pending)
    if not refs:return {'completed':completed,'errors':errors,'pending_trials':pending}
    wanted={r['acceptance_number'] for r in refs}
    signature=fingerprint(refs)
    code=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for section in (*SCOPES,*cde_priority.SECTIONS):
        rc.check_cancelled()
        version=cde_priority._code_hash() if section in cde_priority.SECTIONS else cde_review_browser._code_hash()
        key=f'cde_directory:{section}:{code}:{version}:{signature}'
        cached=get_unit(rc,key)
        if cached is not None:
            completed.append(cached);continue
        try:
            result=_directory(ctx,section)
            result['results']=[row for row in result['results'] if row['acceptance_number'] in wanted]
            attribute={'priority_included':'cde_priority_refs','priority_proposed':'cde_priority_proposed_refs'}.get(section,'cde_review_refs')
            linked=cde_review_browser.persist_refs(ctx,result,'trial:cde:'+section,ref_attribute=attribute)
            info={'section':section,'source_id':result['source_id'],'acceptance_numbers':sorted(wanted),
                  'matched_count':len(result['results']),'linked_refs':linked,'complete':True}
            put_unit(rc,key,info,source_ids=[result['source_id'],*(r['source_id'] for r in refs)])
            completed.append(info)
            rc.db.log_coverage(rc.run_id,'trial:cde:'+section,'china',','.join(sorted(wanted)),
                               'ok',hits=len(result['results']))
        except Exception as exc:  # noqa: BLE001 - One unavailable directory must not erase neighboring evidence.
            pending.append({'kind':'cde_directory','section':section,'acceptance_numbers':sorted(wanted),
                            'reason':'source_directory_failed'})
            errors.append(f'{section}: {exc}')
            rc.db.log_coverage(rc.run_id,'trial:cde:'+section,'china',','.join(sorted(wanted)),
                               'failed',note=str(exc)[:300])
    return {'completed':completed,'errors':errors,'pending_trials':pending}
