"""C source-bound development saves, not clinical/actual-project/browser acceptance."""

import json
from pathlib import Path

import pytest

from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveError,
)
from ci_workflow.storage.sqlite import open_database
from tests.integration.reports.test_b_report_portal import _page_json_assignment
from tests.integration.test_w04_user_fact_edit import NOW, PROJECT_ID, _project, _projection

ROW = "c-nct02260986-sample-size"


def _command(edits: FactEdit, *, revision: int = 0, version: str = "fact-c-threshold-v1",
             request: str = "sample-current", operation: str = "save"):
    return UserFactSaveCommand.model_validate({
        "request_id": request, "project_id": PROJECT_ID, "expected_revision": revision,
        "operation": operation,
        "target": FactTargetIdentity(fact_id="fact-c-threshold", fact_version_id=version,
                                    entity_id="entity-arm", field_id="design.sample_size"),
        "edits": edits, "user_basis": "开发保存验收，不改实际项目。",
        "saved_by": "development-test", "saved_at": NOW,
    })


def _current_row(root: Path):
    return next(row for row in _projection(root, "C")["observations"] if row["row_id"] == ROW)


@pytest.mark.parametrize("value", [500, 0])
def test_sample_save_uses_current_number_not_original_threshold(tmp_path: Path, value: int):
    root, _ = _project(tmp_path, c_sample_size=True)
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    command = _command(FactEdit(raw_value=str(value), normalized_value=value))
    saved = service.save(command)
    fact = service.current_facts()["fact-c-threshold"]
    assert float(fact["normalized_value"]) == value
    assert fact["threshold_value"] == value
    row = _current_row(root)
    assert float(row["threshold_value"]) == value
    assert row["source_text"] == "740"
    assert saved.rebuilt_reports == ("C",)
    current = service.read_current_delivery()
    assert [item for item in current.reports if item.report != "C"] == [
        item for item in before.reports if item.report != "C"
    ]
    site = root / next(item for item in current.reports if item.report == "C").site_relative_path
    groups = _page_json_assignment(site, "sample-analysis-statistics.html", "__CHART_GROUPS__")
    points = [row for group in groups for row in group["rows"] if row["row_id"] == ROW]
    assert points and all(float(point["numeric_projection"]["plot_value"]) == value
                          for point in points)
    assert service.save(command) == saved
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute("SELECT content_text FROM evidence_fragments "
                                "WHERE fragment_id='fragment-threshold'").fetchone()[0] == "740"


@pytest.mark.parametrize(("raw", "normalized"), [
    ("-1", -1), ("0.5", 0.5), ("True", True), ("inf", "inf"),
    ("nan", "nan"), ("500", 501),
    ("9007199254740993", "9007199254740993"),
])
def test_invalid_sample_save_keeps_current_and_source_unchanged(
    tmp_path: Path, raw: str, normalized: object,
):
    root, _ = _project(tmp_path, c_sample_size=True)
    service = UserFactEditService(root)
    before = service.read_current_delivery()
    with pytest.raises(UserFactSaveError, match="样本量"):
        service.save(_command(FactEdit.model_validate(
            {"raw_value": raw, "normalized_value": normalized},
        )))
    assert service.read_current_delivery() == before
    assert _current_row(root)["source_text"] == "740"
    with open_database(root / "state/project.sqlite") as database:
        assert database.execute("SELECT count(*) FROM user_fact_edit_requests").fetchone()[0] == 0
        assert database.execute("SELECT count(*) FROM fact_versions "
                                "WHERE fact_id='fact-c-threshold'").fetchone()[0] == 1


def test_sample_clear_restore_and_undo_keep_original_source(tmp_path: Path):
    root, _ = _project(tmp_path, c_sample_size=True)
    service = UserFactEditService(root)
    clear = service.save(_command(FactEdit(normalized_value=None)))
    assert _current_row(root)["threshold_value"] is None
    assert _current_row(root)["disclosure_state"] == "user_cleared"
    restore = service.save(_command(
        FactEdit(raw_value="500", normalized_value=500), revision=1,
        version=clear.fact_version_id, request="sample-restore",
    ))
    assert float(_current_row(root)["threshold_value"]) == 500
    service.save(_command(FactEdit(), revision=2, version=restore.fact_version_id,
                          request="sample-undo-restore", operation="undo"))
    row = _current_row(root)
    assert row["threshold_value"] is None
    assert row["source_text"] == "740"
    assert row["disclosure_state"] == "user_cleared"
    assert "None" not in json.dumps(row["display_text"], ensure_ascii=False)


@pytest.mark.parametrize("cleared", [False, True])
def test_saved_current_narrative_uses_public_field_label_not_internal_key(
    tmp_path: Path, cleared: bool,
) -> None:
    root, _ = _project(tmp_path, c_sample_size=True)
    edits = FactEdit(normalized_value=None) if cleared else FactEdit(
        raw_value="500", normalized_value=500,
    )
    UserFactEditService(root).save(_command(edits))
    row = _current_row(root)
    assert "planned_or_actual_sample_size" not in row["display_text"]
    assert "计划或实际样本量" in row["display_text"]
    assert row["source_text"] == "740"


def test_registered_real_source_sample_stage_keeps_source_and_identity(tmp_path: Path):
    """Source-side seam only: no current exists and no candidate is published/accepted."""
    from ci_workflow.application.c_portal_consumer_registry import register_c_source_consumers
    from ci_workflow.renderers.portal.active_fact_projection import (
        ActiveFact,
        validate_active_fact_binding,
    )
    from ci_workflow.renderers.portal.report_c import _current_sample_number
    from tests.integration.test_r24_c_source_consumers import (
        _AT,
        _DIRECT,
        _candidate,
        _fact_snapshot,
    )

    root, snapshot, report, versions, captures = _candidate(tmp_path)
    (binding,) = register_c_source_consumers(
        root, snapshot, report, {_DIRECT: versions[_DIRECT]}, captures, registered_at=_AT,
    )
    service = UserFactEditService(root)
    original = service._fact_row(versions[_DIRECT])
    source_before = _fact_snapshot(root, (versions[_DIRECT],))
    command = UserFactSaveCommand(
        request_id="development-source-sample", project_id="development-source-seam",
        expected_revision=0,
        target=FactTargetIdentity(**{key: original[key] for key in (
            "fact_id", "fact_version_id", "entity_id", "field_id",
        )}),
        edits=FactEdit(raw_value="50", normalized_value=50),
        user_basis="独立候选库开发接线，不是用户保存或科学接受。",
        saved_by="development-test", saved_at=_AT,
    )
    version, rate = service._stage_fact(
        command, source=original, revision=1, request_digest="a" * 64,
    )
    projected = ActiveFact.model_validate(service._public_fact(service._fact_row(version)))
    assert projected.normalized_value == "50"
    assert _current_sample_number(projected) == 50
    assert projected.source_quote == original["raw_value"]
    assert validate_active_fact_binding(projected, binding, binding) == binding
    assert rate is None
    assert _fact_snapshot(root, (versions[_DIRECT],)) == source_before
    assert not (root / "reports/current.json").exists()
