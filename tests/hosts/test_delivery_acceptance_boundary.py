"""Host delivery must be supported by acceptance, not an index filename."""

import json
from pathlib import Path

import pytest

from ci_workflow.application.capability_preflight import StaticCapabilityProbe
from ci_workflow.hosts.codex import CodexHostAdapter
from ci_workflow.hosts.hermes import HermesHostAdapter
from ci_workflow.hosts.omp import OmpHostAdapter
from tests.hosts._helpers import append_project_state, make_project, write_html_site


@pytest.mark.parametrize("adapter_type", [CodexHostAdapter, HermesHostAdapter, OmpHostAdapter])
def test_preview_file_is_not_delivered(tmp_path: Path, adapter_type: type) -> None:
    project = make_project(tmp_path)
    write_html_site(project, "A")
    receipt = adapter_type(probe=StaticCapabilityProbe()).build_semantic_receipt(
        project_root=project,
    )
    assert receipt.artifacts == ()


def test_complete_event_without_accepted_artifacts_does_not_claim_delivery(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    append_project_state(project, to_state="complete")
    receipt = CodexHostAdapter(probe=StaticCapabilityProbe()).build_semantic_receipt(
        project_root=project,
    )
    assert receipt.canonical_state != "complete"
    assert "全部报告已完成交付" not in receipt.primary_status_zh


@pytest.mark.parametrize("damage", ["html", "snapshot", "verifier", "predecessor", "symlink"])
def test_accepted_label_cannot_hide_drift(tmp_path: Path, damage: str) -> None:
    from ci_workflow.application.delivered_artifacts import read_accepted_html_artifacts
    from ci_workflow.storage.manifest_store import ManifestIntegrityError
    from tests.hosts._helpers import write_accepted_html_site

    project = make_project(tmp_path)
    entry = write_accepted_html_site(project, "A")
    assert len(read_accepted_html_artifacts(project)) == 1
    accepted = project / "manifests/artifacts/accepted-A-v1.json"
    if damage == "html":
        entry.write_text("changed")
    elif damage == "snapshot":
        snapshot = next((project / "snapshots/reports/A").glob("*.json"))
        snapshot.write_text("{}")
    elif damage == "verifier":
        payload = json.loads(accepted.read_bytes())
        payload["accepted_by"] = "different-reviewer"
        accepted.write_text(json.dumps(payload))
    elif damage == "predecessor":
        (project / "manifests/artifacts/candidate-A-v1.json").unlink()
    else:
        target = project / "copied.html"
        target.write_bytes(entry.read_bytes())
        entry.unlink()
        entry.symlink_to(target)
    with pytest.raises((ValueError, RuntimeError, OSError, ManifestIntegrityError)):
        read_accepted_html_artifacts(project)
