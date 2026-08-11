from __future__ import annotations

import re
from pathlib import PurePosixPath

from ci_workflow.domain.enums import OutputFormat, ReportKind

_VERSION_PATTERN = re.compile(r"^v[0-9]+(?:\.[0-9]+){0,2}(?:-[a-z0-9][a-z0-9.-]*)?$")


class ArtifactPathViolation(ValueError):
    """产物路径脱离规范目录合同。"""


class ArtifactPathService:
    """A/B/C 四格式唯一的、可移动的产物路径生成器。"""

    def version_root(
        self, report: ReportKind, report_version: str
    ) -> PurePosixPath:
        self._validate_version(report_version)
        return PurePosixPath("reports", report.value, report_version)

    def artifact(
        self,
        report: ReportKind,
        report_version: str,
        output: OutputFormat,
    ) -> PurePosixPath:
        root = self.version_root(report, report_version)
        names = {
            OutputFormat.HTML: "html",
            OutputFormat.PDF: "report.pdf",
            OutputFormat.HTML_PPT: "html-ppt",
            OutputFormat.PPTX: "report.pptx",
        }
        return root / names[output]

    def manifest(
        self,
        report: ReportKind,
        report_version: str,
        output: OutputFormat,
    ) -> PurePosixPath:
        return self.version_root(report, report_version) / f"{output.value}.manifest.json"

    def coverage_projection(
        self,
        report: ReportKind,
        report_version: str,
        output: OutputFormat,
    ) -> PurePosixPath:
        return self.version_root(report, report_version) / (
            f"{output.value}.coverage-projection.json"
        )

    def validate_persisted_path(
        self, value: str | PurePosixPath
    ) -> PurePosixPath:
        raw = str(value)
        if "\\" in raw:
            raise ArtifactPathViolation("持久路径必须使用 POSIX 相对路径")
        path = PurePosixPath(raw)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise ArtifactPathViolation("产物路径必须是不含跳转的相对路径")
        if len(path.parts) != 4 or path.parts[0] != "reports":
            raise ArtifactPathViolation("产物路径必须包含报告类型和版本层")
        try:
            report = ReportKind(path.parts[1])
        except ValueError as exc:
            raise ArtifactPathViolation("报告目录只允许 A、B、C 大写标识") from exc
        version = path.parts[2]
        self._validate_version(version)
        candidates: set[PurePosixPath] = set()
        for output in OutputFormat:
            candidates.add(self.artifact(report, version, output))
            candidates.add(self.manifest(report, version, output))
            candidates.add(self.coverage_projection(report, version, output))
        if path not in candidates:
            raise ArtifactPathViolation("产物路径不属于任一规范格式位置")
        return path

    @staticmethod
    def _validate_version(value: str) -> None:
        if not _VERSION_PATTERN.fullmatch(value):
            raise ArtifactPathViolation("报告版本必须是单个小写 v 开头的安全路径段")
