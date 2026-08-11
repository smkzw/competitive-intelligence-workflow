from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.migrations import apply_migrations
from ci_workflow.storage.sqlite import open_database

ROOT = Path(__file__).resolve().parents[2]


def _reported(value: str, locator: EvidenceLocator) -> DateEvidence:
    return DateEvidence(state="reported", value=value, locator=locator)


def test_source_version_separates_acquired_published_effective_and_first_disclosed_dates(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    page_locator = EvidenceLocator(document_role="registry", page=1, paragraph="Study Overview")
    label_locator = EvidenceLocator(document_role="label", page=2, table="批准信息")

    first = repository.add_source_version(
        source_id="source_nct01234567",
        content=b"registry version 2025-01-01",
        media_type="text/html",
        acquired_at=datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        published_at=_reported("2025-01-01T09:00:00-05:00", page_locator),
        effective_at=DateEvidence(
            state="not_publicly_disclosed", value=None, locator=label_locator
        ),
        first_disclosed_at=_reported("2025-01-01T09:00:00-05:00", page_locator),
    )
    duplicate_later_download = repository.add_source_version(
        source_id="source_nct01234567",
        content=b"registry version 2025-01-01",
        media_type="text/html",
        acquired_at=datetime(2026, 8, 12, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        published_at=_reported("2025-01-01T09:00:00-05:00", page_locator),
        effective_at=DateEvidence(
            state="not_publicly_disclosed", value=None, locator=label_locator
        ),
        first_disclosed_at=_reported("2025-01-01T09:00:00-05:00", page_locator),
    )
    changed = repository.add_source_version(
        source_id="source_nct01234567",
        content=b"registry version 2026-08-01",
        media_type="text/html",
        acquired_at=datetime(2026, 8, 12, 9, 5, tzinfo=ZoneInfo("Asia/Shanghai")),
        published_at=_reported("2026-08-01T09:00:00-04:00", page_locator),
        effective_at=DateEvidence(state="not_applicable", value=None, locator=page_locator),
        first_disclosed_at=_reported("2026-08-01T09:00:00-04:00", page_locator),
    )

    assert duplicate_later_download.source_version_id == first.source_version_id
    assert duplicate_later_download.acquired_at == first.acquired_at
    assert changed.source_version_id != first.source_version_id
    assert first.published_at.value is not None
    assert first.published_at.value.utcoffset() is not None
    assert first.effective_at.state == "not_publicly_disclosed"
    assert first.effective_at.value is None

    with open_database(database_path) as database:
        versions = database.execute(
            "SELECT source_version_id, acquired_at, published_at, effective_at, "
            "first_disclosed_at FROM source_versions ORDER BY created_at"
        ).fetchall()
        assert len(versions) == 2
        assert versions[0][1] == "2026-08-11T10:00:00+08:00"
        assert versions[0][3] is None
        assertions = database.execute(
            "SELECT date_role, disclosure_state, observed_at, timezone, date_precision, "
            "locator_json "
            "FROM source_date_assertions WHERE source_version_id = ? ORDER BY date_role",
            (first.source_version_id,),
        ).fetchall()
        assert {row[0] for row in assertions} == {
            "acquired_at",
            "effective_at",
            "first_disclosed_at",
            "published_at",
        }
        assert all(row[3] for row in assertions)
        assert all(row[4] == "instant" for row in assertions)
        assert all(json.loads(row[5]) for row in assertions)


def test_fragment_locator_returns_to_field_page_table_or_paragraph_and_fact_needs_original(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    database_path = project_root / "state/project.sqlite"
    apply_migrations(database_path)
    repository = EvidenceRepository(database_path, ContentAddressedStore(project_root))
    locator = EvidenceLocator(
        document_role="registry-results",
        field_path="protocolSection.outcomesModule.primaryOutcomes[0]",
        page=4,
        table="Primary Outcome Measures",
        paragraph="Change from baseline at Week 24",
    )
    source = repository.add_source_version(
        source_id="source_nct00000001",
        content=b"full registry source",
        media_type="text/html",
        acquired_at=datetime(2026, 8, 11, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        published_at=DateEvidence(state="not_applicable", value=None, locator=locator),
        effective_at=DateEvidence(state="not_applicable", value=None, locator=locator),
        first_disclosed_at=_reported("2026-01-01T00:00:00+00:00", locator),
    )
    fragment = repository.add_fragment(
        source_version_id=source.source_version_id,
        locator=locator,
        original_text="第24周主要终点较基线变化：治疗组 -2.1，对照组 -0.8。",
    )

    assert repository.read_fragment(fragment.fragment_id) == fragment
    assert fragment.locator.field_path is not None
    assert fragment.locator.page == 4
    assert fragment.locator.table == "Primary Outcome Measures"
    assert fragment.locator.paragraph is not None

    with pytest.raises(ValueError, match="原文"):
        repository.add_fragment(
            source_version_id=source.source_version_id,
            locator=locator,
            original_text="   ",
        )

    with (
        open_database(database_path) as database,
        pytest.raises(sqlite3.IntegrityError, match="原文"),
    ):
        database.execute(
            "INSERT INTO evidence_fragments "
            "(fragment_id, source_version_id, locator, content_text, created_at) "
            "VALUES ('blank', ?, '{}', '   ', '2026-08-11T10:00:00+08:00')",
            (source.source_version_id,),
        )

    for schema_name in ("source-version.schema.json", "evidence-fragment.schema.json"):
        schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        payload = (
            source.model_dump(mode="json")
            if schema_name.startswith("source-version")
            else fragment.model_dump(mode="json")
        )
        validator.validate(payload)
