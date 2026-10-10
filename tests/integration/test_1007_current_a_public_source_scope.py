"""Synthetic physical snapshots exercise ordinary current-source continuity.

No source or clinical approval is minted here. The tests call the production
preflight/builder, not a hand-authored HTML demo or a mocked source projection.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from ci_workflow.application.latest_delivery import CurrentReportDelivery
from ci_workflow.application.user_fact_edit import (
    CurrentDeliveryConflictError,
    build_current_report,
    preflight_current_report,
)
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact
from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    active_fact_binding_for_a,
    render_report_a_site,
)
from tests.integration.test_r24_a_provenance_continuity import _locked_candidate
from tools.materialize_ctgov_a_candidate import public_provenance_for_candidate


def _case(tmp_path: Path, *, old_public: bool = False) -> tuple[
    Path, ReportAPortalData, CurrentReportDelivery, tuple[str, str], dict[str, Any],
]:
    root, old, receipt = _locked_candidate(tmp_path)
    site = root / "reports/A/v1/html"
    public = public_provenance_for_candidate(root, old, receipt) if old_public else None
    render_report_a_site(old, site, public_provenance=public,
                         publication_limitation_zh="合成连续性测试，非科学或发布验收。")
    old_input = root / "inputs/old-a.json"
    old_input.parent.mkdir(parents=True, exist_ok=True)
    old_input.write_text(old.model_dump_json())
    previous = CurrentReportDelivery(
        report="A", revision=0, report_version="v1",
        site_relative_path=site.relative_to(root).as_posix(),
        file_hashes={p.relative_to(site).as_posix(): sha256(p.read_bytes()).hexdigest()
                     for p in site.rglob("*") if p.is_file()},
        fact_version_ids=(), fact_revision_digest=sha256(b"[]").hexdigest(),
        builder_input_relative_path=old_input.relative_to(root).as_posix(),
        builder_input_sha256=sha256(old_input.read_bytes()).hexdigest(),
    )
    current_data = old.model_copy(update={
        "source_evidence_snapshot_id": receipt["snapshot_id"],
        "report_version": "v1-expanded-source-input",
    })
    current_input = root / "inputs/new-a.json"
    current_input.write_text(current_data.model_dump_json())
    return root, current_data, previous, (
        current_input.relative_to(root).as_posix(), sha256(current_input.read_bytes()).hexdigest(),
    ), receipt


@pytest.mark.parametrize("old_public", [False, True])
def test_ordinary_current_builder_projects_actual_new_snapshot_not_old_context(
    tmp_path: Path, old_public: bool,
) -> None:
    root, data, previous, binding, receipt = _case(tmp_path, old_public=old_public)
    original = {p: (root / previous.site_relative_path / p).read_bytes()
                for p in previous.file_hashes}
    row = data.efficacy[0]
    consumer = active_fact_binding_for_a(data, "efficacy", row.row_id)
    # A real render receipt requires an actual consumer. This synthetic source
    # fact uses that native row's exact identity; it is not a scientific approval.
    identity = consumer.model_dump(mode="json", exclude={
        "report", "collection", "row_id", "original_row_sha256", "source_version_id",
    })
    fact = ActiveFact(
        **identity, fact_id="synthetic-public-fact", fact_version_id="synthetic-public-fact-v1",
        field_id="efficacy", raw_value=str(row.value), normalized_value=row.value,
        primary_fragment_id="synthetic-public-fragment", source_quote="合成原文，仅测试来源呈现。",
        source_version_id=consumer.source_version_id, source_locator=consumer.source_pointer,
        consumer_bindings=(consumer,),
    )
    rebuilt = build_current_report(
        root, previous, revision=1, request_id="current-source-scope-1",
        changed_fact_id=fact.fact_id, fact_version_ids=(fact.fact_version_id,),
        public_facts={fact.fact_id: fact.model_dump(mode="json")},
        report_version="v1-current-r1", builder_binding=binding,
    )
    site = root / rebuilt.site_relative_path
    context = json.loads((site / "data/render-context.json").read_bytes())
    public = context["public_provenance"]
    assert public is not None, "physical locked sources must reach normal current rendering"
    assert public["evidence_snapshot_id"] == receipt["snapshot_id"]
    assert public["report_data_digest"] == sha256(data.model_dump_json().encode()).hexdigest()
    assert public["sources"][0]["source_version_id"] == receipt["source_version_ids"][0]
    for page in site.rglob("*.html"):
        section = page.read_text().split('id="external-sources"', 1)[1].split("</section>", 1)[0]
        assert "https://clinicaltrials.gov/study/NCT00000001" in section
        assert "未绑定可核验的公共来源谱系" not in section
        assert "非科学或发布验收" in page.read_text()
    assert {p: (root / previous.site_relative_path / p).read_bytes()
            for p in previous.file_hashes} == original


@pytest.mark.parametrize("drift", ["missing", "bytes", "symlink", "capture_identity"])
def test_current_source_preflight_rejects_corrupt_declared_snapshot_before_staging(
    tmp_path: Path, drift: str,
) -> None:
    root, _data, previous, binding, receipt = _case(tmp_path)
    snapshot = root / receipt["snapshot_relative_path"]
    raw = snapshot.read_bytes()
    # Mutation is limited to synthetic tmp_path fixtures; real snapshots stay immutable.
    if drift == "missing":
        snapshot.rename(snapshot.with_suffix(".saved"))
    elif drift == "bytes":
        snapshot.write_bytes(raw + b" ")
    elif drift == "symlink":
        external = tmp_path / "outside-synthetic-snapshot.json"
        snapshot.rename(external)
        snapshot.symlink_to(external)
    else:
        from ci_workflow.storage.snapshot_store import SnapshotStore

        payload = json.loads(raw)
        payload["closure"]["sources"][0]["capture"]["content_text"] += " altered source"
        changed = SnapshotStore(root).lock_evidence_snapshot(payload)
        input_path = root / binding[0]
        report = ReportAPortalData.model_validate_json(input_path.read_bytes())
        input_path.write_text(report.model_copy(update={
            "source_evidence_snapshot_id": changed.snapshot_id,
        }).model_dump_json())
        binding = (binding[0], sha256(input_path.read_bytes()).hexdigest())
    with pytest.raises(CurrentDeliveryConflictError, match="来源|快照"):
        preflight_current_report(
            root, previous, revision=1, request_id="bad-current-source",
            fact_version_ids=(), public_facts={}, builder_binding=binding,
        )
    assert not (root / "reports/A/v1-current-r1").exists()


@pytest.mark.parametrize("drift", ["missing", "bytes"])
def test_current_preflight_does_not_discard_bound_source_context(
    tmp_path: Path, drift: str,
) -> None:
    root, _data, previous, binding, _receipt = _case(tmp_path, old_public=True)
    context = root / previous.site_relative_path / "data/render-context.json"
    if drift == "missing":
        context.rename(context.with_suffix(".saved"))
    else:
        context.write_bytes(context.read_bytes() + b" ")
    with pytest.raises(CurrentDeliveryConflictError, match="来源.*上下文"):
        preflight_current_report(
            root, previous, revision=1, request_id="bad-old-source-context",
            fact_version_ids=(), public_facts={}, builder_binding=binding,
        )
