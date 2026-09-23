from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from ci_workflow.application.project_service import create_project_workspace
from ci_workflow.domain.contracts import create_project_contract
from ci_workflow.domain.enums import (
    DownloadRequestState,
    FactDisclosureState,
    FactReviewState,
    FormatArtifactState,
    ProjectRunState,
    ReportEvidenceState,
    RevisionApprovalState,
)
from ci_workflow.storage.migrations import (
    MigrationDriftError,
    MigrationSequenceError,
    apply_migrations,
    migration_directory,
)
from ci_workflow.storage.sqlite import open_database

EXPECTED_MIGRATIONS = (
    "0001_project_identity.sql",
    "0002_evidence_claims.sql",
    "0003_gates_snapshots.sql",
    "0004_delivery_workflow.sql",
    "0005_corrections_idempotency.sql",
    "0006_append_only_guards.sql",
    "0007_evidence_audit_chain.sql",
    "0008_project_lineage_guards.sql",
    "0009_source_date_precision.sql",
    "0010_source_text_derivations.sql",
    "0011_candidate_lineage_closure.sql",
    "0012_user_fact_edits.sql",
    "0013_user_refresh_comparisons.sql",
    "0014_current_generation_protocol.sql",
    "0015_evidence_calculation_derivations.sql",
)

EXPECTED_TABLES = {
    "project_contract_versions",
    "project_runs",
    "entities",
    "entity_identifiers",
    "entity_relations",
    "source_versions",
    "source_eligibility_evaluations",
    "refresh_candidates",
    "evidence_fragments",
    "fact_versions",
    "fact_evidence",
    "claim_versions",
    "claim_facts",
    "conflict_sets",
    "gate_evaluations",
    "report_snapshots",
    "coverage_sets",
    "coverage_projections",
    "format_jobs",
    "render_queue",
    "artifact_records",
    "download_requests",
    "correction_proposals",
    "idempotency_keys",
    "content_blobs",
    "source_date_assertions",
    "source_text_derivations",
    "source_acquisition_attempts",
    "evidence_derivations",
    "user_fact_edit_requests",
    "user_fact_derivations",
    "user_refresh_conflicts",
    "current_delivery_generations",
    "current_delivery_state",
}


def test_ordered_migrations_preserve_task_1_3_and_extend_the_truth_store(
    tmp_path: Path,
) -> None:
    assert tuple(path.name for path in sorted(migration_directory().glob("*.sql"))) == (
        EXPECTED_MIGRATIONS
    )
    database_path = tmp_path / "project.sqlite"
    applied = apply_migrations(database_path)
    assert [migration.version for migration in applied] == list(
        range(1, len(EXPECTED_MIGRATIONS) + 1)
    )

    with open_database(database_path) as database:
        tables = {
            row[0]
            for row in database.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert tables >= EXPECTED_TABLES
        assert database.execute("PRAGMA foreign_keys").fetchone() == (1,)
        assert database.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert database.execute("PRAGMA user_version").fetchone() == (len(EXPECTED_MIGRATIONS),)
        recorded = database.execute(
            "SELECT version, name, length(sha256) FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert recorded == [
            (index, name, 64) for index, name in enumerate(EXPECTED_MIGRATIONS, start=1)
        ]

    assert apply_migrations(database_path) == ()


def test_calculation_migration_preserves_old_rows_and_append_only_guards(
    tmp_path: Path,
) -> None:
    old_root = tmp_path / "prior-migrations"
    old_root.mkdir()
    for name in EXPECTED_MIGRATIONS[:-1]:
        shutil.copyfile(migration_directory() / name, old_root / name)
    database_path = tmp_path / "old-project.sqlite"
    apply_migrations(database_path, old_root)
    with open_database(database_path) as database:
        database.execute(
            "INSERT INTO evidence_derivations "
            "(derivation_id,derivation_kind,input_fragment_ids_json,rule_id,"
            "rule_version,output_json,created_at) VALUES (?,?,?,?,?,?,?)",
            ("old-normalization", "normalization", "[]", "old-rule", "1", "{}", "t"),
        )

    assert [item.version for item in apply_migrations(database_path)] == [15]
    with open_database(database_path) as database:
        assert database.execute(
            "SELECT derivation_kind,rule_id FROM evidence_derivations "
            "WHERE derivation_id='old-normalization'"
        ).fetchone() == ("normalization", "old-rule")
        database.execute(
            "INSERT INTO evidence_derivations "
            "(derivation_id,derivation_kind,input_fragment_ids_json,rule_id,"
            "rule_version,output_json,created_at) VALUES (?,?,?,?,?,?,?)",
            ("new-calculation", "calculation", "[]", "rate-rule", "1", "{}", "t"),
        )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            database.execute(
                "UPDATE evidence_derivations SET rule_id='changed' "
                "WHERE derivation_id='old-normalization'"
            )
        assert database.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_migration_sequence_and_applied_digest_drift_fail_closed(tmp_path: Path) -> None:
    database_path = tmp_path / "project.sqlite"
    apply_migrations(database_path)

    drifted = tmp_path / "drifted"
    shutil.copytree(migration_directory(), drifted)
    first = drifted / EXPECTED_MIGRATIONS[0]
    first.write_text(first.read_text(encoding="utf-8") + "\n-- drift\n", encoding="utf-8")
    with pytest.raises(MigrationDriftError, match="摘要"):
        apply_migrations(database_path, drifted)

    incomplete = tmp_path / "incomplete"
    shutil.copytree(migration_directory(), incomplete)
    (incomplete / EXPECTED_MIGRATIONS[2]).unlink()
    with pytest.raises(MigrationSequenceError, match="连续"):
        apply_migrations(tmp_path / "incomplete.sqlite", incomplete)


def test_project_creation_migrates_database_and_persists_contract_version(
    tmp_path: Path,
) -> None:
    contract = create_project_contract(
        indication="类风湿关节炎",
        reports=["A", "C"],
        outputs=["html"],
        timezone="Asia/Shanghai",
        cutoff="2026-08-10",
    )
    project_root = create_project_workspace(tmp_path / "类风湿项目", contract)
    with open_database(project_root / "state/project.sqlite") as database:
        stored = database.execute(
            """
            SELECT project_id, contract_version, timezone, data_cutoff, contract_json
            FROM project_contract_versions
            """
        ).fetchone()
        assert stored is not None
        assert stored[:4] == (
            contract.project_id,
            1,
            "Asia/Shanghai",
            "2026-08-10T23:59:59.999999+08:00",
        )
        assert json.loads(stored[4]) == contract.model_dump(mode="json")


def test_project_scoped_snapshots_gates_and_corrections_reject_orphan_projects(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "lineage.sqlite"
    apply_migrations(database_path)
    orphan_statements = (
        """
        INSERT INTO gate_evaluations (
            gate_evaluation_id, project_id, report_kind, gate_id, result,
            details_json, created_at
        ) VALUES ('gate_orphan', 'project_missing', 'A', 'gate-a', 'failed', '{}', 'now')
        """,
        """
        INSERT INTO report_snapshots (
            snapshot_id, project_id, report_kind, report_version, evidence_state,
            manifest_json, created_at
        ) VALUES ('snapshot_orphan', 'project_missing', 'B', 'v1', 'queued', '{}', 'now')
        """,
        """
        INSERT INTO correction_proposals (
            proposal_id, project_id, state, proposal_json, created_at
        ) VALUES ('proposal_orphan', 'project_missing', 'submitted', '{}', 'now')
        """,
    )
    with open_database(database_path) as database:
        for statement in orphan_statements:
            with pytest.raises(sqlite3.IntegrityError, match="project lineage"):
                database.execute(statement)
        for table in ("gate_evaluations", "report_snapshots", "correction_proposals"):
            assert database.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)


def _seed_state_parents(database: sqlite3.Connection) -> None:
    database.execute(
        """
        INSERT INTO project_contract_versions (
            project_id, contract_version, contract_json, timezone, data_cutoff, created_at
        ) VALUES ('project_test', 1, '{}', 'Asia/Shanghai', '2026-08-10T23:59:59+08:00',
                  '2026-08-11T09:00:00+08:00')
        """
    )
    database.execute(
        "INSERT INTO entities (entity_id, entity_type, canonical_name, created_at) "
        "VALUES ('entity_test', 'drug', '测试药物', '2026-08-11T09:00:00+08:00')"
    )
    database.execute(
        """
        INSERT INTO source_versions (
            source_version_id, source_id, content_sha256, acquired_at, created_at
        ) VALUES ('source_version_test', 'source_test', 'abc',
                  '2026-08-11T09:00:00+08:00', '2026-08-11T09:00:00+08:00')
        """
    )
    database.execute(
        """
        INSERT INTO evidence_fragments (
            fragment_id, source_version_id, locator, content_text, created_at
        ) VALUES ('fragment_test', 'source_version_test', 'p.1', '原文',
                  '2026-08-11T09:00:00+08:00')
        """
    )


def test_state_families_accept_their_exact_values_and_reject_cross_family_values(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "states.sqlite"
    apply_migrations(database_path)
    with open_database(database_path) as database:
        _seed_state_parents(database)
        for index, state in enumerate(ProjectRunState):
            database.execute(
                "INSERT INTO project_runs VALUES (?, 'project_test', 1, ?, ?)",
                (f"run_{index}", state.value, "2026-08-11T09:00:00+08:00"),
            )
        for index, state in enumerate(FactDisclosureState):
            if state is FactDisclosureState.USER_CLEARED:
                # Source fact disclosure and the effective user current layer
                # are distinct: an edit must not rewrite source disclosure.
                continue
            database.execute(
                """
                INSERT INTO fact_versions (
                    fact_version_id, fact_id, entity_id, field_id, raw_value,
                    disclosure_state, review_state, primary_fragment_id, created_at
                ) VALUES (?, ?, 'entity_test', 'efficacy.endpoint', '1', ?, 'candidate',
                          'fragment_test', '2026-08-11T09:00:00+08:00')
                """,
                (f"fact_disclosure_{index}", f"fact_d_{index}", state.value),
            )
        with pytest.raises(sqlite3.IntegrityError, match="disclosure_state"):
            database.execute(
                "INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,"
                "disclosure_state,review_state,primary_fragment_id,created_at) "
                "VALUES ('fact-user-clear','fact-user-clear','entity_test','safety.event',"
                "'user_cleared','user_modified','fragment_test',"
                "'2026-08-11T09:00:00+08:00')"
            )
        for index, state in enumerate(FactReviewState):
            database.execute(
                """
                INSERT INTO fact_versions (
                    fact_version_id, fact_id, entity_id, field_id, raw_value,
                    disclosure_state, review_state, primary_fragment_id, created_at
                ) VALUES (?, ?, 'entity_test', 'safety.event', '1', 'reported_value', ?,
                          'fragment_test', '2026-08-11T09:00:00+08:00')
                """,
                (f"fact_review_{index}", f"fact_r_{index}", state.value),
            )
        for index, state in enumerate(ReportEvidenceState):
            database.execute(
                "INSERT INTO report_snapshots VALUES (?, 'project_test', 'A', ?, ?, '{}', ?)",
                (
                    f"snapshot_{index}",
                    f"v{index + 1}",
                    state.value,
                    "2026-08-11T09:00:00+08:00",
                ),
            )
        database.execute(
            "INSERT INTO report_snapshots VALUES "
            "('snapshot_format', 'project_test', 'B', 'v1', 'snapshot_locked', '{}', "
            "'2026-08-11T09:00:00+08:00')"
        )
        for index, state in enumerate(FormatArtifactState):
            database.execute(
                "INSERT INTO format_jobs VALUES (?, 'snapshot_format', 'html', ?, ?)",
                (f"job_{index}", state.value, "2026-08-11T09:00:00+08:00"),
            )
        database.execute(
            """
            INSERT INTO artifact_records (
                artifact_id, format_job_id, artifact_path, sha256, byte_size, mtime,
                state, created_at
            ) VALUES ('artifact_valid', 'job_0', 'reports/B/v1/report.pdf', 'abc', 3, 1,
                      'queued', '2026-08-11T09:00:00+08:00')
            """
        )
        for index, state in enumerate(DownloadRequestState):
            database.execute(
                "INSERT INTO download_requests VALUES (?, NULL, ?, NULL, ?)",
                (f"download_{index}", state.value, "2026-08-11T09:00:00+08:00"),
            )
        for index, state in enumerate(RevisionApprovalState):
            database.execute(
                "INSERT INTO correction_proposals VALUES (?, 'project_test', ?, '{}', ?)",
                (f"revision_{index}", state.value, "2026-08-11T09:00:00+08:00"),
            )

        invalid_statements = (
            "INSERT INTO project_runs VALUES ('bad_run', 'project_test', 1, 'reported_value', 'x')",
            """INSERT INTO fact_versions (
                fact_version_id, fact_id, entity_id, field_id, disclosure_state,
                review_state, primary_fragment_id, created_at
            ) VALUES ('bad_fact_disclosure', 'bad_d', 'entity_test', 'x', 'running',
                      'candidate', 'fragment_test', 'x')""",
            """INSERT INTO fact_versions (
                fact_version_id, fact_id, entity_id, field_id, disclosure_state,
                review_state, primary_fragment_id, created_at
            ) VALUES ('bad_fact_review', 'bad_r', 'entity_test', 'x', 'reported_value',
                      'running', 'fragment_test', 'x')""",
            "INSERT INTO report_snapshots VALUES "
            "('bad_snapshot', 'project_test', 'A', 'v99', 'generating', '{}', 'x')",
            "INSERT INTO format_jobs VALUES "
            "('bad_job', 'snapshot_format', 'html', 'collecting', 'x')",
            "INSERT INTO download_requests VALUES ('bad_download', NULL, 'published', NULL, 'x')",
            "INSERT INTO correction_proposals VALUES "
            "('bad_revision', 'project_test', 'file_detected', '{}', 'x')",
            """INSERT INTO artifact_records (
                artifact_id, format_job_id, artifact_path, sha256, byte_size, mtime,
                state, created_at
            ) VALUES ('bad_artifact', 'job_0', '/tmp/report.pdf', 'abc', 3, 1,
                      'queued', 'x')""",
            "INSERT INTO download_requests VALUES "
            "('bad_download_path', NULL, 'awaiting_user', '/Users/example/file.pdf', 'x')",
        )
        for statement in invalid_statements:
            with pytest.raises(sqlite3.IntegrityError):
                database.execute(statement)
