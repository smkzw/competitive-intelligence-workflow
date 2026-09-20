"""PPTX 来源包与一次性确认的项目运行适配器。

该模块只准备 PPT Master 的输入，不调用 PPT Master、不创建 PPTX 或逐页
SVG。它把报告 HTML 清单已经锁定的快照/覆盖身份转成来源包，并在项目内
持久化一次性中文确认入口。确认结果存在后，恢复运行只读取并关闭原会话，
不会重新生成推荐或再次询问。
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from pydantic import BaseModel

from ci_workflow.domain.ids import stable_id
from ci_workflow.renderers.pptx_master.confirmation import (
    ConfirmationRecommendations,
    ConfirmationResult,
    ConfirmationSession,
    ConfirmationSessionStore,
    PptxConfirmationError,
    build_recommendations,
    load_confirmation_result,
    load_confirmation_session,
    load_recommendations,
    open_confirmation_session,
    validate_confirmation_result,
    write_confirmation_session,
    write_recommendations,
)
from ci_workflow.renderers.pptx_master.source_pack import (
    SourcePack,
    SourcePackBuildError,
    SourcePackSummary,
    build_source_pack,
    load_design_contract,
    load_page_strategy,
    load_source_pack_summary,
    validate_source_pack_summary,
    write_source_pack,
)
from ci_workflow.storage.manifest_store import ArtifactManifest
from ci_workflow.storage.snapshot_store import compute_locked_snapshot

ReportKey = Literal["A", "B", "C"]
ConfirmationState = Literal["awaiting_confirmation", "confirmed"]

_SOURCE_PACK_ROOT = PurePosixPath("state", "pptx", "source-packs")
_CONFIRM_UI_ROOT = PurePosixPath("confirm_ui")
_INDEX_RELATIVE_PATH = _CONFIRM_UI_ROOT / "index.json"
_REPORT_ORDER = {"A": 0, "B": 1, "C": 2}


@dataclass(frozen=True)
class PptxReportInput:
    """一个报告的锁定数据、快照和规范覆盖集合输入。"""

    report: ReportKey | str
    report_data: Mapping[str, Any] | BaseModel
    snapshot: Mapping[str, Any] | BaseModel
    coverage_set: Mapping[str, Any] | BaseModel


@dataclass(frozen=True)
class PptxConfirmationEntry:
    """项目确认入口中的一个报告条目。"""

    report: ReportKey
    state: ConfirmationState
    source_pack_path: str
    summary_path: str
    recommendations_path: str
    result_path: str
    session_path: str
    source_pack_id: str
    snapshot_id: str
    snapshot_sha256: str
    coverage_set_id: str
    recommendations_sha256: str
    result_sha256: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "report": self.report,
            "state": self.state,
            "source_pack_path": self.source_pack_path,
            "summary_path": self.summary_path,
            "recommendations_path": self.recommendations_path,
            "result_path": self.result_path,
            "session_path": self.session_path,
            "source_pack_id": self.source_pack_id,
            "snapshot_id": self.snapshot_id,
            "snapshot_sha256": self.snapshot_sha256,
            "coverage_set_id": self.coverage_set_id,
            "recommendations_sha256": self.recommendations_sha256,
            "result_sha256": self.result_sha256,
        }


@dataclass(frozen=True)
class PptxConfirmationBatch:
    """一次项目运行为全部选定 PPTX 报告准备的确认状态。"""

    project_id: str
    snapshot_id: str
    snapshot_sha256: str
    index_path: str
    entries: tuple[PptxConfirmationEntry, ...]

    @property
    def all_confirmed(self) -> bool:
        return bool(self.entries) and all(item.state == "confirmed" for item in self.entries)

    @property
    def state(self) -> ConfirmationState:
        return "confirmed" if self.all_confirmed else "awaiting_confirmation"

    @property
    def awaiting_reports(self) -> tuple[ReportKey, ...]:
        return tuple(item.report for item in self.entries if item.state != "confirmed")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "contract_version": "8.7",
            "project_id": self.project_id,
            "snapshot_id": self.snapshot_id,
            "snapshot_sha256": self.snapshot_sha256,
            "index_path": self.index_path,
            "state": self.state,
            "all_confirmed": self.all_confirmed,
            "awaiting_reports": list(self.awaiting_reports),
            "entries": [item.as_dict() for item in self.entries],
            "no_svg": True,
            "pptx_generated": False,
        }


@dataclass(frozen=True)
class _PreparedInput:
    report: ReportKey
    source_pack: SourcePack
    source_pack_path: str
    summary_path: str
    recommendations_path: str
    result_path: str
    session_path: str


class PptxConfirmationAdapter:
    """在项目运行中准备来源包和确认状态，不产生 PPTX 副作用。"""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).expanduser().resolve()

    def prepare(
        self,
        report_inputs: Sequence[PptxReportInput],
        *,
        now: datetime | None = None,
        allow_report_scoped_snapshots: bool = False,
    ) -> PptxConfirmationBatch:
        """准备并持久化全部报告输入，返回等待或已确认状态。

        默认要求批次内使用同一个锁定快照；项目运行整合 A/B/C 时可显式允许
        每个报告使用其自身的报告快照，批次顶层身份随后绑定全部报告身份。
        """
        normalized = self._normalize_inputs(report_inputs)
        if now is None:
            now = datetime.now(UTC)
        if now.tzinfo is None or now.utcoffset() is None:
            raise PptxConfirmationError("确认适配器时间必须包含明确时区", "TIME_INVALID")

        try:
            prepared = self._build_inputs(normalized)
        except SourcePackBuildError as exc:
            raise PptxConfirmationError(
                f"PPTX 来源包输入无法准备：{exc}", "SOURCE_PACK_INVALID"
            ) from exc
        snapshot_id, snapshot_sha256 = self._assert_shared_snapshot(
            prepared,
            allow_report_scoped_snapshots=allow_report_scoped_snapshots,
        )
        entries = tuple(self._persist_one(item, now=now) for item in prepared)
        batch = PptxConfirmationBatch(
            project_id=prepared[0].source_pack.summary.project_id,
            snapshot_id=snapshot_id,
            snapshot_sha256=snapshot_sha256,
            index_path=_INDEX_RELATIVE_PATH.as_posix(),
            entries=entries,
        )
        self._write_index(batch)
        return batch

    def prepare_from_mappings(
        self,
        report_inputs: Mapping[str, Mapping[str, Any]],
        *,
        now: datetime | None = None,
        allow_report_scoped_snapshots: bool = False,
    ) -> PptxConfirmationBatch:
        """便于运行服务把 ``{report: {report_data, snapshot, coverage_set}}`` 交接进来。"""

        values: list[PptxReportInput] = []
        for report, payload in report_inputs.items():
            try:
                values.append(
                    PptxReportInput(
                        report=cast(ReportKey, report),
                        report_data=payload["report_data"],
                        snapshot=payload["snapshot"],
                        coverage_set=payload["coverage_set"],
                    )
                )
            except KeyError as exc:
                raise PptxConfirmationError(
                    f"报告 {report} 的 PPTX 输入缺少 {exc.args[0]}", "INPUT_MISSING"
                ) from exc
        return self.prepare(
            values,
            now=now,
            allow_report_scoped_snapshots=allow_report_scoped_snapshots,
        )

    def _normalize_inputs(self, values: Sequence[PptxReportInput]) -> tuple[PptxReportInput, ...]:
        if not values:
            raise PptxConfirmationError("PPTX 确认至少需要一个报告输入", "INPUT_MISSING")
        by_report: dict[ReportKey, PptxReportInput] = {}
        for value in values:
            report = self._report_key(value.report)
            if report in by_report:
                raise PptxConfirmationError(f"报告 {report} 的 PPTX 输入重复", "INPUT_DUPLICATE")
            by_report[report] = PptxReportInput(
                report=report,
                report_data=value.report_data,
                snapshot=value.snapshot,
                coverage_set=value.coverage_set,
            )
        return tuple(by_report[key] for key in sorted(by_report, key=_REPORT_ORDER.__getitem__))

    @staticmethod
    def _report_key(value: ReportKey | str) -> ReportKey:
        normalized = str(getattr(value, "value", value))
        if normalized not in _REPORT_ORDER:
            raise PptxConfirmationError(f"非法 PPTX 报告类型：{normalized}", "REPORT_INVALID")
        return cast(ReportKey, normalized)

    def _build_inputs(self, values: Sequence[PptxReportInput]) -> tuple[_PreparedInput, ...]:
        result: list[_PreparedInput] = []
        multi = len(values) > 1
        for value in values:
            report = self._report_key(value.report)
            source_data = _mapping(value.report_data, "锁定报告数据")
            if "report_version" not in source_data:
                raise PptxConfirmationError(
                    "锁定报告数据缺少 report_version", "INPUT_MISSING"
                )
            prefix = _SOURCE_PACK_ROOT / report
            source_rel = (prefix / "source-pack.md").as_posix()
            summary_rel = (prefix / "source-pack.summary.json").as_posix()
            confirm_prefix = _CONFIRM_UI_ROOT / report if multi else _CONFIRM_UI_ROOT
            prepared_pack = build_source_pack(
                report,
                source_data,
                value.snapshot,
                value.coverage_set,
                load_page_strategy(report),
                load_design_contract(),
                source_pack_path=source_rel,
                summary_path=summary_rel,
            )
            result.append(
                _PreparedInput(
                    report=report,
                    source_pack=prepared_pack,
                    source_pack_path=source_rel,
                    summary_path=summary_rel,
                    recommendations_path=(confirm_prefix / "recommendations.json").as_posix(),
                    result_path=(confirm_prefix / "result.json").as_posix(),
                    session_path=(confirm_prefix / "session.json").as_posix(),
                )
            )
        return tuple(result)
        
    @staticmethod
    def _assert_shared_snapshot(
        values: Sequence[_PreparedInput],
        *,
        allow_report_scoped_snapshots: bool = False,
    ) -> tuple[str, str]:
        project_ids = {item.source_pack.summary.project_id for item in values}
        if len(project_ids) != 1:
            raise PptxConfirmationError(
                "A/B/C PPTX 来源包必须绑定同一项目和锁定报告快照", "SNAPSHOT_MISMATCH"
            )
        identities = {
            (
                item.source_pack.summary.report,
                item.source_pack.summary.snapshot_id,
                item.source_pack.summary.snapshot_sha256,
            )
            for item in values
        }
        if (
            len(
                {
                    (snapshot_id, snapshot_sha256)
                    for _, snapshot_id, snapshot_sha256 in identities
                }
            )
            == 1
        ):
            snapshot_id, snapshot_sha256 = next(
                (snapshot_id, snapshot_sha256)
                for _, snapshot_id, snapshot_sha256 in identities
            )
            return snapshot_id, snapshot_sha256
        if not allow_report_scoped_snapshots:
            raise PptxConfirmationError(
                "A/B/C PPTX 来源包必须绑定同一项目和锁定报告快照", "SNAPSHOT_MISMATCH"
            )
        ordered = sorted(identities, key=lambda item: _REPORT_ORDER[item[0]])
        aggregate = [
            {
                "report": report,
                "snapshot_id": snapshot_id,
                "snapshot_sha256": snapshot_sha256,
            }
            for report, snapshot_id, snapshot_sha256 in ordered
        ]
        return (
            stable_id(
                "pptx-confirmation-snapshot-batch",
                *[
                    f"{item['report']}:{item['snapshot_id']}:{item['snapshot_sha256']}"
                    for item in aggregate
                ],
            ),
            _sha256(aggregate),
        )

    def _persist_one(self, item: _PreparedInput, *, now: datetime) -> PptxConfirmationEntry:
        source_path = self._resolve_relative(item.source_pack_path)
        summary_path = self._resolve_relative(item.summary_path)
        self._persist_source_pack(item.source_pack, source_path, summary_path)
        pack_summary = item.source_pack.summary

        recommendation_path = self._resolve_relative(item.recommendations_path)
        result_path = self._resolve_relative(item.result_path)
        session_path = self._resolve_relative(item.session_path)
        recommendations = self._load_or_create_recommendations(
            pack_summary,
            recommendation_path,
            item.recommendations_path,
            now=now,
        )
        session = self._load_or_create_session(
            recommendations,
            session_path,
            item.session_path,
            item.result_path,
        )
        result: ConfirmationResult | None = None
        if result_path.exists():
            try:
                result = load_confirmation_result(result_path)
                result = validate_confirmation_result(result, recommendations)
            except PptxConfirmationError:
                raise
            except (OSError, ValueError) as exc:
                raise PptxConfirmationError(
                    f"确认结果无法读取：{result_path}", "RESULT_INVALID"
                ) from exc
            if session.state == "open":
                session = ConfirmationSessionStore(session_path).close(
                    recommendations,
                    result,
                    closed_at=result.confirmed_at,
                )
            elif session.result_sha256 != result.result_sha256:
                raise PptxConfirmationError(
                    "已关闭确认会话与结果摘要不一致", "SESSION_RESULT_MISMATCH"
                )
        elif session.state == "closed":
            raise PptxConfirmationError(
                f"已关闭确认会话缺少结果：{result_path}", "RESULT_MISSING"
            )

        state: ConfirmationState = (
            "confirmed"
            if session.state == "closed" and result is not None
            else "awaiting_confirmation"
        )
        return PptxConfirmationEntry(
            report=item.report,
            state=state,
            source_pack_path=item.source_pack_path,
            summary_path=item.summary_path,
            recommendations_path=item.recommendations_path,
            result_path=item.result_path,
            session_path=item.session_path,
            source_pack_id=pack_summary.source_pack_id,
            snapshot_id=pack_summary.snapshot_id,
            snapshot_sha256=pack_summary.snapshot_sha256,
            coverage_set_id=pack_summary.coverage_set_id,
            recommendations_sha256=recommendations.recommendations_sha256,
            result_sha256=result.result_sha256 if result is not None else None,
        )

    def _persist_source_pack(self, pack: SourcePack, source_path: Path, summary_path: Path) -> None:
        source_exists = source_path.exists()
        summary_exists = summary_path.exists()
        if source_exists != summary_exists:
            raise PptxConfirmationError(
                "来源包与摘要清单必须成对存在", "SOURCE_PACK_INCOMPLETE"
            )
        if not source_exists:
            try:
                write_source_pack(pack, self.project_root)
            except SourcePackBuildError as exc:
                raise PptxConfirmationError(str(exc), "SOURCE_PACK_WRITE_FAILED") from exc
            return
        try:
            existing = load_source_pack_summary(summary_path)
            validate_source_pack_summary(existing, markdown=source_path)
        except (OSError, SourcePackBuildError, ValueError) as exc:
            raise PptxConfirmationError(
                f"既有 PPTX 来源包无法验证：{source_path}", "SOURCE_PACK_INVALID"
            ) from exc
        if existing.model_dump(mode="json") != pack.summary.model_dump(mode="json"):
            raise PptxConfirmationError(
                f"既有 PPTX 来源包与当前锁定快照不一致：{source_path}", "SOURCE_PACK_DRIFT"
            )

    def _load_or_create_recommendations(
        self,
        summary: SourcePackSummary,
        path: Path,
        relative_path: str,
        *,
        now: datetime,
    ) -> ConfirmationRecommendations:
        if path.exists():
            try:
                recommendations = load_recommendations(path)
            except PptxConfirmationError:
                raise
            except (OSError, ValueError) as exc:
                raise PptxConfirmationError(
                    f"推荐清单无法读取：{path}", "RECOMMENDATIONS_INVALID"
                ) from exc
            self._assert_recommendation_binding(recommendations, summary, relative_path)
            return recommendations
        recommendations = build_recommendations(
            summary,
            generated_at=now,
            recommendations_path=relative_path,
        )
        try:
            write_recommendations(recommendations, path)
        except (OSError, ValueError) as exc:
            raise PptxConfirmationError(
                f"推荐清单写入失败：{path}", "RECOMMENDATIONS_WRITE_FAILED"
            ) from exc
        return recommendations

    @staticmethod
    def _assert_recommendation_binding(
        recommendations: ConfirmationRecommendations,
        summary: SourcePackSummary,
        relative_path: str,
    ) -> None:
        expected = {
            "project_id": summary.project_id,
            "report": summary.report,
            "report_version": summary.report_version,
            "source_pack_id": summary.source_pack_id,
            "source_pack_sha256": summary.source_pack_sha256,
            "snapshot_id": summary.snapshot_id,
            "snapshot_sha256": summary.snapshot_sha256,
            "claim_snapshot_id": summary.claim_snapshot_id,
            "evidence_snapshot_id": summary.evidence_snapshot_id,
            "coverage_set_id": summary.coverage_set_id,
        }
        actual = {
            key: getattr(recommendations, key)
            for key in expected
        }
        if actual != expected or recommendations.recommendations_path != relative_path:
            raise PptxConfirmationError(
                "推荐清单与当前来源包/锁定快照不一致", "RECOMMENDATIONS_DRIFT"
            )

    def _load_or_create_session(
        self,
        recommendations: ConfirmationRecommendations,
        path: Path,
        relative_path: str,
        result_relative_path: str,
    ) -> ConfirmationSession:
        if path.exists():
            try:
                session = load_confirmation_session(path)
            except PptxConfirmationError:
                raise
            except (OSError, ValueError) as exc:
                raise PptxConfirmationError(
                    f"确认会话无法读取：{path}", "SESSION_INVALID"
                ) from exc
            if (
                session.session_id != recommendations.session_id
                or session.recommendations_sha256 != recommendations.recommendations_sha256
                or session.binding != recommendations.binding
                or session.recommendations_path != relative_path
                or session.result_path != result_relative_path
            ):
                raise PptxConfirmationError(
                    "持久化确认会话与当前推荐清单不一致", "SESSION_MISMATCH"
                )
            return session
        session = open_confirmation_session(
            recommendations,
            opened_at=recommendations.generated_at,
            recommendations_path=relative_path,
            result_path=result_relative_path,
        )
        try:
            write_confirmation_session(session, path)
        except (OSError, ValueError) as exc:
            raise PptxConfirmationError(
                f"确认会话写入失败：{path}", "SESSION_WRITE_FAILED"
            ) from exc
        return session

    def _write_index(self, batch: PptxConfirmationBatch) -> None:
        base: dict[str, Any] = {
            "schema_version": "1.0",
            "contract_version": "8.7",
            "project_id": batch.project_id,
            "snapshot_id": batch.snapshot_id,
            "snapshot_sha256": batch.snapshot_sha256,
            "state": batch.state,
            "all_confirmed": batch.all_confirmed,
            "entries": [item.as_dict() for item in batch.entries],
            "no_svg": True,
            "pptx_generated": False,
        }
        base["index_sha256"] = _sha256(base)
        path = self._resolve_relative(_INDEX_RELATIVE_PATH.as_posix())
        _atomic_write_json(path, base)

    def _resolve_relative(self, relative: str) -> Path:
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or any(part in {"", ".", ".."} for part in pure.parts)
            or "\\" in relative
        ):
            raise PptxConfirmationError(f"项目相对路径非法：{relative}", "PATH_INVALID")
        path = (self.project_root / Path(*pure.parts)).resolve()
        if not path.is_relative_to(self.project_root):
            raise PptxConfirmationError(f"项目相对路径越界：{relative}", "PATH_INVALID")
        return path


# ─── Report manifest adapter ────────────────────────────────────────────────


def pptx_report_input_from_manifest(
    project_root: Path,
    *,
    report_data: Mapping[str, Any] | BaseModel,
    manifest_path: Path,
) -> PptxReportInput:
    """从已生成 HTML 清单和报告快照构造 PPTX 输入。

    HTML/PDF/PPTX 共享这里读取出的报告快照和覆盖集合身份；若 HTML 清单
    或快照文件已经漂移，适配器在写入来源包前失败关闭。
    """

    root = Path(project_root).expanduser().resolve()
    manifest_file = Path(manifest_path)
    if not manifest_file.is_absolute():
        manifest_file = root / manifest_file
    try:
        manifest = ArtifactManifest.model_validate_json(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PptxConfirmationError(
            f"HTML 产物清单无法读取：{manifest_file}", "MANIFEST_INVALID"
        ) from exc
    data = _mapping(report_data, "锁定报告数据")
    report = manifest.report
    if str(data.get("report_version")) != manifest.report_version:
        raise PptxConfirmationError("报告数据与 HTML 清单版本不一致", "REPORT_MISMATCH")
    snapshot_file = root / "snapshots" / "reports" / report / f"{manifest.report_snapshot_id}.json"
    try:
        snapshot_payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PptxConfirmationError(
            f"报告锁定快照无法读取：{snapshot_file}", "SNAPSHOT_INVALID"
        ) from exc
    if not isinstance(snapshot_payload, dict):
        raise PptxConfirmationError("报告锁定快照顶层必须是对象", "SNAPSHOT_INVALID")
    try:
        locked = compute_locked_snapshot(kind="report", report=report, manifest=snapshot_payload)
    except (TypeError, ValueError) as exc:
        raise PptxConfirmationError("报告锁定快照不符合合同", "SNAPSHOT_INVALID") from exc
    if (
        locked.snapshot_id != manifest.report_snapshot_id
        or locked.sha256 != _sha256_bytes(snapshot_file.read_bytes())
    ):
        raise PptxConfirmationError("报告锁定快照身份或摘要与 HTML 清单不一致", "SNAPSHOT_MISMATCH")
    if locked.snapshot_id != manifest.report_snapshot_id:
        raise PptxConfirmationError("报告锁定快照标识与 HTML 清单不一致", "SNAPSHOT_MISMATCH")
    snapshot = {
        "project_id": manifest.project_id,
        "report": report,
        "report_version": manifest.report_version,
        "snapshot_id": locked.snapshot_id,
        "snapshot_sha256": locked.sha256,
        "claim_snapshot_id": manifest.claim_snapshot_id,
        "evidence_snapshot_id": manifest.evidence_snapshot_id,
        "coverage_set_id": manifest.coverage_set_id,
        "locked_at": str(snapshot_payload.get("created_at", manifest.generated_at.isoformat())),
    }
    coverage = _coverage_payload_from_manifest(manifest, data)
    return PptxReportInput(
        report=report,
        report_data=data,
        snapshot=snapshot,
        coverage_set=coverage,
    )


def _coverage_payload_from_manifest(
    manifest: ArtifactManifest,
    report_data: Mapping[str, Any],
) -> dict[str, Any]:
    """从同一 HTML 清单的责任集合构造 PPTX 覆盖摘要输入。

    覆盖集合 ID 直接继承 HTML/PDF 的清单，不另造报告范围；项目中没有
    将完整 CoverageSet 落盘时，清单中已有的页、产品、试验、声明、图和表
    身份被保守地展开为可追溯条目。
    """

    report = manifest.report
    pages = tuple(manifest.pages_or_sections)
    fallback_page = pages[0]
    items: list[dict[str, Any]] = []

    def add(kind: str, identity: str, page: str, label: str) -> None:
        items.append(
            {
                "item_id": stable_id("pptx-coverage-item", report, kind, page, identity),
                "kind": kind,
                "page_responsibility_id": page,
                "referenced_ids": [identity],
                "label_zh": label,
            }
        )

    for page in pages:
        add("page", page, page, page)
    for product_id in manifest.product_ids:
        add(
            "product",
            product_id,
            "product-overview" if "product-overview" in pages else fallback_page,
            product_id,
        )
    for trial_id in manifest.trial_ids:
        add(
            "trial",
            trial_id,
            "product-trial-profiles" if "product-trial-profiles" in pages else fallback_page,
            trial_id,
        )
    for claim_id in manifest.claim_ids:
        add("claim", claim_id, "overview" if "overview" in pages else fallback_page, claim_id)
    for chart_id in manifest.chart_ids:
        add("chart", chart_id, fallback_page, chart_id)
    for table_id in manifest.table_ids:
        add("table", table_id, fallback_page, table_id)
    for evidence_id in manifest.evidence_reference_ids:
        add("evidence", evidence_id, fallback_page, evidence_id)
    if not items:
        # ArtifactManifest already requires one page, this is a defensive guard
        # for future alternate manifest implementations.
        add("page", fallback_page, fallback_page, fallback_page)
    return {
        "schema_version": "1.0",
        "coverage_set_id": manifest.coverage_set_id,
        "project_id": manifest.project_id,
        "contract_version": manifest.contract_version,
        "report": report,
        "report_version": manifest.report_version,
        "data_cutoff": manifest.data_cutoff.isoformat(),
        "evidence_snapshot_id": manifest.evidence_snapshot_id,
        "claim_snapshot_id": manifest.claim_snapshot_id,
        "items": items,
        "created_at": manifest.generated_at.isoformat(),
        "report_data_keys": sorted(str(key) for key in report_data),
    }


def _mapping(value: Mapping[str, Any] | BaseModel, field: str) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        raw = value.model_dump(mode="json")
    elif isinstance(value, Mapping):
        try:
            raw = json.loads(json.dumps(dict(value), ensure_ascii=False, allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise PptxConfirmationError(f"{field} 不是可规范化 JSON", "INPUT_INVALID") from exc
    else:
        raise PptxConfirmationError(f"{field} 必须是对象", "INPUT_INVALID")
    if not isinstance(raw, dict):
        raise PptxConfirmationError(f"{field} 顶层必须是对象", "INPUT_INVALID")
    return raw


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PptxConfirmationError("确认入口不是有限 JSON", "SERIALIZATION_ERROR") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value))


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical_json(payload))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise PptxConfirmationError(f"确认入口写入失败：{path}", "INDEX_WRITE_FAILED") from exc
    finally:
        temporary.unlink(missing_ok=True)


def prepare_pptx_confirmation(
    project_root: Path,
    report_inputs: Sequence[PptxReportInput] | Mapping[str, Mapping[str, Any]],
    *,
    now: datetime | None = None,
) -> PptxConfirmationBatch:
    """函数式适配入口；支持结构化输入序列或报告映射。"""

    adapter = PptxConfirmationAdapter(project_root)
    if isinstance(report_inputs, Mapping):
        return adapter.prepare_from_mappings(report_inputs, now=now)
    return adapter.prepare(report_inputs, now=now)


ensure_pptx_confirmation = prepare_pptx_confirmation


__all__ = [
    "PptxConfirmationAdapter",
    "PptxConfirmationBatch",
    "PptxConfirmationEntry",
    "PptxReportInput",
    "ensure_pptx_confirmation",
    "prepare_pptx_confirmation",
    "pptx_report_input_from_manifest",
]
