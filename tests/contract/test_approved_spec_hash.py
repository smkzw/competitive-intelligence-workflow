from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPROVED_SPEC = ROOT / "docs" / "specs" / "competitive-intelligence-workflow-design-v1.2.md"
APPROVED_SPEC_SHA256 = "f96be175464d06f4a4b2075f020016148e3ac864d07b7ffe05a27db476ca465f"


def test_approved_v1_2_spec_copy_remains_byte_identical() -> None:
    actual = hashlib.sha256(APPROVED_SPEC.read_bytes()).hexdigest()
    assert actual == APPROVED_SPEC_SHA256
