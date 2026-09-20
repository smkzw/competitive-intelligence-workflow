"""Task 10.6A：bundle clean-commit provenance、dirty fail-closed 与最终内容闭合。

全部测试只使用 pytest 临时目录中的独立 Git 仓库与手工 bundle manifest；
不读取真实仓库的 Git 状态，不创建真实 commit/tag，不触碰宿主或验收根。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.build_bundle import BundleBuildResult, build_bundle
from tools.build_bundle import main as build_main
from tools.bundle_contract import (
    BUNDLE_FORMAT,
    BUNDLE_MANIFEST_NAME,
    BUNDLE_SCHEMA_VERSION,
    FINAL_REQUIRED_CONTENT,
    BundleError,
    sha256_bytes,
    verify_bundle,
)
from tools.verify_bundle import main as verify_main

ALLOWLIST = ["package-manifest.json", "allowed"]


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return (completed.stdout or "").strip()


def _source_repo(tmp_path: Path) -> Path:
    """在临时目录构造一个恰好包含一个提交的独立 Git 仓库。"""

    root = tmp_path / "source"
    (root / "allowed").mkdir(parents=True)
    (root / "allowed" / "data.txt").write_text("允许内容\n", encoding="utf-8")
    (root / "package-manifest.json").write_text(
        json.dumps({"package": {"name": "candidate", "version": "1.0.0"}}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "bundle-provenance@example.com")
    _git(root, "config", "user.name", "bundle-provenance")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _build(root: Path, output: Path, commit: str | None = None) -> BundleBuildResult:
    return build_bundle(
        root,
        output,
        allowlist=ALLOWLIST,
        archive_name="candidate.tar.zst",
        expected_source_commit=commit,
    )


def _materialize_directory(
    result: BundleBuildResult,
    source_root: Path,
    destination: Path,
) -> Path:
    destination.mkdir(parents=True)
    shutil.copyfile(result.manifest_path, destination / BUNDLE_MANIFEST_NAME)
    for record in result.files:
        target = destination / record.path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / record.path, target)
    return destination


def _handcrafted_bundle(
    root: Path,
    files: dict[str, bytes],
    *,
    manifest_extra: dict[str, Any] | None = None,
) -> Path:
    """写出一个未经构建器的解包 bundle，用于校验器合同测试。"""

    root.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    for path in sorted(files):
        payload = files[path]
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        records.append(
            {"path": path, "sha256": sha256_bytes(payload), "bytes": len(payload)}
        )
    manifest: dict[str, Any] = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle": {
            "format": BUNDLE_FORMAT,
            "compression": "zstd",
            "manifest_path": BUNDLE_MANIFEST_NAME,
        },
        "allowlist": ["payload"],
        "files": records,
    }
    if manifest_extra is not None:
        manifest.update(manifest_extra)
    (root / BUNDLE_MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    return root


def _require_zstd() -> None:
    if shutil.which("zstd") is None:
        pytest.skip("zstd unavailable")


def test_clean_commit_build_records_provenance_and_stays_deterministic(tmp_path: Path) -> None:
    _require_zstd()
    root = _source_repo(tmp_path)
    head = _git(root, "rev-parse", "HEAD")

    first = _build(root, tmp_path / "dist", head)
    assert first.source_commit == head
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_commit"] == head

    second = _build(root, tmp_path / "dist", head)
    assert second.archive_sha256 == first.archive_sha256

    verified = verify_bundle(first.archive_path)
    assert verified.manifest["source_commit"] == head

    _git(root, "commit", "-q", "--allow-empty", "-m", "rc-second")
    new_head = _git(root, "rev-parse", "HEAD")
    assert new_head != head
    third = _build(root, tmp_path / "dist", new_head)
    assert third.source_commit == new_head
    # 树内容相同而 commit 不同：provenance 必须真正改变归档摘要。
    assert third.archive_sha256 != first.archive_sha256


def test_build_cli_prints_provenance_on_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _require_zstd()
    root = _source_repo(tmp_path)
    head = _git(root, "rev-parse", "HEAD")
    rc = build_main(
        [
            "--source-root",
            str(root),
            "--output",
            str(tmp_path / "dist"),
            "--allowlist",
            "package-manifest.json",
            "--allowlist",
            "allowed",
            "--archive-name",
            "candidate.tar.zst",
            "--from-clean-commit",
            head,
        ]
    )
    assert rc == 0
    assert f"source_commit={head}" in capsys.readouterr().out


def test_dirty_tree_fails_closed_without_writing_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _require_zstd()
    root = _source_repo(tmp_path)
    head = _git(root, "rev-parse", "HEAD")
    dist = tmp_path / "dist"
    argv = [
        "--source-root",
        str(root),
        "--output",
        str(dist),
        "--archive-name",
        "candidate.tar.zst",
        "--from-clean-commit",
        head,
    ]

    (root / "allowed" / "untracked.txt").write_text("未跟踪\n", encoding="utf-8")
    assert build_main(argv) == 2
    captured = capsys.readouterr()
    assert "BUNDLE_ERROR" in captured.err
    assert "不干净" in captured.err
    assert not dist.exists()

    (root / "allowed" / "untracked.txt").unlink()
    (root / "allowed" / "data.txt").write_text("已修改\n", encoding="utf-8")
    assert build_main(argv) == 2
    assert "不干净" in capsys.readouterr().err
    assert not dist.exists()

    _git(root, "add", "-A")
    assert build_main(argv) == 2
    assert "不干净" in capsys.readouterr().err
    assert not dist.exists()


def test_clean_commit_gate_rejects_head_drift_and_bad_refs(tmp_path: Path) -> None:
    _require_zstd()
    root = _source_repo(tmp_path)
    first_head = _git(root, "rev-parse", "HEAD")
    _git(root, "commit", "-q", "--allow-empty", "-m", "second")
    second_head = _git(root, "rev-parse", "HEAD")
    drift_output = tmp_path / "dist-drift"
    unknown_output = tmp_path / "dist-unknown"

    with pytest.raises(BundleError, match="不一致"):
        _build(root, drift_output, first_head)
    with pytest.raises(BundleError, match="无法解析"):
        _build(root, unknown_output, "0" * 40)
    with pytest.raises(BundleError, match="不是安全的"):
        _build(root, tmp_path / "dist-evil", "--upload-pack=evil")
    assert not drift_output.exists()
    assert not unknown_output.exists()

    # 解析到 HEAD 的引用允许使用，但 manifest 必须记录完整 SHA。
    resolved = _build(root, tmp_path / "dist-resolved", "HEAD")
    assert resolved.source_commit == second_head


def test_clean_commit_gate_requires_repo_toplevel(tmp_path: Path) -> None:
    root = _source_repo(tmp_path)
    head = _git(root, "rev-parse", "HEAD")
    with pytest.raises(BundleError, match="仓库根目录"):
        build_bundle(
            root / "allowed",
            tmp_path / "dist-subdir",
            allowlist=["data.txt"],
            expected_source_commit=head,
        )

    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "data.txt").write_text("无仓库\n", encoding="utf-8")
    with pytest.raises(BundleError, match="Git 仓库"):
        build_bundle(
            plain,
            tmp_path / "dist-plain",
            allowlist=["data.txt"],
            expected_source_commit=head,
        )


def test_manifest_rejects_unknown_and_malformed_fields(
    tmp_path: Path,
) -> None:
    _require_zstd()
    root = _source_repo(tmp_path)
    result = _build(root, tmp_path / "dist")

    def mutated_copy(name: str, mutate: Callable[[dict[str, Any]], None]) -> Path:
        bundle = _materialize_directory(result, root, tmp_path / name)
        manifest = json.loads((bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
        mutate(manifest)
        (bundle / BUNDLE_MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return bundle

    cases: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
        ("top-unknown", lambda m: m.update({"extraneous": True}), "未知字段"),
        ("bundle-unknown", lambda m: m["bundle"].update({"extra": 1}), "未知字段"),
        ("package-unknown", lambda m: m["package"].update({"stage": "x"}), "未知字段"),
        ("bad-commit", lambda m: m.update({"source_commit": "ABC123"}), "source_commit"),
        ("slash-name", lambda m: m["package"].update({"name": "a/b"}), "路径分隔符"),
        (
            "missing-version",
            lambda m: m["package"].pop("version"),
            "package.version 无效",
        ),
    ]
    for name, mutate, expected in cases:
        with pytest.raises(BundleError, match=expected):
            verify_bundle(mutated_copy(f"bundle-{name}", mutate))


def test_expected_source_commit_binding_is_exact(tmp_path: Path) -> None:
    commit = "b" * 40
    files = {"payload/data.txt": b"payload\n"}
    bundle = _handcrafted_bundle(
        tmp_path / "with-commit",
        files,
        manifest_extra={"source_commit": commit},
    )
    verified = verify_bundle(bundle, expected_source_commit=commit)
    assert verified.manifest["source_commit"] == commit

    with pytest.raises(BundleError, match="不一致"):
        verify_bundle(bundle, expected_source_commit="c" * 40)

    bare = _handcrafted_bundle(tmp_path / "without-commit", files)
    with pytest.raises(BundleError, match="不一致"):
        verify_bundle(bare, expected_source_commit=commit)

    with pytest.raises(BundleError, match="期望 source_commit 必须"):
        verify_bundle(bundle, expected_source_commit="HEAD")


def test_final_content_closure_gate_and_cli_tokens(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    files = {path: f"{path}\n".encode() for path in FINAL_REQUIRED_CONTENT}
    complete = _handcrafted_bundle(tmp_path / "complete", files)
    assert verify_bundle(complete, require_final_content=True).files

    assert verify_main(["--bundle", str(complete), "--require-final-content"]) == 0
    out = capsys.readouterr().out
    assert "BUNDLE_OK" in out
    assert "catalog=required-v12" in out

    committed = _handcrafted_bundle(
        tmp_path / "committed",
        files,
        manifest_extra={"source_commit": "b" * 40},
    )
    assert verify_main(["--bundle", str(committed)]) == 0
    assert f"source_commit={'b' * 40}" in capsys.readouterr().out

    reduced = dict(files)
    reduced.pop("skills/competitive-intelligence-workflow/SKILL.md")
    incomplete = _handcrafted_bundle(tmp_path / "incomplete", reduced)
    with pytest.raises(BundleError, match="未随包闭合"):
        verify_bundle(incomplete, require_final_content=True)
    assert verify_main(["--bundle", str(incomplete), "--require-final-content"]) == 2
    assert "未随包闭合" in capsys.readouterr().err
