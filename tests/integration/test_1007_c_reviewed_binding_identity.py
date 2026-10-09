"""Accepted C rows keep exact pre-adoption source identity, not lifecycle identity."""
import json
from pathlib import Path

import pytest

from ci_workflow.domain.enums import FactDisclosureState, FactReviewState
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_c import (
    ReportCPortalData,
    active_fact_binding_for_c,
    render_report_c_site,
    validate_active_fact_revision_c,
)


def _world(*, source_only: bool = False):
    report = ReportCPortalData.model_validate_json(Path(
        "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json"
    ).read_bytes())
    row = next(r for r in report.observations if r.row_id == "c-nct02260986-sample-size")
    if source_only:
        row = row.model_copy(update={"row_id": "extra-source-observation",
                                    "field": "raw_outcome_measure"})
        report = report.model_copy(update={"observations": (*report.observations, row)})
    candidate = row.model_copy(update={"review_state": FactReviewState.CANDIDATE})
    original = report.model_copy(update={"observations": tuple(
        candidate if r.row_id == row.row_id else r for r in report.observations
    )})
    binding = active_fact_binding_for_c(original, row.row_id)
    extra = binding.model_dump(exclude={
        "report", "collection", "row_id", "source_version_id", "source_pointer",
        "original_row_sha256",
    })
    fact = ActiveFact(
        fact_id="source-fact", fact_version_id="source-version", field_id="c.sample_size",
        primary_fragment_id="fragment", source_version_id=binding.source_version_id,
        source_locator=binding.source_pointer, source_quote=row.source_text,
        consumer_bindings=(binding,), review_state="accepted", **extra,
    )
    revision = ActiveFactRevision(revision=1, request_id="source-lifecycle-check",
                                  fact_revision_digest="0" * 64, facts=(fact,))
    return report, row, revision


def test_accepted_projection_validates_and_renders_without_rewriting_original_hash(
    tmp_path: Path,
) -> None:
    report, row, revision = _world()
    before = revision.model_dump_json()
    validate_active_fact_revision_c(report, revision)
    site = tmp_path / "site"
    render_report_c_site(report, site, active_revision=revision)
    receipt = json.loads((site / "data/consumer-receipt.json").read_bytes())
    consumer = next(c for c in receipt["consumers"] if c["row_id"] == row.row_id)
    assert consumer["original_row_sha256"] == (
        revision.facts[0].consumer_bindings[0].original_row_sha256
    )
    assert revision.model_dump_json() == before


@pytest.mark.parametrize("changed", [
    {"source_text": "changed source"}, {"threshold_value": "741"},
    {"threshold_unit": "mg"}, {"display_text": "changed meaning"},
    {"disclosure_state": FactDisclosureState.NOT_PUBLICLY_DISCLOSED},
    {"source_version_id": "different-source"},
    {"period": "different-period"},
    {"review_state": FactReviewState.USER_MODIFIED},
])
def test_lifecycle_compatibility_never_accepts_other_row_changes(tmp_path: Path, changed):
    report, row, revision = _world()
    altered = row.model_copy(update=changed)
    data = report.model_copy(update={"observations": tuple(
        altered if r.row_id == row.row_id else r for r in report.observations
    )})
    with pytest.raises(ValueError, match="原消费者科学身份不一致"):
        validate_active_fact_revision_c(data, revision)
    with pytest.raises(ValueError, match="原消费者科学身份不一致"):
        render_report_c_site(data, tmp_path / "must-not-render", active_revision=revision)
    assert not (tmp_path / "must-not-render").exists()


def test_state_compatibility_never_relaxes_declared_scientific_context() -> None:
    report, _, revision = _world()
    fact = revision.facts[0]
    binding = fact.consumer_bindings[0].model_copy(update={"group_id": "wrong-arm"})
    forged = revision.model_copy(update={"facts": (
        fact.model_copy(update={"consumer_bindings": (binding,)}),
    )})
    with pytest.raises(ValueError, match="group_id"):
        validate_active_fact_revision_c(report, forged)


def test_source_observation_without_topic_has_real_trial_detail_consumer(tmp_path: Path) -> None:
    report, row, revision = _world(source_only=True)
    render_report_c_site(report, tmp_path, active_revision=revision)
    receipt = json.loads((tmp_path / "data/consumer-receipt.json").read_bytes())
    consumer = next(c for c in receipt["consumers"] if c["row_id"] == row.row_id)
    assert consumer["page_relative_path"] == f"trials/{row.trial_id}.html"
    assert row.row_id in (tmp_path / consumer["page_relative_path"]).read_text()
