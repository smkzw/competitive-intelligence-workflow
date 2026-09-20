import json
from pathlib import Path

import pytest

from ci_workflow.application import host_smoke_scenario as scenario
from ci_workflow.application import run_service

CATALOG = Path(__file__).resolve().parents[2] / "fixtures/catalog.yaml"


@pytest.mark.parametrize("damage", ["html", "snapshot"])
def test_completed_resume_rejects_damaged_report(tmp_path: Path, damage: str) -> None:
    scenario.run_host_smoke_scenario(project_root=tmp_path, catalog_path=CATALOG)
    path = next((tmp_path / "reports/A").glob("*/html.manifest.json"))
    manifest = json.loads(path.read_bytes())
    target = (
        tmp_path / manifest["artifact"]["relative_path"] / "efficacy.html"
        if damage == "html" else
        tmp_path / "snapshots/reports/A" / f'{manifest["report_snapshot_id"]}.json'
    )
    target.write_bytes(b"corrupted")
    with pytest.raises((ValueError, RuntimeError)):
        scenario.run_host_smoke_scenario(
            project_root=tmp_path, catalog_path=CATALOG, resume=True,
        )
    assert target.read_bytes() == b"corrupted"


def test_recovery_excludes_unrelated_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = run_service._render_html_a

    def crash(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("interrupt after commit")

    with monkeypatch.context() as patch:
        patch.setattr(run_service, "_render_html_a", crash)
        with pytest.raises(scenario.HostSmokeScenarioError):
            scenario.run_host_smoke_scenario(project_root=tmp_path, catalog_path=CATALOG)
    fake = tmp_path / "reports/B/v99/html.manifest.json"
    fake.parent.mkdir(parents=True)
    fake.write_text('{"project_id":"other","status":"failed"}')
    before = fake.read_bytes()
    result = scenario.run_host_smoke_scenario(
        project_root=tmp_path, catalog_path=CATALOG, resume=True,
    )
    assert result.run_result.exit_code == 0
    assert "reports/B/v99/html.manifest.json" not in result.record["final"]["artifact_digests"]
    assert fake.read_bytes() == before


@pytest.mark.parametrize("fault", ["missing", "site", "project", "contract"])
def test_explicit_report_reference_is_verified(tmp_path: Path, fault: str) -> None:
    result = scenario.run_host_smoke_scenario(project_root=tmp_path, catalog_path=CATALOG)
    rel = next(iter(result.record["final"]["artifact_digests"]))
    data = json.loads((tmp_path / rel).read_bytes())
    site = data["artifact"]["relative_path"]
    if fault == "missing":
        rel = "reports/A/missing/html.manifest.json"
    if fault == "site":
        site = "reports/A/other/html"
    with pytest.raises((ValueError, RuntimeError)):
        run_service._collect_outputs(
            tmp_path, {}, "completed", report_references={rel: site},
            project_id="other" if fault == "project" else data["project_id"],
            contract_version=data["contract_version"] + (fault == "contract"),
        )


@pytest.mark.parametrize("fault", ["missing", "wrong-report", "duplicate"])
def test_format_node_cannot_omit_or_misbind_report(fault: str) -> None:
    value = {
        "format": "html", "site_relative_path": "reports/A/v1/html",
        "manifest_relative_path": "reports/A/v1/html.manifest.json",
    }
    if fault == "missing":
        value.pop("manifest_relative_path")
    nodes = {("format:B" if fault == "wrong-report" else "format:A", "input1"): value}
    if fault == "duplicate":
        nodes[("format:A", "input2")] = value
    with pytest.raises(run_service.RunError):
        run_service._report_references_from_nodes(nodes)


def test_legacy_completion_without_references_is_not_silently_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tests.integration.test_fresh_a_scientific_review import (
        _run_ready_project,
        _write_a_project,
    )

    project = _write_a_project(tmp_path)
    assert _run_ready_project(project).outcome == "completed"
    before = {p: p.read_bytes() for p in (project / "reports").rglob("*") if p.is_file()}
    derive = run_service._derive_completed_nodes

    def legacy(events):
        completed = derive(events)
        for key, variants in completed.items():
            if key.startswith("format:"):
                for value in variants.values():
                    value["outputs"].pop("site_relative_path", None)
                    value["outputs"].pop("manifest_relative_path", None)
        return completed

    monkeypatch.setattr(run_service, "_derive_completed_nodes", legacy)
    with pytest.raises(run_service.RunError, match="历史格式节点缺少显式产物引用"):
        _run_ready_project(project, resume=True)
    assert before == {p: p.read_bytes() for p in (project / "reports").rglob("*") if p.is_file()}
