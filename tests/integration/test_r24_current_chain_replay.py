"""Replay tooling must verify its fixed source before creating a working copy."""

import json
from hashlib import sha256
from pathlib import Path

import pytest

from tools.replay_r24_current_chain import (
    validate_current_safety_projection,
    verify_source_candidate,
)


def test_public_clear_keeps_chinese_label_and_original_source() -> None:
    row = {"value": None, "source_text": "1", "numerator": None,
           "denominator": None, "disclosure_state": "用户清除，待重新核实"}
    validate_current_safety_projection(row, expected=None, original_source="1")
    for field, value in (("value", 0), ("source_text", ""), ("numerator", 1),
                         ("disclosure_state", "来源未公开")):
        with pytest.raises(AssertionError):
            validate_current_safety_projection(
                {**row, field: value}, expected=None, original_source="1",
            )


def test_replay_rejects_source_drift_before_copying(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    inputs = candidate / "source-project/inputs"
    inputs.mkdir(parents=True)
    for name in ("a", "b"):
        (inputs / f"{name}.json").write_text("{}")
    manifest = {
        "current_generation_switched": False,
        "source_snapshot_sha256": "0" * 64,
        "rendered_files": {
            f"source-project/inputs/{name}.json": sha256(b"{}").hexdigest()
            for name in ("a", "b")
        },
    }
    (candidate / "candidate-manifest.json").write_text(json.dumps(manifest))
    (inputs / "a.json").write_text('{"changed":true}')
    with pytest.raises(ValueError, match="drift"):
        verify_source_candidate(tmp_path, candidate)


def test_replay_rejects_out_of_root_or_symlink_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside"):
        verify_source_candidate(tmp_path, tmp_path.parent)
    target = tmp_path / "source"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        verify_source_candidate(tmp_path, link)
