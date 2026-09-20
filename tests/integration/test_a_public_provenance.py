"""Public provenance through the real run path, using explicitly synthetic research."""
import json
from dataclasses import replace
from html import escape
from pathlib import Path

import pytest

from ci_workflow.application.source_research_service import (
    ResearchPackageError,
    compute_research_content_digest,
    ingest_fresh_a_research_package,
    load_fresh_a_research_package,
    project_a_public_provenance,
)
from ci_workflow.domain.public_provenance import public_source_url
from ci_workflow.renderers.portal.report_a import ReportAPortalError, render_report_a_site
from tests.integration.test_fresh_a_scientific_review import (
    _run_ready_project,
    _write_a_project,
)


def test_fresh_run_projects_sources_on_every_physical_page(tmp_path: Path) -> None:
    project = _write_a_project(tmp_path)
    _run_ready_project(project)
    pages = tuple((project / "reports/A/v1/html").rglob("*.html"))
    assert len(pages) > 11
    for page in pages:
        section = page.read_text().split('id="external-sources"', 1)[1].split('</section>', 1)[0]
        assert escape("ClinicalTrials.gov 已存测试记录") in section
        assert 'href="https://clinicaltrials.gov/study/NCT00000001"' in section
        assert "发布日期：2026-07-01" in section
        assert "数据截止：2026-07-31" in section


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "file:///private/source", "//example.org",
    "https://user:secret@example.org", "https://example.org?access_token=secret",
    "https://example.org?X-Amz-Signature=secret", "https://example.org/#token=secret",
    "https://example.org\\@evil.org", "https://example.org\n", "https://[invalid",
    "http://localhost/report", "http://127.0.0.1/report", "http://192.168.1.2/report",
    "http://[::1]/report", "http://workstation.local/report",
])
def test_unsafe_urls_are_not_public(url: str) -> None:
    assert public_source_url(url) is None


def test_projection_escaping_unknown_dates_and_drift(tmp_path: Path) -> None:
    project = _write_a_project(tmp_path)
    path = project / "evidence/library/a-research-package.json"
    payload = json.loads(path.read_text())
    payload["sources"][0]["title"] = '<img src=x onerror="alert(1)">合成来源'
    payload["sources"][0]["url"] = "https://user:secret@example.org"
    payload["sources"][0]["published_at"] = None
    payload["sources"].append({
        **payload["sources"][0], "source_id": "second-synthetic-source",
        "title": "第二份合成来源", "url": "https://example.org/study?id=2",
    })
    # This is a fixture digest, never an independent scientific approval.
    payload["scientific_review"]["reviewed_content_digest"] = (
        compute_research_content_digest(payload)
    )
    path.write_text(json.dumps(payload))
    package = load_fresh_a_research_package(path)
    lineage = ingest_fresh_a_research_package(
        project_root=project,
        project_id=json.loads((project / "project.yaml").read_text())[
            "project_contract_versions"
        ][0]["project_id"],
        contract_version=1, package=package,
    )
    public = project_a_public_provenance(package, lineage)
    reordered = project_a_public_provenance(
        package, replace(lineage, source_version_ids=tuple(reversed(lineage.source_version_ids)))
    )
    assert reordered == public
    assert public.sources[1].label == "第二份合成来源"
    pages = render_report_a_site(package.report_data, tmp_path / "html", public_provenance=public)
    for page in pages:
        section = page.read_text().split('id="external-sources"', 1)[1].split('</section>', 1)[0]
        assert "&lt;img" in section and '<img src=x' not in section
        assert "发布日期：未知（来源未明确公开）" in section
        assert "secret" not in section and "2026-08-18" not in section
    with pytest.raises(ResearchPackageError, match="来源版本"):
        project_a_public_provenance(package, replace(lineage, source_version_ids=("wrong",)))
    with pytest.raises(ResearchPackageError, match="研究内容"):
        project_a_public_provenance(package, replace(lineage, package_digest="wrong"))
    with pytest.raises(ReportAPortalError, match="报告内容"):
        render_report_a_site(
            package.report_data.model_copy(update={"report_version": "drift"}),
            tmp_path / "drift", public_provenance=public,
        )
    legacy = render_report_a_site(package.report_data, tmp_path / "legacy")
    assert "未绑定可核验的公共来源谱系" in legacy[0].read_text()

    from ci_workflow.renderers.portal.report_a import (
        ReportALineageBinding,
        build_report_a_artifact,
    )

    data_path = tmp_path / "data.json"
    data_path.write_text(package.report_data.model_dump_json())
    binding = ReportALineageBinding(
        evidence_snapshot_id="wrong-snapshot",
        claim_snapshot_id=lineage.claim_snapshot_id,
        coverage_set_id=lineage.coverage_set_id,
        coverage_projection_id=lineage.coverage_projection_id,
        claim_ids=lineage.claim_ids, source_version_ids=lineage.source_version_ids,
    )
    with pytest.raises(ReportAPortalError, match="报告谱系"):
        build_report_a_artifact(
            project_root=project, data_path=data_path, project_id="synthetic",
            contract_version=1, run_id="synthetic", lineage=binding, public_provenance=public,
        )
    with pytest.raises(ValueError, match="公共来源文字"):
        render_report_a_site(
            package.report_data, tmp_path / "private",
            public_provenance=public.model_copy(update={
                "sources": (public.sources[0].model_copy(update={"label": "/private/raw.txt"}),),
            }),
        )
