"""Fixed public C source tests must not depend on ignored local run products."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType

import pytest

from tests.integration import test_r24_c_ctgov_protocol_atoms as atoms
from tests.integration import test_r24_ctgov_c_design_projection as projection
from tools.bundle_contract import DEFAULT_ALLOWLIST


@pytest.mark.parametrize("module", [atoms, projection], ids=["atoms", "projection"])
def test_fixed_source_lives_in_portable_test_fixture(module: ModuleType) -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "tests/fixtures/ctgov-c-source"
    assert fixture == module._CAS_ROOT
    digest = module._CAS_DIGEST
    asset = fixture / f"evidence/raw/sha256/{digest[:2]}/{digest}.bin"
    assert asset.is_file() and not asset.is_symlink()
    assert hashlib.sha256(asset.read_bytes()).hexdigest() == digest
    assert asset.stat().st_size == 2_251_577


def test_fixed_registry_raw_is_not_part_of_skill_install_payload() -> None:
    fixture = Path("tests/fixtures/ctgov-c-source")
    assert all(
        not fixture.is_relative_to(Path(entry))
        and not Path(entry).is_relative_to(fixture)
        for entry in DEFAULT_ALLOWLIST
    )
