"""F6 合同：发货 README 的交付面声明与 package-manifest 保持一致。

README.md 进入安装包（bundle allowlist）；它不得宣传被排除的输出格式，
也不得保留过时阶段状态（v1.4 §1.2、Reviewer-B F6）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_formats_match_package_manifest() -> None:
    manifest = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8"))
    formats = manifest["package"]["formats"]
    assert formats == ["html"]

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "formats: [\"html\"]" in readme or "formats: [\"html\"]".replace('"', '"') in readme
    # 排除格式不得作为当前交付面出现（历史代码留仓说明除外，措辞限定）。
    for excluded in ("原生 PDF", "HTML-PPT 与", "可编辑 PPTX"):
        assert excluded not in readme, f"README 宣传了排除格式：{excluded}"


def test_readme_has_no_stale_phase_marker() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert not re.search(r"Phase 0 基线建设", readme)
    assert "开发候选" in readme
