"""Public C evidence must reference the real locked version, not its capture ID.

The scientific observation retains its original capture identity. One explicit
projection from the verified snapshot supplies the public source version and
snapshot, without rewriting source facts or accepting the review-only candidate.
"""

import json
from datetime import UTC, datetime

import pytest

from ci_workflow.application.c_portal_consumer_registry import (
    CPortalConsumerRegistrationError,
    register_c_source_consumers,
)
from ci_workflow.application.source_research_service import SourceCapture
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    _chart_row,
    _evidence_view,
    _table_rows,
)
from ci_workflow.storage.snapshot_store import LockedSnapshot, SnapshotStore
from ci_workflow.storage.sqlite import open_database
from tests.integration.test_r24_c_candidate_materialization import _raw
from tests.integration.test_r24_ctgov_c_design_projection import _CAS_ROOT, _full_bindings
from tools.materialize_ctgov_c_candidate import materialize, render_review_preview

_OBSERVED = datetime(2026, 10, 3, tzinfo=UTC)


@pytest.fixture(scope="module")
def candidate(tmp_path_factory):
    output = tmp_path_factory.mktemp("locked-c-display") / "candidate"
    manifest = materialize(
        source_root=_CAS_ROOT, raw_asset=_raw(), output=output,
        bindings=_full_bindings(), indication_id="pnh",
        indication="阵发性睡眠性血红蛋白尿症", cutoff="2026-09-26",
        observed_at=_OBSERVED,
    )
    render_review_preview(output, rendered_at=_OBSERVED)
    root = output / "project"
    locked = LockedSnapshot.model_validate(manifest["snapshot"])
    snapshot = SnapshotStore(root).read(locked)
    expected = {entry["capture"]["source_id"]: entry["source_version_id"]
                for entry in snapshot["closure"]["sources"]}
    report = ReportCPortalData.model_validate_json(
        (output / "review-portal-data.json").read_bytes()
    )
    return output, root, manifest, locked, expected, report


def test_materialized_report_has_exact_locked_public_source_projection(candidate):
    output, root, manifest, locked, expected, report = candidate
    assert report.source_evidence_snapshot_id == locked.snapshot_id
    assert report.report_snapshot_id is None
    assert report.model_dump().get("source_version_by_source_id") == expected
    projection = json.loads((output / "projection.json").read_bytes())
    assert report.model_dump(mode="json")["observations"] == projection["observations"]
    assert len(expected) == manifest["source_versions"] == 2
    assert not (root / "reports/current.json").exists()
    status = json.loads((root / "reports/C/review-candidate/html/data/research-status.json")
                        .read_bytes())
    assert status["delivery_status"] == "unreviewed_candidate"


def test_public_chart_table_and_evidence_consume_actual_version(candidate):
    _, _, _, locked, expected, report = candidate
    for observation in report.observations:
        actual_version = expected[observation.source_version_id]
        assert actual_version != observation.source_version_id
        evidence = _evidence_view(report, observation, page_id="trial-profile")
        assert evidence.row.report_snapshot_id == locked.snapshot_id
        assert evidence.source_version_id == actual_version
        assert evidence.original_text == observation.source_text
        assert evidence.source_trace_state == "located"
        chart = _chart_row(report, observation, chart_type="status_matrix")
        assert chart["source_version_id"] == actual_version
        table = _table_rows(report, (observation,), page_id="trial-detail")
        assert all(row["source_version"] == actual_version for row in table)
        assert all(row["source_version_id"] == actual_version for row in table)


@pytest.mark.parametrize("mode", ["wrong_snapshot", "wrong_version", "missing_source", "empty_map"])
def test_forged_public_projection_is_rejected_before_new_consumers(candidate, mode):
    output, root, manifest, locked, expected, report = candidate
    changes = {"source_version_by_source_id": dict(expected),
               "source_evidence_snapshot_id": locked.snapshot_id}
    if mode == "wrong_snapshot":
        changes["source_evidence_snapshot_id"] = "different-locked-snapshot"
    elif mode == "wrong_version":
        key = next(iter(expected))
        changes["source_version_by_source_id"][key] = "wrong-source-version"
    elif mode == "missing_source":
        del changes["source_version_by_source_id"][next(iter(expected))]
    else:
        changes["source_version_by_source_id"] = {}
    # model_copy deliberately bypasses Pydantic to challenge the production
    # registration boundary, which must independently verify locked provenance.
    invalid = report.model_copy(update=changes)
    inputs = json.loads((output / "inputs.json").read_bytes())
    captures = {item["source_id"]: SourceCapture.model_validate(item) for item in inputs["sources"]}
    database = root / "state/project.sqlite"
    with open_database(database) as connection:
        before = connection.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings"
        ).fetchone()
    with pytest.raises(CPortalConsumerRegistrationError, match="快照|来源|版本"):
        register_c_source_consumers(
            root, locked, invalid, manifest["fact_version_by_ref"], captures,
            registered_at=_OBSERVED,
        )
    with open_database(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM source_portal_consumer_bindings"
        ).fetchone() == before
    assert not (root / "reports/current.json").exists()


def test_legacy_report_remains_readable_without_in_place_scientific_migration(candidate):
    _, _, _, _, _, report = candidate
    payload = report.model_dump(mode="json")
    payload.pop("source_version_by_source_id", None)
    payload.pop("report_snapshot_id", None)
    payload.pop("source_evidence_snapshot_id", None)
    legacy = ReportCPortalData.model_validate(payload)
    assert legacy.observations == report.observations
    observation = legacy.observations[0]
    assert _evidence_view(legacy, observation, page_id="trial-profile").source_version_id == (
        observation.source_version_id
    )


def test_report_snapshot_and_source_evidence_snapshot_are_distinct_contexts(candidate):
    output, root, manifest, locked, expected, report = candidate
    projected = report.model_copy(update={
        "report_snapshot_id": "report-snapshot-independent-delivery-context",
        "source_evidence_snapshot_id": locked.snapshot_id,
        "source_version_by_source_id": expected,
    })
    inputs = json.loads((output / "inputs.json").read_bytes())
    captures = {item["source_id"]: SourceCapture.model_validate(item) for item in inputs["sources"]}
    bindings = register_c_source_consumers(
        root, locked, projected, manifest["fact_version_by_ref"], captures,
        registered_at=_OBSERVED,
    )
    assert len(bindings) == len(projected.observations)
    evidence = _evidence_view(projected, projected.observations[0], page_id="trial-profile")
    assert evidence.row.report_snapshot_id == projected.report_snapshot_id
    assert evidence.source_version_id == expected[projected.observations[0].source_version_id]
