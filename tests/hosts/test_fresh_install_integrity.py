"""G6-02: real release archives and isolated installs, never host runners."""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import tarfile
import zipfile
from collections.abc import Iterator
from copy import copy
from pathlib import Path

import pytest

from ci_workflow.application.fresh_install import (
    FreshInstallError,
    FreshInstallLayout,
    _entrypoint_content,
    _open_tar,
    install_bundle,
    load_fresh_install_layout,
)
from tools.build_bundle import BundleBuildResult, build_bundle

ROOT = Path(__file__).resolve().parents[2]
MODULE = "src/ci_workflow/__main__.py"


def test_entry_generation_rejects_extra_bootstrap(tmp_path: Path) -> None:
    bootstrap = tmp_path / "bootstrap"
    bootstrap.mkdir()
    for name in ("fresh_install.py", "bundle_contract.py", "extra.py"):
        (bootstrap / name).write_bytes(b"# bootstrap\n")
    (tmp_path / "installation.json").write_bytes(b"{}")
    with pytest.raises(FreshInstallError):
        _entrypoint_content(tmp_path)


@pytest.mark.parametrize("boundary", ["load", "startup", "reinstall"])
def test_install_protected_metadata(
    release: BundleBuildResult, tmp_path: Path, boundary: str
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    targets = [
        layout.install_root / relative
        for relative in (
            ".", "bin", "bootstrap", "versions", "omp", "omp/skills",
            "runtime", "runtime/venv", "runtime/venv/bin",
            "bootstrap/fresh_install.py", "bootstrap/bundle_contract.py",
            "installation.json", "bin/ci-workflow",
        )
    ] + [layout.bundle_root, layout.bundle_root / "src"]
    for target in targets:
        original = target.lstat().st_mode & 0o7777
        try:
            target.chmod(0o777)
            if boundary == "load":
                with pytest.raises(FreshInstallError):
                    load_fresh_install_layout(layout.install_root)
            elif boundary == "reinstall":
                with pytest.raises(FreshInstallError):
                    install_bundle(release.archive_path, layout.install_root)
                assert target.lstat().st_mode & 0o7777 == 0o777
            else:
                result = subprocess.run(
                    [str(layout.entrypoint), "--help"], capture_output=True,
                    text=True, timeout=30, check=False,
                )
                assert result.returncode != 0, str(target)
        finally:
            target.chmod(original)
    load_fresh_install_layout(layout.install_root)


@pytest.mark.parametrize("kind", ["file", "directory", "symlink"])
def test_bootstrap_exact_set(
    release: BundleBuildResult, tmp_path: Path, kind: str
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    extra = layout.install_root / "bootstrap/extra"
    if kind == "file":
        extra.write_bytes(b"unexpected")
    elif kind == "directory":
        extra.mkdir()
    else:
        extra.symlink_to("missing")
    with pytest.raises(FreshInstallError):
        load_fresh_install_layout(layout.install_root)
    result = subprocess.run(
        [str(layout.entrypoint), "--help"], capture_output=True,
        text=True, timeout=30, check=False,
    )
    assert result.returncode != 0
    before = _tree(layout.install_root)
    with pytest.raises(FreshInstallError):
        install_bundle(release.archive_path, layout.install_root)
    assert _tree(layout.install_root) == before


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo", "missing"])
def test_bootstrap_node_types_before_read(
    release: BundleBuildResult, tmp_path: Path, kind: str
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    for relative in (
        "bootstrap/fresh_install.py", "bootstrap/bundle_contract.py", "installation.json",
    ):
        target = layout.install_root / relative
        saved = tmp_path / "saved"
        target.rename(saved)
        try:
            if kind == "symlink":
                target.symlink_to(saved)
            elif kind == "directory":
                target.mkdir()
            elif kind == "fifo":
                os.mkfifo(target)
            with pytest.raises(FreshInstallError):
                load_fresh_install_layout(layout.install_root)
            result = subprocess.run(
                [str(layout.entrypoint), "--help"], capture_output=True,
                text=True, timeout=10, check=False,
            )
            assert result.returncode != 0
            with pytest.raises(FreshInstallError):
                install_bundle(release.archive_path, layout.install_root)
        finally:
            if kind == "directory":
                target.rmdir()
            elif kind != "missing":
                target.unlink()
            saved.rename(target)
    load_fresh_install_layout(layout.install_root)


def test_protected_directory_symlinks_are_not_adopted(
    release: BundleBuildResult, tmp_path: Path
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    targets = [
        layout.install_root / relative
        for relative in ("bootstrap", "bin", "versions", "omp/skills", "runtime/venv/bin")
    ] + [layout.bundle_root / "src"]
    for target in targets:
        saved = tmp_path / "saved"
        target.rename(saved)
        target.symlink_to(saved, target_is_directory=True)
        try:
            with pytest.raises(FreshInstallError):
                load_fresh_install_layout(layout.install_root)
            result = subprocess.run(
                [str(layout.entrypoint), "--help"], capture_output=True,
                text=True, timeout=30, check=False,
            )
            assert result.returncode != 0
            with pytest.raises(FreshInstallError):
                install_bundle(release.archive_path, layout.install_root)
            assert target.is_symlink() and target.readlink() == saved
        finally:
            target.unlink()
            saved.rename(target)
    load_fresh_install_layout(layout.install_root)


def test_install_modes_are_independent_of_umask(
    release: BundleBuildResult, tmp_path: Path
) -> None:
    previous = os.umask(0o077)
    try:
        layout = install_bundle(release.archive_path, tmp_path / "install")
    finally:
        os.umask(previous)
    load_fresh_install_layout(layout.install_root)
    result = subprocess.run(
        [str(layout.entrypoint), "--help"], capture_output=True,
        text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr


def test_entrypoint_bytes_and_symlink_rejected(
    release: BundleBuildResult, tmp_path: Path
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    original = layout.entrypoint.read_bytes()
    for kind in ("bytes", "symlink"):
        if kind == "bytes":
            layout.entrypoint.write_bytes(original + b"\n# drift\n")
        else:
            saved = tmp_path / "saved-entry"
            saved.write_bytes(original)
            saved.chmod(0o755)
            layout.entrypoint.unlink()
            layout.entrypoint.symlink_to(saved)
        with pytest.raises(FreshInstallError):
            load_fresh_install_layout(layout.install_root)
        result = subprocess.run(
            [str(layout.entrypoint), "--help"], capture_output=True,
            text=True, timeout=30, check=False,
        )
        assert result.returncode != 0
        before = _tree(layout.install_root)
        with pytest.raises(FreshInstallError):
            install_bundle(release.archive_path, layout.install_root)
        assert _tree(layout.install_root) == before


@pytest.fixture(scope="module", autouse=True)
def isolated_download_cache(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CI_WORKFLOW_INSTALL_CACHE", str(tmp_path_factory.mktemp("private-uv-cache")))
        yield


def test_load_rejects_source_drift(release: BundleBuildResult, tmp_path: Path) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    (layout.bundle_root / MODULE).write_bytes(b"raise RuntimeError('drift')\n")
    with pytest.raises(FreshInstallError):
        load_fresh_install_layout(layout.install_root)


def test_startup_rejects_drift_before_candidate_import(
    release: BundleBuildResult, tmp_path: Path
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    (layout.bundle_root / "src/ci_workflow/cli.py").write_bytes(
        b"raise RuntimeError('UNTRUSTED_CODE_EXECUTED')\n"
    )
    completed = subprocess.run(
        [str(layout.entrypoint), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode != 0
    assert "UNTRUSTED_CODE_EXECUTED" not in completed.stderr
    assert "发行文件漂移" in completed.stderr


def test_independent_metadata_resources_and_preflight(
    release: BundleBuildResult, tmp_path: Path
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    env = os.environ.copy()
    env.update(
        PYTHONPATH="/nonexistent-poison",
        PYTHONHOME="/nonexistent-poison",
        CI_WORKFLOW_PYTHON="/nonexistent-poison",
    )
    for arguments in [
        ["package", "verify", "--root", str(layout.bundle_root)],
        [
            "capability",
            "preflight",
            "--host",
            "codex",
            "--reports",
            "A",
            "--outputs",
            "html",
            "--json",
            str(tmp_path / "preflight.json"),
        ],
    ]:
        result = subprocess.run(
            [str(layout.entrypoint), *arguments],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        # An actual capability deficit may block research, but it must be a
        # parsed preflight result, not an interpreter/import/resource failure.
        if arguments[0] == "package":
            assert result.returncode == 0, result.stderr
            assert "PACKAGE_OK" in result.stdout
        else:
            assert result.returncode in {0, 5}, (result.stdout, result.stderr)
            assert "PREFLIGHT_COMPLETE" in result.stdout
            assert json.loads((tmp_path / "preflight.json").read_bytes())


def test_moved_install_requires_runtime_rebuild(release: BundleBuildResult, tmp_path: Path) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    moved = tmp_path / "moved"
    layout.install_root.rename(moved)
    result = subprocess.run(
        [str(moved / "bin/ci-workflow"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert "已移动" in result.stderr and "重建" in result.stderr


def test_distributed_bootstrap_without_checkout(release: BundleBuildResult, tmp_path: Path) -> None:
    assert release.installer_path is not None
    with zipfile.ZipFile(release.installer_path) as archive:
        archive.extractall(tmp_path / "trusted")
    python = subprocess.run(
        ["uv", "python", "find", "--managed-python", "--no-python-downloads", "3.13"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    env = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "CI_WORKFLOW_PYTHON"):
        env.pop(name, None)
    result = subprocess.run(
        [
            python,
            "-I",
            "-B",
            str(tmp_path / "trusted/bootstrap/install.py"),
            "--bundle",
            str(release.archive_path),
            "--root",
            str(tmp_path / "standalone"),
            "--expected-digest",
            release.archive_sha256,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=660,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    layout = load_fresh_install_layout(tmp_path / "standalone")
    result = subprocess.run(
        [
            str(layout.entrypoint),
            "project",
            "create",
            "--root",
            str(tmp_path / "project"),
            "--indication",
            "安装测试",
            "--reports",
            "A",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "project/state/checkpoints").is_dir()


def test_bootstrap_and_receipt_tampering_rejected(
    release: BundleBuildResult, tmp_path: Path
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    for relative in (
        "bootstrap/fresh_install.py",
        "bootstrap/bundle_contract.py",
        "installation.json",
    ):
        target = layout.install_root / relative
        original = target.read_bytes()
        target.write_bytes(original + b"\n ")
        with pytest.raises(FreshInstallError):
            load_fresh_install_layout(layout.install_root)
        result = subprocess.run(
            [str(layout.entrypoint), "--help"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert result.returncode != 0
        assert "安装引导文件漂移" in result.stderr
        with pytest.raises(FreshInstallError):
            install_bundle(release.archive_path, layout.install_root)
        target.write_bytes(original)
    load_fresh_install_layout(layout.install_root)


def test_concurrent_install_lock_preserves_other_owner(
    release: BundleBuildResult, tmp_path: Path
) -> None:
    lock = tmp_path / ".install.install-lock"
    lock.mkdir()
    (lock / "owner").write_text("other-installer")
    with pytest.raises(FreshInstallError, match="并发"):
        install_bundle(release.archive_path, tmp_path / "install")
    assert (lock / "owner").read_text() == "other-installer"
    assert not (tmp_path / "install").exists()


@pytest.fixture(scope="module")
def release(tmp_path_factory: pytest.TempPathFactory) -> BundleBuildResult:
    return build_bundle(ROOT, tmp_path_factory.mktemp("g6-02-real-bundle"))


def _tree(root: Path) -> dict[str, tuple[int, bytes | str]]:
    if not root.exists():
        return {}
    return {
        str(p.relative_to(root)): (
            p.lstat().st_mode,
            os.readlink(p) if p.is_symlink() else p.read_bytes() if p.is_file() else "directory",
        )
        for p in root.rglob("*")
    }


def _alter_archive(source: Path, destination: Path, mutation: str) -> Path:
    with _open_tar(source) as original, tarfile.open(destination, "w") as output:
        for member in original:
            if mutation in {"missing", "missing_required_declared"} and member.name == MODULE:
                continue
            if (
                mutation == "missing_component_declared"
                and member.name == "schemas/source-version.schema.json"
            ):
                continue
            if mutation == "missing_manifest" and member.name == "bundle-manifest.json":
                continue
            stream = original.extractfile(member) if member.isfile() else None
            data = stream.read() if stream else b""
            if stream:
                stream.close()
            if mutation == "changed" and member.name == MODULE:
                data += b"\n# tampered\n"
            if member.name == "bundle-manifest.json":
                manifest = json.loads(data)
                if mutation in {"missing_required_declared", "missing_component_declared"}:
                    removed = (
                        MODULE
                        if mutation == "missing_required_declared"
                        else "schemas/source-version.schema.json"
                    )
                    manifest["files"] = [
                        item for item in manifest["files"] if item["path"] != removed
                    ]
                if mutation == "declared_extra":
                    extra = b"not allowed\n"
                    manifest["files"].append(
                        {
                            "path": "src/ci_workflow/injected.py",
                            "sha256": hashlib.sha256(extra).hexdigest(),
                            "bytes": len(extra),
                        }
                    )
                if mutation == "allowlist":
                    manifest["allowlist"].append("untrusted")
                if mutation in {
                    "missing_required_declared",
                    "missing_component_declared",
                    "declared_extra",
                    "allowlist",
                }:
                    data = json.dumps(manifest).encode("utf-8")
            member = copy(member)
            if member.isfile():
                member.size = len(data)
            output.addfile(member, io.BytesIO(data) if member.isfile() else None)
        if mutation == "extra":
            member = tarfile.TarInfo("src/ci_workflow/injected.py")
            data = b"raise RuntimeError('must never run')\n"
            member.size = len(data)
            output.addfile(member, io.BytesIO(data))
        if mutation == "declared_extra":
            member = tarfile.TarInfo("src/ci_workflow/injected.py")
            member.size = len(b"not allowed\n")
            output.addfile(member, io.BytesIO(b"not allowed\n"))
        if mutation == "empty_directory":
            member = tarfile.TarInfo("extra-empty")
            member.type = tarfile.DIRTYPE
            output.addfile(member)
    return destination


@pytest.mark.parametrize(
    "mutation",
    [
        "changed",
        "missing",
        "extra",
        "missing_manifest",
        "missing_required_declared",
        "missing_component_declared",
        "declared_extra",
        "allowlist",
        "empty_directory",
    ],
)
def test_first_install_verifies_every_release_byte(
    release: BundleBuildResult, tmp_path: Path, mutation: str
) -> None:
    archive = _alter_archive(release.archive_path, tmp_path / "tampered.tar", mutation)
    root = tmp_path / "install"
    with pytest.raises(FreshInstallError):
        install_bundle(
            archive, root, expected_digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        )
    assert not root.exists()
    assert not list(tmp_path.glob(".install.staging-*"))


@pytest.mark.parametrize(
    "mutation",
    [
        "changed",
        "missing",
        "extra",
        "empty_directory",
        "symlink",
        "cache",
        "mode",
        "rehash_manifest",
    ],
)
def test_reinstall_rejects_actual_file_drift_without_repair(
    release: BundleBuildResult, tmp_path: Path, mutation: str
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    if mutation == "changed":
        (layout.bundle_root / MODULE).write_bytes(b"tampered code\n")
    elif mutation == "missing":
        (layout.bundle_root / MODULE).unlink()
    elif mutation == "extra":
        (layout.bundle_root / "injected.txt").write_bytes(b"unexpected\n")
    elif mutation == "empty_directory":
        (layout.bundle_root / "unexpected-empty").mkdir()
    elif mutation == "symlink":
        (layout.bundle_root / MODULE).unlink()
        (layout.bundle_root / MODULE).symlink_to(layout.package_manifest)
    elif mutation == "cache":
        cache = layout.bundle_root / "src/ci_workflow/__pycache__"
        cache.mkdir()
        (cache / "arbitrary.pyc").write_bytes(b"not a release file")
    elif mutation == "mode":
        (layout.bundle_root / MODULE).chmod(0o777)
    else:
        data = b"tampered code with a matching local manifest\n"
        (layout.bundle_root / MODULE).write_bytes(data)
        path = layout.bundle_root / "bundle-manifest.json"
        manifest = json.loads(path.read_bytes())
        record = next(item for item in manifest["files"] if item["path"] == MODULE)
        record.update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        path.write_text(json.dumps(manifest), encoding="utf-8")
    before = _tree(layout.install_root)
    with pytest.raises(FreshInstallError):
        install_bundle(release.archive_path, layout.install_root)
    assert _tree(layout.install_root) == before


def test_clean_reinstall_after_real_cli_does_not_create_release_caches(
    release: BundleBuildResult,
    tmp_path: Path,
) -> None:
    layout = install_bundle(
        release.archive_path, tmp_path / "install", expected_digest=release.archive_sha256
    )
    before = _tree(layout.install_root)
    env = os.environ.copy()
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    completed = subprocess.run(
        [str(layout.entrypoint), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert not list(layout.bundle_root.rglob("__pycache__"))
    assert (
        install_bundle(release.archive_path, layout.install_root).bundle_digest
        == release.archive_sha256
    )
    assert _tree(layout.install_root) == before


@pytest.mark.parametrize("preexisting", [False, True])
def test_failure_after_entry_creation_rolls_back_only_new_paths(
    release: BundleBuildResult,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    preexisting: bool,
) -> None:
    root = tmp_path / "install"
    if preexisting:
        (root / "bin").mkdir(parents=True)
        (root / "bin/keep").write_bytes(b"user-owned\n")
    before = _tree(root)

    def fail_verify(self: FreshInstallLayout) -> None:
        raise FreshInstallError("injected final verification failure")

    monkeypatch.setattr(FreshInstallLayout, "verify_layout", fail_verify)
    with pytest.raises(FreshInstallError, match="injected"):
        install_bundle(release.archive_path, root)
    assert _tree(root) == before
    assert root.exists() == preexisting
    assert not list(tmp_path.glob(".install.staging-*"))


def test_bad_archive_preserves_existing_install(
    release: BundleBuildResult,
    tmp_path: Path,
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    before = _tree(layout.install_root)
    archive = _alter_archive(release.archive_path, tmp_path / "changed.tar", "changed")
    with pytest.raises(FreshInstallError):
        install_bundle(archive, layout.install_root)
    assert _tree(layout.install_root) == before


def test_external_digest_mismatch_does_not_create_install(
    release: BundleBuildResult,
    tmp_path: Path,
) -> None:
    root = tmp_path / "install"
    with pytest.raises(FreshInstallError, match="外部摘要不一致"):
        install_bundle(release.archive_path, root, expected_digest="0" * 64)
    assert not root.exists()


def test_reinstall_does_not_repair_entrypoint_permissions(
    release: BundleBuildResult,
    tmp_path: Path,
) -> None:
    layout = install_bundle(release.archive_path, tmp_path / "install")
    layout.entrypoint.chmod(0o644)
    before = _tree(layout.install_root)
    with pytest.raises(FreshInstallError, match="权限漂移"):
        install_bundle(release.archive_path, layout.install_root)
    assert _tree(layout.install_root) == before


def test_atomic_entrypoint_publication_never_clobbers_racing_file(
    release: BundleBuildResult,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "install"

    def competing_entry(source: Path, destination: Path) -> None:
        assert source.read_bytes().startswith(b"#!/bin/sh\nset -eu\n")
        assert source.stat().st_mode & 0o777 == 0o755
        destination.write_bytes(b"concurrently-created-user-entry\n")
        raise FileExistsError("simulated competing entry")

    monkeypatch.setattr(os, "link", competing_entry)
    with pytest.raises(FreshInstallError, match="创建竞争"):
        install_bundle(release.archive_path, root)
    assert (root / "bin/ci-workflow").read_bytes() == b"concurrently-created-user-entry\n"
    assert set(_tree(root)) == {"bin", "bin/ci-workflow"}
    assert not list(tmp_path.glob(".install.staging-*"))
