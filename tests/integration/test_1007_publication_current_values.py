"""Source-printed components remain distinct from edited current numeric values."""

import hashlib
import json
from datetime import UTC, datetime

import pytest

from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveError,
)
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, numeric_value
from ci_workflow.renderers.portal.report_a import EfficacyRow, _a_statistical_identity
from ci_workflow.renderers.portal.report_b import _b_statistical_identity
from ci_workflow.storage.sqlite import open_database
from tests.unit.test_source_publication_view import _fact


def _active(text="14 (18.4)", **updates):
    source = _fact(text)
    original = source.model_dump(mode="json")
    return ActiveFact.model_validate({**original, "fact_version_id": "source-fact-v1",
        "primary_fragment_id": "original-cell", "source_version_id": "source-v1",
        "source_locator": source.locator.model_dump_json(), "source_quote": source.original_text,
        "statistical_form": "reported_proportion", "measure_object": "participants",
        "unit": "%", "normalized_unit": "%", **updates})


def test_original_printed_percent_projects_without_normalizing_the_parent():
    original = _active()
    before = original.model_dump_json()
    assert numeric_value(original) == 18.4
    assert original.normalized_value is None
    assert original.raw_value == "14 (18.4)"
    assert original.model_dump_json() == before


def test_exact_zero_is_not_missing_and_printed_rounding_is_not_recomputed():
    assert numeric_value(_active("0 (0.0)")) == 0
    assert numeric_value(_active("1 (1.3)")) == 1.3
    assert not (_active().model_extra or {})["result_context"]["denominator_candidates"]


@pytest.mark.parametrize("damage", ["no_form", "domain", "quote", "raw", "unit",
                                  "role", "measure", "locator", "false_zero", "threshold"])
def test_no_lexical_or_damaged_source_fallback(damage):
    original = _active()
    raw = original.model_dump(mode="json")
    if damage == "no_form":
        raw["statistical_form"] = "estimate"
    elif damage == "domain":
        raw["result_context"]["domain"] = "immunogenicity"
    elif damage == "quote":
        raw["source_quote"] = "45 (60.0)"
    elif damage == "raw":
        raw["raw_value"] = "45 (60.0)"
    elif damage == "unit":
        raw["normalized_unit"] = "participants"
    elif damage == "role":
        raw["result_context"]["value_role"] = "denominator"
    elif damage == "measure":
        raw["result_context"]["source_measure_path"] = "/article/foreign-cell"
    elif damage == "locator":
        raw["source_locator"] = '{"field_path":"/article/foreign-cell"}'
    elif damage == "false_zero":
        raw["disclosure_state"] = "reported_zero"
    else:
        raw["raw_value"] = raw["original_text"] = raw["source_quote"] = "1 (<1)"
    with pytest.raises(ValueError):
        numeric_value(ActiveFact.model_validate(raw))


def test_user_current_value_never_redivides_or_reuses_the_original_component():
    source = _active()
    edited = source.model_copy(update={"raw_value": "20.1%", "normalized_value": 20.1,
        "review_state": "user_modified"})
    assert numeric_value(edited) == 20.1
    assert edited.source_quote == "14 (18.4)"
    cleared = edited.model_copy(update={"raw_value": None, "normalized_value": None,
                                         "disclosure_state": "user_cleared"})
    with pytest.raises(ValueError):
        numeric_value(cleared)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True])
def test_nonfinite_or_boolean_current_values_fail(value):
    with pytest.raises(ValueError):
        numeric_value(_active(normalized_value=value))


def test_a_b_use_the_same_reported_percent_identity_not_a_crude_rate():
    row = EfficacyRow(row_id="printed-cell", product_id="drug", trial_id="study",
        endpoint="Original response definition", timepoint="Week 24", arm="Treatment",
        value=18.4, unit="%", population="FAS", value_basis="reported_percent")
    assert _a_statistical_identity(row) == ("reported_proportion", "participants")
    assert _b_statistical_identity(row) == _a_statistical_identity(row)
    assert row.numerator is None and row.denominator is None


def test_source_scoped_ids_are_opaque_data_not_file_resource_names():
    original = _fact("14 (18.4)")
    target = FactTargetIdentity(fact_id=original.fact_id, fact_version_id="source-v1",
        entity_id=original.entity_id, field_id=original.field_id)
    assert target.fact_id == original.fact_id
    command = UserFactSaveCommand(request_id="safe-request", project_id="project",
        expected_revision=0, target=target, edits=FactEdit(raw_value=None),
        user_basis="测试", saved_by="test", saved_at=datetime(2026, 10, 7, tzinfo=UTC))
    assert command.model_dump(mode="json")["target"]["fact_id"] == original.fact_id
    with pytest.raises(ValueError):
        UserFactSaveCommand.model_validate({**command.model_dump(mode="json"),
                                           "request_id": "../outside"})


@pytest.mark.parametrize("bad", ["", " leading", "trailing ", "a\x00b", "a\nb", "a" * 4097])
def test_opaque_target_ids_do_not_normalize_or_accept_unbounded_control_text(bad):
    with pytest.raises(ValueError):
        FactTargetIdentity(fact_id=bad, fact_version_id="source-v1",
                           entity_id="entity", field_id="field")


def _stage_candidate(tmp_path):
    # Only a synthetic source fixture. Exercise the actual append-only staging
    # method without pretending to register a real product or commit a report.
    service = UserFactEditService(tmp_path / "component-project")
    source = _active()
    context = source.model_dump(mode="json")
    for key in ("fact_version_id", "primary_fragment_id", "source_version_id",
                "source_locator", "source_quote"):
        context.pop(key)
    stamp = datetime(2026, 10, 7, tzinfo=UTC).isoformat()
    encoded = json.dumps(context, ensure_ascii=False, sort_keys=True)
    with open_database(service.database_path) as db:
        db.execute("INSERT INTO entities VALUES (?,?,?,?)",
                   (context["entity_id"], "clinical_trial", "Synthetic source study", stamp))
        db.execute("INSERT INTO source_versions (source_version_id,source_id,content_sha256,"
                   "acquired_at,created_at) VALUES (?,?,?,?,?)",
                   ("source-v1", context["source_id"], "a" * 64, stamp, stamp))
        db.execute("INSERT INTO evidence_fragments (fragment_id,source_version_id,locator,"
                   "content_text,content_sha256,created_at) VALUES (?,?,?,?,?,?)",
                   (source.primary_fragment_id, source.source_version_id, source.source_locator,
                    source.source_quote, hashlib.sha256(source.source_quote.encode()).hexdigest(),
                    stamp))
        db.execute("INSERT INTO fact_versions (fact_version_id,fact_id,entity_id,field_id,"
                   "raw_value,"
                   "normalized_value,disclosure_state,review_state,primary_fragment_id,created_at,"
                   "content_sha256,scientific_context_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   (source.fact_version_id, source.fact_id, context["entity_id"], source.field_id,
                    source.raw_value, None, "reported_value", "accepted",
                    source.primary_fragment_id,
                    stamp, hashlib.sha256(encoded.encode()).hexdigest(), encoded))
        db.execute("INSERT INTO fact_evidence VALUES (?,?,?,?)",
                   (source.fact_version_id, source.primary_fragment_id, "primary", stamp))
    return service, source


def _stage(service, source, request, edits, *, revision=1, operation="save"):
    row = service._fact_row(source.fact_version_id)
    command = UserFactSaveCommand(request_id=request, project_id="synthetic-project",
        expected_revision=revision - 1, operation=operation,
        target=FactTargetIdentity(fact_id=row["fact_id"], fact_version_id=row["fact_version_id"],
                                entity_id=row["entity_id"], field_id=row["field_id"]),
        edits=edits, user_basis="合成来源保存测试", saved_by="test",
        saved_at=datetime(2026, 10, 7, tzinfo=UTC))
    version, rate = service._stage_fact(command, source=row, revision=revision,
                                      request_digest=hashlib.sha256(request.encode()).hexdigest())
    assert rate is None
    return ActiveFact.model_validate(service._public_fact(service._fact_row(version)))


def test_append_only_edit_then_undo_restores_original_composite_without_normalization(tmp_path):
    service, source = _stage_candidate(tmp_path)
    before = service._fact_row(source.fact_version_id)
    edited = _stage(service, source, "edit", FactEdit(raw_value="20.1%", normalized_value=20.1))
    assert numeric_value(edited) == 20.1
    restored = _stage(service, edited, "undo", FactEdit(), revision=2, operation="undo")
    assert restored.raw_value == "14 (18.4)" and restored.normalized_value is None
    assert numeric_value(restored) == 18.4
    assert restored.source_quote == source.source_quote
    assert service._fact_row(source.fact_version_id) == before


@pytest.mark.parametrize("edits", [FactEdit(raw_value="101%", normalized_value=101),
    FactEdit(raw_value="20.1%", normalized_value=20.2),
    FactEdit(raw_value="nan", normalized_value="nan"),
    FactEdit(raw_value="20.1%", normalized_value=20.1, denominator=76)])
def test_reported_percent_save_rejects_invalid_current_value_before_staging(tmp_path, edits):
    service, source = _stage_candidate(tmp_path)
    with open_database(service.database_path) as db:
        before = db.execute("SELECT * FROM fact_versions").fetchall()
    with pytest.raises(UserFactSaveError):
        _stage(service, source, "invalid", edits)
    with open_database(service.database_path) as db:
        assert db.execute("SELECT * FROM fact_versions").fetchall() == before
