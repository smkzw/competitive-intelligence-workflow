"""PK01–PK02：候选 bundle 构建、内容寻址和失败关闭合同。"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import tarfile
from pathlib import Path

import pytest

from tools.build_bundle import BundleBuildResult, build_bundle
from tools.bundle_contract import BUNDLE_MANIFEST_NAME, BundleError
from tools.verify_bundle import verify_bundle


def _source_tree(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    (root / "allowed").mkdir(parents=True)
    (root / "allowed" / "data.txt").write_text("允许内容\n", encoding="utf-8")
    (root / "package-manifest.json").write_text(
        json.dumps(
            {"package": {"name": "candidate", "version": "1.0.0"}},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "allowed" / "__pycache__").mkdir()
    (root / "allowed" / "__pycache__" / "stale.pyc").write_bytes(b"cache")
    (root / "allowed" / "output").mkdir()
    (root / "allowed" / "output" / "old.html").write_text("旧输出", encoding="utf-8")
    (root / "allowed" / "credentials.json").write_text("凭据", encoding="utf-8")
    return root


def _materialize_directory(
    result: BundleBuildResult,
    source_root: Path,
    destination: Path,
) -> Path:
    destination.mkdir()
    shutil.copyfile(result.manifest_path, destination / BUNDLE_MANIFEST_NAME)
    for record in result.files:
        target = destination / record.path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / record.path, target)
    return destination


def test_builder_emits_deterministic_archive_manifest_and_external_sha256(tmp_path: Path) -> None:
    if shutil.which("zstd") is None:
        pytest.skip("zstd unavailable")
    source = _source_tree(tmp_path)
    output = tmp_path / "dist"
    allowlist = ["package-manifest.json", "allowed"]

    first = build_bundle(source, output, allowlist=allowlist, archive_name="candidate.tar.zst")
    first_bytes = first.archive_path.read_bytes()
    second = build_bundle(source, output, allowlist=allowlist, archive_name="candidate.tar.zst")

    assert first.archive_sha256 == second.archive_sha256
    assert first_bytes == second.archive_path.read_bytes()
    assert set(record.path for record in first.files) == {
        "allowed/data.txt",
        "package-manifest.json",
    }
    assert first.checksum_path.read_text(encoding="ascii") == (
        f"{first.archive_sha256}  candidate.tar.zst\n"
    )
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["bundle"]["manifest_path"] == BUNDLE_MANIFEST_NAME
    assert [item["path"] for item in manifest["files"]] == [
        "allowed/data.txt",
        "package-manifest.json",
    ]
    verified = verify_bundle(first.archive_path)
    assert verified.archive_sha256 == first.archive_sha256
    assert len(verified.files) == 2


def test_verifier_rejects_missing_extra_and_digest_drift(tmp_path: Path) -> None:
    if shutil.which("zstd") is None:
        pytest.skip("zstd unavailable")
    source = _source_tree(tmp_path)
    result = build_bundle(
        source,
        tmp_path / "dist",
        allowlist=["package-manifest.json", "allowed"],
        archive_name="candidate.tar.zst",
    )

    missing = _materialize_directory(result, source, tmp_path / "missing")
    (missing / "allowed" / "data.txt").unlink()
    with pytest.raises(BundleError, match="缺少清单声明文件"):
        verify_bundle(missing)

    extra = _materialize_directory(result, source, tmp_path / "extra")
    (extra / "unexpected.txt").write_text("额外文件", encoding="utf-8")
    with pytest.raises(BundleError, match="未声明文件"):
        verify_bundle(extra)

    drift = _materialize_directory(result, source, tmp_path / "drift")
    (drift / "allowed" / "data.txt").write_text("漂移内容\n", encoding="utf-8")
    with pytest.raises(BundleError, match="摘要漂移"):
        verify_bundle(drift)


def test_verifier_rejects_manifest_path_escape_and_symlink(tmp_path: Path) -> None:
    if shutil.which("zstd") is None:
        pytest.skip("zstd unavailable")
    source = _source_tree(tmp_path)
    result = build_bundle(
        source,
        tmp_path / "dist",
        allowlist=["package-manifest.json", "allowed"],
        archive_name="candidate.tar.zst",
    )

    escaped = _materialize_directory(result, source, tmp_path / "escaped")
    manifest = json.loads((escaped / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.txt"
    (escaped / BUNDLE_MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(BundleError, match="非法路径段"):
        verify_bundle(escaped)

    linked = _materialize_directory(result, source, tmp_path / "linked")
    outside = tmp_path / "outside.txt"
    outside.write_text("外部", encoding="utf-8")
    (linked / "linked.txt").symlink_to(outside)
    with pytest.raises(BundleError, match="软链接"):
        verify_bundle(linked)


def test_archive_member_path_escape_is_rejected_before_manifest_comparison(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "malicious.tar"
    manifest = {
        "schema_version": "1.0",
        "bundle": {
            "format": "skill-bundle",
            "compression": "zstd",
            "manifest_path": BUNDLE_MANIFEST_NAME,
        },
        "allowlist": ["payload.txt"],
        "files": [
            {
                "path": "payload.txt",
                "sha256": hashlib.sha256(b"payload").hexdigest(),
                "bytes": 7,
            }
        ],
    }
    manifest_bytes = (json.dumps(manifest) + "\n").encode("utf-8")
    with tarfile.open(archive_path, mode="w") as archive:
        manifest_info = tarfile.TarInfo(BUNDLE_MANIFEST_NAME)
        manifest_info.size = len(manifest_bytes)
        archive.addfile(manifest_info, fileobj=io.BytesIO(manifest_bytes))
        escape_info = tarfile.TarInfo("../outside.txt")
        escape_info.size = 7
        archive.addfile(escape_info, fileobj=io.BytesIO(b"payload"))

    with pytest.raises(BundleError, match="非法路径段"):
        verify_bundle(archive_path, require_external_digest=False)
