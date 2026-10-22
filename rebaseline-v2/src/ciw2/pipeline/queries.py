"""Shared project-scoped pipeline queries; no research or identity decisions."""
from __future__ import annotations

from typing import Any

from ciw2.pipeline.context import RunContext


def intake_data(rc: RunContext) -> dict[str, Any]:
    return rc.db.stage_output(rc.run_id, 'intake') or {
        'indication': rc.project['indication'], 'indication_en': '', 'aliases': []}


def scoped_drugs(rc: RunContext) -> list[dict[str, Any]]:
    return [drug for drug in rc.db.entities(rc.project_id, 'drug') if drug['in_scope'] != 0]


def drug_trials(rc: RunContext, drug_id: str) -> list[dict[str, Any]]:
    ids = {r['dst'] for r in rc.db.query(
        "SELECT dst FROM links WHERE project_id=? AND src=? AND rel='drug-trial'", (rc.project_id, drug_id))}
    return [trial for trial in rc.db.entities(rc.project_id, 'trial') if trial['id'] in ids]
