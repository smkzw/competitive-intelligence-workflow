"""Missing receipt resources must fail before spending a real host run."""
from pathlib import Path

import pytest

from ci_workflow.application import host_smoke as smoke


@pytest.mark.parametrize("damage", ["package_missing", "package_invalid", "root_invalid"])
def test_schema_damage_fails_before_any_host_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    packaged = tmp_path / "packaged.json"
    root = tmp_path / "root.json"
    packaged.write_text('{"type":"object"}')
    root.write_text('{"type":"object"}')
    if damage == "package_missing":
        packaged.unlink()
    elif damage == "package_invalid":
        packaged.write_text('{"type":"invented"}')
    else:
        root.write_text('not json')
    monkeypatch.setattr(smoke, "_PACKAGED_SCHEMA", packaged)
    monkeypatch.setattr(smoke, "_ROOT_SCHEMA", root)

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid installed resources reached host startup")

    monkeypatch.setattr(smoke.subprocess, "Popen", forbidden)
    project = tmp_path / "project"
    with pytest.raises(smoke.HostSmokeError, match="Schema"):
        smoke.run_host_smoke(
            "omp", project_root=project, require_external_host_process=True,
            omp_model="openai-codex/gpt-6.1-sol", omp_thinking="high",
        )
    assert not project.exists()
