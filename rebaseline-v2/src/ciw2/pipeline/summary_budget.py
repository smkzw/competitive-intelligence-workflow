"""Bound expected full-fact tool expansion without trimming observations or source text."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from ciw2.pipeline.context import RunContext

TARGET_CONTEXT_CHARS=24000
MAX_CONTEXT_CHARS=72000  # Full evidence allowance plus the existing 8k narrative/metadata envelope.


def read_costs(rc: RunContext, refs: dict[str,list[str]]) -> dict[str,int]:
    facts={f['id']:f for f in rc.db.current_facts(rc.project_id)}
    costs={}
    for alias,ids in refs.items():
        if len(ids)!=1:raise ValueError('摘要证据引用必须一对一')
        fact=facts.get(ids[0])
        result=({'status':'ok','requested_ref':alias,'fact':fact} if fact else
                {'status':'tool_failed','error':'该事实不属于本项目当前事实集合'})
        costs[alias]=len(json.dumps(result,ensure_ascii=False))+200  # Tool-call envelope, not a scientific value.
    return costs


def context_chars(task: dict[str,Any], costs: dict[str,int]) -> int:
    return len(json.dumps(task,ensure_ascii=False))+sum(costs[a] for a in set(task['verified_fact_ids']))


def _packet(parent: dict[str,Any], records: list[dict]) -> dict[str,Any]:
    return {**parent,'data':{**parent['data'],'candidate_findings':list(records)},
            'verified_fact_ids':sorted({a for row in records for a in row['fact_refs']}),
            'finding_limit':min(6,(len(records)+1)//2)}


def packets(tasks: list[dict], costs: dict[str,int], cached: Callable[[dict],bool]) -> list[dict]:
    planned=[]
    for parent in tasks:
        original=_packet(parent,parent['data']['candidate_findings'])
        if cached(original):
            planned.append(original);continue  # No fact expansion/model call is needed for a qualified receipt.
        pending=[]
        for row in original['data']['candidate_findings']:
            one=_packet(original,[row])
            if context_chars(one,costs)>MAX_CONTEXT_CHARS:
                raise ValueError('单条完整要点的证据上下文超预算；保留原文和已完成单元，不截断事实')
            candidate=_packet(original,[*pending,row])
            if pending and context_chars(candidate,costs)>TARGET_CONTEXT_CHARS:
                planned.append(_packet(original,pending));pending=[]
            pending.append(row)
        if pending:planned.append(_packet(original,pending))
    return planned
