"""可移动 Skill bundle 的共享合同与低层校验工具。

PK01/PK02 的边界只有内容闭合与可移植性：构建器使用显式 allowlist，
校验器只接受普通文件和目录，并对每个文件重算 SHA-256。这里不读取
项目输出、缓存或凭据，也不执行安装或宿主适配器。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO, Any, cast

BUNDLE_MANIFEST_NAME = "bundle-manifest.json"
BUNDLE_FORMAT = "skill-bundle"
BUNDLE_SCHEMA_VERSION = "1.0"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
# Git SHA-1 (40) 与 SHA-256 仓库（64）的完整 commit SHA；拒绝缩写与拼写变体。
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:")
REQUIRED_CATALOG_ID = "required-v12"
PORTAL_ASSET_MIRROR_FILES: tuple[str, ...] = (
    "charts.js",
    "portal.css",
    "portal.js",
    "evidence-drawer.css",
    "evidence-drawer.js",
    "report-a.css",
    "report-a.js",
    "report-b.css",
    "report-b.js",
    "report-c.css",
    "report-c.js",
)

# These names are never valid payloads for a portable candidate bundle. The
# builder skips them when they occur below an approved directory; the verifier
# rejects them if they somehow occur in a staged directory or archive.
FORBIDDEN_COMPONENTS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        ".tox",
        ".nox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "__pycache__",
        "output",
        ".artifacts",
        "tmp",
        "runs",
        "logs",
        "archives",
        "context",
        "reviews",
        "plans",
        "prompts",
        "conference",
    }
)
_ALLOWED_RUNTIME_TEST = PurePosixPath("contracts/kangzhe/design_specs/tests/test_package_load.py")
_SECRET_BASENAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "credentials",
        "credentials.json",
        "credentials.yaml",
        "credentials.yml",
        "secrets",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
        "service-account.json",
        "id_rsa",
        "id_ed25519",
        "password",
        "password.txt",
        "api_key",
        "api-key",
        "token",
        "token.txt",
    }
)
_SECRET_SUFFIXES = frozenset(
    {
        ".pem",
        ".key",
        ".p12",
        ".pfx",
        ".secret",
        ".secrets",
        ".token",
        ".tokens",
        ".credentials",
    }
)
_FORBIDDEN_SUFFIXES = frozenset({".pyc", ".pyo", ".log", ".tmp", ".swp"})
_V1_DEFERRED_PATHS = frozenset(
    {
        "assets/html-ppt",
        "fixtures/synthetic/pdf-native-slice",
        "src/ci_workflow/application/monitoring_service.py",
        "src/ci_workflow/application/ppt_master_job.py",
        "src/ci_workflow/domain/monitoring.py",
        "src/ci_workflow/graph/definitions/monitoring.py",
        "src/ci_workflow/qc/pdf.py",
        "src/ci_workflow/renderers/html_ppt",
        "src/ci_workflow/renderers/pdf",
        "src/ci_workflow/renderers/pdf_native",
        "src/ci_workflow/renderers/pptx_master",
        "schemas/monitoring-change-candidate.schema.json",
        "schemas/ppt-master-job.schema.json",
        "schemas/pptx-confirmation.schema.json",
        "schemas/pptx-source-pack.schema.json",
        "skills/_internal/monitoring",
    }
)


def is_v1_deferred_path(relative_path: str) -> bool:
    """判断路径是否属于 v1 明确延后的格式、监测或 PDF 交付面。"""
    path = PurePosixPath(relative_path)
    return any(
        path == PurePosixPath(prefix) or PurePosixPath(prefix) in path.parents
        for prefix in _V1_DEFERRED_PATHS
    )


def _assert_not_deferred(relative_path: str, *, label: str) -> None:
    if is_v1_deferred_path(relative_path):
        raise BundleError(f"{label}属于 v1 延后能力，不得进入 HTML-only bundle：{relative_path}")


class BundleError(ValueError):
    """输入或内容不符合 bundle 合同。"""


class BundleEnvironmentError(BundleError):
    """构建或校验所需的外部环境工具不可用。"""


@dataclass(frozen=True)
class FileRecord:
    """逐文件内容绑定。"""

    path: str
    sha256: str
    byte_size: int

    def as_dict(self) -> dict[str, object]:
        return {"path": self.path, "sha256": self.sha256, "bytes": self.byte_size}


@dataclass(frozen=True)
class BundleVerificationResult:
    """校验成功后的紧凑证据。"""

    bundle_path: Path
    manifest: dict[str, Any]
    files: tuple[FileRecord, ...]
    archive_sha256: str | None


@dataclass(frozen=True)
class _ArchiveInventory:
    manifest_bytes: bytes
    files: dict[str, tuple[str, int]]


def canonical_json_bytes(value: object) -> bytes:
    """生成跨运行稳定的 UTF-8 JSON 字节。"""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise BundleError(f"无法读取文件：{path}") from exc
    return digest.hexdigest()


def validate_relative_path(value: object, *, label: str = "路径") -> str:
    """校验并返回严格的相对 POSIX 路径。"""

    if not isinstance(value, str) or not value:
        raise BundleError(f"{label}必须是非空字符串")
    if "\x00" in value:
        raise BundleError(f"{label}包含 NUL 字符：{value!r}")
    if "\\" in value:
        raise BundleError(f"{label}必须使用 POSIX 分隔符：{value}")
    if value.startswith("/") or _WINDOWS_ABSOLUTE_PATTERN.match(value):
        raise BundleError(f"{label}不能是绝对路径：{value}")
    if value.endswith("/"):
        raise BundleError(f"{label}不能以目录分隔符结尾：{value}")
    path = PurePosixPath(value)
    if path == PurePosixPath(".") or not path.parts:
        raise BundleError(f"{label}不能是当前目录：{value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise BundleError(f"{label}包含非法路径段：{value}")
    if path.as_posix() != value:
        raise BundleError(f"{label}不是规范相对路径：{value}")
    return value


def normalise_archive_member_name(value: object, *, is_directory: bool) -> str:
    """严格规范 tar 成员名；拒绝绝对路径、``..`` 和反斜杠。"""

    if not isinstance(value, str) or not value:
        raise BundleError("归档成员名不能为空")
    original = value
    if is_directory:
        value = value.rstrip("/")
        if original not in {value, f"{value}/"}:
            raise BundleError(f"归档目录成员名不是规范路径：{original}")
    elif value.endswith("/"):
        raise BundleError(f"普通文件成员名不能以目录分隔符结尾：{value}")
    return validate_relative_path(value, label="归档成员名")


def is_forbidden_path(relative_path: str) -> bool:
    """判断路径是否属于缓存、旧输出、测试或凭据。"""

    path = PurePosixPath(relative_path)
    if "tests" in path.parts and path not in {
        _ALLOWED_RUNTIME_TEST.parent,
        _ALLOWED_RUNTIME_TEST,
    }:
        return True
    if any(part in FORBIDDEN_COMPONENTS for part in path.parts):
        return True
    basename = path.name.lower()
    if (
        basename in _SECRET_BASENAMES
        or basename.startswith(".env.")
        or basename.startswith("credentials.")
        or basename.startswith("secrets.")
        or basename.startswith("password.")
        or basename.startswith("api_key.")
        or basename.startswith("api-key.")
    ):
        return True
    return any(basename.endswith(suffix) for suffix in (*_SECRET_SUFFIXES, *_FORBIDDEN_SUFFIXES))


def _assert_not_forbidden(relative_path: str, *, label: str) -> None:
    if is_forbidden_path(relative_path):
        raise BundleError(f"{label}命中禁止打包路径：{relative_path}")


def _resolved_root(source_root: Path) -> Path:
    expanded = source_root.expanduser()
    if expanded.is_symlink():
        raise BundleError(f"源根目录不能是软链接：{source_root}")
    source = expanded.resolve()
    if not source.is_dir():
        raise BundleError(f"源根目录不存在或不是普通目录：{source_root}")
    return source


def _relative_from_root(path: Path, root: Path) -> str:
    try:
        relative = path.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise BundleError(f"路径越出源根目录：{path}") from exc
    return validate_relative_path(relative.as_posix(), label="源文件路径")


def _collect_directory_files(directory: Path, root: Path) -> set[str]:
    """递归收集普通文件，跳过缓存、延后能力和凭据。"""

    collected: set[str] = set()
    for current, dirnames, filenames in os.walk(directory, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            child = current_path / dirname
            relative = _relative_from_root(child, root)
            if is_v1_deferred_path(relative):
                continue
            if child.is_symlink():
                raise BundleError(f"allowlist 目录包含软链接：{relative}")
            if is_forbidden_path(relative):
                continue
            if not child.is_dir():
                raise BundleError(f"allowlist 目录包含非目录节点：{relative}")
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            child = current_path / filename
            relative = _relative_from_root(child, root)
            if is_v1_deferred_path(relative):
                continue
            if child.is_symlink():
                raise BundleError(f"allowlist 目录包含软链接：{relative}")
            if not child.is_file():
                raise BundleError(f"allowlist 目录包含非普通文件：{relative}")
            if is_forbidden_path(relative):
                continue
            collected.add(relative)
    return collected


def expand_allowlist(
    source_root: Path,
    allowlist: Iterable[str | Path],
) -> tuple[str, ...]:
    """展开显式 allowlist，返回排序后的逐文件相对路径。"""
    root = _resolved_root(source_root)
    entries = list(allowlist)
    if not entries:
        raise BundleError("allowlist 不能为空")
    files: set[str] = set()
    for raw_entry in entries:
        if isinstance(raw_entry, Path):
            entry = raw_entry.as_posix()
        elif isinstance(raw_entry, str):
            entry = raw_entry
        else:
            raise BundleError("allowlist 项必须是路径字符串")
        relative = validate_relative_path(entry, label="allowlist 路径")
        _assert_not_forbidden(relative, label="allowlist 路径")
        _assert_not_deferred(relative, label="allowlist 路径")
        candidate = root / relative
        try:
            candidate_resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise BundleError(f"allowlist 路径不存在：{relative}") from exc
        if not candidate_resolved.is_relative_to(root):
            raise BundleError(f"allowlist 路径越出源根目录：{relative}")
        if candidate.is_symlink() or candidate_resolved.is_symlink():
            raise BundleError(f"allowlist 路径不能是软链接：{relative}")
        if candidate.is_file():
            files.add(relative)
        elif candidate.is_dir():
            files.update(_collect_directory_files(candidate, root))
        else:
            raise BundleError(f"allowlist 路径不是普通文件或目录：{relative}")
    if not files:
        raise BundleError("allowlist 没有可打包的普通文件")
    return tuple(sorted(files))


# Explicit roots, not a repository-wide glob. Directory roots are recursively
# v1 release source set. Directory entries are explicit roots; the collector
# removes only the listed historical/deferred paths below. Governance tools,
# acceptance evidence, caches, and prior-format renderers are not payloads.
DEFAULT_ALLOWLIST: tuple[str, ...] = (
    "package-manifest.json",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    "src/ci_workflow/__init__.py",
    "src/ci_workflow/__main__.py",
    "src/ci_workflow/cli.py",
    "src/ci_workflow/application",
    "src/ci_workflow/capabilities",
    "src/ci_workflow/domain",
    "src/ci_workflow/gates",
    "src/ci_workflow/graph",
    "src/ci_workflow/hosts",
    "src/ci_workflow/ingestion",
    "src/ci_workflow/qc/__init__.py",
    "src/ci_workflow/qc/browser.py",
    "src/ci_workflow/qc/report_a_acceptance.py",
    "src/ci_workflow/qc/review_receipt.py",
    "src/ci_workflow/qc/scientific.py",
    "src/ci_workflow/reports",
    "src/ci_workflow/renderers/__init__.py",
    "src/ci_workflow/renderers/portal",
    "src/ci_workflow/sources",
    "src/ci_workflow/storage",
    "skills/competitive-intelligence-workflow",
    "skills/_internal",
    "schemas",
    "policies",
    "contracts/kangzhe",
    "assets/brand",
    "assets/portal",
    "assets/third-party/echarts",
    "migrations",
    "fixtures/catalog.yaml",
    "fixtures/synthetic",
    "fixtures/positive/b-pnh",
    "docs/user-guide/install.md",
)


# 最终包闭合项只列 v1 runtime、公开入口、schema、静态资源和可重放 fixture。
# 科学复核信任根链（状态迁移、真实回执、判定模型、能力层校验与两个 schema）
# 是 v1 HTML-only 交付的一部分，缺一即验证失败关闭。
FINAL_REQUIRED_CONTENT: tuple[str, ...] = (
    "package-manifest.json",
    "README.md",
    "uv.lock",
    "pyproject.toml",
    "src/ci_workflow/__main__.py",
    "src/ci_workflow/cli.py",
    "src/ci_workflow/application/fresh_install.py",
    "src/ci_workflow/application/fixture_runner.py",
    "src/ci_workflow/application/autonomous_research.py",
    "src/ci_workflow/application/research_package_submission.py",
    "src/ci_workflow/application/yaozh_access.py",
    "src/ci_workflow/application/review_issuer.py",
    "src/ci_workflow/application/scientific_review_transition.py",
    "src/ci_workflow/capabilities/scientific_qc.py",
    "src/ci_workflow/qc/review_receipt.py",
    "src/ci_workflow/qc/scientific.py",
    "src/ci_workflow/renderers/portal/report_a.py",
    "src/ci_workflow/renderers/portal/report_b.py",
    "src/ci_workflow/renderers/portal/report_c.py",
    "skills/competitive-intelligence-workflow/SKILL.md",
    "skills/_internal/intake-preflight/SKILL.md",
    "schemas/package-manifest.schema.json",
    "schemas/research-package.schema.json",
    "schemas/user-fact-save.schema.json",
    "schemas/scientific-qc-verdict.schema.json",
    "schemas/scientific-review-receipt.schema.json",
    "assets/portal/manifest.json",
    "assets/brand/manifest.json",
    "assets/third-party/echarts/manifest.json",
    "fixtures/catalog.yaml",
    "docs/user-guide/install.md",
)


def validate_portal_asset_mirror(source_root: Path) -> None:
    """Require authored module assets, bundle mirror, and manifest to agree."""

    author_root = source_root / "src/ci_workflow/renderers/portal/assets"
    mirror_root = source_root / "assets/portal"
    manifest = _load_json_object(mirror_root / "manifest.json")
    if manifest.get("author_source") != "src/ci_workflow/renderers/portal/assets/":
        raise BundleError("门户资源清单未声明模块 assets 为唯一作者源")
    records = manifest.get("files")
    if not isinstance(records, dict):
        raise BundleError("门户资源清单 files 必须是对象")
    for name in PORTAL_ASSET_MIRROR_FILES:
        author = author_root / name
        mirror = mirror_root / name
        if not author.is_file() or not mirror.is_file():
            raise BundleError(f"门户资源作者源或发包镜像缺失：{name}")
        author_bytes = author.read_bytes()
        if mirror.read_bytes() != author_bytes:
            raise BundleError(f"门户资源发包镜像与模块作者源不一致：{name}")
        record = records.get(name)
        if not isinstance(record, dict):
            raise BundleError(f"门户资源清单缺少镜像条目：{name}")
        digest = hashlib.sha256(author_bytes).hexdigest()
        if record.get("sha256") != digest or record.get("bytes") != len(author_bytes):
            raise BundleError(f"门户资源清单与模块作者源不一致：{name}")


def default_allowlist(source_root: Path) -> tuple[str, ...]:
    """返回当前候选包的显式 allowlist，并校验门户资源同步合同。"""

    validate_portal_asset_mirror(source_root)
    return DEFAULT_ALLOWLIST


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BundleError(f"无法读取 JSON 文件：{path}") from exc
    if not isinstance(value, dict):
        raise BundleError(f"JSON 顶层必须是对象：{path}")
    return cast(dict[str, Any], value)


def package_identity(source_root: Path) -> tuple[str, str]:
    manifest = _load_json_object(source_root / "package-manifest.json")
    package = manifest.get("package")
    if not isinstance(package, dict):
        raise BundleError("package-manifest.json 缺少 package 对象")
    name = package.get("name")
    version = package.get("version")
    if not isinstance(name, str) or not name.strip():
        raise BundleError("package-manifest.json 的 package.name 无效")
    if not isinstance(version, str) or not version.strip():
        raise BundleError("package-manifest.json 的 package.version 无效")
    if "/" in name or "\\" in name or "/" in version or "\\" in version:
        raise BundleError("包名和版本不能包含路径分隔符")
    return name, version


def _git_output(source_root: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise BundleEnvironmentError("缺少 git；无法执行 clean-commit 来源验证")
    try:
        completed = subprocess.run(
            [executable, "-C", str(source_root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise BundleError(f"git 命令超时：{' '.join(args)}") from exc
    except OSError as exc:
        raise BundleError(f"git 命令无法启动：{' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        if "not a git repository" in stderr.lower():
            raise BundleError(f"源根目录不是 Git 仓库：{source_root}") from exc
        detail = stderr.splitlines()[-1] if stderr else f"退出码 {exc.returncode}"
        raise BundleError(f"git 命令失败（{' '.join(args)}）：{detail}") from exc
    return (completed.stdout or "").strip()


def require_clean_commit_provenance(source_root: Path, expected_commit: str) -> str:
    """校验 source_root 是干净工作树且 HEAD 等于期望 RC commit，返回完整 commit SHA。

    失败关闭语义：源根必须是 Git 仓库根目录本身（不允许仓库子目录或非仓库
    目录）；期望引用必须可解析为提交且与 HEAD 一致；任何已暂存、未暂存或
    未跟踪改动都会拒绝构建。ignored 文件（缓存、虚拟环境、dist）不算脏。
    """

    if not isinstance(expected_commit, str) or not expected_commit.strip():
        raise BundleError("期望 RC commit 不能为空")
    if expected_commit != expected_commit.strip() or expected_commit.startswith("-"):
        raise BundleError(f"期望 RC commit 不是安全的 commit/tag 引用：{expected_commit!r}")
    resolved_root = source_root.expanduser().resolve()
    toplevel = _git_output(resolved_root, "rev-parse", "--show-toplevel")
    if not toplevel or Path(toplevel).resolve() != resolved_root:
        raise BundleError(
            f"源根目录不是 Git 仓库根目录（toplevel={toplevel or 'N/A'}）；"
            "clean-commit 构建必须从仓库根目录发起"
        )
    try:
        commit_ref = f"{expected_commit}^{{commit}}"
        resolved = _git_output(resolved_root, "rev-parse", "--verify", commit_ref)
    except BundleError as exc:
        raise BundleError(f"期望 RC commit 无法解析为提交：{expected_commit}") from exc
    head = _git_output(resolved_root, "rev-parse", "HEAD")
    if resolved != head:
        raise BundleError(f"HEAD {head} 与期望 RC commit {resolved} 不一致")
    if COMMIT_PATTERN.fullmatch(head) is None:
        raise BundleError(f"HEAD 不是规范的完整 commit SHA：{head}")
    status = _git_output(resolved_root, "status", "--porcelain", "--untracked-files=normal")
    if status:
        dirty_count = len(status.splitlines())
        raise BundleError(
            f"工作树不干净（{dirty_count} 项已暂存/未暂存/未跟踪改动）；clean-commit 构建失败关闭"
        )
    return head


def missing_final_content(manifest: Mapping[str, Any]) -> list[str]:
    """返回最终包必需内容中未出现在 manifest files 的路径，全部闭合时为空。"""

    files = manifest.get("files")
    if not isinstance(files, list):
        raise BundleError("bundle manifest files 必须是列表")
    present = {item.get("path") for item in files if isinstance(item, Mapping)}
    return [path for path in FINAL_REQUIRED_CONTENT if path not in present]


_MANIFEST_ALLOWED_KEYS = frozenset(
    {"schema_version", "bundle", "allowlist", "files", "package", "source_commit"}
)
_BUNDLE_ALLOWED_KEYS = frozenset(
    {
        "format",
        "compression",
        "manifest_path",
        "archive_name",
        "external_manifest",
        "external_sha256",
    }
)
_PACKAGE_ALLOWED_KEYS = frozenset({"name", "version"})


def _reject_unknown_keys(raw: Mapping[str, Any], *, allowed: frozenset[str], label: str) -> None:
    unknown = sorted(str(key) for key in raw if key not in allowed)
    if unknown:
        raise BundleError(f"{label}包含未知字段：{', '.join(unknown)}")


def _ensure_manifest_shape(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BundleError("bundle manifest 顶层必须是对象")
    manifest = cast(dict[str, Any], raw)
    _reject_unknown_keys(manifest, allowed=_MANIFEST_ALLOWED_KEYS, label="bundle manifest ")
    if manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise BundleError("bundle manifest schema_version 必须为 1.0")
    bundle = manifest.get("bundle")
    if not isinstance(bundle, dict):
        raise BundleError("bundle manifest 缺少 bundle 对象")
    _reject_unknown_keys(bundle, allowed=_BUNDLE_ALLOWED_KEYS, label="bundle manifest bundle 对象")
    if bundle.get("format") != BUNDLE_FORMAT:
        raise BundleError("bundle manifest format 不正确")
    if bundle.get("compression") != "zstd":
        raise BundleError("bundle manifest compression 必须为 zstd")
    if bundle.get("manifest_path") != BUNDLE_MANIFEST_NAME:
        raise BundleError("bundle manifest manifest_path 不正确")
    source_commit = manifest.get("source_commit")
    if source_commit is not None and (
        not isinstance(source_commit, str) or COMMIT_PATTERN.fullmatch(source_commit) is None
    ):
        raise BundleError("bundle manifest source_commit 必须是小写完整 commit SHA")
    package = manifest.get("package")
    if package is not None:
        if not isinstance(package, dict):
            raise BundleError("bundle manifest package 必须是对象")
        _reject_unknown_keys(
            package, allowed=_PACKAGE_ALLOWED_KEYS, label="bundle manifest package 对象"
        )
        for field in ("name", "version"):
            value = package.get(field)
            if not isinstance(value, str) or not value.strip():
                raise BundleError(f"bundle manifest package.{field} 无效")
            if "/" in value or "\\" in value:
                raise BundleError(f"bundle manifest package.{field} 不能包含路径分隔符")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise BundleError("bundle manifest files 必须是列表")
    parsed: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            raise BundleError(f"bundle manifest files[{index}] 必须是对象")
        path = validate_relative_path(item.get("path"), label=f"files[{index}].path")
        if path == BUNDLE_MANIFEST_NAME:
            raise BundleError("bundle manifest 不能把自身列入 files")
        _assert_not_forbidden(path, label=f"files[{index}].path")
        _assert_not_deferred(path, label=f"files[{index}].path")
        if path in seen:
            raise BundleError(f"bundle manifest 存在重复文件：{path}")
        seen.add(path)
        digest = item.get("sha256")
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise BundleError(f"files[{index}].sha256 必须是小写 SHA-256")
        byte_size = item.get("bytes")
        if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size < 0:
            raise BundleError(f"files[{index}].bytes 必须是非负整数")
        parsed.append({"path": path, "sha256": digest, "bytes": byte_size})
    # Keep the parsed list canonical for callers and reject malformed optional
    # allowlists without making them part of the payload digest calculation.
    allowlist = manifest.get("allowlist")
    if not isinstance(allowlist, list) or not allowlist:
        raise BundleError("bundle manifest allowlist 必须是非空列表")
    for index, item in enumerate(allowlist):
        path = validate_relative_path(item, label=f"allowlist[{index}]")
        _assert_not_forbidden(path, label=f"allowlist[{index}]")
        _assert_not_deferred(path, label=f"allowlist[{index}]")
    manifest["files"] = parsed
    return manifest


def parse_manifest_bytes(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleError("bundle manifest 不是有效 UTF-8 JSON") from exc
    return _ensure_manifest_shape(value)


def records_from_manifest(manifest: Mapping[str, Any]) -> tuple[FileRecord, ...]:
    files = manifest.get("files")
    if not isinstance(files, list):
        raise BundleError("bundle manifest files 必须是列表")
    return tuple(
        FileRecord(path=str(item["path"]), sha256=str(item["sha256"]), byte_size=int(item["bytes"]))
        for item in files
        if isinstance(item, Mapping)
    )


def _hash_stream(stream: IO[bytes]) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def _inventory_directory(root: Path) -> _ArchiveInventory:
    if root.is_symlink() or not root.is_dir():
        raise BundleError(f"bundle 根不是普通目录：{root}")
    manifest_path = root / BUNDLE_MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise BundleError(f"bundle 缺少 {BUNDLE_MANIFEST_NAME}")
    manifest_bytes = manifest_path.read_bytes()
    files: dict[str, tuple[str, int]] = {}
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            child = current_path / dirname
            relative = child.relative_to(root).as_posix()
            relative = validate_relative_path(relative, label="bundle 目录")
            _assert_not_forbidden(relative, label="bundle 目录")
            _assert_not_deferred(relative, label="bundle 目录")
            if child.is_symlink():
                raise BundleError(f"bundle 包含软链接：{relative}")
            if not child.is_dir():
                raise BundleError(f"bundle 包含非目录节点：{relative}")
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            child = current_path / filename
            relative = child.relative_to(root).as_posix()
            relative = validate_relative_path(relative, label="bundle 文件")
            _assert_not_forbidden(relative, label="bundle 文件")
            _assert_not_deferred(relative, label="bundle 文件")
            if child.is_symlink():
                raise BundleError(f"bundle 包含软链接：{relative}")
            if not child.is_file():
                raise BundleError(f"bundle 包含非普通文件：{relative}")
            files[relative] = (sha256_file(child), child.stat().st_size)
    if BUNDLE_MANIFEST_NAME not in files:
        raise BundleError(f"bundle 缺少普通文件 {BUNDLE_MANIFEST_NAME}")
    files.pop(BUNDLE_MANIFEST_NAME)
    return _ArchiveInventory(manifest_bytes=manifest_bytes, files=files)


def _inventory_tar(tar_path: Path) -> _ArchiveInventory:
    manifest_bytes: bytes | None = None
    files: dict[str, tuple[str, int]] = {}
    seen: set[str] = set()
    try:
        with tarfile.open(tar_path, mode="r:") as archive:
            for member in archive:
                if member.isdir():
                    name = normalise_archive_member_name(member.name, is_directory=True)
                    _assert_not_forbidden(name, label="归档目录")
                    _assert_not_deferred(name, label="归档目录")
                    if name in seen:
                        raise BundleError(f"归档存在重复成员：{name}")
                    seen.add(name)
                elif member.isreg():
                    name = normalise_archive_member_name(member.name, is_directory=False)
                    _assert_not_forbidden(name, label="归档文件")
                    _assert_not_deferred(name, label="归档文件")
                    if name in seen:
                        raise BundleError(f"归档存在重复成员：{name}")
                    seen.add(name)
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise BundleError(f"归档成员无法读取：{name}")
                    if name == BUNDLE_MANIFEST_NAME:
                        manifest_bytes = stream.read()
                    else:
                        digest, size = _hash_stream(stream)
                        files[name] = (digest, size)
                else:
                    raise BundleError(f"归档包含软链接、硬链接或特殊节点：{member.name}")
    except (tarfile.TarError, OSError) as exc:
        raise BundleError(f"无法读取 tar 归档：{tar_path}") from exc
    if manifest_bytes is None:
        raise BundleError(f"归档缺少 {BUNDLE_MANIFEST_NAME}")
    return _ArchiveInventory(manifest_bytes=manifest_bytes, files=files)


def _decompress_zstd(archive_path: Path, destination: Path) -> None:
    executable = shutil.which("zstd")
    if executable is None:
        raise BundleEnvironmentError(
            "缺少 zstd；请安装 zstd 后重试，不要以未压缩 tar 冒充 .tar.zst"
        )
    try:
        with destination.open("wb") as stream:
            subprocess.run(
                [executable, "--quiet", "--decompress", "--stdout", str(archive_path)],
                check=True,
                stdout=stream,
                stderr=subprocess.PIPE,
                text=False,
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BundleError(f"无法解压 zstd bundle：{archive_path}") from exc


def _read_checksum_file(checksum_path: Path, archive_path: Path) -> str:
    try:
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise BundleError(f"无法读取外部 SHA-256 文件：{checksum_path}") from exc
    nonempty = [line.strip() for line in lines if line.strip()]
    if len(nonempty) != 1:
        raise BundleError("外部 SHA-256 文件必须恰好包含一行")
    fields = nonempty[0].split()
    if len(fields) not in {1, 2} or SHA256_PATTERN.fullmatch(fields[0]) is None:
        raise BundleError("外部 SHA-256 文件格式无效")
    if len(fields) == 2:
        referenced = fields[1].lstrip("*")
        if Path(referenced).name != archive_path.name:
            raise BundleError("外部 SHA-256 文件未绑定当前归档文件名")
    return fields[0]


def _verify_inventory(
    inventory: _ArchiveInventory,
) -> tuple[dict[str, Any], tuple[FileRecord, ...]]:
    manifest = parse_manifest_bytes(inventory.manifest_bytes)
    records = records_from_manifest(manifest)
    declared = {record.path: record for record in records}
    actual = inventory.files
    missing = sorted(set(declared) - set(actual))
    extra = sorted(set(actual) - set(declared))
    if missing:
        raise BundleError(f"bundle 缺少清单声明文件：{', '.join(missing)}")
    if extra:
        raise BundleError(f"bundle 包含未声明文件：{', '.join(extra)}")
    for path, record in declared.items():
        actual_digest, actual_size = actual[path]
        if actual_size != record.byte_size:
            raise BundleError(f"文件字节数漂移：{path}")
        if actual_digest != record.sha256:
            raise BundleError(f"文件摘要漂移：{path}")
    return manifest, records


def verify_bundle(
    bundle_path: Path,
    *,
    checksum_path: Path | None = None,
    manifest_path: Path | None = None,
    require_external_digest: bool = True,
    expected_source_commit: str | None = None,
    require_final_content: bool = False,
) -> BundleVerificationResult:
    """校验目录或 ``.tar.zst``，并拒绝缺失、额外、漂移和路径异常。"""

    expanded = bundle_path.expanduser()
    if expanded.is_symlink():
        raise BundleError(f"bundle 根不能是软链接：{bundle_path}")
    bundle = expanded.resolve()
    if bundle.is_dir():
        if checksum_path is not None:
            raise BundleError("目录 bundle 不能绑定外部归档 SHA-256")
        inventory = _inventory_directory(bundle)
        archive_digest = None
    elif bundle.is_file():
        sidecar = checksum_path or Path(f"{bundle}.sha256")
        if not sidecar.is_file():
            if require_external_digest:
                raise BundleError(f"缺少外部 SHA-256 文件：{sidecar}")
            expected_digest = None
        else:
            expected_digest = _read_checksum_file(sidecar, bundle)
        actual_digest = sha256_file(bundle)
        if expected_digest is not None and actual_digest != expected_digest:
            raise BundleError("归档外部 SHA-256 与实际内容不一致")
        with tempfile.TemporaryDirectory(prefix=".bundle-verify-") as temporary:
            tar_path = Path(temporary) / "bundle.tar"
            if bundle.name.endswith(".zst"):
                _decompress_zstd(bundle, tar_path)
            else:
                tar_path = bundle
            inventory = _inventory_tar(tar_path)
        archive_digest = actual_digest
    else:
        raise BundleError(f"bundle 路径不存在：{bundle_path}")
    manifest, records = _verify_inventory(inventory)
    if expected_source_commit is not None:
        if (
            not isinstance(expected_source_commit, str)
            or COMMIT_PATTERN.fullmatch(expected_source_commit) is None
        ):
            raise BundleError("期望 source_commit 必须是小写完整 commit SHA")
        if manifest.get("source_commit") != expected_source_commit:
            raise BundleError(
                "bundle source_commit 与期望 RC commit 不一致："
                f"{manifest.get('source_commit')!r} != {expected_source_commit!r}"
            )
    if require_final_content:
        missing = missing_final_content(manifest)
        if missing:
            raise BundleError(f"最终必需内容未随包闭合：{', '.join(missing)}")
    sibling_manifest = manifest_path
    if sibling_manifest is None and bundle.is_file():
        candidate = Path(f"{bundle}.manifest.json")
        sibling_manifest = candidate if candidate.is_file() else None
    if sibling_manifest is not None:
        try:
            sidecar_bytes = sibling_manifest.read_bytes()
        except OSError as exc:
            raise BundleError(f"无法读取外部 bundle manifest：{sibling_manifest}") from exc
        if sidecar_bytes != inventory.manifest_bytes:
            raise BundleError("外部 bundle manifest 与归档内清单不一致")
    return BundleVerificationResult(
        bundle_path=bundle,
        manifest=manifest,
        files=records,
        archive_sha256=archive_digest,
    )
