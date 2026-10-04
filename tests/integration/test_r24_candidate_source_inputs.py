"""Fresh corrected source inputs cannot inherit a historical payload identity."""

from pathlib import Path

import pytest

from tools.build_r24_desktop_candidate import build


def test_corrected_source_requires_both_payload_and_sidecar_pins(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = tmp_path / "must-not-be-created"
    with pytest.raises(ValueError, match="payload.*sidecar"):
        build(root, output, payload_path=root / ".artifacts/r24-71-safety-source-20261003/a.json")
    assert not output.exists()


def test_corrected_source_byte_drift_fails_before_project_creation(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = tmp_path / "must-not-be-created"
    with pytest.raises(ValueError, match="payload.*changed"):
        build(
            root, output,
            payload_path=root / ".artifacts/r24-71-safety-source-20261003/a.json",
            payload_sha256="0" * 64,
            sidecar_path=root / ".artifacts/r24-71-safety-source-20261003/a.derivation.json",
            sidecar_sha256="0" * 64,
        )
    assert not output.exists()
