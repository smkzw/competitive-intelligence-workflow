from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tools.check_clean_tree import CleanTreeError, check_clean_tree
from tools.verify_rebaseline_source_set import (
    SourceSetError,
    validate_source_set_document,
    verify_source_set,
)

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "tools" / "gate.sh"
R0_GOVERNANCE = ROOT / "docs" / "governance" / "r0-provenance-and-quality-gate.md"
POSTQUALITY_SOURCE_SET = (
    ROOT / "docs" / "governance" / "rebaseline-release-source-set-v1-postquality.json"
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _new_git_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Governance Tests")
    (root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "--quiet", "-m", "baseline")
    return root


def test_clean_tree_is_fail_closed_and_requires_repository_root(tmp_path: Path) -> None:
    root = _new_git_repo(tmp_path)

    clean = check_clean_tree(root)
    assert clean.ok
    assert clean.entries == ()

    (root / "tracked.txt").write_text("staged change\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    staged = check_clean_tree(root)
    assert not staged.ok
    assert [(entry.code, entry.path) for entry in staged.unexpected] == [("M ", "tracked.txt")]

    (root / "draft.txt").write_text("not released\n", encoding="utf-8")
    dirty = check_clean_tree(root)
    assert not dirty.ok
    assert {(entry.code, entry.path) for entry in dirty.unexpected} == {
        ("M ", "tracked.txt"),
        ("??", "draft.txt"),
    }

    (root / "nested").mkdir()
    with pytest.raises(CleanTreeError, match="仓库根目录"):
        check_clean_tree(root / "nested")


def test_clean_tree_accepts_only_explicit_prefixes(tmp_path: Path) -> None:
    root = _new_git_repo(tmp_path)
    output = root / "runs" / "acceptance" / "case" / "result.json"
    output.parent.mkdir(parents=True)
    output.write_text("{}\n", encoding="utf-8")

    result = check_clean_tree(root, allow_prefixes=("runs/acceptance",))
    assert result.ok
    assert result.unexpected == ()

    with pytest.raises(CleanTreeError, match="不得包含绝对路径"):
        check_clean_tree(root, allow_prefixes=("../outside",))


def test_postquality_source_set_is_valid_historical_baseline_only(tmp_path: Path) -> None:
    payload = validate_source_set_document(POSTQUALITY_SOURCE_SET)
    assert payload["basis"]["file_count"] == 422
    assert payload["provenance"]["state"] == "dirty-baseline"
    assert payload["provenance"]["requires_clean_commit_for_release"] is True

    tampered = dict(payload)
    tampered["source_set_sha256"] = hashlib.sha256(b"tampered").hexdigest()
    tampered_path = tmp_path / "tampered-source-set.json"
    tampered_path.write_text(
        json.dumps(tampered, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SourceSetError, match="source_set_sha256 不匹配"):
        validate_source_set_document(tampered_path)

    invalid = dict(payload)
    invalid["roots"] = ["../outside"]
    invalid_path = tmp_path / "invalid-source-set.json"
    invalid_path.write_text(
        json.dumps(invalid, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(SourceSetError, match="来源集合 root包含非法路径段"):
        validate_source_set_document(invalid_path)

    with pytest.raises(SourceSetError, match="历史脏树基线不能证明发布就绪"):
        verify_source_set(POSTQUALITY_SOURCE_SET, root=ROOT, require_clean=True)


def test_gate_rejects_historical_source_set_clean_claim_before_running_steps() -> None:
    result = subprocess.run(
        [
            "bash",
            str(GATE),
            "--require-clean",
            "--source-set",
            str(POSTQUALITY_SOURCE_SET),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "GATE_USAGE_ERROR" in result.stderr
    assert "GATE_STEP" not in result.stdout + result.stderr


def test_r0_disk_hygiene_is_fail_closed_and_excludes_legacy_root() -> None:
    policy = R0_GOVERNANCE.read_text(encoding="utf-8")

    assert "里程碑磁盘卫生（R0.4）" in policy
    assert "禁止 broad glob、仓库级清理和 `git clean`" in policy
    assert "原始科学证据" in policy
    assert "当前和上一可恢复点" in policy
    assert "真实旧根不属于空间盘点对象" in policy
