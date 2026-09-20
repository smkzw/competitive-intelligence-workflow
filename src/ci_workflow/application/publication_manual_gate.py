"""Materialize the one publication-supply interruption for a research snapshot."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from ci_workflow.domain.enums import DownloadRequestState
from ci_workflow.domain.ids import stable_id
from ci_workflow.domain.research_package import ResearchPackage
from ci_workflow.gates.models import GateSpec
from ci_workflow.ingestion.manual_inbox import ManualInboxService
from ci_workflow.ingestion.publication_gate import (
    ManualFileValidationReceipt,
    ManualSupplyGate,
    ManualSupplyRequest,
    ManualSupplyResponse,
)


class PublicationManualGateError(ValueError):
    """The persisted snapshot gate is missing, drifted, or malformed."""


@dataclass(frozen=True)
class MaterializedManualGate:
    gate: ManualSupplyGate
    relative_path: str
    replayed: bool


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _gate_identity(gate: ManualSupplyGate) -> tuple[object, ...]:
    return gate.gate_id, gate.snapshot_id, gate.requests, gate.affected_reports


def _persist_gate(path: Path, gate: ManualSupplyGate) -> None:
    _atomic_write(
        path,
        (
            json.dumps(
                gate.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode(),
    )


def _publish_user_gate(project_root: Path, gate: ManualSupplyGate) -> None:
    markdown_path = project_root / "logs/manual-supply-request.md"
    markdown = (gate.to_markdown().rstrip() + "\n").encode()
    if not markdown_path.is_file() or markdown_path.read_bytes() != markdown:
        _atomic_write(markdown_path, markdown)
    _atomic_write(
        project_root / "logs/download_requests.md",
        (
            "# 下载请求内部状态\n\n"
            "Publication 补件请以 `manual-supply-request.md` 为唯一用户操作入口。\n"
        ).encode(),
    )


def _reconcile_received_files(
    path: Path, gate: ManualSupplyGate, inbox: ManualInboxService
) -> ManualSupplyGate:
    if gate.state != "awaiting_user":
        return gate
    children = []
    for item in gate.requests:
        child = inbox.load_request(item.request_id)
        inbox_path = inbox.project_root / child.inbox_directory
        has_new_file = inbox_path.is_dir() and any(
            candidate.is_file() and not candidate.name.startswith(".")
            for candidate in inbox_path.iterdir()
        )
        if child.state is DownloadRequestState.NEEDS_RE_DOWNLOAD and has_new_file:
            inbox.re_request(
                item.request_id,
                reason_zh="已检测到新的候选文件，继续在同一次补件门内核验。",
            )
        children.append(inbox.scan_and_process_inbox(item.request_id))
    child_tuple = tuple(children)
    if not child_tuple or any(
        child is None or child.state is not DownloadRequestState.ACCEPTED for child in child_tuple
    ):
        return gate
    accepted = tuple(child for child in child_tuple if child is not None)
    response = ManualSupplyResponse(
        response_id=stable_id("manual-supply-response", gate.gate_id, "file-received"),
        outcome="file_received",
        responded_at=datetime.now(UTC),
        original_filenames=tuple(child.original_filename or "" for child in accepted),
        validation_receipts=tuple(
            ManualFileValidationReceipt(
                request_id=child.request_id,
                content_sha256=child.content_sha256 or "",
                canonical_relative_path=child.canonical_relative_path or "",
                source_version_id=child.source_version_id or "",
            )
            for child in accepted
        ),
    )
    updated = gate.record_user_response(response, official_evidence_sufficient=False)
    _persist_gate(path, updated)
    return updated


def materialize_publication_manual_gate(
    project_root: Path,
    package: ResearchPackage,
    *,
    snapshot_id: str,
) -> MaterializedManualGate | None:
    """Create or replay one immutable-identity gate for required missing publications."""

    missing = tuple(
        record for record in package.publication_records if record.manual_supply_required
    )
    if not missing:
        return None
    gate_id = stable_id("manual-supply-gate", package.contract_identity.project_id, snapshot_id)
    inbox = ManualInboxService(project_root)
    requests: list[ManualSupplyRequest] = []
    for record in missing:
        report = next(
            (
                item
                for item in record.affected_reports
                if any(field.startswith(f"{item.lower()}_") for field in record.blocking_fields)
            ),
            record.affected_reports[0],
        )
        missing_fields = (
            tuple(
                field for field in record.blocking_fields if field.startswith(f"{report.lower()}_")
            )
            or record.blocking_fields
        )
        spec = GateSpec.from_yaml(
            Path(__file__).resolve().parents[3] / "policies/gates" / f"{report}-v1.yaml"
        )
        child = inbox.create_request(
            project_id=package.contract_identity.project_id,
            run_id=gate_id,
            report_kind=report,
            spec=spec,
            blocking_priority="blocking",
            product_id=record.product_id,
            trial_id=record.linked_trial_ids[0],
            registry_identifiers=record.registry_identifiers,
            doi=record.doi,
            pmid=record.pmid,
            document_role="publication_pdf",
            title=record.title,
            publisher=urlsplit(record.source_url).netloc,
            landing_page_url=record.source_url,
            attachment_url=record.source_url,
            missing_fields=missing_fields,
            reason_zh="关键公开论文尚未取得，受影响报告需要原文核验。",
            gap_still_open=True,
            expected_to_close_units=missing_fields,
        )
        requests.append(
            ManualSupplyRequest(
                request_id=child.request_id,
                product_id=record.product_id,
                trial_id=record.linked_trial_ids[0],
                registry_identifiers=record.registry_identifiers,
                doi=record.doi,
                pmid=record.pmid,
                exact_title=record.title,
                blocking_fields=record.blocking_fields,
                attempted_paths=tuple(item.strategy_id for item in record.fetch_attempts),
                source_links=(record.source_url,),
                delivery_directory=child.inbox_directory,
                minimum_user_action="请下载原始全文并保留发布者文件名后放入上述目录",
                affected_reports=record.affected_reports,
            )
        )
    affected_reports = tuple(
        report
        for report in package.reports
        if any(report in request.affected_reports for request in requests)
    )
    gate = ManualSupplyGate(
        gate_id=gate_id,
        snapshot_id=snapshot_id,
        requests=tuple(requests),
        affected_reports=affected_reports,
    )
    relative_path = f"state/manual-supply-gates/{snapshot_id}.json"
    path = project_root / relative_path
    replayed = path.exists()
    if replayed:
        try:
            persisted = ManualSupplyGate.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as error:
            raise PublicationManualGateError("已保存的 publication 补件门不可验证") from error
        if _gate_identity(persisted) != _gate_identity(gate):
            raise PublicationManualGateError("同一研究快照的 publication 补件门身份已漂移")
        gate = _reconcile_received_files(path, persisted, inbox)
    else:
        _persist_gate(path, gate)
    _publish_user_gate(project_root, gate)
    return MaterializedManualGate(gate=gate, relative_path=relative_path, replayed=replayed)


def mark_publication_files_unavailable(
    project_root: Path,
    *,
    snapshot_id: str,
    official_evidence_sufficient: bool,
    limitation_zh: str | None = None,
) -> ManualSupplyGate:
    """Record the sole unavailable response for a known snapshot gate."""

    path = project_root / f"state/manual-supply-gates/{snapshot_id}.json"
    try:
        gate = ManualSupplyGate.model_validate_json(path.read_bytes())
    except (OSError, ValueError) as error:
        raise PublicationManualGateError("找不到可响应的 publication 补件门") from error
    response = ManualSupplyResponse(
        response_id=stable_id("manual-supply-response", gate.gate_id, "file-unavailable"),
        outcome="file_unavailable",
        responded_at=datetime.now(UTC),
    )
    try:
        updated = gate.record_user_response(
            response,
            official_evidence_sufficient=official_evidence_sufficient,
            limitation_zh=limitation_zh,
        )
    except ValueError as error:
        raise PublicationManualGateError(str(error)) from error
    _persist_gate(path, updated)
    _publish_user_gate(project_root, updated)
    return updated


__all__ = [
    "MaterializedManualGate",
    "PublicationManualGateError",
    "mark_publication_files_unavailable",
    "materialize_publication_manual_gate",
]
