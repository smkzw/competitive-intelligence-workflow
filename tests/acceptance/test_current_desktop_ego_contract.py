"""Current desktop viewport contract; synthetic binding, not real visual evidence."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application import acceptance_runner as runner

DESKTOP = ((1440, 900), (1600, 900), (1920, 1080), (2560, 1440))
LEGACY = ((1024, 768), (1280, 800), (1440, 900), (1920, 1080))


def _bind(tmp_path: Path, report: str, viewports: tuple[tuple[int, int], ...]) -> dict:
    instant = datetime.now(UTC)
    artifact = runner.CurrentHtmlArtifact(
        report=report, version="synthetic-desktop-v1",
        site_relative_path=f"reports/{report}/synthetic/html", site_sha256="1" * 64,
        site_byte_size=10, manifest_relative_path=f"reports/{report}/synthetic/manifest.json",
        manifest_sha256="2" * 64, manifest_id="synthetic-manifest",
        report_snapshot_id="synthetic-snapshot", generated_at=instant.isoformat(),
        entry_route="overview.html", entry_relative_path="overview.html",
        entry_sha256="3" * 64, routes=("overview.html",),
    )
    path = tmp_path / "ego-receipt.json"
    path.write_text(json.dumps({
        "schema_version": "1.0", "tool": "ego-lite", "ok": True,
        "report": report, "version": artifact.version, "run_id": "synthetic-run",
        "pre_rc_run_id": "synthetic-pre-rc", "manifest_id": artifact.manifest_id,
        "report_snapshot_id": artifact.report_snapshot_id,
        "site_digest": artifact.site_sha256, "routes": list(artifact.routes),
        "viewports": viewports, "pages": [{"route": "overview.html", "ok": True}],
        "verified_at": instant.isoformat(),
    }), encoding="utf-8")
    return runner._load_and_bind_ego_receipt(
        path, report=report, artifact=artifact, project_root=tmp_path,
        run_id="synthetic-run", started_at=instant, pre_rc_run_id="synthetic-pre-rc",
    )


def test_release_viewports_match_current_prd_and_not_retired_mobile_gate() -> None:
    assert runner.PRESCRIBED_VIEWPORTS == DESKTOP


@pytest.mark.parametrize("report", ("A", "B", "C"))
def test_each_report_binds_current_desktop_receipt(tmp_path: Path, report: str) -> None:
    result = _bind(tmp_path, report, DESKTOP)
    assert result["viewports"] == [list(viewport) for viewport in DESKTOP]


@pytest.mark.parametrize("report", ("A", "B", "C"))
def test_legacy_viewport_receipt_cannot_authorize_current_release(
    tmp_path: Path, report: str,
) -> None:
    with pytest.raises(runner.AcceptanceRunnerError, match="规定视口"):
        _bind(tmp_path, report, LEGACY)


def test_missing_receipt_guidance_uses_same_current_viewport_authority(tmp_path: Path) -> None:
    guidance = runner._ego_receipt_guidance(
        [tmp_path / "missing.json"], run_id="synthetic-run", pre_rc_run_id="synthetic-pre-rc",
    )
    for width, height in DESKTOP:
        assert f"{width}x{height}" in guidance
    assert "1024x768" not in guidance
    assert "1280x800" not in guidance
