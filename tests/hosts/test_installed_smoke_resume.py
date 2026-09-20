from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ci_workflow.application import host_smoke_runner as runner


def _setup(tmp_path: Path) -> tuple[Any, Path, Path]:
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text("fixture identity", encoding="utf-8")
    manifest = tmp_path / "package-manifest.json"
    manifest.write_text("package identity", encoding="utf-8")
    layout = SimpleNamespace(bundle_digest="a" * 64, package_manifest=manifest)
    return layout, tmp_path / "project", catalog


def test_resume_preserves_existing_project(tmp_path: Path) -> None:
    layout, project, catalog = _setup(tmp_path)
    runner._prepare_smoke_project(
        project, layout=layout, host="codex", catalog=catalog, resume=False,
    )
    sentinel = project / "sentinel"
    sentinel.write_bytes(b"preserve")
    runner._prepare_smoke_project(
        project, layout=layout, host="codex", catalog=catalog, resume=True,
    )
    assert sentinel.read_bytes() == b"preserve"


@pytest.mark.parametrize("change", ["bundle", "catalog", "host", "missing"])
def test_resume_rejects_identity_drift(tmp_path: Path, change: str) -> None:
    layout, project, catalog = _setup(tmp_path)
    if change != "missing":
        runner._prepare_smoke_project(
            project, layout=layout, host="codex", catalog=catalog, resume=False,
        )
    if change == "bundle":
        layout.bundle_digest = "b" * 64
    if change == "catalog":
        catalog.write_text("changed", encoding="utf-8")
    with pytest.raises(runner.HostSmokeRunnerError):
        runner._prepare_smoke_project(
            project, layout=layout, host="omp" if change == "host" else "codex",
            catalog=catalog, resume=True,
        )


def test_new_run_rejects_nonempty_project(tmp_path: Path) -> None:
    layout, project, catalog = _setup(tmp_path)
    project.mkdir()
    (project / "sentinel").write_bytes(b"keep")
    with pytest.raises(runner.HostSmokeRunnerError):
        runner._prepare_smoke_project(
            project, layout=layout, host="codex", catalog=catalog, resume=False,
        )
    assert (project / "sentinel").read_bytes() == b"keep"


def test_single_resume_reaches_lower_layer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ci_workflow.application import host_smoke

    layout, project, catalog = _setup(tmp_path)
    layout.bundle_root = tmp_path / "bundle"
    layout.install_root = tmp_path
    layout.entrypoint = tmp_path / "bin" / "ci-workflow"
    layout.verify_layout = lambda: None
    runner._prepare_smoke_project(
        project, layout=layout, host="codex", catalog=catalog, resume=False,
    )
    (project / "sentinel").write_bytes(b"preserve")
    monkeypatch.setattr(runner, "_candidate_environment", lambda _: nullcontext())
    monkeypatch.setattr(host_smoke, "resolve_real_entry", lambda **_: object())

    def reached(*args: Any, **kwargs: Any) -> Any:
        assert kwargs["resume"] is True
        assert kwargs["project_root"] == project
        raise host_smoke.HostSmokeError("LOWER_LAYER_REACHED")

    monkeypatch.setattr(host_smoke, "run_host_smoke", reached)
    with pytest.raises(runner.HostSmokeRunnerError, match="LOWER_LAYER_REACHED"):
        runner.run_installed_single_host_smoke(
            layout, host="codex", receipt_path=tmp_path / "receipt.json",
            project_root=project, catalog_path=catalog, resume=True,
        )
    assert (project / "sentinel").read_bytes() == b"preserve"


def test_batch_binds_every_project_before_first_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ci_workflow.application import host_smoke

    layout, projects, catalog = _setup(tmp_path)
    layout.bundle_root = tmp_path / "bundle"
    layout.install_root = tmp_path
    layout.entrypoint = tmp_path / "bin" / "ci-workflow"
    layout.verify_layout = lambda: None
    monkeypatch.setattr(runner, "_candidate_environment", lambda _: nullcontext())
    monkeypatch.setattr(host_smoke, "resolve_real_entry", lambda **_: object())

    def failed_dispatch(*args: Any, **kwargs: Any) -> Any:
        for host in runner.HOSTS:
            assert (projects / host).is_dir()
            assert (projects / f".{host}.host-smoke-binding.json").is_file()
        raise host_smoke.HostSmokeError("ISOLATED_DISPATCH_FAILURE")

    monkeypatch.setattr(host_smoke, "run_host_smoke", failed_dispatch)
    with pytest.raises(runner.HostSmokeRunnerError, match="ISOLATED_DISPATCH_FAILURE"):
        runner.run_installed_host_smoke(layout, project_root=projects, catalog_path=catalog)


@pytest.mark.parametrize("host", runner.HOSTS)
def test_external_host_receives_explicit_project_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host: str,
) -> None:
    from ci_workflow.application import host_smoke

    monkeypatch.setattr(host_smoke, "_load_smoke_case", lambda _: (
        {"reports": ["A"], "outputs": ["html"], "expected": {"outcome": "rendered"}},
        tmp_path,
    ))
    monkeypatch.setattr(host_smoke, "resolve_host_executable", lambda *a, **k: (
        {"path": str(tmp_path / host)}, None,
    ))

    def capture(argv: list[str], **kwargs: Any) -> Any:
        prompt = argv[-1]
        assert "--resume" in prompt
        assert "不得重新初始化" in prompt
        raise host_smoke.HostSmokeError("PROMPT_CAPTURED_WITHOUT_DISPATCH")

    monkeypatch.setattr(host_smoke.subprocess, "Popen", capture)
    with pytest.raises(host_smoke.HostSmokeError, match="PROMPT_CAPTURED_WITHOUT_DISPATCH"):
        host_smoke.run_host_smoke(
            host, project_root=tmp_path / "project",
            entry=SimpleNamespace(command=(str(tmp_path / "ci-workflow"),)),
            resume=True, require_external_host_process=True,
        )
