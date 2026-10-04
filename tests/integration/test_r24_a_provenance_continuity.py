"""Source links survive ordinary rendering and actual user-save rebuilding.

Synthetic sources exercise continuity, not independent medical acceptance.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

import tests.integration.test_w04_user_fact_edit as edit_fixtures
import tools.build_r24_desktop_candidate as candidate_builder
import tools.materialize_ctgov_a_candidate as materializer
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.source_research_service import (
    ingest_fresh_a_research_package,
    load_fresh_a_research_package,
)
from ci_workflow.application.user_fact_edit import FactEdit, UserFactEditService
from ci_workflow.domain.public_provenance import PublicProvenance, PublicSource
from ci_workflow.renderers.portal.report_a import (
    ReportAPortalData,
    ReportAPortalError,
    render_report_a_site,
)
from tests.integration.test_fresh_a_scientific_review import _write_a_project


def _locked_candidate(tmp_path: Path) -> tuple[Path, ReportAPortalData, dict[str, Any]]:
    root = _write_a_project(tmp_path)
    package = load_fresh_a_research_package(root / "evidence/library/a-research-package.json")
    lineage = ingest_fresh_a_research_package(
        project_root=root, project_id=verify_project_workspace(root).contract.project_id,
        contract_version=1, package=package,
    )
    receipt = {
        "snapshot_id": lineage.evidence_snapshot.snapshot_id,
        "snapshot_sha256": lineage.evidence_snapshot.sha256,
        "snapshot_relative_path": lineage.evidence_snapshot.relative_path,
        "source_version_ids": list(lineage.source_version_ids),
        "bound_report_data": {
            "sha256": sha256(package.report_data.model_dump_json().encode()).hexdigest(),
        },
    }
    return root, package.report_data, receipt


def test_locked_candidate_provenance_is_exact_not_inferred_from_trial_id(tmp_path: Path) -> None:
    root, report, receipt = _locked_candidate(tmp_path)
    factory = getattr(materializer, "public_provenance_for_candidate", None)
    assert callable(factory), "ordinary candidate renderer needs locked source projection"
    public = factory(root, report, receipt)
    assert public.evidence_snapshot_id == receipt["snapshot_id"]
    assert public.report_data_digest == receipt["bound_report_data"]["sha256"]
    assert public.sources[0].url == "https://clinicaltrials.gov/study/NCT00000001"
    assert public.sources[0].source_version_id == receipt["source_version_ids"][0]


@pytest.mark.parametrize("drift", ["report", "source_version", "snapshot"])
def test_candidate_provenance_rejects_unbound_or_changed_material(
    tmp_path: Path, drift: str,
) -> None:
    root, report, receipt = _locked_candidate(tmp_path)
    factory = getattr(materializer, "public_provenance_for_candidate", None)
    assert callable(factory), "locked source continuity must fail closed"
    if drift == "report":
        report = report.model_copy(update={"report_version": "unbound"})
    elif drift == "source_version":
        receipt["source_version_ids"] = ["unknown-source-version"]
    else:
        receipt["snapshot_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="来源|报告|快照"):
        factory(root, report, receipt)


def test_ordinary_presentation_render_passes_verified_public_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, report, receipt = _locked_candidate(tmp_path)
    source = tmp_path / "candidate"
    (tmp_path / "src/ci_workflow/renderers/portal/assets").mkdir(parents=True)
    inputs = source / "source-project/inputs"
    inputs.mkdir(parents=True)
    # No science fixture is accepted here; source snapshot is copied byte-for-byte.
    snapshot = project / receipt["snapshot_relative_path"]
    destination = source / "source-project" / receipt["snapshot_relative_path"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(snapshot.read_bytes())
    receipt_path = source / "source-project/logs/diagnostics/r24-66-source.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt))
    (inputs / "a.json").write_text(report.model_dump_json())
    b_path = Path("fixtures/positive/b-pnh/inputs/report-data.json")
    (inputs / "b.json").write_bytes(b_path.read_bytes())
    pin_paths = [inputs / "a.json", inputs / "b.json", receipt_path, destination]
    (source / "candidate-manifest.json").write_text(json.dumps({
        "rendered_files": {str(path.relative_to(source)): sha256(path.read_bytes()).hexdigest()
                           for path in pin_paths},
    }))
    seen: list[dict[str, Any]] = []

    def render_a(data: ReportAPortalData, output: Path, **kwargs: Any) -> None:
        seen.append(kwargs)
        output.mkdir(parents=True)

    monkeypatch.setattr(candidate_builder, "render_report_a_site", render_a)
    monkeypatch.setattr(candidate_builder, "render_report_b_site", lambda *_: None)
    candidate_builder.render_existing(tmp_path, source, tmp_path / "new-candidate")
    assert seen[0].get("public_provenance") is not None
    assert seen[0]["public_provenance"].sources[0].url.endswith("NCT00000001")


def test_legal_a_b_save_and_clear_preserve_source_links_and_limitations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_renderer = edit_fixtures.render_report_a_site

    def render_with_sources(data: ReportAPortalData, output: Path) -> tuple[Path, ...]:
        row = next(row for row in data.safety if row.row_id == "safe-apply-t-1")
        public = PublicProvenance(
            evidence_snapshot_id="synthetic-provenance-snapshot",
            report_data_digest=sha256(data.model_dump_json().encode()).hexdigest(),
            sources=(PublicSource(
                source_version_id=row.source_version_id, label="合成来源，仅测试连续性",
                url="https://clinicaltrials.gov/study/NCT04558918",
                source_type="临床试验登记", published_at="2026-09-01",
                data_cutoff="2026-09-20", limitation="非医学验收依据",
            ),),
        )
        return original_renderer(data, output, public_provenance=public,
                                 publication_limitation_zh="开发候选，不作临床结论。")

    monkeypatch.setattr(edit_fixtures, "render_report_a_site", render_with_sources)
    root, _ = edit_fixtures._project(tmp_path, cross_report_binding="legal_AB")
    service = UserFactEditService(root)
    source_html = root / "reports/A/v1/html/safety.html"
    original_bytes = source_html.read_bytes()
    initial_report = json.loads(
        (source_html.parent / "data/report.js").read_text().split("=", 1)[1].rstrip(";\n")
    )
    expected_sources = initial_report["public_sources"]
    operations = (FactEdit(numerator=24, denominator=80), FactEdit(raw_value=None))
    for revision, edits in enumerate(operations):
        previous = service.read_current_delivery()
        command = edit_fixtures._command(
            request_id=f"provenance-continuity-{revision}", expected_revision=revision,
            fact_version_id=next(version for version in previous.active_fact_version_ids
                                 if service._fact_row(version)["fact_id"] == "fact-crude-rate"),
            edits=edits,
        )
        result = service.save(command)
        assert result.rebuilt_reports == ("A", "B")
        current = service.read_current_delivery()
        entry = next(item for item in current.reports if item.report == "A")
        site = root / entry.site_relative_path
        report_js = json.loads((site / "data/report.js").read_text().split("=", 1)[1].rstrip(";\n"))
        assert report_js["public_sources"], "user save must not erase public source identity"
        assert report_js["public_sources"] == expected_sources
        assert report_js["public_sources"][0]["url"].endswith("NCT04558918")
        html = (site / "safety.html").read_text()
        assert "开发候选，不作临床结论。" in html
        assert "非医学验收依据" in html
    assert source_html.read_bytes() == original_bytes


def test_public_provenance_rejects_wrong_original_report_before_any_projection(
    tmp_path: Path,
) -> None:
    root, data, receipt = _locked_candidate(tmp_path)
    public = PublicProvenance(
        evidence_snapshot_id=receipt["snapshot_id"], report_data_digest="0" * 64, sources=(),
    )
    with pytest.raises(ReportAPortalError, match="报告内容"):
        render_report_a_site(data, tmp_path / "wrong", public_provenance=public)
    assert not (tmp_path / "wrong").exists()
