"""Read-only bridge may suggest an A match, never move a current user edit."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_current_a_refresh_bridge import (
    BridgeAuditError,
    _pinned_input_digests,
    _tool_identity,
    _verified_source_epoch,
    assess_refresh_bridge,
    read_current_bindings,
)


def _atom(row_id: str, value: str, page: str) -> dict[str, str]:
    value_path = (
        "$.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0]"
        ".categories[0].measurements[0].value"
    )
    return {
        "trial_id": "nct04820530",
        "value_path": value_path,
        "domain": "efficacy",
        "raw_value": value,
        "raw_value_type": "str",
        "raw_unit": "percentage",
        "outcome_title": "Hemoglobin Response",
        "group_id": "OG1",
        "source_page_sha256": page,
        "row_id": row_id,
    }


def _binding(report: str, row_id: str) -> dict[str, str]:
    return {
        "source_fact_version_id": "fact-version-source",
        "evidence_snapshot_id": "evidence-snapshot_" + "a" * 24,
        "report": report,
        "collection": "efficacy",
        "row_id": row_id,
    }


def test_exact_a_candidate_keeps_b_and_user_revision_blocked() -> None:
    before = {"row_source_map": [_atom("eff-1", "92.2", "old-page")]}
    after = {"row_source_map": [_atom("eff-stable", "92.2", "new-page")]}
    result = assess_refresh_bridge(
        before, after,
        [_binding("A", "eff-1"), _binding("B", "eff-1")],
        [{"target_fact_version_id": "fact-version-source",
          "result_fact_version_id": "fact-version-user"}],
        {"revision": 1, "generation_sha256": "a" * 64},
        expected_generation_sha256="a" * 64,
    )
    assert result["safe_to_switch_current"] is False
    assert result["counts"]["a_exact_path_candidates"] == 1
    assert result["counts"]["other_reports_rebuild_required"] == 1
    assert result["counts"]["user_edits_requiring_three_way_merge"] == 1
    assert result["bindings"][0]["new_row_id"] == "eff-stable"
    assert result["bindings"][0]["source_page_changed"] is True
    assert result["bindings"][1]["new_row_id"] is None
    assert result["user_edits"][0]["bound_reports"] == ["A", "B"]


def test_changed_atom_duplicate_old_row_and_generation_mismatch_fail_closed() -> None:
    before = {"row_source_map": [_atom("eff-1", "92.2", "old-page")]}
    changed = {"row_source_map": [_atom("eff-stable", "93.0", "new-page")]}
    result = assess_refresh_bridge(
        before, changed, [_binding("A", "eff-1")], [],
        {"revision": 0, "generation_sha256": "b" * 64},
        expected_generation_sha256="b" * 64,
    )
    assert result["bindings"][0]["status"] == "source_changed_review"
    assert result["bindings"][0]["new_row_id"] is None
    with pytest.raises(BridgeAuditError, match="duplicate old row_id"):
        assess_refresh_bridge(
            {"row_source_map": [before["row_source_map"][0],
                                {**before["row_source_map"][0], "value_path": "$.other.value"}]},
            changed, [_binding("A", "eff-1")], [],
            {"revision": 0, "generation_sha256": "b" * 64},
            expected_generation_sha256="b" * 64,
        )
    with pytest.raises(BridgeAuditError, match="generation"):
        assess_refresh_bridge(
            before, changed, [_binding("A", "eff-1")], [],
            {"revision": 0, "generation_sha256": "b" * 64},
            expected_generation_sha256="c" * 64,
        )
    wrong_domain = assess_refresh_bridge(
        before, before, [{**_binding("A", "eff-1"), "collection": "safety"}], [],
        {"revision": 0, "generation_sha256": "b" * 64},
        expected_generation_sha256="b" * 64,
    )
    assert wrong_domain["bindings"][0]["status"] == "old_source_row_unresolved"

    observation = {**_atom("other-1", "3.2", "old"),
                   "domain": "additional_observations"}
    matching_observation = assess_refresh_bridge(
        {"row_source_map": [observation]},
        {"row_source_map": [{**observation, "row_id": "other-new"}]},
        [{**_binding("A", "other-1"), "collection": "observations"}], [],
        {"revision": 0, "generation_sha256": "b" * 64},
        expected_generation_sha256="b" * 64,
    )
    assert matching_observation["bindings"][0]["status"] == (
        "exact_path_candidate_not_accepted"
    )
    with pytest.raises(BridgeAuditError, match="unknown source atom field"):
        assess_refresh_bridge(
            {"row_source_map": [{**before["row_source_map"][0],
                                 "new_analysis_set": "unknown scientific context"}]},
            changed, [_binding("A", "eff-1")], [],
            {"revision": 0, "generation_sha256": "b" * 64},
            expected_generation_sha256="b" * 64,
        )


def test_frozen_inputs_and_both_code_modules_are_pinned(tmp_path: Path) -> None:
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    database = tmp_path / "project.sqlite"
    old.write_bytes(b"old")
    new.write_bytes(b"new")
    database.write_bytes(b"db")
    paths = {"old_sidecar": old, "new_sidecar": new, "project_db": database}
    expected = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in paths.items()}
    assert _pinned_input_digests(paths, expected) == expected
    with pytest.raises(BridgeAuditError, match="old_sidecar.*digest mismatch"):
        _pinned_input_digests(paths, {**expected, "old_sidecar": "0" * 64})
    with pytest.raises(BridgeAuditError, match="project_db.*digest mismatch"):
        _pinned_input_digests(paths, {**expected, "project_db": "0" * 64})
    identity = _tool_identity()
    assert set(identity) == {"audit_tool_sha256", "delta_tool_sha256"}
    assert all(len(digest) == 64 for digest in identity.values())


def test_old_sidecar_and_bindings_require_same_pinned_source_epoch(
    tmp_path: Path,
) -> None:
    project_db = tmp_path / "state/project.sqlite"
    project_db.parent.mkdir()
    project_db.write_bytes(b"db")
    snapshot_id = "evidence-snapshot_" + "a" * 24
    snapshot = tmp_path / "snapshots/evidence" / f"{snapshot_id}.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(b'{"fixed":"snapshot"}')
    old_digest = hashlib.sha256(b"old sidecar").hexdigest()
    receipt = tmp_path / "epoch-receipt.json"
    receipt.write_text(json.dumps({"source": {
        "sidecar_sha256": old_digest,
        "snapshot_id": snapshot_id,
        "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
    }}), encoding="utf-8")
    receipt_digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
    binding = _binding("A", "eff-1")
    verified = _verified_source_epoch(
        receipt, receipt_digest, project_db, old_digest, [binding],
    )
    assert verified["evidence_snapshot_id"] == snapshot_id
    assert verified["snapshot_sha256"] == hashlib.sha256(snapshot.read_bytes()).hexdigest()
    with pytest.raises(BridgeAuditError, match="old sidecar.*epoch"):
        _verified_source_epoch(receipt, receipt_digest, project_db, "0" * 64, [binding])
    with pytest.raises(BridgeAuditError, match="binding.*snapshot"):
        _verified_source_epoch(
            receipt, receipt_digest, project_db, old_digest,
            [{**binding, "evidence_snapshot_id": "evidence-snapshot_" + "b" * 24}],
        )
    with pytest.raises(BridgeAuditError, match="receipt digest"):
        _verified_source_epoch(receipt, "0" * 64, project_db, old_digest, [binding])
    snapshot.write_bytes(b'{"altered":"snapshot"}')
    with pytest.raises(BridgeAuditError, match="snapshot digest"):
        _verified_source_epoch(receipt, receipt_digest, project_db, old_digest, [binding])


def test_database_reader_is_pinned_and_read_only(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite"
    generation = {"active_fact_version_ids": ["fact-version-user-2"]}
    generation_text = json.dumps(generation)
    generation_hash = hashlib.sha256(generation_text.encode()).hexdigest()
    with sqlite3.connect(database) as connection:
        connection.executescript(
            "CREATE TABLE current_delivery_state (revision INTEGER, generation_sha256 TEXT);"
            "CREATE TABLE current_delivery_generations (generation_sha256 TEXT,"
            "bundle_json TEXT);"
            "CREATE TABLE source_portal_consumer_bindings (source_fact_version_id TEXT,"
            "evidence_snapshot_id TEXT, report TEXT, collection TEXT, row_id TEXT);"
            "CREATE TABLE user_fact_edit_requests (target_fact_version_id TEXT,"
            "result_fact_version_id TEXT, status TEXT);"
            "CREATE TABLE fact_versions (fact_version_id TEXT,"
            "supersedes_fact_version_id TEXT);"
            "INSERT INTO source_portal_consumer_bindings VALUES"
            "('fact-version-source','evidence-snapshot_aaaaaaaaaaaaaaaaaaaaaaaa',"
            "'A','efficacy','eff-1');"
            "INSERT INTO source_portal_consumer_bindings VALUES"
            "('fact-version-old','evidence-snapshot_aaaaaaaaaaaaaaaaaaaaaaaa',"
            "'A','efficacy','eff-legacy');"
            "INSERT INTO user_fact_edit_requests VALUES"
            "('fact-version-source','fact-version-user','complete');"
            "INSERT INTO user_fact_edit_requests VALUES"
            "('fact-version-user','fact-version-user-2','complete');"
        )
        connection.execute("INSERT INTO current_delivery_state VALUES (?,?)",
                           (1, generation_hash))
        connection.execute("INSERT INTO current_delivery_generations VALUES (?,?)",
                           (generation_hash, generation_text))
    current, bindings, edits = read_current_bindings(database)
    assert current == {"revision": 1, "generation_sha256": generation_hash}
    assert bindings == [_binding("A", "eff-1")]
    assert edits == [
        {"target_fact_version_id": "fact-version-source",
         "result_fact_version_id": "fact-version-user"},
        {"target_fact_version_id": "fact-version-user",
         "result_fact_version_id": "fact-version-user-2"},
    ]
    assessment = assess_refresh_bridge(
        {"row_source_map": [_atom("eff-1", "92.2", "old")]},
        {"row_source_map": [_atom("eff-new", "92.2", "new")]},
        bindings, edits, current, expected_generation_sha256=generation_hash,
    )
    assert [item["bound_reports"] for item in assessment["user_edits"]] == [
        ["A"], ["A"],
    ]
    database.with_name(database.name + "-wal").write_bytes(b"not safe to ignore")
    with pytest.raises(BridgeAuditError, match="WAL"):
        read_current_bindings(database)
    database.with_name(database.name + "-wal").unlink()
    refreshed = {"active_fact_version_ids": ["fact-version-source-refresh"]}
    refreshed_text = json.dumps(refreshed)
    refreshed_hash = hashlib.sha256(refreshed_text.encode()).hexdigest()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO fact_versions VALUES (?,?)",
            ("fact-version-source-refresh", "fact-version-source"),
        )
        connection.execute("DELETE FROM current_delivery_state")
        connection.execute("INSERT INTO current_delivery_state VALUES (?,?)",
                           (2, refreshed_hash))
        connection.execute("INSERT INTO current_delivery_generations VALUES (?,?)",
                           (refreshed_hash, refreshed_text))
    with pytest.raises(BridgeAuditError, match="non-edit supersedes"):
        read_current_bindings(database)


def test_fixed_real_refresh_bridge_replays_only_candidate_counts() -> None:
    repository = Path(__file__).resolve().parents[2]
    relative_paths = {
        "old_sidecar": ".artifacts/r24-pnh-candidate-20260926/"
        "report-a-r24-14-final.derivation.json",
        "new_sidecar": ".artifacts/r24-pnh-current-ctgov-20260926/"
        "report-a-ctgov-20260926-sponsor-separate-v5.derivation.json",
        "project_db": ".artifacts/r24-pnh-real-ab-20260926/state/project.sqlite",
        "source_epoch_receipt": "packets/2026-09-22-sol-delivery/evidence/"
        "0924V1-r24/r24-23-real-a-b-development-chain.json",
    }
    paths = {name: repository / relative for name, relative in relative_paths.items()}
    if any(not path.is_file() for path in paths.values()):
        pytest.skip("fixed offline source project is absent; no real replay was run")
    expected = {
        "old_sidecar": "2cbba015597af4cefbd1fb8104fc7c00e33563fdf515350d4e9046b955d0ad09",
        "new_sidecar": "0ef8a7275bab87eccc4e0a296744b8ae624a0771ca1d082300a1fa081b78d655",
        "project_db": "fd9ad81d4d7122dbfd3f1c15af75b5c0800ff2ca2de44aca58c0e906b6f5bca1",
        "source_epoch_receipt": "88a55d3657879756908f81e562231e04fcf65e5d70ea9bc82a994932a202298b",
    }
    assert _pinned_input_digests(paths, expected) == expected
    current, bindings, edits = read_current_bindings(paths["project_db"])
    epoch = _verified_source_epoch(
        paths["source_epoch_receipt"], expected["source_epoch_receipt"],
        paths["project_db"], expected["old_sidecar"], bindings,
    )
    assert epoch["evidence_snapshot_id"] == (
        "evidence-snapshot_68fd97a331040c3637068faf"
    )
    assessed = assess_refresh_bridge(
        json.loads(paths["old_sidecar"].read_text(encoding="utf-8")),
        json.loads(paths["new_sidecar"].read_text(encoding="utf-8")),
        bindings, edits, current,
        expected_generation_sha256=(
            "9d31c4a28ceabfd131a2d4ecd28b4a560b4f3d9fec31be79209372519f564d3c"
        ),
    )
    assert assessed["safe_to_switch_current"] is False
    assert assessed["counts"] == {
        "a_exact_path_candidates": 18,
        "a_source_changed_review": 0,
        "a_unresolved": 0,
        "other_reports_rebuild_required": 1,
        "user_edits_requiring_three_way_merge": 1,
    }
