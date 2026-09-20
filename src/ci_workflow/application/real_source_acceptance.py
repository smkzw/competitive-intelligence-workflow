"""Task 10.2 read-only exact acceptance for fresh real-source HTML runs.

The normal project runner and the portal browser verifier each validate one
layer of a delivery.  This module joins those layers without writing to the
project: a current run manifest, one current HTML artifact manifest and its
report snapshot, the physical site, and a complete Chromium/WebKit verifier
report must all describe the same run and bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from zipfile import BadZipFile, ZipFile

from ci_workflow.application.acceptance_boundary import (
    AcceptanceBoundaryError,
    require_accepted_origin_report_states,
)
from ci_workflow.application.project_service import (
    ProjectWorkspaceError,
    verify_project_workspace,
)
from ci_workflow.application.run_service import (
    MANIFEST_RECORDED_EVENT,
    NODE_REUSED_EVENT,
    validate_run_manifest,
)
from ci_workflow.domain.enums import ReportKind
from ci_workflow.domain.ids import stable_id
from ci_workflow.qc.browser import (
    LockedSitemapSourceError,
    derive_sitemap_contract,
    enumerate_site_routes,
    load_locked_sitemap_source,
    route_to_site_path,
    scan_page_html,
    site_directory_digest,
    verify_page_defects,
    verify_route_reachability,
    verify_sitemap_one_to_one,
)
from ci_workflow.reports.common.page_registry import PageRegistry
from ci_workflow.storage.event_store import EventStore
from ci_workflow.storage.manifest_store import ArtifactManifest

ReportValue = Literal["A", "B", "C"]
_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_REQUIRED_BROWSERS: tuple[str, ...] = ("chromium", "webkit")


class RealSourceAcceptanceError(ValueError):
    """Current-run exact acceptance failed closed."""


@dataclass(frozen=True)
class RealSourceAcceptanceResult:
    """Identifiers and byte identities proved by one exact acceptance node."""

    report: ReportValue
    project_root: Path
    run_id: str
    report_version: str
    manifest_id: str
    report_snapshot_id: str
    site_digest: str
    browser_report_path: Path
    browser_run_digest: str
    routes: tuple[str, ...]
    browsers: tuple[str, ...]
    viewports: tuple[tuple[int, int], ...]




def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise RealSourceAcceptanceError(f"无法读取摘要文件：{path}") from error
    return digest.hexdigest()


def current_package_digest(package_manifest_path: Path | None = None) -> str:
    """Return the byte digest of the package manifest used by the source run."""

    path = package_manifest_path or Path(__file__).resolve().parents[3] / "package-manifest.json"
    if not path.is_file():
        raise RealSourceAcceptanceError(f"当前安装包缺少 package-manifest.json：{path}")
    return _sha256_file(path)


def current_source_commit(repository_root: Path | None = None) -> str:
    """Return the current git commit; absence is an acceptance error, not a fallback."""

    root = (repository_root or Path(__file__).resolve().parents[3]).resolve()
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RealSourceAcceptanceError(f"无法读取当前源代码提交摘要：{root}") from error
    value = completed.stdout.strip()
    if _COMMIT.fullmatch(value) is None:
        raise RealSourceAcceptanceError("当前源代码提交摘要不是 40 或 64 位小写十六进制")
    return value


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealSourceAcceptanceError(f"{label}不能为空")
    return value.strip()




def _required_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RealSourceAcceptanceError(f"{label}必须是对象")
    return value


def _required_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise RealSourceAcceptanceError(f"{label}必须是数组")
    return value


def _parse_datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise RealSourceAcceptanceError(f"{label}必须是带时区的日期时间")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise RealSourceAcceptanceError(f"{label}不是有效日期时间") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RealSourceAcceptanceError(f"{label}必须包含明确时区偏移")
    return parsed


def _parse_digest(value: object, label: str) -> str:
    text = _required_text(value, label)
    if _SHA256.fullmatch(text) is None:
        raise RealSourceAcceptanceError(f"{label}必须是小写 SHA-256")
    return text


def _parse_commit(value: object, label: str) -> str:
    text = _required_text(value, label)
    if _COMMIT.fullmatch(text) is None:
        raise RealSourceAcceptanceError(f"{label}必须是 40 或 64 位小写十六进制")
    return text


def _validate_project_relative(value: object, label: str) -> str:
    text = _required_text(value, label)
    pure = PurePosixPath(text)
    if pure.is_absolute() or ".." in pure.parts or "\\" in text:
        raise RealSourceAcceptanceError(f"{label}必须是项目内 POSIX 相对路径")
    return pure.as_posix()


def _timestamp_ns(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)


def _project_cutoff_matches(actual: datetime, expected: datetime) -> bool:
    localized = actual.astimezone(expected.tzinfo)
    return localized.date() == expected.date() and localized.timetz().replace(
        tzinfo=None
    ) == time.max


def _not_older_than(actual_ns: int, expected: datetime, label: str) -> None:
    # Some filesystems round mtimes.  A whole second is enough tolerance while
    # still rejecting an artifact or verifier copied from an earlier run.
    if actual_ns + 1_000_000_000 < _timestamp_ns(expected):
        raise RealSourceAcceptanceError(f"{label}早于当前运行，疑似复用了旧产物")


def _resolve_path_inside(
    raw: object,
    *,
    base: Path,
    label: str,
    allow_absolute: bool,
) -> Path:
    text = _required_text(raw, label)
    candidate = Path(text).expanduser()
    if candidate.is_absolute() and not allow_absolute:
        raise RealSourceAcceptanceError(f"{label}必须是相对路径")
    options = [candidate] if candidate.is_absolute() else [base / candidate, candidate]
    resolved_base = base.resolve()
    for option in options:
        resolved = option.resolve()
        if resolved == resolved_base or resolved.is_relative_to(resolved_base):
            return resolved
    raise RealSourceAcceptanceError(f"{label}不能离开验收输出目录")


def _assert_fresh_run(
    project_root: Path,
    run_manifest: Mapping[str, Any],
    *,
    project_id: str,
    run_id: str,
) -> tuple[datetime, datetime, str]:
    if run_manifest.get("outcome") != "completed":
        raise RealSourceAcceptanceError("当前运行未以 completed 终态结束")
    if run_manifest.get("case_id") is not None or run_manifest.get("case_digest") is not None:
        raise RealSourceAcceptanceError("真实来源验收不得复用 fixture case 或 case digest")

    started_at = _parse_datetime(run_manifest.get("started_at"), "当前运行开始时间")
    finished_at = _parse_datetime(run_manifest.get("finished_at"), "当前运行结束时间")
    if finished_at < started_at:
        raise RealSourceAcceptanceError("当前运行结束时间早于开始时间")

    reused = run_manifest.get("reused")
    if not isinstance(reused, list):
        raise RealSourceAcceptanceError("当前运行复用节点记录无效")
    reused_artifacts = run_manifest.get("reused_artifacts")
    if not isinstance(reused_artifacts, list):
        raise RealSourceAcceptanceError("当前运行复用产物记录无效")

    artifact_run_id = run_id
    promotion = run_manifest.get("resume") is True
    if promotion:
        states = require_accepted_origin_report_states(
            run_manifest, reports=tuple(run_manifest.get("report_states", {}))
        )
        if len(states) != 1:
            raise RealSourceAcceptanceError("科学复核续接必须且只能绑定一类报告")
        report = next(iter(states))
        node_summary = _required_mapping(run_manifest.get("node_summary"), "当前节点摘要")
        qc_state = node_summary.get(f"scientific_qc:{report}")
        if qc_state not in ("completed", "reused"):
            raise RealSourceAcceptanceError("科学复核续接缺少已完成或可追溯复用的独立质控节点")
        if qc_state == "reused":
            qc_reuse = [
                item
                for item in reused
                if isinstance(item, Mapping)
                and item.get("node_id") == f"scientific_qc:{report}"
            ]
            if len(qc_reuse) != 1:
                raise RealSourceAcceptanceError("科学复核续接缺少唯一独立质控生产运行引用")
        if node_summary.get(f"format:{report}") != "reused":
            raise RealSourceAcceptanceError("科学复核续接必须复用逐字节不变的候选门户")
        receipts = _required_mapping(
            run_manifest.get("scientific_review_receipts"), "科学复核回执摘要"
        )
        _parse_digest(receipts.get(report), "科学复核回执摘要")
        format_reuse = [
            item
            for item in reused
            if isinstance(item, Mapping) and item.get("node_id") == f"format:{report}"
        ]
        if len(format_reuse) != 1:
            raise RealSourceAcceptanceError("科学复核续接缺少唯一门户生产运行引用")
        artifact_run_id = _required_text(
            format_reuse[0].get("run_id"), "门户生产运行标识"
        )
        if artifact_run_id == run_id or not reused_artifacts:
            raise RealSourceAcceptanceError("科学复核续接未绑定原始候选门户")
    elif run_manifest.get("resume") is not False:
        raise RealSourceAcceptanceError("真实来源验收缺少明确的新运行或科学复核续接标记")
    elif reused or reused_artifacts:
        raise RealSourceAcceptanceError("新鲜运行不得包含复用节点或复用产物")

    input_hashes = _required_mapping(run_manifest.get("input_hashes"), "当前运行输入摘要")
    if not input_hashes:
        raise RealSourceAcceptanceError("当前运行缺少真实输入摘要")
    for raw_path, raw_digest in input_hashes.items():
        _validate_project_relative(raw_path, "当前运行输入路径")
        _parse_digest(raw_digest, f"当前运行输入摘要 {raw_path}")

    events = EventStore(project_root).read_all()
    if not events:
        raise RealSourceAcceptanceError("当前运行缺少事件链，不能证明运行身份")
    if any(event.project_id != project_id for event in events):
        raise RealSourceAcceptanceError("事件链包含其他项目身份")
    events_by_run: dict[str, list[Any]] = {}
    for event in events:
        events_by_run.setdefault(event.run_id, []).append(event)

    # 从当前验收运行沿显式 run.node.reused 来源边构造可信运行闭包。等待独立
    # 回执期间可有任意次纯复用 resume；这类中间运行只有复用与清单事件，且
    # 每个来源必须已落入同一闭包。任何有独立计算、失败或无来源的旁支仍拒绝。
    allowed_run_ids = {run_id, artifact_run_id}
    queue = [run_id]
    while queue:
        current = queue.pop()
        for event in events_by_run.get(current, ()):
            if event.event_type != NODE_REUSED_EVENT:
                continue
            source_run_id = event.payload.get("source_run_id")
            if isinstance(source_run_id, str) and source_run_id not in allowed_run_ids:
                allowed_run_ids.add(source_run_id)
                queue.append(source_run_id)

    changed = True
    while changed:
        changed = False
        for candidate_run_id, candidate_events in events_by_run.items():
            if candidate_run_id in allowed_run_ids:
                continue
            reused_events = [
                event for event in candidate_events if event.event_type == NODE_REUSED_EVENT
            ]
            if not reused_events or any(
                event.event_type not in (NODE_REUSED_EVENT, MANIFEST_RECORDED_EVENT)
                for event in candidate_events
            ):
                continue
            source_ids = {
                str(event.payload.get("source_run_id")) for event in reused_events
            }
            if source_ids <= allowed_run_ids:
                allowed_run_ids.add(candidate_run_id)
                changed = True

    unrelated = sorted(set(events_by_run) - allowed_run_ids)
    if unrelated:
        raise RealSourceAcceptanceError(
            "项目存在未连接到当前候选复用谱系的无关历史运行事件："
            + "、".join(unrelated[:3])
        )
    source_events = [event for event in events if event.run_id == artifact_run_id]
    if not source_events:
        raise RealSourceAcceptanceError("门户生产运行缺少事件链")
    source_started_at = min(event.occurred_at for event in source_events)
    return source_started_at, finished_at, artifact_run_id


def _artifact_output(
    run_manifest: Mapping[str, Any],
    *,
    report: ReportValue,
) -> tuple[dict[str, Any], str]:
    outputs = _required_list(run_manifest.get("outputs"), "当前运行产物")
    outputs += _required_list(
        run_manifest.get("reused_artifacts"), "当前运行复用产物"
    )
    prefix = f"reports/{report}/"
    matches: list[tuple[dict[str, Any], str]] = []
    for raw in outputs:
        if not isinstance(raw, dict):
            raise RealSourceAcceptanceError("当前运行产物记录必须是对象")
        rel = _validate_project_relative(raw.get("relative_path"), "当前运行产物路径")
        if rel.startswith(prefix) and rel.endswith("/html.manifest.json"):
            matches.append((raw, rel))
        lower = rel.casefold()
        if lower.endswith((".pdf", ".pptx")) or "/html-ppt/" in lower:
            raise RealSourceAcceptanceError("Task 10.2 首版只接受 HTML，不得包含 PDF/PPT 产物")
    if len(matches) != 1:
        raise RealSourceAcceptanceError(
            f"当前运行必须恰有一份 {report} 类 HTML 产物清单，实际 {len(matches)} 份"
        )
    return matches[0]


def _load_artifact_manifest(
    project_root: Path,
    run_manifest: Mapping[str, Any],
    *,
    report: ReportValue,
    project_id: str,
    artifact_run_id: str,
    started_at: datetime,
) -> tuple[ArtifactManifest, Path, str]:
    output, relative = _artifact_output(run_manifest, report=report)
    manifest_path = project_root / relative
    try:
        manifest = ArtifactManifest.model_validate_json(manifest_path.read_bytes())
    except (OSError, ValueError) as error:
        raise RealSourceAcceptanceError(
            f"当前 {report} 类 HTML 清单无法校验：{manifest_path}"
        ) from error

    version = _required_text(manifest.report_version, "报告版本")
    expected_relative = f"reports/{report}/{version}/html"
    if manifest.report != report or manifest.artifact.relative_path != expected_relative:
        raise RealSourceAcceptanceError("当前 HTML 清单的报告类型、版本或产物路径不一致")
    if manifest.project_id != project_id or manifest.contract_version < 1:
        raise RealSourceAcceptanceError("当前 HTML 清单未绑定当前项目合同")
    if manifest.producer_run_id != artifact_run_id:
        raise RealSourceAcceptanceError("HTML 清单未绑定受控门户生产运行")
    if manifest.manifest_id != stable_id(
        "artifact-manifest", project_id, artifact_run_id, report, version
    ):
        raise RealSourceAcceptanceError("HTML 清单身份不是当前运行派生身份")
    if manifest.status in ("failed", "superseded"):
        raise RealSourceAcceptanceError(f"HTML 清单状态 {manifest.status} 不可用于验收")
    _not_older_than(_timestamp_ns(manifest.generated_at), started_at, "HTML 清单生成时间")

    # The output row is checked again by validate_run_manifest, but keeping the
    # exact digest comparison here ties runtime metadata to the bytes we parsed.
    actual_manifest_digest = _sha256_file(manifest_path)
    if _parse_digest(output.get("sha256"), "HTML 清单文件摘要") != actual_manifest_digest:
        raise RealSourceAcceptanceError("当前运行产物记录与 HTML 清单文件摘要不一致")
    if output.get("byte_size") != manifest_path.stat().st_size:
        raise RealSourceAcceptanceError("当前运行产物记录与 HTML 清单字节数不一致")
    output_mtime = manifest_path.stat().st_mtime_ns
    if output.get("mtime_ns") != output_mtime:
        raise RealSourceAcceptanceError("当前运行产物记录与 HTML 清单 mtime 不一致")
    _not_older_than(output_mtime, started_at, "HTML 清单文件")
    return manifest, manifest_path, actual_manifest_digest

def _verify_artifact_directory(
    project_root: Path,
    *,
    manifest: ArtifactManifest,
    started_at: datetime,
) -> None:
    if manifest.artifact.media_type != "directory":
        raise RealSourceAcceptanceError("HTML 产物必须是目录")
    site_root = project_root.joinpath(*PurePosixPath(manifest.artifact.relative_path).parts)
    if not site_root.is_dir():
        raise RealSourceAcceptanceError(f"HTML 产物目录不存在：{site_root}")
    try:
        files = tuple(path for path in site_root.rglob("*") if path.is_file())
        if not files:
            raise RealSourceAcceptanceError("HTML 产物目录为空")
        actual_digest, actual_bytes = site_directory_digest(site_root)
        latest_mtime = max(path.stat().st_mtime_ns for path in files)
    except OSError as error:
        raise RealSourceAcceptanceError("HTML 产物目录不可读") from error
    if actual_digest != manifest.artifact.sha256:
        raise RealSourceAcceptanceError("HTML 产物目录摘要与清单不一致")
    if actual_bytes != manifest.artifact.byte_size:
        raise RealSourceAcceptanceError("HTML 产物目录字节数与清单不一致")
    modified_at = datetime.fromtimestamp(
        latest_mtime / 1_000_000_000,
        tz=manifest.artifact.modified_at.tzinfo,
    )
    if abs((modified_at - manifest.artifact.modified_at).total_seconds()) > 1.0:
        raise RealSourceAcceptanceError("HTML 产物目录 mtime 与清单不一致")
    _not_older_than(latest_mtime, started_at, "HTML 产物目录")
    _not_older_than(latest_mtime, manifest.generated_at, "HTML 产物目录")




def _verify_runtime_bindings(
    run_manifest: Mapping[str, Any],
    *,
    report: ReportValue,
    manifest: ArtifactManifest,
    manifest_digest: str,
) -> None:
    try:
        require_accepted_origin_report_states(run_manifest, reports=(report,))
    except AcceptanceBoundaryError as error:
        raise RealSourceAcceptanceError(str(error)) from error

    raw_format_states = run_manifest.get("format_states")
    if raw_format_states is not None:
        format_states = _required_mapping(raw_format_states, "格式状态")
        report_formats = _required_mapping(
            format_states.get(report), f"{report} 格式状态"
        )
        if report_formats.get("html") not in {"generated", "quality_check", "delivery_ready"}:
            raise RealSourceAcceptanceError("当前运行没有可验收的 HTML 格式状态")

    raw_manifest_digests = run_manifest.get("html_manifest_sha256")
    if raw_manifest_digests is not None:
        manifest_digests = _required_mapping(raw_manifest_digests, "HTML 清单摘要映射")
        if manifest_digests.get(report) != manifest_digest:
            raise RealSourceAcceptanceError("当前运行的 HTML 清单摘要映射不一致")

    raw_artifact_digests = run_manifest.get("artifact_manifest_sha256")
    if raw_artifact_digests is not None:
        artifact_digests = _required_mapping(raw_artifact_digests, "产物清单摘要映射")
        report_artifact = _required_mapping(
            artifact_digests.get(report), f"{report} 产物清单摘要"
        )
        if report_artifact.get("html") != manifest_digest:
            raise RealSourceAcceptanceError("当前运行的产物清单摘要未绑定 HTML 清单")

    raw_snapshot_ids = run_manifest.get("snapshot_ids")
    if raw_snapshot_ids is not None:
        snapshot_ids = _required_mapping(raw_snapshot_ids, "报告快照映射")
        if snapshot_ids.get(report) != manifest.report_snapshot_id:
            raise RealSourceAcceptanceError("当前运行的报告快照映射不一致")


def _verify_static_site(
    project_root: Path,
    *,
    report: ReportValue,
    manifest: ArtifactManifest,
    started_at: datetime,
) -> tuple[tuple[str, ...], Path]:
    try:
        source = load_locked_sitemap_source(
            project_root, ReportKind(report), manifest.report_version
        )
    except (LockedSitemapSourceError, OSError, ValueError) as error:
        raise RealSourceAcceptanceError(f"锁定报告快照/站点摘要无法闭合：{error}") from error
    if source.manifest != manifest:
        raise RealSourceAcceptanceError("锁定站点来源与当前 HTML 清单不是同一份内容")
    # 快照是按证据内容寻址的不可变研究对象，created_at 可早于渲染运行；
    # 新鲜性由当前运行/复核链、快照摘要与实际站点文件 mtime 共同证明。

    site_root = project_root.joinpath(*PurePosixPath(manifest.artifact.relative_path).parts)
    try:
        contract = derive_sitemap_contract(
            PageRegistry.load(),
            ReportKind(report),
            product_ids=source.product_ids,
            trial_ids=source.trial_ids,
        )
        actual_routes = enumerate_site_routes(site_root, ReportKind(report))
        sitemap = verify_sitemap_one_to_one(contract, actual_routes)
    except (OSError, ValueError) as error:
        raise RealSourceAcceptanceError(f"站点地图无法读取：{error}") from error
    if not sitemap.ok:
        raise RealSourceAcceptanceError(sitemap.message_zh)

    inspections = []
    for route in contract.routes:
        path = site_root / route_to_site_path(route)
        try:
            inspection = scan_page_html(path.read_text(encoding="utf-8"), route)
        except (OSError, UnicodeError, ValueError) as error:
            raise RealSourceAcceptanceError(f"路由 {route} 页面无法读取：{path}") from error
        inspections.append(inspection)
    valid_paths = tuple(
        sorted(path.relative_to(site_root) for path in site_root.rglob("*") if path.is_file())
    )
    defects = tuple(verify_page_defects(item, valid_paths) for item in inspections)
    failed_defects = tuple(item for item in defects if not item.ok)
    if failed_defects:
        raise RealSourceAcceptanceError(failed_defects[0].message_zh)
    reachability = verify_route_reachability(contract, inspections)
    if not reachability.ok:
        raise RealSourceAcceptanceError(reachability.message_zh)
    return contract.routes, site_root


def _path_text_matches_directory(raw: object, directory: Path, *, label: str) -> Path:
    resolved = _resolve_path_inside(
        raw,
        base=directory,
        label=label,
        allow_absolute=True,
    )
    if resolved != directory.resolve():
        raise RealSourceAcceptanceError(f"{label}未绑定当前浏览器验收输出目录")
    return resolved


def _png_is_real(path: Path, *, label: str) -> None:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise RealSourceAcceptanceError(f"{label}无法读取：{path}") from error
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise RealSourceAcceptanceError(f"{label}不是有效 PNG：{path}")
    if int.from_bytes(payload[16:20], "big") <= 0 or int.from_bytes(payload[20:24], "big") <= 0:
        raise RealSourceAcceptanceError(f"{label}尺寸无效：{path}")


def _zip_contains(path: Path, needles: tuple[bytes, ...], *, label: str) -> None:
    try:
        with ZipFile(path) as archive:
            if archive.testzip() is not None or not archive.namelist():
                raise RealSourceAcceptanceError(f"{label}不是完整浏览器 trace：{path}")
            found = [False] * len(needles)
            for member in archive.infolist():
                with archive.open(member) as stream:
                    tail = b""
                    while True:
                        chunk = stream.read(64 * 1024)
                        if not chunk:
                            break
                        payload = tail + chunk
                        for index, needle in enumerate(needles):
                            if not found[index] and needle in payload:
                                found[index] = True
                        tail = payload[-max(len(needle) for needle in needles) :]
            if not all(found):
                raise RealSourceAcceptanceError(
                    f"{label}未包含当前运行/站点摘要：{path}"
                )
    except (BadZipFile, KeyError, OSError, RuntimeError) as error:
        raise RealSourceAcceptanceError(f"{label}不是有效 ZIP：{path}") from error


def _verify_browser_report(
    browser_report_path: Path,
    *,
    report: ReportValue,
    manifest: ArtifactManifest,
    run_id: str,
    started_at: datetime,
    routes: tuple[str, ...],
    required_browsers: tuple[str, ...],
) -> tuple[str, tuple[tuple[int, int], ...]]:
    try:
        payload = json.loads(browser_report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RealSourceAcceptanceError(f"浏览器验收结论无法读取：{browser_report_path}") from error
    if not isinstance(payload, dict):
        raise RealSourceAcceptanceError("浏览器验收结论顶层必须是对象")
    if payload.get("tool") != "verify_portal" or payload.get("ok") is not True:
        raise RealSourceAcceptanceError("浏览器验收结论不是当前 verify_portal 的通过结果")
    if payload.get("report") != report or payload.get("version") != manifest.report_version:
        raise RealSourceAcceptanceError("浏览器验收结论的报告或版本不一致")
    if payload.get("manifest_id") != manifest.manifest_id:
        raise RealSourceAcceptanceError("浏览器验收结论未绑定当前产物清单")
    if payload.get("report_snapshot_id") != manifest.report_snapshot_id:
        raise RealSourceAcceptanceError("浏览器验收结论未绑定当前报告快照")
    site_digest = _parse_digest(payload.get("site_digest"), "浏览器验收站点摘要")
    if site_digest != manifest.artifact.sha256:
        raise RealSourceAcceptanceError("浏览器验收站点摘要与当前产物不一致")
    run_digest = _parse_digest(payload.get("run_digest"), "浏览器验收运行摘要")

    browsers_raw = _required_list(payload.get("browsers"), "浏览器列表")
    declared_browsers = tuple(_required_text(item, "浏览器名称") for item in browsers_raw)
    if (
        len(set(declared_browsers)) != len(declared_browsers)
        or set(declared_browsers) != set(required_browsers)
    ):
        raise RealSourceAcceptanceError("浏览器验收必须恰好覆盖 Chromium 与 WebKit")
    browsers = required_browsers
    viewports_raw = _required_list(payload.get("viewports"), "验收视口列表")
    viewports: list[tuple[int, int]] = []
    for raw in viewports_raw:
        if not isinstance(raw, list) or len(raw) != 2 or not all(type(v) is int for v in raw):
            raise RealSourceAcceptanceError("验收视口必须是 [width, height]")
        width, height = raw
        if width <= 0 or height <= 0:
            raise RealSourceAcceptanceError("验收视口尺寸必须为正数")
        viewports.append((width, height))
    if not viewports or len(set(viewports)) != len(viewports):
        raise RealSourceAcceptanceError("验收视口列表不能为空或重复")
    expected_routes = list(routes)
    if payload.get("routes") != expected_routes:
        raise RealSourceAcceptanceError("浏览器验收路由集合与当前站点地图不一致")

    sitemap = _required_mapping(payload.get("sitemap"), "浏览器站点地图结论")
    if sitemap.get("ok") is not True:
        raise RealSourceAcceptanceError("浏览器验收的站点地图结论未通过")
    sitemap_expected = sitemap.get("expected_routes")
    sitemap_actual = sitemap.get("actual_routes")
    if (
        not isinstance(sitemap_expected, list)
        or not all(isinstance(route, str) for route in sitemap_expected)
        or len(sitemap_expected) != len(set(sitemap_expected))
        or set(sitemap_expected) != set(expected_routes)
        or not isinstance(sitemap_actual, list)
        or not all(isinstance(route, str) for route in sitemap_actual)
        or len(sitemap_actual) != len(set(sitemap_actual))
        or set(sitemap_actual) != set(expected_routes)
    ):
        raise RealSourceAcceptanceError("浏览器验收站点地图不是当前完整路由集合")
    reachability = _required_mapping(payload.get("reachability"), "浏览器可达性结论")
    if reachability.get("ok") is not True or reachability.get("unreachable_routes") != []:
        raise RealSourceAcceptanceError("浏览器验收存在不可达路由")
    reachable_routes = reachability.get("reachable_routes")
    if (
        not isinstance(reachable_routes, list)
        or not all(isinstance(route, str) for route in reachable_routes)
        or len(reachable_routes) != len(set(reachable_routes))
        or set(reachable_routes) != set(expected_routes)
    ):
        raise RealSourceAcceptanceError("浏览器验收未覆盖全部可达路由")

    pages = _required_list(payload.get("pages"), "浏览器页面结论")
    if len(pages) != len(routes):
        raise RealSourceAcceptanceError("浏览器验收页面数量与路由数量不一致")
    seen_routes: set[str] = set()
    expected_checks = {(browser, viewport) for browser in browsers for viewport in viewports}
    for raw_page in pages:
        page = _required_mapping(raw_page, "浏览器页面结论")
        route = _required_text(page.get("route"), "浏览器页面路由")
        if route in seen_routes or route not in routes:
            raise RealSourceAcceptanceError("浏览器验收页面路由重复或不在当前站点地图")
        seen_routes.add(route)
        if page.get("ok") is not True:
            raise RealSourceAcceptanceError(f"浏览器验收页面未通过：{route}")
        checks = _required_list(page.get("checks"), f"{route} 浏览器检查")
        if len(checks) != len(expected_checks):
            raise RealSourceAcceptanceError(f"{route} 未覆盖全部浏览器/视口检查")
        actual_checks: set[tuple[str, tuple[int, int]]] = set()
        for raw_check in checks:
            check = _required_mapping(raw_check, f"{route} 浏览器检查")
            browser = _required_text(check.get("browser"), "浏览器检查名称")
            raw_viewport = check.get("viewport")
            if (
                not isinstance(raw_viewport, list)
                or len(raw_viewport) != 2
                or not all(type(value) is int for value in raw_viewport)
            ):
                raise RealSourceAcceptanceError(f"{route} 浏览器检查视口无效")
            viewport = (raw_viewport[0], raw_viewport[1])
            if viewport not in viewports or (browser, viewport) in actual_checks:
                raise RealSourceAcceptanceError(f"{route} 浏览器检查重复或超出声明集合")
            actual_checks.add((browser, viewport))
            if check.get("ok") is not True or check.get("violations") != []:
                raise RealSourceAcceptanceError(f"{route} 存在浏览器缺陷：{browser} {viewport}")
        if actual_checks != expected_checks:
            raise RealSourceAcceptanceError(f"{route} 未覆盖 Chromium/WebKit 全部视口")
    if seen_routes != set(routes):
        raise RealSourceAcceptanceError("浏览器验收缺少站点路由")

    output_dir = _path_text_matches_directory(
        payload.get("output_dir"), browser_report_path.parent, label="浏览器验收输出目录"
    )
    screenshots = _required_mapping(payload.get("screenshots"), "截图结论")
    screenshot_dir = _path_text_matches_directory(
        screenshots.get("dir"), output_dir / "screenshots", label="截图目录"
    )
    expected_screenshot_count = len(routes) * len(browsers) * len(viewports)
    if (
        type(screenshots.get("count")) is not int
        or screenshots.get("count") != expected_screenshot_count
    ):
        raise RealSourceAcceptanceError("截图数量未覆盖全部路由、浏览器和视口")
    for route in routes:
        slug = route.lstrip("/").replace("/", "_")
        for browser in browsers:
            for width, height in viewports:
                path = screenshot_dir / f"{slug}__{browser}__{width}x{height}.png"
                if not path.is_file():
                    raise RealSourceAcceptanceError(f"缺少当前浏览器截图：{path}")
                _png_is_real(path, label="浏览器截图")
                _not_older_than(path.stat().st_mtime_ns, started_at, "浏览器截图")

    traces = _required_list(payload.get("traces"), "trace 结论")
    if len(traces) != len(browsers):
        raise RealSourceAcceptanceError("trace 数量未覆盖全部浏览器")
    seen_trace_browsers: set[str] = set()
    for raw_trace in traces:
        trace = _required_mapping(raw_trace, "trace 结论")
        browser = _required_text(trace.get("browser"), "trace 浏览器名称")
        if browser not in browsers or browser in seen_trace_browsers:
            raise RealSourceAcceptanceError("trace 浏览器重复或未声明")
        seen_trace_browsers.add(browser)
        if trace.get("run_digest") != run_digest or trace.get("site_digest") != site_digest:
            raise RealSourceAcceptanceError("trace 未绑定当前浏览器运行和站点摘要")
        raw_path = trace.get("path")
        trace_path = _resolve_path_inside(
            raw_path,
            base=output_dir,
            label="trace 路径",
            allow_absolute=False,
        )
        if not trace_path.is_file():
            raise RealSourceAcceptanceError(f"缺少当前浏览器 trace：{trace_path}")
        _not_older_than(trace_path.stat().st_mtime_ns, started_at, "浏览器 trace")
        _zip_contains(
            trace_path,
            (run_digest.encode("ascii"), site_digest.encode("ascii")),
            label="浏览器 trace",
        )
    if seen_trace_browsers != set(browsers):
        raise RealSourceAcceptanceError("trace 未覆盖 Chromium/WebKit")

    _not_older_than(browser_report_path.stat().st_mtime_ns, started_at, "浏览器验收结论")
    # ``run_id`` is not emitted by the legacy verifier.  The current artifact
    # and current site digest are the binding edge; requiring the same project
    # run through the manifest above prevents an unrelated old report from
    # being accepted.  Keep the argument consumed to make that invariant
    # explicit at the call site and prevent accidental API drift.
    if not run_id.strip():
        raise RealSourceAcceptanceError("当前运行标识不能为空")
    return run_digest, tuple(viewports)


def verify_current_run_exact(
    project_root: Path,
    *,
    report: ReportValue,
    expected_indication: str,
    expected_data_cutoff: datetime,
    expected_source_commit: str | None = None,
    expected_package_digest: str | None = None,
    expected_run_id: str | None = None,
    browser_report_path: Path | None = None,
    required_browsers: Sequence[str] = _REQUIRED_BROWSERS,
) -> RealSourceAcceptanceResult:
    """Verify one A/B/C project from current run through browser verdict.

    This is deliberately read-only.  It rejects missing/empty roots, fixture
    runs, resumed or reused state, stale manifests and files, broken local
    links, incomplete browser matrices, and self-asserted browser verdicts.
    """

    if report not in {"A", "B", "C"}:
        raise RealSourceAcceptanceError(f"不支持的报告类型：{report}")
    if not expected_indication.strip():
        raise RealSourceAcceptanceError("期望适应症不能为空")
    if expected_data_cutoff.tzinfo is None or expected_data_cutoff.utcoffset() is None:
        raise RealSourceAcceptanceError("期望数据截止时间必须包含明确时区")
    browsers = tuple(required_browsers)
    if browsers != _REQUIRED_BROWSERS:
        raise RealSourceAcceptanceError("Task 10.2 必须固定覆盖 Chromium 与 WebKit")

    root = project_root.expanduser().resolve()
    try:
        verification = verify_project_workspace(root)
    except (ProjectWorkspaceError, OSError, ValueError) as error:
        raise RealSourceAcceptanceError(f"项目根不是可验收的新鲜项目：{root}；{error}") from error
    contract = verification.contract
    if tuple(item.value for item in contract.reports) != (report,):
        raise RealSourceAcceptanceError("项目合同必须只选择当前报告类型")
    if tuple(item.value for item in contract.outputs) != ("html",):
        raise RealSourceAcceptanceError("项目合同必须只选择 HTML 首版范围")
    if " ".join(contract.indication.split()) != " ".join(expected_indication.split()):
        raise RealSourceAcceptanceError("项目合同适应症与当前真实来源项目不一致")
    if not _project_cutoff_matches(contract.data_cutoff, expected_data_cutoff):
        raise RealSourceAcceptanceError("项目合同数据截止时间与当前历史 cutoff 不一致")

    try:
        run_manifest = validate_run_manifest(root)
    except Exception as error:  # noqa: BLE001 - malformed state must fail closed
        if isinstance(error, RealSourceAcceptanceError):
            raise
        raise RealSourceAcceptanceError(f"当前运行清单无法校验：{error}") from error
    run_id = _required_text(run_manifest.get("run_id"), "当前运行标识")
    if expected_run_id is not None and run_id != expected_run_id:
        raise RealSourceAcceptanceError("当前运行标识与期望运行不一致")
    try:
        started_at, _finished_at, artifact_run_id = _assert_fresh_run(
            root,
            run_manifest,
            project_id=contract.project_id,
            run_id=run_id,
        )
    except RealSourceAcceptanceError:
        raise
    except Exception as error:  # noqa: BLE001 - malformed state must fail closed
        raise RealSourceAcceptanceError(f"当前运行状态无法闭合：{error}") from error

    source_commit = _parse_commit(
        expected_source_commit
        if expected_source_commit is not None
        else current_source_commit(),
        "期望源代码提交摘要",
    )
    package_digest = _parse_digest(
        expected_package_digest
        if expected_package_digest is not None
        else current_package_digest(),
        "期望安装包摘要",
    )
    try:
        manifest, manifest_path, manifest_digest = _load_artifact_manifest(
            root,
            run_manifest,
            report=report,
            project_id=contract.project_id,
            artifact_run_id=artifact_run_id,
            started_at=started_at,
        )
    except RealSourceAcceptanceError:
        raise
    except Exception as error:  # noqa: BLE001 - malformed state must fail closed
        raise RealSourceAcceptanceError(f"当前 HTML 清单无法闭合：{error}") from error
    if manifest.data_cutoff != expected_data_cutoff:
        raise RealSourceAcceptanceError("HTML 清单数据截止时间与当前历史 cutoff 不一致")
    if manifest.source_commit != source_commit:
        raise RealSourceAcceptanceError("HTML 清单未绑定当前源代码提交摘要")
    if manifest.package_digest != package_digest:
        raise RealSourceAcceptanceError("HTML 清单未绑定当前安装包摘要")
    if manifest.design_contract.digest != manifest.package_digest:
        raise RealSourceAcceptanceError("设计合同摘要与安装包摘要脱链")
    try:
        _verify_runtime_bindings(
            run_manifest,
            report=report,
            manifest=manifest,
            manifest_digest=manifest_digest,
        )
    except RealSourceAcceptanceError:
        raise
    except Exception as error:  # noqa: BLE001 - malformed state must fail closed
        raise RealSourceAcceptanceError(f"当前运行绑定无法闭合：{error}") from error
    try:
        _verify_artifact_directory(root, manifest=manifest, started_at=started_at)
    except RealSourceAcceptanceError:
        raise
    except Exception as error:  # noqa: BLE001 - malformed state must fail closed
        raise RealSourceAcceptanceError(f"HTML 产物目录无法闭合：{error}") from error

    try:
        routes, _site_root = _verify_static_site(
            root,
            report=report,
            manifest=manifest,
            started_at=started_at,
        )
    except RealSourceAcceptanceError:
        raise
    except Exception as error:  # noqa: BLE001 - malformed site must fail closed
        raise RealSourceAcceptanceError(f"锁定站点无法闭合：{error}") from error
    default_browser_report = (
        root / "verification" / report / manifest.report_version / "report.json"
    )
    browser_path = (browser_report_path or default_browser_report).expanduser().resolve()
    if not browser_path.is_relative_to(root):
        raise RealSourceAcceptanceError("浏览器验收结论必须保存在当前项目根内")
    if not browser_path.is_file():
        raise RealSourceAcceptanceError(f"缺少当前双浏览器验收结论：{browser_path}")
    try:
        browser_run_digest, viewports = _verify_browser_report(
            browser_path,
            report=report,
            manifest=manifest,
            run_id=run_id,
            started_at=started_at,
            routes=routes,
            required_browsers=browsers,
        )
    except RealSourceAcceptanceError:
        raise
    except Exception as error:  # noqa: BLE001 - malformed verdicts fail closed
        raise RealSourceAcceptanceError(f"浏览器验收结论无法闭合：{error}") from error
    return RealSourceAcceptanceResult(
        report=report,
        project_root=root,
        run_id=run_id,
        report_version=manifest.report_version,
        manifest_id=manifest.manifest_id,
        report_snapshot_id=manifest.report_snapshot_id,
        site_digest=manifest.artifact.sha256,
        browser_report_path=browser_path,
        browser_run_digest=browser_run_digest,
        routes=routes,
        browsers=browsers,
        viewports=viewports,
    )


__all__ = [
    "RealSourceAcceptanceError",
    "RealSourceAcceptanceResult",
    "current_package_digest",
    "current_source_commit",
    "verify_current_run_exact",
]
