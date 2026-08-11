from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from ci_workflow.domain.enums import OutputFormat, ReportKind
from ci_workflow.storage.paths import ArtifactPathService, ArtifactPathViolation


@pytest.mark.parametrize("report", list(ReportKind))
@pytest.mark.parametrize("output", list(OutputFormat))
def test_artifact_path_service_is_the_only_versioned_report_path_generator(
    report: ReportKind,
    output: OutputFormat,
) -> None:
    service = ArtifactPathService()
    version = "v1.0"
    version_root = PurePosixPath("reports", report.value, version)
    expected = {
        OutputFormat.HTML: version_root / "html",
        OutputFormat.PDF: version_root / "report.pdf",
        OutputFormat.HTML_PPT: version_root / "html-ppt",
        OutputFormat.PPTX: version_root / "report.pptx",
    }

    assert service.artifact(report, version, output) == expected[output]
    assert service.manifest(report, version, output) == version_root / (
        f"{output.value}.manifest.json"
    )
    assert service.coverage_projection(report, version, output) == version_root / (
        f"{output.value}.coverage-projection.json"
    )
    for path in (
        expected[output],
        service.manifest(report, version, output),
        service.coverage_projection(report, version, output),
    ):
        assert not path.is_absolute()
        assert service.validate_persisted_path(path) == path


@pytest.mark.parametrize(
    "path",
    (
        "reports/c/html",
        ".artifacts/report-a/html",
        "reports/A/html",
        "reports/A/v1.0/../report.pdf",
        "/tmp/reports/A/v1.0/report.pdf",
        "reports/A/v1.0/custom.pdf",
        "reports/A/v1.0/pdf/report.pdf",
    ),
)
def test_noncanonical_or_machine_bound_artifact_paths_fail_closed(path: str) -> None:
    with pytest.raises(ArtifactPathViolation):
        ArtifactPathService().validate_persisted_path(path)


@pytest.mark.parametrize("version", ("", ".", "..", "V1", "v 1", "v1/other"))
def test_report_version_is_one_safe_lowercase_segment(version: str) -> None:
    with pytest.raises(ArtifactPathViolation):
        ArtifactPathService().artifact(ReportKind.A, version, OutputFormat.HTML)
