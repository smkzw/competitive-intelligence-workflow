"""Native source refresh entry: real transaction, synthetic accepted test atoms.

This is command/runtime verification, not independent scientific acceptance.
"""

import json
from pathlib import Path

import pytest

from ci_workflow.cli import main
from tests.integration.test_r24_source_current_refresh import (
    SOURCE_FACT_2,
    SOURCE_VERSION_2,
    _new_bindings,
    _read_current,
    _refresh_command,
    _seed_source_atom,
    _world,
    _write_new_inputs,
)


@pytest.mark.parametrize("accepted", [True, False])
def test_source_refresh_command_calls_real_atomic_service(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], accepted: bool,
) -> None:
    world = _world(tmp_path, complete_workspace=True)
    paths = _write_new_inputs(
        world.root, source_version=SOURCE_VERSION_2, value=50.0,
        raw="50.0% (31/62)", numerator=31, denominator=62,
    )
    _seed_source_atom(
        world.root, version_id=SOURCE_FACT_2, source_version=SOURCE_VERSION_2,
        raw="50.0% (31/62)", normalized="50.0", numerator=31, denominator=62,
        bindings=_new_bindings(world.root, paths),
        review_state="accepted" if accepted else "candidate",
    )
    command = _refresh_command(world, paths=paths)
    path = world.root / "inputs/source-refresh.json"
    path.write_text(command.model_dump_json(exclude_unset=True), encoding="utf-8")
    args = ["project", "refresh-source", "--root", str(world.root), "--command", str(path)]
    code = main(args)
    output = capsys.readouterr()
    current = _read_current(world.root)
    if accepted:
        assert code == 0, output.err
        result = json.loads(output.out.removeprefix("SOURCE_REFRESHED "))
        assert result["revision"] == 1
        assert result["rebuilt_reports"] == ["A", "B"]
        assert current.request_id == command.request_id
        assert main(args) == 0
        assert _read_current(world.root) == current
    else:
        assert code == 2
        assert "候选不得自动晋级" in output.err
        assert current == world.current


def test_malformed_source_refresh_command_does_not_create_a_project_or_echo_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "not-a-project"
    path = tmp_path / "bad-command.json"
    path.write_text('{"private_marker":"do-not-echo-this"}', encoding="utf-8")
    assert main([
        "project", "refresh-source", "--root", str(project), "--command", str(path),
    ]) == 2
    output = capsys.readouterr()
    assert "do-not-echo-this" not in output.out + output.err
    assert not project.exists()
