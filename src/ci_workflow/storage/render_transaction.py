"""共享的未发布渲染目录事务边界（A/B/C HTML 渲染接入）。

一个事务只针对当前项目内一个精确的未发布版本目录
``reports/<A|B|C>/<version>``，语义分两段：

- ``begin()``：目标版本目录必须可证明未发布——版本根不存在任何
  ``*.manifest.json`` 清单、不存在 ``html.coverage-projection.json``、
  产物清单存储（``manifests/artifacts``）、当前运行清单和科学复核状态中
  没有记录绑定当前站点或产物清单；
  否则失败关闭并保持既有字节不变。随后精确清理上一轮中断残留（只允许
  无清单的 ``html/`` 目录、``.render-staging.*`` 目录与
  ``.html.manifest.json.*.tmp`` 临时文件三类），返回全新 staging 目录。
- ``commit(manifest_bytes)``：提交前重查绑定；随后把 staging 原子换名为
  ``html``，并把清单原子写入 ``html.manifest.json``。清单写入成功即事务
  提交点；此前的一切中断都只留下可证明未发布的残留，下一轮 ``begin()``
  可恢复。换名遇到非空 ``html``（并发产物）时失败关闭。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from ci_workflow.domain.enums import OutputFormat, ReportKind
from ci_workflow.storage.paths import ArtifactPathService


class RenderTransactionError(RuntimeError):
    """未发布渲染目录事务无法安全开放、提交或恢复。"""


_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_STAGING_PREFIX = ".render-staging."
_MANIFEST_SUFFIX = ".manifest.json"
_MANIFEST_TEMP_PREFIX = ".html.manifest.json."
_MANIFEST_TEMP_SUFFIX = ".tmp"
_COVERAGE_PROJECTION_NAME = "html.coverage-projection.json"


def _contains_path(value: object, targets: frozenset[str]) -> bool:
    """递归判断封闭 JSON 记录是否精确引用当前站点或清单路径。"""
    if isinstance(value, str):
        return value in targets
    if isinstance(value, list):
        return any(_contains_path(item, targets) for item in value)
    if isinstance(value, dict):
        return any(_contains_path(item, targets) for item in value.values())
    return False


class UnpublishedRenderTransaction:
    """单个未发布版本目录的可恢复渲染事务。"""

    def __init__(
        self,
        project_root: Path,
        *,
        report: Literal["A", "B", "C"],
        report_version: str,
        run_id: str,
    ) -> None:
        if not isinstance(run_id, str) or _RUN_ID_PATTERN.fullmatch(run_id) is None:
            raise RenderTransactionError("运行标识必须是安全路径段")
        paths = ArtifactPathService()
        try:
            kind = ReportKind(report)
            version_relative = paths.version_root(kind, report_version)
            site_relative = paths.artifact(kind, report_version, OutputFormat.HTML)
            manifest_relative = paths.manifest(kind, report_version, OutputFormat.HTML)
        except ValueError as error:
            raise RenderTransactionError(f"渲染事务身份不合法：{error}") from error
        self.project_root = project_root.resolve()
        self.report = report
        self.report_version = report_version
        self.run_id = run_id
        self.version_root = self.project_root.joinpath(*version_relative.parts)
        self.site_root = self.project_root.joinpath(*site_relative.parts)
        self.manifest_path = self.project_root.joinpath(*manifest_relative.parts)
        self.staging_root = self.version_root / f"{_STAGING_PREFIX}{run_id}"

    def _binding_conflict(self) -> str | None:
        """返回阻止事务开放的完成绑定说明；无绑定则返回 None。"""
        if self.version_root.is_dir():
            for entry in sorted(self.version_root.iterdir()):
                if entry.name.endswith(_MANIFEST_SUFFIX):
                    return f"版本目录已存在产物清单，拒绝覆盖完成绑定：{entry.name}"
            if (self.version_root / _COVERAGE_PROJECTION_NAME).exists():
                return "版本目录已存在覆盖投影，拒绝覆盖完成绑定"
        store_directory = self.project_root / "manifests" / "artifacts"
        if store_directory.is_dir():
            site_relative = self.site_root.relative_to(self.project_root).as_posix()
            for record in sorted(store_directory.glob("*.json")):
                if not record.is_file():
                    continue
                try:
                    payload = json.loads(record.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    return f"产物清单存储存在不可读记录，无法证明未发布：{record.name}"
                artifact = payload.get("artifact") if isinstance(payload, dict) else None
                bound = (
                    artifact.get("relative_path") if isinstance(artifact, dict) else None
                )
                if bound == site_relative:
                    return f"产物清单存储已绑定当前版本目录，拒绝覆盖：{record.name}"
        targets = frozenset(
            {
                self.site_root.relative_to(self.project_root).as_posix(),
                self.manifest_path.relative_to(self.project_root).as_posix(),
            }
        )
        current_run = self.project_root / "manifests" / "current_run.json"
        conflict = self._json_binding_conflict(
            current_run,
            targets,
            label="当前运行清单",
        )
        if conflict is not None:
            return conflict
        review_directory = self.project_root / "state" / "scientific_review" / self.report
        if review_directory.exists():
            if review_directory.is_symlink() or not review_directory.is_dir():
                return "科学复核状态目录不可读，无法证明未发布"
            for record in sorted(review_directory.glob("*.json")):
                conflict = self._json_binding_conflict(
                    record,
                    targets,
                    label="科学复核状态",
                )
                if conflict is not None:
                    return conflict
        return None

    @staticmethod
    def _json_binding_conflict(
        path: Path,
        targets: frozenset[str],
        *,
        label: str,
    ) -> str | None:
        if not path.exists():
            return None
        if path.is_symlink() or not path.is_file():
            return f"{label}不可读，无法证明未发布：{path.name}"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return f"{label}存在不可读记录，无法证明未发布：{path.name}"
        if _contains_path(payload, targets):
            return f"{label}已绑定当前版本产物，拒绝覆盖：{path.name}"
        return None

    def _discard_residue(self) -> None:
        """全量检查通过后，精确清理当前版本目录内的未发布残留。"""
        if not self.version_root.exists():
            return
        if self.version_root.is_symlink() or not self.version_root.is_dir():
            raise RenderTransactionError("版本目录不是可控目录，无法证明未发布")
        if not self.version_root.resolve().is_relative_to(self.project_root):
            raise RenderTransactionError("版本目录越出项目根，拒绝清理")
        cleanup: list[tuple[Path, bool]] = []
        for entry in sorted(self.version_root.iterdir()):
            if entry.is_symlink():
                raise RenderTransactionError(f"残留项是符号链接，拒绝清理：{entry.name}")
            is_staging = entry.name.startswith(_STAGING_PREFIX)
            if (entry == self.site_root or is_staging) and entry.is_dir():
                cleanup.append((entry, True))
            elif (
                entry.name.startswith(_MANIFEST_TEMP_PREFIX)
                and entry.name.endswith(_MANIFEST_TEMP_SUFFIX)
                and entry.is_file()
            ):
                cleanup.append((entry, False))
            else:
                raise RenderTransactionError(
                    f"版本目录含未知内容，无法证明未发布：{entry.name}"
                )
        # 检查阶段不得删除任何项：后置未知内容或符号链接也须保留全部现场。
        for entry, is_directory in cleanup:
            if is_directory:
                shutil.rmtree(entry)
            else:
                entry.unlink()
        self.version_root.rmdir()

    def begin(self) -> Path:
        """确认目标未发布、清理中断残留，并返回全新 staging 目录。"""
        conflict = self._binding_conflict()
        if conflict is not None:
            raise RenderTransactionError(conflict)
        self._discard_residue()
        self.staging_root.mkdir(parents=True)
        return self.staging_root

    def commit(self, manifest_bytes: bytes) -> tuple[Path, Path]:
        """staging 原子换名为 html 并最后原子写入清单（事务提交点）。"""
        if not self.staging_root.is_dir():
            raise RenderTransactionError("渲染事务尚未开始或已被清理，无法提交")
        conflict = self._binding_conflict()
        if conflict is not None:
            raise RenderTransactionError(f"提交前发现完成绑定，事务中止：{conflict}")
        try:
            os.replace(self.staging_root, self.site_root)
        except OSError as error:
            raise RenderTransactionError(f"未发布渲染目录换名失败：{error}") from error
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=_MANIFEST_TEMP_PREFIX, suffix=_MANIFEST_TEMP_SUFFIX, dir=self.version_root
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(manifest_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.manifest_path)
        except OSError as error:
            raise RenderTransactionError(f"产物清单原子写入失败：{error}") from error
        finally:
            temporary.unlink(missing_ok=True)
        return self.site_root, self.manifest_path
