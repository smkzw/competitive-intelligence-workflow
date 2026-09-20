"""Only accepted immutable portals may advance the per-report latest pointer."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ci_workflow.application.latest_delivery import publish_latest_delivery, read_latest_delivery
from tests.hosts._helpers import make_project, write_accepted_html_site, write_html_site


def test_latest_is_atomic_idempotent_and_not_replaced_by_preview(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    assert read_latest_delivery(root, "A") is None
    write_html_site(root, "A", "preview")
    with pytest.raises(ValueError):
        publish_latest_delivery(root, "candidate-A-preview")
    assert not (root / "reports/A/latest.json").exists()
    first = write_accepted_html_site(root, "A", "v1")
    original = first.read_bytes()
    publication = publish_latest_delivery(root, "accepted-A-v1")
    path = root / "reports/A/latest.json"
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    assert publish_latest_delivery(root, "accepted-A-v1") == publication
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    write_accepted_html_site(root, "A", "v2")
    next_publication = publish_latest_delivery(root, "accepted-A-v2")
    assert next_publication.report_version == "v2"
    assert read_latest_delivery(root, "A") == next_publication
    with pytest.raises(ValueError, match="回退"):
        publish_latest_delivery(root, "accepted-A-v1")
    assert read_latest_delivery(root, "A") == next_publication
    assert first.read_bytes() == original


def test_latest_reopens_artifact_instead_of_trusting_pointer(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    entry = write_accepted_html_site(root, "A")
    publish_latest_delivery(root, "accepted-A-v1")
    entry.write_text("changed")
    with pytest.raises((ValueError, RuntimeError)):
        read_latest_delivery(root, "A")


def test_pending_child_contract_preserves_previous_accepted_portal(tmp_path: Path) -> None:
    from ci_workflow.application.project_service import create_project_workspace
    from ci_workflow.domain.contracts import create_project_contract, refresh_project_contract
    from ci_workflow.storage.migrations import persist_project_contract

    parent = create_project_contract(
        indication="测试适应症", reports=["A"], outputs=["html"], cutoff="2026-08-01",
    )
    root = create_project_workspace(tmp_path / "project", parent)
    write_accepted_html_site(root, "A", "v1")
    previous = publish_latest_delivery(root, "accepted-A-v1")
    child = refresh_project_contract(parent, cutoff="2026-08-02", created_at=datetime.now(UTC))
    persist_project_contract(root / "state/project.sqlite", child)
    path = root / "project.yaml"
    document = json.loads(path.read_bytes())
    document["project_contract_versions"].append(child.model_dump(mode="json"))
    document["active_contract_version"] = child.contract_version
    path.write_text(json.dumps(document))
    assert read_latest_delivery(root, "A") == previous
    write_accepted_html_site(root, "A", "v2")
    current = publish_latest_delivery(root, "accepted-A-v2")
    assert current.contract_version == 2
    assert read_latest_delivery(root, "A") == current


def test_failed_replace_preserves_previous_pointer_and_can_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ci_workflow.application.latest_delivery as module

    root = make_project(tmp_path)
    write_accepted_html_site(root, "A", "v1")
    previous = publish_latest_delivery(root, "accepted-A-v1")
    write_accepted_html_site(root, "A", "v2")
    path = root / "reports/A/latest.json"
    before = path.read_bytes()

    def unavailable(*args: object) -> None:
        raise OSError("synthetic replace interruption")

    with monkeypatch.context() as patch:
        patch.setattr(module.os, "replace", unavailable)
        with pytest.raises(OSError):
            publish_latest_delivery(root, "accepted-A-v2")
    assert path.read_bytes() == before
    assert read_latest_delivery(root, "A") == previous
    assert not tuple(path.parent.glob(".latest-*"))
    assert publish_latest_delivery(root, "accepted-A-v2").report_version == "v2"
