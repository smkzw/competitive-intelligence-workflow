"""Task 9.5 PK03：隔离、内容寻址的候选 Skill fresh-install 布局。

安装器只写调用方提供的候选根目录。归档内容先在同一父目录的临时目录中
解包和校验，再原子移动到 ``versions/<bundle_sha256>``；现有版本或宿主入口
不会被覆盖。共享规范根是一个指向该版本的明确链接，OMP 只建立一个公共
Skill 链接，供真实宿主 runner 在隔离根中解析。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import posixpath
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

PACKAGE_NAME = "competitive-intelligence-workflow"
PUBLIC_SKILL_RELATIVE = PurePosixPath("skills/competitive-intelligence-workflow/SKILL.md")
BUNDLE_DIRECTORY_NAME = "versions"
SHARED_ROOT_NAME = "shared"
OMP_SKILLS_ROOT = PurePosixPath("omp/skills")
ENTRYPOINT_RELATIVE = PurePosixPath("bin/ci-workflow")
_SHA256_LENGTH = 64
_BOOTSTRAP_FILES = ("fresh_install.py", "bundle_contract.py")
_PROTECTED_DIRECTORIES = (
    ".", "versions", "bin", "omp", "omp/skills", "bootstrap",
    "runtime", "runtime/venv", "runtime/venv/bin",
)


def _require_node(path: Path, mode: int) -> None:
    """Exact lstat type and mode before reading; not a concurrent-write sandbox."""
    try:
        actual = path.lstat().st_mode
    except OSError as exc:
        raise FreshInstallError(f"安装节点缺失或不可读：{path}") from exc
    if actual != mode:
        raise FreshInstallError(f"安装节点类型或权限漂移：{path}")


class FreshInstallError(RuntimeError):
    """候选包无法在隔离根安全、完整安装。"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise FreshInstallError(f"无法读取候选包：{path}") from exc
    return digest.hexdigest()


def _validate_digest(value: str, *, label: str) -> str:
    if len(value) != _SHA256_LENGTH or any(c not in "0123456789abcdef" for c in value):
        raise FreshInstallError(f"{label} 必须是小写 SHA-256")
    return value


def _safe_relative(value: str, *, label: str) -> PurePosixPath:
    if not value or "\x00" in value or "\\" in value:
        raise FreshInstallError(f"{label} 不是合法的 POSIX 相对路径")
    path = PurePosixPath(value)
    if path.is_absolute() or path == PurePosixPath(".") or ".." in path.parts:
        raise FreshInstallError(f"{label} 不得是绝对路径或包含 ..：{value}")
    # ``PurePosixPath`` folds repeated slashes; reject the spelling so duplicate
    # archive entries cannot alias a different-looking path.
    if posixpath.normpath(value) != value or value.startswith("./"):
        raise FreshInstallError(f"{label} 必须是规范 POSIX 相对路径：{value}")
    return path


def _assert_inside(root: Path, candidate: Path, *, label: str) -> None:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise FreshInstallError(f"{label} 不得离开隔离根：{candidate}") from exc


def _assert_no_symlink_parent(root: Path, parent: Path) -> None:
    """拒绝经过归档内已创建软链接的路径，避免解包写出 staging。"""
    current = parent
    root_resolved = root.resolve(strict=False)
    while current != root_resolved:
        if current.is_symlink():
            raise FreshInstallError(f"归档路径经过软链接，拒绝解包：{current}")
        if current == current.parent:
            break
        current = current.parent


@contextmanager
def _open_tar(bundle: Path) -> Iterator[tarfile.TarFile]:
    """以流模式读取 tar 或外部 zstd 流，不把完整归档复制到内存。"""
    is_zstd = bundle.name.endswith((".tar.zst", ".tzst"))
    if not is_zstd:
        try:
            with tarfile.open(bundle, mode="r:*") as archive:
                yield archive
        except (OSError, tarfile.TarError) as exc:
            raise FreshInstallError(f"无法读取候选包归档：{bundle}") from exc
        return

    decoder = shutil.which("zstd")
    if decoder is None:
        raise FreshInstallError("解包 .tar.zst 需要 zstd；未找到可执行文件")
    process = subprocess.Popen(
        [decoder, "--decompress", "--stdout", "--quiet", "--", str(bundle)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None or process.stderr is None:  # pragma: no cover - Popen contract
        process.kill()
        process.wait()
        raise FreshInstallError("无法启动 zstd 解码器")
    try:
        try:
            with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                yield archive
        except (OSError, tarfile.TarError) as exc:
            raise FreshInstallError(f"无法读取 .tar.zst 候选包：{bundle}") from exc
    finally:
        process.stdout.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace").strip()
        process.stderr.close()
        returncode = process.wait()
        if returncode != 0:
            detail = f"：{stderr[-400:]}" if stderr else ""
            raise FreshInstallError(f"zstd 解码失败（退出码 {returncode}）{detail}")


def _extract_archive(bundle: Path, staging: Path) -> None:
    seen: set[str] = set()
    try:
        with _open_tar(bundle) as archive:
            for member in archive:
                path = _safe_relative(member.name, label="归档成员")
                relative = path.as_posix()
                if relative in seen:
                    raise FreshInstallError(f"归档包含重复成员：{relative}")
                seen.add(relative)
                destination = staging.joinpath(*path.parts)
                _assert_inside(staging, destination, label="归档成员")
                _assert_no_symlink_parent(staging, destination.parent)

                if member.issym() or member.islnk():
                    raise FreshInstallError(f"候选包不得包含归档软链接或硬链接：{relative}")
                if member.isdev() or member.isfifo():
                    raise FreshInstallError(f"候选包不得包含特殊文件：{relative}")
                if member.isdir():
                    if destination.exists() and not destination.is_dir():
                        raise FreshInstallError(f"归档成员类型冲突：{relative}")
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isreg():
                    raise FreshInstallError(f"候选包包含不支持的归档成员：{relative}")
                if destination.exists() or destination.is_symlink():
                    raise FreshInstallError(f"归档成员覆盖已有路径：{relative}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise FreshInstallError(f"归档文件无法读取：{relative}")
                with extracted, destination.open("xb") as output:
                    shutil.copyfileobj(extracted, output, length=1024 * 1024)
                mode = stat.S_IMODE(member.mode)
                destination.chmod(mode or 0o644)
        # Only freshly extracted directories are normalized, never existing installs.
        for directory in (staging, *(p for p in staging.rglob("*") if p.is_dir())):
            directory.chmod(0o755)
    except FreshInstallError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise FreshInstallError(f"候选包解包失败：{bundle}") from exc


def _package_root(staging: Path) -> Path:
    direct_manifest = staging / "package-manifest.json"
    if direct_manifest.is_file():
        return staging
    entries = list(staging.iterdir())
    if len(entries) != 1 or not entries[0].is_dir() or entries[0].is_symlink():
        raise FreshInstallError("候选包必须在根目录或唯一顶层目录提供 package-manifest.json")
    nested = entries[0]
    if not (nested / "package-manifest.json").is_file():
        raise FreshInstallError("候选包缺少根 package-manifest.json")
    return nested


def _read_package_manifest(root: Path) -> dict[str, Any]:
    path = root / "package-manifest.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshInstallError(f"候选包 package-manifest.json 无法读取：{path}") from exc
    if not isinstance(value, dict):
        raise FreshInstallError("候选包 package-manifest.json 顶层必须是对象")
    package = value.get("package")
    if not isinstance(package, dict) or package.get("name") != PACKAGE_NAME:
        raise FreshInstallError("候选包名称与竞品调研 Skill 不一致")
    public_skill = value.get("public_skill")
    if not isinstance(public_skill, str):
        raise FreshInstallError("候选包清单缺少 public_skill")
    public_path = _safe_relative(public_skill, label="public_skill")
    if public_path != PUBLIC_SKILL_RELATIVE:
        raise FreshInstallError("候选包 public_skill 未绑定唯一公开 Skill")
    if not (root / public_path).is_file():
        raise FreshInstallError("候选包缺少清单声明的公开 Skill")
    return value


def _trusted_bundle_contract() -> ModuleType:
    """Load the installer-side verifier, never code supplied by the archive.

    Developer tooling and the separately distributed bootstrap share this
    verifier. Absent trusted tooling must fail closed, never fall back to a
    verifier from the candidate or the current directory.
    """
    own_path = Path(__file__).resolve()
    path = (
        own_path.parent / "bundle_contract.py"
        if own_path.parent.name == "bootstrap"
        else own_path.parents[3] / "tools/bundle_contract.py"
    )
    if path.is_symlink() or not path.is_file():
        raise FreshInstallError("安装器缺少受信任的 bundle 校验工具")
    name = "_ci_fresh_install_bundle_contract"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FreshInstallError("无法加载安装器的 bundle 校验工具")
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through the defining module registry.
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    return module


def _verify_release_tree(root: Path) -> dict[str, tuple[str, int, int]]:
    """Exact distribution set: caches and runtime output are not release files."""
    contract = _trusted_bundle_contract()
    try:
        verified = contract.verify_bundle(root, require_final_content=True)
        declared = {record.path for record in verified.files}
        allowlist = verified.manifest["allowlist"]
        if len(allowlist) != len(set(allowlist)) or set(allowlist) != set(
            contract.DEFAULT_ALLOWLIST
        ):
            raise FreshInstallError("发行白名单与安装器批准的白名单不一致")
        if declared != set(contract.expand_allowlist(root, contract.DEFAULT_ALLOWLIST)):
            raise FreshInstallError("发行文件集合不等于批准白名单展开结果")
        package = _read_package_manifest(root)
        identity = verified.manifest.get("package")
        if identity != {key: package["package"].get(key) for key in ("name", "version")}:
            raise FreshInstallError("发行清单与 package manifest 身份不一致")
        internal = package.get("internal_skills")
        components = package.get("components")
        if not isinstance(internal, list) or not isinstance(components, dict):
            raise FreshInstallError("package manifest 缺少内部 Skill 或组件清单")
        required = [package["public_skill"]]
        for item in internal:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise FreshInstallError("package manifest 内部 Skill 路径无效")
            required.append(item["path"])
        for paths in components.values():
            if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
                raise FreshInstallError("package manifest 组件路径无效")
            required.extend(paths)
        for relative in required:
            if _safe_relative(relative, label="package manifest 内容").as_posix() not in declared:
                raise FreshInstallError("package manifest 声明的必需内容不在发行文件集合内")
        records = {
            record.path: (
                record.sha256,
                record.byte_size,
                stat.S_IMODE((root / record.path).stat().st_mode),
            )
            for record in verified.files
        }
        manifest = root / contract.BUNDLE_MANIFEST_NAME
        records[contract.BUNDLE_MANIFEST_NAME] = (
            _sha256(manifest),
            manifest.stat().st_size,
            stat.S_IMODE(manifest.stat().st_mode),
        )
        expected_dirs = {
            parent.as_posix()
            for relative in records
            for parent in PurePosixPath(relative).parents
            if parent != PurePosixPath(".")
        }
        actual_dirs = {
            path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()
        }
        if actual_dirs != expected_dirs:
            raise FreshInstallError("发行目录集合存在多余或缺失目录")
        return records
    except contract.BundleError as exc:
        raise FreshInstallError(f"发行内容完整性校验失败：{exc}") from exc


def _relative_link(source_parent: Path, target: Path) -> str:
    return os.path.relpath(target, start=source_parent)


def _runtime_python(root: Path) -> Path:
    return root / "runtime/venv/bin/python"


def _provision_runtime(root: Path, version_root: Path) -> None:
    """uv consumes the shipped lock in a private environment, never the dev venv.

    The project is editable only to this immutable installed source tree, which
    preserves the existing resource layout. Moving it requires a fresh install.
    """
    uv = shutil.which("uv")
    if uv is None:
        raise FreshInstallError("独立安装需要 uv；未找到安装工具")
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PYTHON", "UV_"))
        and key not in {"VIRTUAL_ENV", "CONDA_PREFIX", "CI_WORKFLOW_PYTHON"}
    }
    environment.update(
        {
            "UV_PROJECT_ENVIRONMENT": str(root / "runtime/venv"),
            "UV_CACHE_DIR": os.environ.get(
                "CI_WORKFLOW_INSTALL_CACHE", str(root / "runtime/cache")
            ),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    # An existing uv-managed *base* Python is not the developer venv. Reuse it
    # read-only when available; otherwise download a private managed Python.
    found = subprocess.run(
        [uv, "--no-config", "python", "find", "--managed-python", "--no-python-downloads", "3.13"],
        env=environment,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    python = found.stdout.strip() if found.returncode == 0 else "3.13"
    if found.returncode:
        environment["UV_PYTHON_INSTALL_DIR"] = str(root / "runtime/python")
    result = subprocess.run(
        [
            uv,
            "--no-config",
            "sync",
            "--frozen",
            "--no-dev",
            "--managed-python",
            "--python",
            python,
            "--project",
            str(version_root),
        ],
        env=environment,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode:
        raise FreshInstallError("独立运行环境安装失败：" + result.stderr[-1500:])
    for relative in ("runtime/venv", "runtime/venv/bin"):
        (root / relative).chmod(0o755)
    _runtime_probe(root, version_root)


def _runtime_probe(root: Path, version_root: Path) -> None:
    # Actual metadata, import origins, and resources; not a --help-only smoke.
    code = """
import importlib, importlib.metadata as md, sys, tomllib
from pathlib import Path
root, bundle = map(Path, sys.argv[1:])
assert Path(sys.prefix).resolve() == root / 'runtime/venv'
project = tomllib.loads((bundle / 'pyproject.toml').read_text())['project']
modules = {'pydantic':'pydantic','Jinja2':'jinja2','pypdf':'pypdf',
           'pdfplumber':'pdfplumber','playwright':'playwright','PyYAML':'yaml',
           'jsonschema':'jsonschema'}
for requirement in project['dependencies']:
    name, version = requirement.split('==')
    assert md.version(name) == version
    module = importlib.import_module(modules[name])
    assert Path(module.__file__).resolve().is_relative_to(root / 'runtime/venv')
assert md.version(project['name']) == project['version']
distribution = md.distribution(project['name'])
assert Path(distribution.locate_file('')).resolve().is_relative_to(root / 'runtime/venv')
import ci_workflow
assert Path(ci_workflow.__file__).resolve() == bundle / 'src/ci_workflow/__init__.py'
from ci_workflow.cli import verify_package
verify_package(bundle)
print('INDEPENDENT_RUNTIME_METADATA_RESOURCES_OK')
"""
    result = subprocess.run(
        [str(_runtime_python(root)), "-I", "-B", "-c", code, str(root), str(version_root)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise FreshInstallError("独立运行环境 metadata/资源校验失败：" + result.stderr[-1500:])


def _entrypoint_content(root: Path) -> bytes:
    # These hashes are installer anchors outside the untrusted candidate tree.
    _require_node(root / "bootstrap", stat.S_IFDIR | 0o755)
    if {path.name for path in (root / "bootstrap").iterdir()} != set(_BOOTSTRAP_FILES):
        raise FreshInstallError("安装引导文件集合漂移")
    relatives = (*(f"bootstrap/{name}" for name in _BOOTSTRAP_FILES), "installation.json")
    for relative in relatives:
        _require_node(root / relative, stat.S_IFREG | 0o644)
    hashes = {
        relative: _sha256(root / relative)
        for relative in relatives
    }
    prelude = (
        "import hashlib,pathlib,runpy,sys; r=pathlib.Path(sys.argv[1]); "
        f"h={hashes!r}; "
        f"assert (r/'bootstrap').lstat().st_mode=={stat.S_IFDIR | 0o755} "
        f"and {{p.name for p in (r/'bootstrap').iterdir()}}==set({_BOOTSTRAP_FILES!r}), "
        "'安装引导文件漂移'; "
        f"assert all((r/p).lstat().st_mode=={stat.S_IFREG | 0o644} "
        "and hashlib.sha256((r/p).read_bytes()).hexdigest()==v "
        "for p,v in h.items()), '安装引导文件漂移'; "
        "runpy.run_path(str(r/'bootstrap/fresh_install.py'),run_name='__main__')"
    )
    import shlex

    return (
        "#!/bin/sh\nset -eu\n"
        'INSTALL_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)\n'
        "unset PYTHONPATH PYTHONHOME CI_WORKFLOW_PYTHON\n"
        "export PYTHONDONTWRITEBYTECODE=1\n"
        'exec "$INSTALL_ROOT/runtime/venv/bin/python" -I -B -S -c '
        + shlex.quote(prelude)
        + ' "$INSTALL_ROOT" "$@"\n'
    ).encode()


def _verify_installation(root: Path, version_root: Path) -> None:
    for relative in _PROTECTED_DIRECTORIES:
        _require_node(root / relative, stat.S_IFDIR | 0o755)
    _require_node(version_root, stat.S_IFDIR | 0o755)
    entry = root / ENTRYPOINT_RELATIVE
    _require_node(entry, stat.S_IFREG | 0o755)
    if entry.read_bytes() != _entrypoint_content(root):
        raise FreshInstallError("安装入口或引导回执漂移")
    receipt_path = root / "installation.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise FreshInstallError("缺少完整安装回执；请使用独立安装器重建")
    receipt = json.loads(receipt_path.read_bytes())
    if not isinstance(receipt, dict) or receipt.get("schema_version") != "1.0":
        raise FreshInstallError("安装回执格式无效")
    if receipt.get("install_root") != str(root):
        raise FreshInstallError("安装根已移动；venv 不可移动，请在新根重新安装重建运行环境")
    if receipt.get("bundle_digest") != version_root.name:
        raise FreshInstallError("安装回执与版本目录不一致")
    expected = receipt.get("release_records")
    if not isinstance(expected, dict):
        raise FreshInstallError("安装回执缺少发行文件绑定")
    actual: dict[str, list[str | int]] = {}
    directories: set[str] = set()
    for current, dirnames, filenames in os.walk(version_root, followlinks=False):
        for name in (*dirnames, *filenames):
            path = Path(current) / name
            if path.is_symlink():
                raise FreshInstallError("已安装发行内容包含链接")
            relative = path.relative_to(version_root).as_posix()
            if path.is_dir():
                _require_node(path, stat.S_IFDIR | 0o755)
                directories.add(relative)
            elif path.is_file():
                actual[relative] = [
                    _sha256(path),
                    path.stat().st_size,
                    stat.S_IMODE(path.stat().st_mode),
                ]
            else:
                raise FreshInstallError("已安装发行内容包含特殊节点")
    expected_dirs = {
        parent.as_posix()
        for item in expected
        for parent in PurePosixPath(item).parents
        if str(parent) != "."
    }
    if actual != expected or directories != expected_dirs:
        raise FreshInstallError("已安装发行文件漂移：多余、缺失或字节/权限改变")
    if not _runtime_python(root).is_file():
        raise FreshInstallError("独立运行环境缺失；请重建安装")


def _bootstrap_main() -> None:
    """Runs under -I -S: verify before site/.pth or candidate code is imported."""
    try:
        root = Path(sys.argv[1]).resolve()
        layout = load_fresh_install_layout(root)
        import site

        site.main()
        if Path(sys.prefix).resolve() != root / "runtime/venv":
            raise FreshInstallError("入口没有使用本安装根的独立运行环境")
        sys.path.insert(0, str(layout.bundle_root / "src"))
        sys.argv = [str(layout.entrypoint), *sys.argv[2:]]
        from ci_workflow.cli import main

        raise SystemExit(main())
    except (FreshInstallError, OSError, ValueError) as exc:
        print(f"安装运行被阻断：{exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _write_entrypoint(path: Path, bundle_root: Path) -> bool:
    """写候选根自己的 console entry；不触碰 PATH 或既有宿主入口。"""
    content = _entrypoint_content(path.parent.parent)
    if path.exists() or path.is_symlink():
        _require_node(path, stat.S_IFREG | 0o755)
        if path.read_bytes() != content:
            raise FreshInstallError(f"候选入口已存在且内容不同，不覆盖：{path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".ci-workflow-entry-", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fchmod(stream.fileno(), 0o755)
                os.fsync(stream.fileno())
            # Atomic no-clobber publication: unlike replace(), a racing existing
            # entry cannot be overwritten. The temporary link is always removed.
            os.link(temporary, path)
        except FileExistsError as exc:  # pragma: no cover - concurrent installer guard
            raise FreshInstallError(f"候选入口创建竞争失败：{path}") from exc
        finally:
            temporary.unlink(missing_ok=True)
        return True
    return False


def _ensure_symlink(link: Path, target: Path, *, label: str) -> bool:
    """创建或确认明确链接；返回是否由本次安装创建。"""
    expected = target.resolve(strict=False)
    if link.is_symlink():
        if link.resolve(strict=False) != expected:
            raise FreshInstallError(f"{label} 已指向另一内容地址版本：{link}")
        return False
    if link.exists():
        raise FreshInstallError(f"{label} 已存在且不是明确软链接：{link}")
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(_relative_link(link.parent, target), link, target_is_directory=target.is_dir())
    return True


@dataclass(frozen=True)
class FreshInstallLayout:
    """隔离候选安装的稳定路径和内容地址。"""

    install_root: Path
    bundle_path: Path | None
    bundle_digest: str
    bundle_root: Path
    shared_root: Path
    omp_skill_link: Path
    entrypoint: Path
    package_manifest: Path

    @property
    def public_skill(self) -> Path:
        return self.bundle_root / PUBLIC_SKILL_RELATIVE

    @property
    def public_skill_dir(self) -> Path:
        return self.public_skill.parent

    @property
    def shared_public_skill(self) -> Path:
        return self.shared_root / PUBLIC_SKILL_RELATIVE

    def verify_layout(self) -> None:
        """确认共享根、OMP 链接和入口仍绑定本次内容地址。"""
        if self.bundle_root.resolve(strict=False).name != self.bundle_digest:
            raise FreshInstallError("候选版本目录名与 bundle 摘要不一致")
        if self.shared_root.resolve(strict=False) != self.bundle_root.resolve(strict=False):
            raise FreshInstallError("共享规范根未解析到同一 bundle 摘要")
        if self.omp_skill_link.resolve(strict=False) != self.public_skill_dir.resolve(strict=False):
            raise FreshInstallError("OMP 公共 Skill 链接未解析到同一 bundle 摘要")
        if not self.entrypoint.is_file() or not os.access(self.entrypoint, os.X_OK):
            raise FreshInstallError("候选包真实入口不可执行")
        if not self.package_manifest.is_file():
            raise FreshInstallError("候选包 package-manifest.json 不存在")
        _verify_installation(self.install_root, self.bundle_root)


def _install_bundle_locked(
    bundle_path: Path,
    install_root: Path,
    *,
    expected_digest: str | None = None,
) -> FreshInstallLayout:
    """把 `.tar.zst` 候选包安装到全新隔离根，不覆盖既有入口。

    ``install_root`` 可以是尚不存在的路径或空目录；若其中已经有另一个
    内容地址版本、共享根、OMP 链接或入口，安装会失败关闭。安装失败只清理
    本次 staging，不撤销或修改其他目录。
    ``expected_digest`` 若提供，必须与归档外部 SHA-256 一致；否则安装失败关闭。
    """
    bundle = bundle_path.expanduser().resolve()
    if not bundle.is_file():
        raise FreshInstallError(f"候选包不存在：{bundle}")
    raw_root = install_root.expanduser()
    if raw_root.is_symlink():
        raise FreshInstallError(f"隔离安装根不得是软链接，不覆盖：{raw_root}")
    root = raw_root.resolve()
    if root.exists() and not root.is_dir():
        raise FreshInstallError(f"隔离安装根不是目录：{root}")
    root.parent.mkdir(parents=True, exist_ok=True)
    archive_digest = _sha256(bundle)
    if expected_digest is not None:
        expected = _validate_digest(expected_digest, label="候选包外部摘要")
        if archive_digest != expected:
            raise FreshInstallError(f"候选包外部摘要不一致：期望 {expected}，实际 {archive_digest}")
    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.staging-", dir=root.parent))
    target_created = False
    created_links: list[Path] = []
    created_entry = False
    runtime_created = False
    created_files: list[Path] = []
    completed = False
    created_dirs: list[Path] = []

    def ensure_directory(directory: Path) -> None:
        if directory.is_symlink():
            raise FreshInstallError(f"安装目录不得是软链接，不覆盖：{directory}")
        if not directory.exists():
            directory.mkdir()
            created_dirs.append(directory)
            directory.chmod(0o755)
        elif not directory.is_dir():
            raise FreshInstallError(f"安装路径不是目录，不覆盖：{directory}")
        _require_node(directory, stat.S_IFDIR | 0o755)

    try:
        _extract_archive(bundle, staging)
        source_root = _package_root(staging)
        candidate_records = _verify_release_tree(source_root)
        if _sha256(bundle) != archive_digest:
            raise FreshInstallError("校验期间候选归档字节发生变化")

        if not root.exists():
            ensure_directory(root)
        elif any(root.iterdir()):
            # Fresh-install may be retried in an already prepared empty root only;
            # an existing production/host root is never adopted or overwritten.
            allowed = {
                BUNDLE_DIRECTORY_NAME,
                SHARED_ROOT_NAME,
                OMP_SKILLS_ROOT.parts[0],
                ENTRYPOINT_RELATIVE.parts[0],
                "runtime",
                "bootstrap",
                "installation.json",
            }
            unexpected = [entry.name for entry in root.iterdir() if entry.name not in allowed]
            if unexpected:
                raise FreshInstallError(
                    f"隔离安装根非空且含未声明入口，不覆盖：{', '.join(sorted(unexpected))}"
                )

        versions = root / BUNDLE_DIRECTORY_NAME
        if versions.is_symlink():
            raise FreshInstallError(f"版本根不得是软链接，不覆盖：{versions}")
        ensure_directory(versions)
        existing_versions = [entry for entry in versions.iterdir() if entry.name != archive_digest]
        if existing_versions:
            names = ", ".join(sorted(entry.name for entry in existing_versions))
            raise FreshInstallError(f"共享规范根已有其他内容地址版本，不覆盖：{names}")
        version_root = versions / archive_digest
        if version_root.exists() or version_root.is_symlink():
            if not version_root.is_dir() or version_root.is_symlink():
                raise FreshInstallError(f"内容地址版本路径不是目录：{version_root}")
            if _verify_release_tree(version_root) != candidate_records:
                raise FreshInstallError("同一 bundle 摘要的已安装内容与候选归档不一致")
        else:
            shutil.move(str(source_root), str(version_root))
            target_created = True
        if staging.exists():
            shutil.rmtree(staging)

        if (root / "installation.json").exists():
            _verify_installation(root, version_root)
            _runtime_probe(root, version_root)
        else:
            runtime = root / "runtime"
            if runtime.exists() or runtime.is_symlink():
                raise FreshInstallError("独立运行环境已存在但未绑定，不覆盖")
            runtime.mkdir()
            runtime_created = True
            runtime.chmod(0o755)
            _provision_runtime(root, version_root)
            if _verify_release_tree(version_root) != candidate_records:
                raise FreshInstallError("运行环境构建改写了不可变发行文件")
            ensure_directory(root / "bootstrap")
            own = Path(__file__).resolve()
            contract_path = (
                own.parent / "bundle_contract.py"
                if own.parent.name == "bootstrap"
                else own.parents[3] / "tools/bundle_contract.py"
            )
            for name, source in (("fresh_install.py", own), ("bundle_contract.py", contract_path)):
                target = root / "bootstrap" / name
                with target.open("xb") as stream:
                    created_files.append(target)
                    stream.write(source.read_bytes())
                    os.fchmod(stream.fileno(), 0o644)
            receipt = root / "installation.json"
            with receipt.open("xb") as stream:
                created_files.append(receipt)
                stream.write(
                    json.dumps(
                        {
                            "schema_version": "1.0",
                            "install_root": str(root),
                            "bundle_digest": archive_digest,
                            "release_records": candidate_records,
                            "runtime_lock_sha256": _sha256(version_root / "uv.lock"),
                        },
                        sort_keys=True,
                    ).encode()
                )
                os.fchmod(stream.fileno(), 0o644)

        manifest = _read_package_manifest(version_root)
        public_relative = _safe_relative(str(manifest["public_skill"]), label="public_skill")
        public_skill = version_root / public_relative
        public_skill_dir = public_skill.parent
        shared_root = root / SHARED_ROOT_NAME
        for protected_root, label in (
            (root / OMP_SKILLS_ROOT.parts[0], "OMP 根"),
            (root / ENTRYPOINT_RELATIVE.parts[0], "候选入口根"),
        ):
            if protected_root.is_symlink():
                raise FreshInstallError(f"{label} 不得是软链接，不覆盖：{protected_root}")
        for directory in (root / "omp", root / OMP_SKILLS_ROOT, root / "bin"):
            ensure_directory(directory)
        if _ensure_symlink(shared_root, version_root, label="共享规范根"):
            created_links.append(shared_root)
        omp_link = root / OMP_SKILLS_ROOT / public_relative.parent.name
        if _ensure_symlink(omp_link, public_skill_dir, label="OMP 公共 Skill 链接"):
            created_links.append(omp_link)
        entrypoint = root / ENTRYPOINT_RELATIVE
        created_entry = _write_entrypoint(entrypoint, version_root)
        layout = FreshInstallLayout(
            install_root=root,
            bundle_path=bundle,
            bundle_digest=archive_digest,
            bundle_root=version_root,
            shared_root=shared_root,
            omp_skill_link=omp_link,
            entrypoint=entrypoint,
            package_manifest=version_root / "package-manifest.json",
        )
        layout.verify_layout()
        completed = True
        return layout
    except FreshInstallError:
        raise
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise FreshInstallError(f"候选包 fresh-install 失败：{exc}") from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if not completed:
            for link in reversed(created_links):
                if link.is_symlink():
                    link.unlink(missing_ok=True)
            if created_entry:
                (root / ENTRYPOINT_RELATIVE).unlink(missing_ok=True)
            for path in reversed(created_files):
                path.unlink(missing_ok=True)
            if runtime_created:
                shutil.rmtree(root / "runtime", ignore_errors=True)
            if target_created:
                shutil.rmtree(root / BUNDLE_DIRECTORY_NAME / archive_digest, ignore_errors=True)
            for directory in reversed(created_dirs):
                if (
                    directory.is_dir()
                    and not directory.is_symlink()
                    and not any(directory.iterdir())
                ):
                    directory.rmdir()


def load_fresh_install_layout(install_root: Path) -> FreshInstallLayout:
    """从已安装候选根恢复布局，供独立外部 runner 进程使用。"""
    raw_root = install_root.expanduser()
    if raw_root.is_symlink():
        raise FreshInstallError(f"候选安装根不得是软链接：{raw_root}")
    root = raw_root.resolve()
    versions = root / BUNDLE_DIRECTORY_NAME
    if versions.is_symlink():
        raise FreshInstallError(f"候选安装版本根不得是软链接：{versions}")
    if not versions.is_dir():
        raise FreshInstallError(f"候选安装缺少 versions 根：{versions}")
    candidates = list(versions.iterdir())
    if len(candidates) != 1 or not candidates[0].is_dir() or candidates[0].is_symlink():
        raise FreshInstallError("候选安装必须恰好包含一个内容地址版本")
    version_root = candidates[0]
    digest = _validate_digest(version_root.name, label="内容地址目录名")
    manifest = _read_package_manifest(version_root)
    public_relative = _safe_relative(str(manifest["public_skill"]), label="public_skill")
    layout = FreshInstallLayout(
        install_root=root,
        bundle_path=None,
        bundle_digest=digest,
        bundle_root=version_root,
        shared_root=root / SHARED_ROOT_NAME,
        omp_skill_link=root / OMP_SKILLS_ROOT / public_relative.parent.name,
        entrypoint=root / ENTRYPOINT_RELATIVE,
        package_manifest=version_root / "package-manifest.json",
    )
    layout.verify_layout()
    return layout


def install_bundle(
    bundle_path: Path,
    install_root: Path,
    *,
    expected_digest: str | None = None,
) -> FreshInstallLayout:
    """Exclusive per-root installation; never adopt another installer's work."""
    raw = install_root.expanduser()
    if raw.is_symlink():
        raise FreshInstallError("隔离安装根不得是软链接，不覆盖")
    root = raw.resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    lock = root.parent / f".{root.name}.install-lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise FreshInstallError("安装根有并发安装或未释放锁，保留现场") from exc
    try:
        return _install_bundle_locked(bundle_path, root, expected_digest=expected_digest)
    finally:
        lock.rmdir()


# Names kept descriptive at the call sites while allowing the runner and tests to
# use the task vocabulary directly.
fresh_install_bundle = install_bundle


if __name__ == "__main__":
    _bootstrap_main()
