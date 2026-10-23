"""Shared project-scoped pipeline queries; no research or identity decisions."""
from __future__ import annotations

from typing import Any

from ciw2.pipeline.context import RunContext
from ciw2.store.db import DB


def intake_data(rc: RunContext) -> dict[str, Any]:
    return rc.db.stage_output(rc.run_id, 'intake') or {
        'indication': rc.project['indication'], 'indication_en': '', 'aliases': []}


def scoped_drugs(rc: RunContext) -> list[dict[str, Any]]:
    return [drug for drug in rc.db.entities(rc.project_id, 'drug') if drug['in_scope'] != 0]


def scoped_trials(db: DB, pid: str) -> list[dict[str, Any]]:
    """Exclude explicit trial/all-parent exclusions; unknown and orphan records remain."""
    drugs={d['id']:d['in_scope'] for d in db.entities(pid,'drug')}
    parents: dict[str,set[str]]={}
    for edge in db.query("SELECT src,dst FROM links WHERE project_id=? AND rel='drug-trial'",(pid,)):
        if edge['src'] in drugs:
            parents.setdefault(edge['dst'],set()).add(edge['src'])
    return [t for t in db.entities(pid,'trial') if t['in_scope']!=0 and
            (not parents.get(t['id']) or any(drugs[d]!=0 for d in parents[t['id']]))]


def drug_trials(rc: RunContext, drug_id: str) -> list[dict[str, Any]]:
    ids = {r['dst'] for r in rc.db.query(
        "SELECT dst FROM links WHERE project_id=? AND src=? AND rel='drug-trial'", (rc.project_id, drug_id))}
    return [trial for trial in scoped_trials(rc.db,rc.project_id) if trial['id'] in ids]
