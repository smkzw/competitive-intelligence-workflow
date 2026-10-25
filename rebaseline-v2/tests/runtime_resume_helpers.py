"""Small temporary DB helpers shared by stage runtime acceptance cases."""
from __future__ import annotations

import json

from ciw2.harness.llm import ScriptedLLM
from ciw2.pipeline import runner, stage_versions
from ciw2.pipeline.stages import Stage
from ciw2.service import Service


def service(settings) -> Service:
    return Service(settings, llm_factory=lambda s: (ScriptedLLM([]), None))


def plan(settings, monkeypatch, stages: list[Stage]) -> Service:
    monkeypatch.setattr(runner, 'STAGES', stages)
    return service(settings)


def receipts(svc: Service, run_id: str, stage: str | None = None) -> list[dict]:
    rows = svc.db.query(
        "SELECT * FROM stages WHERE run_id=? AND name LIKE ? ORDER BY rowid",
        (run_id, stage_versions.RECEIPT_PREFIX + '%'))
    out = []
    for row in rows:
        value = json.loads(row['output_json'])
        if stage is None or value['stage'] == stage:
            out.append({'row': row, 'receipt': value})
    return out


def status(svc: Service, run_id: str) -> str:
    return svc.db.one("SELECT status FROM runs WHERE id=?", (run_id,))['status']


def snapshot(svc: Service) -> list[dict]:
    return svc.db.query(
        "SELECT name, status, output_json, error FROM stages ORDER BY name")
