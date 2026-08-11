from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_task_1_1_stable_ids_are_deterministic_namespaced_and_nonempty() -> None:
    assert (ROOT / "src/ci_workflow/domain/ids.py").is_file()
    from ci_workflow.domain.ids import stable_id

    first = stable_id("product", "  ABC-123  ", "CRSwNP")
    assert first == stable_id("product", "ABC-123", "CRSwNP")
    assert first != stable_id("trial", "ABC-123", "CRSwNP")
    assert first != stable_id("product", "ABC-124", "CRSwNP")
    assert stable_id("product", "ＡＢＣ") == stable_id("product", "ABC")
    assert stable_id("product", "ab", "c") != stable_id("product", "a", "bc")
    assert re.fullmatch(r"product_[0-9a-f]{24}", first)
    with pytest.raises(ValueError, match="不能为空"):
        stable_id("product", "")
    for invalid in (None, 0, False):
        with pytest.raises(ValueError, match="非空文本"):
            stable_id("product", invalid)  # type: ignore[arg-type]
