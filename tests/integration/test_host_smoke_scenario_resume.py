"""Synthetic local recovery contract; no external host acceptance."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ci_workflow.application import host_smoke_scenario as scenario

CATALOG = Path(__file__).resolve().parents[2] / "fixtures/catalog.yaml"


def test_resume_missing_evidence(tmp_path):
    with pytest.raises(scenario.HostSmokeScenarioError, match="恢复证据"):
        scenario.run_host_smoke_scenario(
            project_root=tmp_path / "missing", catalog_path=CATALOG, resume=True
        )


def test_completed_resume_is_noop(tmp_path):
    first = scenario.run_host_smoke_scenario(project_root=tmp_path, catalog_path=CATALOG)
    events = (tmp_path / "events/events.jsonl").read_bytes()
    record = first.record_path.read_bytes()
    second = scenario.run_host_smoke_scenario(
        project_root=tmp_path, catalog_path=CATALOG, resume=True
    )
    assert second.run_result == first.run_result
    assert second.record_path.read_bytes() == record
    assert (tmp_path / "events/events.jsonl").read_bytes() == events


def cli(root, *extra):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ci_workflow",
            "fixture",
            "run",
            "--case",
            "host-smoke-v1",
            "--reports",
            "A",
            "--project",
            str(root),
            "--catalog",
            str(CATALOG),
            "--host-smoke-recovery",
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("point", ["reopen", "rebind", "copy", "render", "mid_render", "rendered"])
def test_interrupted_resume(tmp_path, monkeypatch, point):
    def crash_after(original):
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("synthetic interruption")

        return interrupted

    with monkeypatch.context() as patch:
        if point in ("reopen", "rebind"):
            name = "reopen_project" if point == "reopen" else "rebind_report"
            patch.setattr(
                scenario.PartialDeliveryCoordinator,
                name,
                crash_after(getattr(scenario.PartialDeliveryCoordinator, name)),
            )
        elif point == "copy":
            original = scenario.shutil.copyfile

            def interrupted_copy(source, target, *args, **kwargs):
                result = original(source, target, *args, **kwargs)
                if Path(target) == tmp_path / scenario.CANONICAL_REPORT_DATA_RELATIVE_PATH:
                    raise RuntimeError("synthetic interruption")
                return result

            patch.setattr(scenario.shutil, "copyfile", interrupted_copy)
        elif point == "mid_render":
            from ci_workflow.storage.render_transaction import UnpublishedRenderTransaction

            def before_commit(*args, **kwargs):
                raise RuntimeError("synthetic interruption")

            patch.setattr(UnpublishedRenderTransaction, "commit", before_commit)
        elif point == "rendered":
            patch.setattr(scenario, "run_project", crash_after(scenario.run_project))
        else:

            def interrupted_render(*args, **kwargs):
                raise RuntimeError("synthetic interruption")

            patch.setattr(scenario, "run_project", interrupted_render)
        with pytest.raises(RuntimeError):
            scenario.run_host_smoke_scenario(project_root=tmp_path, catalog_path=CATALOG)
    initial_path = tmp_path / "state/host-smoke-v1-initial-manifest.json"
    initial_bytes = initial_path.read_bytes()
    initial = json.loads((tmp_path / scenario.SCENARIO_RECORD_RELATIVE).read_text())["initial"]
    result = cli(tmp_path, "--resume")
    assert result.returncode == 0, result.stderr
    record = json.loads((tmp_path / scenario.SCENARIO_RECORD_RELATIVE).read_text())
    assert record["initial"] == initial
    assert initial_path.read_bytes() == initial_bytes
    events = scenario.EventStore(tmp_path).read_all()
    for key in ("reopen", "rebind"):
        matching = [e for e in events if e.event_id == record["recovery"][f"{key}_event_id"]]
        assert len(matching) == 1
        assert matching[0].event_digest == record["recovery"][f"{key}_event_digest"]
    replay = cli(tmp_path, "--resume")
    assert replay.returncode == 0, replay.stderr
    assert scenario.EventStore(tmp_path).read_all() == events


def test_cli_positive_and_missing_negative(tmp_path):
    missing = cli(tmp_path / "missing", "--resume")
    assert missing.returncode != 0
    assert "恢复证据" in missing.stderr
    assert not (tmp_path / "missing").exists()
    first = cli(tmp_path / "project")
    assert first.returncode == 0, first.stderr
    assert cli(tmp_path / "project", "--resume").returncode == 0
    assert cli(tmp_path / "project").returncode != 0
    assert cli(tmp_path / "other", "--case", "wrong", "--resume").returncode != 0


@pytest.mark.parametrize(
    "target",
    [
        "initial",
        "events",
        "input",
        "universe",
        "manifest",
        "record",
        "result",
        "binding",
        "contract",
    ],
)
def test_tamper_rejected(tmp_path, target):
    first = scenario.run_host_smoke_scenario(project_root=tmp_path, catalog_path=CATALOG)
    paths = {
        "initial": "state/host-smoke-v1-initial-manifest.json",
        "events": "events/events.jsonl",
        "input": scenario.CANONICAL_REPORT_DATA_RELATIVE_PATH,
        "universe": scenario.CANONICAL_UNIVERSE_RELATIVE_PATH,
        "binding": "events/events.jsonl",
        "contract": "project.yaml",
        "manifest": "manifests/current_run.json",
        "record": scenario.SCENARIO_RECORD_RELATIVE,
        "result": scenario.SCENARIO_RECORD_RELATIVE,
    }
    path = tmp_path / paths[target]
    if target in ("record", "result"):
        record = first.record
        if target == "record":
            record["recovery"]["rebind_event_id"] = "forged"
        else:
            record["result"]["run_id"] = "forged"
        path.write_text(json.dumps(record))
    elif target == "binding":
        from ci_workflow.storage.event_store import WorkflowEvent, _event_digest

        events = [json.loads(line) for line in path.read_text().splitlines()]
        event = next(
            e for e in events if e["event_id"] == first.record["recovery"]["rebind_event_id"]
        )
        event["payload"]["new_object_id"] = "report_A_wrong"
        source = WorkflowEvent.model_validate(
            {k: v for k, v in event.items() if k not in ("sequence", "event_digest")}
        )
        event["event_digest"] = _event_digest(source, event["sequence"])
        path.write_text("".join(json.dumps(e) + "\n" for e in events))
    else:
        path.write_bytes(path.read_bytes() + b"tamper")
    before = path.read_bytes()
    result = cli(tmp_path, "--resume")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert path.read_bytes() == before


def test_cli_surface_stays_seventeen():
    import argparse

    from ci_workflow.cli import _build_parser

    def leaves(parser):
        actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        return sum(leaves(child) for a in actions for child in a.choices.values()) if actions else 1

    # 17 = 15 + fetch-pubmed + semantic-review（P2 路线与 P3.7 流程接线，均经主线程验收）。
    assert leaves(_build_parser()) == 17


def test_committed_artifact_without_node_completion_recovers_without_overwrite(
    tmp_path, monkeypatch,
):
    """Recover the verified committed artifact without rerendering its bytes."""
    from ci_workflow.application import run_service

    original = run_service._render_html_a

    def after_commit(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("synthetic interruption after artifact commit")

    with monkeypatch.context() as patch:
        patch.setattr(run_service, "_render_html_a", after_commit)
        with pytest.raises(scenario.HostSmokeScenarioError):
            scenario.run_host_smoke_scenario(project_root=tmp_path, catalog_path=CATALOG)
    reports = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in (tmp_path / "reports").rglob("*")
        if p.is_file()
    }
    result = cli(tmp_path, "--resume")
    assert result.returncode == 0, result.stderr
    assert all((tmp_path / rel).read_bytes() == content for rel, content in reports.items())
    assert "final" in json.loads((tmp_path / scenario.SCENARIO_RECORD_RELATIVE).read_text())
