"""One pinned PNH source atom: user edit versus a newly captured source version."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.refresh_service import RefreshService
from ci_workflow.application.user_fact_edit import RefreshFieldState

OLD_SOURCE_VERSION = "fact-version_a876aec36e2678898887b4dd"
USER_VERSION = "fact-version_78ec541f77ee047803e486ea"
NEW_SOURCE_VERSION = "fact-version_fc4fd5ad5d1c3bafae8a3055"
OLD_DB_SHA256 = "fd9ad81d4d7122dbfd3f1c15af75b5c0800ff2ca2de44aca58c0e906b6f5bca1"
NEW_DB_SHA256 = "74330a821f722f22f56174b859cf098f289c6b1bd1f2307789f93e16db56d030"
NEW_RECEIPT_SHA256 = "f6f7bfa8aab3d5635f3b93ebae340d5e8c676bb1ad07b983687699a695275e1b"


def _read_fact(database: Path, version_id: str) -> dict[str, Any]:
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT v.fact_id,v.fact_version_id,v.raw_value,v.normalized_value,"
            "v.entity_id,v.field_id,v.primary_fragment_id,v.scientific_context_json,"
            "f.content_text,f.locator,f.source_version_id "
            "FROM fact_versions v JOIN evidence_fragments f "
            "ON f.fragment_id=v.primary_fragment_id WHERE v.fact_version_id=?",
            (version_id,),
        ).fetchone()
    assert row is not None
    return dict(row)


def _fields(fact: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = json.loads(fact["scientific_context_json"])
    context.pop("user_edit", None)
    for key in ("raw_value", "normalized_value", "entity_id", "field_id",
                "primary_fragment_id"):
        context[key] = fact[key]
    return context


def test_pinned_unchanged_source_keeps_hypothetical_user_edit_in_three_way(
    tmp_path: Path,
) -> None:
    repo = Path(__file__).resolve().parents[2]
    old_db = repo / ".artifacts/r24-pnh-real-ab-20260926/state/project.sqlite"
    new_root = repo / ".artifacts/r24-pnh-refresh-slice-20260926"
    new_db = new_root / "state/project.sqlite"
    receipt_path = new_root / "receipts/r24-46-nct04820530-candidate.json"
    if not all(path.exists() for path in (old_db, new_db, receipt_path)):
        pytest.skip("pinned local CT.gov refresh slice unavailable; no science PASS")
    assert hashlib.sha256(old_db.read_bytes()).hexdigest() == OLD_DB_SHA256
    assert hashlib.sha256(new_db.read_bytes()).hexdigest() == NEW_DB_SHA256
    assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == NEW_RECEIPT_SHA256
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "ingested_candidate_not_reviewed_or_current"
    assert receipt["selected_trials"] == ["nct04820530"]
    assert receipt["source_version_ids"] == ["source-version_73c373185062ea7054e135c8"]
    assert {item["row_ref"]: item["fact_version_id"] for item in receipt["fact_bindings"]}[
        "efficacy:eff-9f54cd0202c1f000619a"
    ] == NEW_SOURCE_VERSION

    base = _read_fact(old_db, OLD_SOURCE_VERSION)
    user = _read_fact(old_db, USER_VERSION)
    fresh = _read_fact(new_db, NEW_SOURCE_VERSION)
    assert base["fact_id"] == user["fact_id"] == fresh["fact_id"]
    assert (base["raw_value"], user["raw_value"], fresh["raw_value"]) == (
        "92.2", "90.1", "92.2",
    )
    assert fresh["content_text"] == "92.2"
    assert fresh["source_version_id"] == receipt["source_version_ids"][0]
    assert "outcomeMeasures[0]" in fresh["locator"]
    assert _fields(base)["result_context"] == _fields(fresh)["result_context"]

    scratch = tmp_path / "comparison-only"
    (scratch / "state").mkdir(parents=True)
    shutil.copyfile(old_db, scratch / "state/project.sqlite")
    result = RefreshService(scratch).compare_user_fact_refresh(
        fact_id=base["fact_id"],
        base_fact_version_id=OLD_SOURCE_VERSION,
        user_fact_version_id=USER_VERSION,
        source_version_id=fresh["source_version_id"],
        source_fields=_fields(fresh),
        source_withdrawn=False,
        request_id="r24-46-pinned-source-user-comparison-development",
        compared_at=datetime(2026, 9, 26, 10, 1, tzinfo=UTC),
        actor_id="development-refresh-test",
    )
    assert result.requires_explicit_resolution is False
    assert result.field_states["raw_value"] is RefreshFieldState.USER_MODIFIED
    assert result.field_states["normalized_value"] is RefreshFieldState.USER_MODIFIED
    assert result.field_states["primary_fragment_id"] is RefreshFieldState.SOURCE_CHANGED
    assert result.user_lineage == (USER_VERSION, OLD_SOURCE_VERSION)
    assert hashlib.sha256(old_db.read_bytes()).hexdigest() == OLD_DB_SHA256
    assert hashlib.sha256(new_db.read_bytes()).hexdigest() == NEW_DB_SHA256
