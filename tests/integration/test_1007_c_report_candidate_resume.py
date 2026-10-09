"""A new C candidate must never overwrite an earlier report or adoption."""

from pathlib import Path

import pytest

from tools import ci_1007_prepare_c_report_candidate as candidate


@pytest.mark.parametrize("number", [-1, 0, 1])
def test_invalid_candidate_number_rejected_before_workspace_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, number: int
) -> None:
    monkeypatch.setattr(candidate, "ROOT", tmp_path)
    monkeypatch.setattr(candidate, "PROJECT", tmp_path / "missing-project")
    with pytest.raises(ValueError, match="candidate number"):
        candidate.main(candidate_number=number)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("number", [2, 3])
def test_frozen_candidate_refused_before_project_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, number: int
) -> None:
    monkeypatch.setattr(candidate, "ROOT", tmp_path)
    monkeypatch.setattr(candidate, "PROJECT", tmp_path / "missing-project")
    for existing in [2, 3]:
        receipt = (
            tmp_path / ".artifacts/1007-c-source-repairs-v1"
            / f"report-candidate-v{existing}/candidate-receipt.json"
        )
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_bytes(f"preserve v{existing}".encode())
    before = {p.relative_to(tmp_path): p.read_bytes()
              for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(SystemExit, match="already prepared"):
        candidate.main(candidate_number=number)
    assert {p.relative_to(tmp_path): p.read_bytes()
            for p in tmp_path.rglob("*") if p.is_file()} == before


def test_default_still_refuses_existing_v2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(candidate, "ROOT", tmp_path)
    monkeypatch.setattr(candidate, "PROJECT", tmp_path / "missing-project")
    receipt = (tmp_path / ".artifacts/1007-c-source-repairs-v1"
               / "report-candidate-v2/candidate-receipt.json")
    receipt.parent.mkdir(parents=True)
    receipt.write_bytes(b"original")
    with pytest.raises(SystemExit, match="already prepared"):
        candidate.main()
    assert receipt.read_bytes() == b"original"


def test_freeze_preserves_original_on_changed_candidate_bytes(tmp_path: Path) -> None:
    path = tmp_path / "frozen.json"
    digest = candidate.freeze(path, {"version": 2})
    assert candidate.freeze(path, {"version": 2}) == digest
    with pytest.raises(AssertionError, match="refuse frozen overwrite"):
        candidate.freeze(path, {"version": 3})
    assert candidate.sha(path) == digest
