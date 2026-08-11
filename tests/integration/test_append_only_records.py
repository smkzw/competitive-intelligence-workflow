from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.sqlite import open_database

IMMUTABLE_TABLES = {
    "schema_migrations",
    "project_contract_versions",
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
    "artifact_records",
    "idempotency_keys",
    "content_blobs",
    "source_date_assertions",
}


def _seed_version_chain(database: sqlite3.Connection) -> None:
    database.execute(
        "INSERT INTO project_contract_versions VALUES "
        "('project_test', 1, '{}', 'Asia/Shanghai', '2026-08-10T23:59:59+08:00', 'x')"
    )
    database.execute(
        "INSERT INTO entities VALUES ('entity_test', 'drug', '测试药物', 'x')"
    )
    database.execute(
        "INSERT INTO source_versions "
        "(source_version_id, source_id, content_sha256, acquired_at, created_at) "
        "VALUES ('source_v1', 'source_1', 'abc', 'x', 'x')"
    )
    database.execute(
        "INSERT INTO evidence_fragments "
        "(fragment_id, source_version_id, locator, content_text, created_at) "
        "VALUES ('fragment_1', 'source_v1', 'p.1', '原文', 'x')"
    )
    database.execute(
        """
        INSERT INTO fact_versions (
            fact_version_id, fact_id, entity_id, field_id, raw_value, disclosure_state,
            review_state, primary_fragment_id, created_at
        ) VALUES ('fact_v1', 'fact_1', 'entity_test', 'efficacy.endpoint', '1',
                  'reported_value', 'accepted', 'fragment_1', 'x')
        """
    )
    database.execute(
        """
        INSERT INTO claim_versions (
            claim_version_id, claim_id, claim_text, claim_kind, review_state,
            supersedes_claim_version_id, created_at
        ) VALUES ('claim_v1', 'claim_1', '声明', 'direct_evidence', 'accepted', NULL, 'x')
        """
    )
    database.execute(
        "INSERT INTO report_snapshots VALUES "
        "('snapshot_1', 'project_test', 'A', 'v1', 'snapshot_locked', '{}', 'x')"
    )
    database.execute(
        "INSERT INTO format_jobs VALUES "
        "('job_1', 'snapshot_1', 'pdf', 'passed', 'x')"
    )
    database.execute(
        """
        INSERT INTO artifact_records (
            artifact_id, format_job_id, artifact_path, sha256, byte_size, mtime,
            state, supersedes_artifact_id, created_at
        ) VALUES ('artifact_1', 'job_1', 'reports/A/v1/report.pdf', 'abc', 3, 1,
                  'delivery_ready', NULL, 'x')
        """
    )


def test_version_and_audit_tables_have_update_and_delete_guards(tmp_path: Path) -> None:
    database_path = tmp_path / "append-only.sqlite"
    apply_migrations(database_path)
    with open_database(database_path) as database:
        trigger_rows = database.execute(
            "SELECT tbl_name, name FROM sqlite_master WHERE type = 'trigger'"
        ).fetchall()
        protected = {table for table, _ in trigger_rows}
        assert protected >= IMMUTABLE_TABLES
        for table in IMMUTABLE_TABLES:
            names = {name for trigger_table, name in trigger_rows if trigger_table == table}
            assert any(name.endswith("_no_update") for name in names), table
            assert any(name.endswith("_no_delete") for name in names), table


def test_accepted_records_cannot_be_rewritten_and_corrections_append_new_versions(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "append-only.sqlite"
    apply_migrations(database_path)
    with open_database(database_path) as database:
        _seed_version_chain(database)
        forbidden_changes = (
            "UPDATE project_contract_versions SET timezone = 'UTC'",
            "UPDATE source_versions SET content_sha256 = 'changed'",
            "UPDATE evidence_fragments SET content_text = '改写'",
            "UPDATE fact_versions SET normalized_value = '2'",
            "DELETE FROM claim_versions WHERE claim_version_id = 'claim_v1'",
            "DELETE FROM report_snapshots WHERE snapshot_id = 'snapshot_1'",
            "UPDATE artifact_records SET sha256 = 'changed'",
        )
        for statement in forbidden_changes:
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                database.execute(statement)

        database.execute(
            """
            INSERT INTO fact_versions (
                fact_version_id, fact_id, entity_id, field_id, raw_value, disclosure_state,
                review_state, primary_fragment_id, supersedes_fact_version_id, created_at
            ) VALUES ('fact_v2', 'fact_1', 'entity_test', 'efficacy.endpoint', '2',
                      'reported_value', 'accepted', 'fragment_1', 'fact_v1', 'y')
            """
        )
        database.execute(
            """
            INSERT INTO claim_versions (
                claim_version_id, claim_id, claim_text, claim_kind, review_state,
                supersedes_claim_version_id, created_at
            ) VALUES ('claim_v2', 'claim_1', '新声明', 'direct_evidence', 'accepted',
                      'claim_v1', 'y')
            """
        )
        assert database.execute(
            "SELECT count(*) FROM fact_versions WHERE fact_id = 'fact_1'"
        ).fetchone() == (2,)
        assert database.execute(
            "SELECT count(*) FROM claim_versions WHERE claim_id = 'claim_1'"
        ).fetchone() == (2,)
