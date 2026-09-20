#!/usr/bin/env python3
"""构建可移动、可校验的 ``.tar.zst`` Skill bundle。

默认清单是显式 allowlist，不会扫描仓库根目录。构建结果包含归档内
``bundle-manifest.json``，并在归档旁写出同字节 manifest 与外部 SHA-256
校验文件。缓存、旧输出、测试目录、软链接和凭据不会进入候选包。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:  # pragma: no cover - only used by direct CLI calls
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.bundle_contract import (  # noqa: E402
    BUNDLE_FORMAT,
    BUNDLE_MANIFEST_NAME,
    BUNDLE_SCHEMA_VERSION,
    BundleEnvironmentError,
    BundleError,
    FileRecord,
    default_allowlist,
    expand_allowlist,
    require_clean_commit_provenance,
    sha256_file,
    validate_relative_path,
    verify_bundle,
)


@dataclass(frozen=True)
class BundleBuildResult:
    """构建产物和内容寻址证据。"""

    archive_path: Path
    manifest_path: Path
    checksum_path: Path
    archive_sha256: str
    files: tuple[FileRecord, ...]
    allowlist: tuple[str, ...]
    source_commit: str | None = None
    installer_path: Path | None = None

    @property
    def file_count(self) -> int:
        return len(self.files)


def _normalise_allowlist_for_manifest(
    allowlist: Iterable[str | Path],
) -> tuple[str, ...]:
    values: list[str] = []
    for raw in allowlist:
        value = raw.as_posix() if isinstance(raw, Path) else raw
        values.append(validate_relative_path(value, label="allowlist 路径"))
    if len(values) != len(set(values)):
        raise BundleError("allowlist 不能包含重复路径")
    return tuple(sorted(values))


def _load_optional_package(source_root: Path) -> dict[str, str] | None:
    manifest_path = source_root / "package-manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BundleError(f"无法读取 package-manifest.json：{manifest_path}") from exc
    package = value.get("package") if isinstance(value, dict) else None
    if not isinstance(package, dict):
        raise BundleError("package-manifest.json 缺少 package 对象")
    name = package.get("name")
    version = package.get("version")
    if not isinstance(name, str) or not name.strip():
        raise BundleError("package-manifest.json 的 package.name 无效")
    if not isinstance(version, str) or not version.strip():
        raise BundleError("package-manifest.json 的 package.version 无效")
    return {"name": name, "version": version}


def _archive_name(
    package: dict[str, str] | None,
    requested: str | None,
) -> str:
    if requested is None:
        if package is None:
            raise BundleError(
                "缺少 package-manifest.json；自定义 bundle 必须显式指定 --archive-name"
            )
        requested = f"{package['name']}-{package['version']}.tar.zst"
    if (
        not requested
        or any(character.isspace() for character in requested)
        or Path(requested).name != requested
        or not requested.endswith(".tar.zst")
    ):
        raise BundleError("归档名必须是无空格的单层 .tar.zst 文件名")
    validate_relative_path(requested, label="归档名")
    return requested


def _copy_to_staging(source_root: Path, staging_root: Path, paths: Sequence[str]) -> None:
    for relative in paths:
        source = source_root / relative
        if source.is_symlink() or not source.is_file():
            raise BundleError(f"构建期间源文件不可用或变为软链接：{relative}")
        destination = staging_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copyfile(source, destination)
            os.chmod(destination, 0o644)
        except OSError as exc:
            raise BundleError(f"无法复制 allowlist 文件：{relative}") from exc


def _file_records(staging_root: Path, paths: Sequence[str]) -> tuple[FileRecord, ...]:
    records: list[FileRecord] = []
    for relative in paths:
        path = staging_root / relative
        try:
            byte_size = path.stat().st_size
        except OSError as exc:
            raise BundleError(f"staging 缺少 allowlist 文件：{relative}") from exc
        records.append(FileRecord(path=relative, sha256=sha256_file(path), byte_size=byte_size))
    return tuple(records)


def _parent_directories(paths: Iterable[str]) -> tuple[str, ...]:
    parents: set[str] = set()
    for relative in paths:
        parent = PurePosixPath(relative).parent
        while str(parent) != ".":
            parents.add(parent.as_posix())
            parent = parent.parent
    return tuple(sorted(parents, key=lambda item: (item.count("/"), item)))


def _tar_info(name: str, *, directory: bool, byte_size: int = 0) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=name)
    info.mode = 0o755 if directory else 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.size = 0 if directory else byte_size
    info.pax_headers = {}
    if directory:
        info.type = tarfile.DIRTYPE
    return info


def _write_tar(staging_root: Path, tar_path: Path, records: Sequence[FileRecord]) -> None:
    all_paths = [record.path for record in records]
    for directory in _parent_directories([*all_paths, BUNDLE_MANIFEST_NAME]):
        (staging_root / directory).mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(tar_path, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for directory in _parent_directories([*all_paths, BUNDLE_MANIFEST_NAME]):
                archive.addfile(_tar_info(directory, directory=True))
            for record in [
                *records,
                FileRecord(
                    path=BUNDLE_MANIFEST_NAME,
                    sha256="",
                    byte_size=(staging_root / BUNDLE_MANIFEST_NAME).stat().st_size,
                ),
            ]:
                path = staging_root / record.path
                with path.open("rb") as stream:
                    archive.addfile(
                        _tar_info(record.path, directory=False, byte_size=record.byte_size),
                        stream,
                    )
    except OSError as exc:
        raise BundleError(f"无法生成 tar staging：{tar_path}") from exc


def _compress_zstd(tar_path: Path, archive_path: Path) -> None:
    executable = shutil.which("zstd")
    if executable is None:
        raise BundleEnvironmentError(
            "缺少 zstd；请安装 zstd 后重试，不要以未压缩 tar 冒充 .tar.zst"
        )
    try:
        with archive_path.open("wb") as output:
            subprocess.run(
                [executable, "--quiet", "--threads=1", "--stdout", str(tar_path)],
                check=True,
                stdout=output,
                stderr=subprocess.PIPE,
                text=False,
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BundleError(f"无法压缩 zstd bundle：{archive_path}") from exc


def _atomic_bytes(path: Path, data: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_move(source: Path, destination: Path) -> None:
    try:
        os.replace(source, destination)
    except OSError as exc:
        raise BundleError(f"无法写入构建产物：{destination}") from exc


def _build_installer(source: Path, archive: Path) -> Path:
    """Separate trusted, stdlib-only bootstrap; never taken from the candidate."""
    launcher = """import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fresh_install import install_bundle
parser = argparse.ArgumentParser()
parser.add_argument('--bundle', type=Path, required=True)
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--expected-digest', required=True)
args = parser.parse_args()
layout = install_bundle(args.bundle, args.root, expected_digest=args.expected_digest)
print(layout.entrypoint)
"""
    files = {
        "bootstrap/install.py": launcher.encode(),
        "bootstrap/fresh_install.py": (
            source / "src/ci_workflow/application/fresh_install.py"
        ).read_bytes(),
        "bootstrap/bundle_contract.py": (source / "tools/bundle_contract.py").read_bytes(),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            output.writestr(info, data)
    destination = Path(f"{archive}.installer.zip")
    _atomic_bytes(destination, buffer.getvalue())
    _atomic_bytes(
        Path(f"{destination}.sha256"), f"{sha256_file(destination)}  {destination.name}\n".encode()
    )
    return destination


def build_bundle(
    source_root: Path,
    output_dir: Path,
    *,
    allowlist: Iterable[str | Path] | None = None,
    archive_name: str | None = None,
    expected_source_commit: str | None = None,
) -> BundleBuildResult:
    """从显式 allowlist 生成确定性 ``.tar.zst`` 和两个外部 sidecar。

    指定 ``expected_source_commit`` 时进入 clean-commit 模式：源根必须是
    干净 Git 工作树且 HEAD 等于该 commit/tag，任何偏差在写出任何产物之前
    失败关闭，成功后把完整 commit SHA 记入 bundle manifest。
    """

    expanded_source = source_root.expanduser()
    if expanded_source.is_symlink():
        raise BundleError(f"源根目录不能是软链接：{source_root}")
    source = expanded_source.resolve()
    if not source.is_dir():
        raise BundleError(f"源根目录不存在或不是普通目录：{source_root}")
    source_commit: str | None = None
    if expected_source_commit is not None:
        source_commit = require_clean_commit_provenance(source, expected_source_commit)
    selected_allowlist = tuple(allowlist) if allowlist is not None else default_allowlist(source)
    manifest_allowlist = _normalise_allowlist_for_manifest(selected_allowlist)
    paths = expand_allowlist(source, manifest_allowlist)
    package = _load_optional_package(source)
    name = _archive_name(package, archive_name)
    destination = output_dir.expanduser().resolve()
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BundleError(f"无法创建候选包输出目录：{destination}") from exc
    archive_path = destination / name
    checksum_path = Path(f"{archive_path}.sha256")
    manifest_path = Path(f"{archive_path}.manifest.json")

    with tempfile.TemporaryDirectory(prefix=".bundle-staging-", dir=destination) as temporary:
        staging = Path(temporary)
        _copy_to_staging(source, staging, paths)
        records = _file_records(staging, paths)
        manifest: dict[str, Any] = {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "bundle": {
                "format": BUNDLE_FORMAT,
                "compression": "zstd",
                "manifest_path": BUNDLE_MANIFEST_NAME,
                "archive_name": name,
                "external_manifest": f"{name}.manifest.json",
                "external_sha256": f"{name}.sha256",
            },
            "allowlist": list(manifest_allowlist),
            "files": [record.as_dict() for record in records],
        }
        if package is not None:
            manifest["package"] = package
        if source_commit is not None:
            manifest["source_commit"] = source_commit
        manifest_bytes = (
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        (staging / BUNDLE_MANIFEST_NAME).write_bytes(manifest_bytes)
        tar_path = staging / "bundle.tar"
        _write_tar(staging, tar_path, records)
        temporary_archive = staging / name
        _compress_zstd(tar_path, temporary_archive)
        archive_digest = sha256_file(temporary_archive)

        temporary_archive_output = destination / f".{name}.pending"
        _atomic_move(temporary_archive, temporary_archive_output)
        _atomic_move(temporary_archive_output, archive_path)

    _atomic_bytes(manifest_path, manifest_bytes)
    _atomic_bytes(
        checksum_path,
        f"{archive_digest}  {archive_path.name}\n".encode(),
    )
    verify_bundle(
        archive_path,
        checksum_path=checksum_path,
        manifest_path=manifest_path,
    )
    return BundleBuildResult(
        archive_path=archive_path,
        manifest_path=manifest_path,
        checksum_path=checksum_path,
        archive_sha256=archive_digest,
        files=records,
        allowlist=manifest_allowlist,
        source_commit=source_commit,
        installer_path=_build_installer(source, archive_path) if allowlist is None else None,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", "--root", dest="source_root", default=".", help="源码根目录"
    )
    parser.add_argument(
        "--output-dir", "--output", dest="output_dir", required=True, help="候选包输出目录"
    )
    parser.add_argument(
        "--allowlist",
        action="append",
        default=None,
        help="允许的相对文件或目录；可重复。缺省使用内置最小 allowlist。",
    )
    parser.add_argument("--archive-name", help="可选单层归档名，必须以 .tar.zst 结尾")
    parser.add_argument(
        "--from-clean-commit",
        dest="from_clean_commit",
        metavar="RC_COMMIT",
        help=(
            "clean-commit 模式：仅当源根是干净 Git 工作树且 HEAD 等于该 "
            "commit/tag 时构建，并把完整 commit SHA 记入 bundle manifest"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    requested_output = Path(args.output_dir)
    archive_name = args.archive_name
    if requested_output.name.endswith(".tar.zst"):
        if archive_name is not None and archive_name != requested_output.name:
            print("BUNDLE_ERROR --output 文件名与 --archive-name 不一致", file=sys.stderr)
            return 2
        archive_name = requested_output.name
        requested_output = requested_output.parent
    try:
        result = build_bundle(
            Path(args.source_root),
            requested_output,
            allowlist=args.allowlist,
            archive_name=archive_name,
            expected_source_commit=args.from_clean_commit,
        )
    except BundleEnvironmentError as exc:
        print(f"BUNDLE_ENV_ERROR {exc}", file=sys.stderr)
        return 3
    except (BundleError, OSError, ValueError) as exc:
        print(f"BUNDLE_ERROR {exc}", file=sys.stderr)
        return 2
    provenance = (
        f" source_commit={result.source_commit}" if result.source_commit is not None else ""
    )
    print(
        "BUNDLE_BUILT "
        f"archive={result.archive_path} sha256={result.archive_sha256} "
        f"files={result.file_count} manifest={result.manifest_path} "
        f"checksum={result.checksum_path}{provenance}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
