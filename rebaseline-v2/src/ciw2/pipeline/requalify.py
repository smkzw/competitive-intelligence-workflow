"""离线现行规则复核：只对当前 LLM 已核实事实追加裁决回执。

不新增事实、不改事实/引文/来源/修订链接、不提升任何旧 unverified/conflict/unknown，
不调用模型、网络或浏览器。dry-run 只统计，不写 agent_steps。
"""
from __future__ import annotations

from typing import Any

from ciw2.store.cas import CAS
from ciw2.store.db import DB
from ciw2.verify import assessment

COUNT_KEYS = ('scanned', 'confirmed', 'invalidated', 'missing_quote', 'source_unpinned',
              'source_unavailable', 'source_unreadable', 'source_digest_mismatch', 'skipped', 'errors')


def requalify_project(db: DB, cas: CAS, project_id: str, *, dry_run: bool = False,
                      rule: str | None = None) -> dict[str, Any]:
    if db.project(project_id) is None:
        raise KeyError(project_id)
    current_rule=assessment.rule_identity()
    if rule is not None and rule!=current_rule:
        raise ValueError('离线复核只执行当前实际规则，不为任意版本签发回执')
    rule=current_rule
    targets = [row for row in db.raw_current_facts(project_id)
               if str(row.get('extracted_by') or '').startswith('llm:') and row['status'] == 'verified']
    latest = db.latest_verdicts(project_id, rule)
    counts = dict.fromkeys(COUNT_KEYS, 0)
    prepared=[]
    for row in targets:
        counts['scanned'] += 1
        try:
            result = assessment.inspect_fact(db,cas,row)
        except Exception:  # noqa: BLE001 - 单条读取异常不能中断整个项目复核
            counts['errors'] += 1
            continue
        counts[result['verdict']] += 1
        receipt = assessment.make_receipt(row, rule=rule, stored_status='verified', result=result)
        prepared.append(receipt)
        if dry_run:
            counts['skipped']+=int(assessment.same_receipt(latest.get(row['id']),receipt))
            continue
    if not dry_run:
        with db.tx(immediate=True):
            latest=db.latest_verdicts(project_id,rule)
            current={row['id']:row for row in db.raw_current_facts(project_id)}
            for receipt in prepared:
                row=current.get(receipt['fact_id'])
                if row is None or not assessment.receipt_matches(receipt,row,db=db):
                    counts[receipt['verdict']]-=1
                    counts['errors']+=1
                    continue
                if assessment.same_receipt(latest.get(receipt['fact_id']),receipt):
                    counts['skipped']+=1
                    continue
                db.log_step(None,'requalification','verify',0,assessment.ROLE,receipt)
                latest[receipt['fact_id']]=receipt
    return {'schema_version': 'ciw2-requalify-v1', 'project_id': project_id, 'rule': rule,
            'dry_run': dry_run, 'counts': counts}
