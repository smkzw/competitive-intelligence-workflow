"""Validate and atomically bind host research to a product project.

The host Agent performs research.  This boundary accepts one strict v1.3 audit
envelope plus one report-specific scientific payload per selected report.  A
manifest is written last; the product runner trusts neither loose files nor a
partially completed submission.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast
from zoneinfo import ZoneInfo

from ci_workflow.application.autonomous_research import load_default_source_policy
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.domain.research_package import ResearchPackage, validate_research_package
from ci_workflow.gates.models import GateBlockingLevel, GateSpec
from ci_workflow.ingestion.publication_gate import ManualSupplyGate

ReportName = Literal["A", "B", "C"]

AUDIT_PACKAGE_PATH = "evidence/library/research-package.json"
SUBMISSION_MANIFEST_PATH = "manifests/research-package-submission.json"
REPORT_PACKAGE_PATHS: dict[ReportName, str] = {
    "A": "evidence/library/a-research-package.json",
    "B": "evidence/library/b-research-package.json",
    "C": "evidence/library/c-research-package.json",
}


class ResearchPackageSubmissionError(ValueError):
    """A host package cannot be admitted to the deterministic runner."""


# Capture aliases used by the A fixture and B/C package builders. These are
# document kinds, NOT source-policy family IDs or source instance IDs.
# There is no review_publication role in v1.3. A review is not automatically a
# *specified* secondary source, so those aliases remain explicitly unresolved.
_CAPTURE_SOURCE_CLASSIFICATIONS: dict[str, tuple[str, str, str]] = {
    "clinical_trial_registry": ("registry", "official_registry", "not_applicable"),
    "primary_trial_report": ("publication", "primary_publication", "primary_result"),
    "peer_reviewed_primary_report": ("publication", "primary_publication", "primary_result"),
    "peer_reviewed_primary_report_recovered": (
        "publication",
        "primary_publication",
        "primary_result",
    ),
    "company_official_disclosure": ("company", "company_disclosure", "not_applicable"),
    "company_official_result_disclosure": ("company", "company_disclosure", "not_applicable"),
    "company_regulatory_disclosure": ("company", "company_disclosure", "not_applicable"),
    "conference_result_official_disclosure": ("conference", "conference", "not_applicable"),
    "official_conference_primary_result": ("conference", "conference", "not_applicable"),
    "regulatory_label_or_approval": ("regulatory", "regulatory", "not_applicable"),
    "regulatory_review": ("regulatory", "regulatory", "not_applicable"),
}

_UNRESOLVED_CAPTURE_TYPES = frozenset(
    {
        "peer_reviewed_publication",  # Publication subtype and role are not declared.
        "peer_reviewed_regulatory_milestone_review",  # Review classification, no defined role.
        "peer_reviewed_evidence_review",  # Do not invent a specified_secondary designation.
    }
)


def _capture_source_classification(source_type: str) -> tuple[str, str, str]:
    """Fail closed when the capture does not declare an unambiguous document kind.

    In particular peer_reviewed_publication (used by the real A fixture) does
    not say primary, extension, safety, or review. Never infer this from a title,
    source-ID prefix, or the unbound envelope. Its migration needs reviewed data.
    """

    if source_type in _UNRESOLVED_CAPTURE_TYPES:
        raise ResearchPackageSubmissionError(
            "来源绑定：载荷来源类型未明确角色及论文分类，需要复核迁移"
        )
    try:
        return _CAPTURE_SOURCE_CLASSIFICATIONS[source_type]
    except KeyError:
        raise ResearchPackageSubmissionError("来源绑定：载荷来源类型未明确角色及论文分类") from None


def _assert_source_bindings(
    package: ResearchPackage, payload: Any, *, timezone: str = "UTC",
    project_root: Path | None = None,
) -> None:
    envelope = {source.source_id: source for source in package.sources}
    seen: set[str] = set()
    for capture in payload.sources:
        if capture.source_id in seen:
            raise ResearchPackageSubmissionError("来源绑定：科学载荷来源实例标识重复")
        seen.add(capture.source_id)
        source = envelope.get(capture.source_id)
        if source is None:
            raise ResearchPackageSubmissionError("来源绑定：科学载荷含审计包外来源")
        if source.locator_detail is None or source.locator_detail != capture.locator:
            raise ResearchPackageSubmissionError("来源绑定：完整结构化定位缺失或不一致")
        if source.text_derivation != capture.text_derivation:
            raise ResearchPackageSubmissionError("来源绑定：原始资产派生回执不一致")
        if capture.text_derivation is not None:
            from ci_workflow.storage.source_derivation import (
                SourceDerivationError,
                verify_source_text_derivation,
            )

            if project_root is None:
                raise ResearchPackageSubmissionError("来源绑定：缺少原始资产核验工作区")
            try:
                verify_source_text_derivation(
                    project_root, capture.text_derivation, capture.content_text
                )
            except SourceDerivationError as error:
                raise ResearchPackageSubmissionError(f"来源绑定：{error}") from error
        expected = {
            "url": capture.url,
            # ResearchSource collapses whitespace; SourceCapture only strips it.
            "title": " ".join(capture.title.split()),
            "retrieved_at": capture.acquired_at,
            "access_state": "available",
        }
        for field in ("published_at", "effective_at"):
            timestamp = getattr(capture, field)
            expected[field] = (
                (timestamp.date() if capture.date_evidence(field).precision == "calendar_day"
                 else timestamp.astimezone(ZoneInfo(timezone)).date())
                if timestamp is not None else None
            )
        for field, value in expected.items():
            if getattr(source, field) != value:
                raise ResearchPackageSubmissionError(f"来源绑定：{field} 不一致")
        # This hashes exactly the validated text bytes consumed by A/B/C
        # ingestion. It is NOT the payload JSON hash or an original PDF/file
        # hash. Do not rewrite a mismatching original-file receipt into a text
        # receipt; a separate versioned raw-to-text derivation is still needed.
        if source.content_sha256 != _sha256(capture.content_text.encode("utf-8")):
            raise ResearchPackageSubmissionError("来源绑定：规范入库文本摘要不一致")
        if (source.source_type, source.source_role, source.publication_classification) != (
            _capture_source_classification(capture.source_type)
        ):
            raise ResearchPackageSubmissionError("来源绑定：来源类型、角色或论文分类不一致")


@dataclass(frozen=True)
class ProductResearchSubmission:
    package: ResearchPackage
    audit_package_path: Path
    report_package_paths: Mapping[ReportName, Path]
    manifest_path: Path
    replayed: bool
    authorization_state: Literal["candidate_unreviewed"] = "candidate_unreviewed"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json(value: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ResearchPackageSubmissionError(f"{label}必须是 UTF-8 JSON 对象") from error
    if not isinstance(payload, dict):
        raise ResearchPackageSubmissionError(f"{label}顶层必须是对象")
    return cast(dict[str, Any], payload)


def _read_file(path: Path, *, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ResearchPackageSubmissionError(f"{label}必须是普通文件")
    try:
        return path.read_bytes()
    except OSError as error:
        raise ResearchPackageSubmissionError(f"无法读取{label}") from error


def _validate_report_payload(report: ReportName, value: bytes) -> Any:
    payload = _load_json(value, label=f"{report} 类科学载荷")
    try:
        if report == "A":
            from ci_workflow.application.source_research_service import (
                FreshAResearchPackage,
            )

            return FreshAResearchPackage.model_validate(payload)
        if report == "B":
            from ci_workflow.application.fresh_b_research_package import (
                FreshBResearchPackage,
            )

            return FreshBResearchPackage.model_validate(payload)
        from ci_workflow.application.fresh_c_research_package import FreshCResearchPackage

        return FreshCResearchPackage.model_validate(payload)
    except ValueError as error:
        # Pydantic diagnostics may contain submitted values.  Do not echo them.
        raise ResearchPackageSubmissionError(f"{report} 类科学载荷未通过严格合同校验") from error


def _assert_payload_binding(
    package: ResearchPackage,
    report: ReportName,
    payload: Any,
    payload_bytes: bytes,
    *,
    project_id: str,
    indication: str,
    cutoff_date: Any,
    timezone: str,
    project_root: Path,
) -> None:
    binding = next(item for item in package.report_payloads if item.report == report)
    if binding.relative_path != REPORT_PACKAGE_PATHS[report]:
        raise ResearchPackageSubmissionError("报告科学载荷路径绑定错误")
    if binding.content_sha256 != _sha256(payload_bytes):
        raise ResearchPackageSubmissionError(f"{report} 类科学载荷字节摘要不一致")
    if report == "B" and payload.project_id != project_id:
        raise ResearchPackageSubmissionError("B 类科学载荷项目身份不一致")
    if " ".join(payload.indication.split()) != indication:
        raise ResearchPackageSubmissionError(f"{report} 类科学载荷适应症不一致")
    payload_date = payload.data_cutoff.astimezone(ZoneInfo(timezone)).date()
    if payload_date != cutoff_date:
        raise ResearchPackageSubmissionError(f"{report} 类科学载荷数据截止日不一致")

    _assert_source_bindings(package, payload, timezone=timezone, project_root=project_root)
    if tuple(payload.universe_product_ids) != tuple(binding.universe_product_ids):
        raise ResearchPackageSubmissionError(
            f"{report} 类科学载荷的竞品顺序必须等于独立复核的报告候选宇宙"
        )

    envelope_attempt_ids = {
        attempt_id for route in package.routes for attempt_id in route.attempt_ids
    }
    payload_attempt_ids = {item.attempt_id for item in payload.route_attempts}
    if not payload_attempt_ids <= envelope_attempt_ids:
        raise ResearchPackageSubmissionError(f"{report} 类科学载荷含审计包外路线尝试")


def _atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _persist_immutable(path: Path, value: bytes) -> bool:
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != value:
            raise ResearchPackageSubmissionError(f"已存在内容与本次提交不同，拒绝覆盖：{path.name}")
        return True
    _atomic_write(path, value)
    return False


def _manual_recovery_digests(root: Path) -> frozenset[str]:
    digests: set[str] = set()
    for path in sorted((root / "state/manual-supply-gates").glob("*.json")):
        try:
            gate = ManualSupplyGate.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as error:
            raise ResearchPackageSubmissionError("已保存的 publication 补件门不可验证") from error
        if gate.state != "accepted" or gate.response is None:
            continue
        digests.update(item.content_sha256 for item in gate.response.validation_receipts)
    return frozenset(digests)


def _authorize_manual_recovery_replacement(root: Path, package: ResearchPackage) -> None:
    accepted_digests = _manual_recovery_digests(root)
    if not accepted_digests:
        raise ResearchPackageSubmissionError("已存在内容与本次提交不同，且没有已接受的补件恢复")
    source_digests = {
        source.content_sha256 for source in package.sources if source.content_sha256 is not None
    }
    if not accepted_digests <= source_digests:
        raise ResearchPackageSubmissionError("恢复提交未绑定全部已核验补件字节")
    if any(record.manual_supply_required for record in package.publication_records):
        raise ResearchPackageSubmissionError("恢复提交仍把已核验 publication 标记为需要人工补件")


def _archive_current_submission(root: Path, selected_reports: tuple[str, ...]) -> None:
    audit_path = root / AUDIT_PACKAGE_PATH
    old_digest = _sha256(_read_file(audit_path, label="既有研究审计包"))
    archive_root = root / "snapshots/research-submissions" / old_digest
    paths = (
        AUDIT_PACKAGE_PATH,
        SUBMISSION_MANIFEST_PATH,
        *(REPORT_PACKAGE_PATHS[cast(ReportName, report)] for report in selected_reports),
    )
    for relative in paths:
        source = root / relative
        if not source.is_file():
            raise ResearchPackageSubmissionError("既有研究提交不完整，拒绝恢复替换")
        _persist_immutable(archive_root / relative, source.read_bytes())


def _manifest_bytes(package: ResearchPackage, audit_bytes: bytes) -> bytes:
    value = {
        "schema_version": "1.0",
        "package_id": package.package_id,
        "project_id": package.contract_identity.project_id,
        "authorization_state": "candidate_unreviewed",
        "reports": list(package.reports),
        "audit_package": {
            "relative_path": AUDIT_PACKAGE_PATH,
            "sha256": _sha256(audit_bytes),
        },
        "report_payloads": [
            {
                "report": item.report,
                "relative_path": item.relative_path,
                "sha256": item.content_sha256,
            }
            for item in package.report_payloads
        ],
    }
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{serialized}\n".encode()


def _assert_publication_gate_units(package: ResearchPackage) -> None:
    """Bind manual-publication fields to the approved report gate specifications."""

    package_root = Path(__file__).resolve().parents[3]
    critical_by_report = {
        report: {
            unit.unit_id
            for unit in GateSpec.from_yaml(
                package_root / "policies/gates" / f"{report}-v1.yaml"
            ).units
            if unit.blocking_level is GateBlockingLevel.CRITICAL
        }
        for report in package.reports
    }
    for record in package.publication_records:
        if not record.manual_supply_required:
            continue
        for report in record.affected_reports:
            fields = {
                field for field in record.blocking_fields if field.startswith(f"{report.lower()}_")
            }
            if not fields or not fields <= critical_by_report[report]:
                raise ResearchPackageSubmissionError(
                    f"publication 阻断字段未绑定 {report} 类批准 GateSpec"
                )


def submit_product_research_package(
    project_root: Path,
    *,
    audit_package: Path,
    report_packages: Mapping[ReportName, Path],
) -> ProductResearchSubmission:
    """Validate all bytes, persist payloads, then publish the bound manifest."""

    root = project_root.expanduser().resolve()
    contract = verify_project_workspace(root).contract
    audit_bytes = _read_file(audit_package, label="研究审计包")
    try:
        package = validate_research_package(
            _load_json(audit_bytes, label="研究审计包"), require_gate_ready=True
        )
        package.assert_product_handoff_ready()
    except ValueError as error:
        raise ResearchPackageSubmissionError("研究审计包未通过严格合同校验") from error
    if package.closure.review_digest_version != "2":
        raise ResearchPackageSubmissionError(
            "来源元数据需要独立复核摘要v2；历史回执只读保留，请重新复核后提交"
        )
    _assert_publication_gate_units(package)

    source_policy = load_default_source_policy(Path(__file__).resolve().parents[3])
    if (
        package.source_policy_id != source_policy.policy_id
        or package.source_policy_version != source_policy.version
    ):
        raise ResearchPackageSubmissionError("研究审计包来源政策版本与当前安装包不一致")

    selected_reports = tuple(item.value for item in contract.reports)
    if tuple(package.reports) != selected_reports or set(report_packages) != set(selected_reports):
        raise ResearchPackageSubmissionError("提交的报告集合与项目合同不一致")
    if package.contract_identity.project_id != contract.project_id:
        raise ResearchPackageSubmissionError("研究审计包项目身份不一致")
    if package.contract_identity.indication != contract.indication:
        raise ResearchPackageSubmissionError("研究审计包适应症不一致")
    cutoff_date = contract.data_cutoff.astimezone(ZoneInfo(contract.timezone)).date()
    if package.data_cutoff != cutoff_date:
        raise ResearchPackageSubmissionError("研究审计包数据截止日不一致")

    payload_bytes: dict[ReportName, bytes] = {}
    for report in selected_reports:
        report_name = cast(ReportName, report)
        value = _read_file(report_packages[report_name], label=f"{report_name} 类科学载荷")
        payload = _validate_report_payload(report_name, value)
        _assert_payload_binding(
            package,
            report_name,
            payload,
            value,
            project_id=contract.project_id,
            indication=contract.indication,
            cutoff_date=cutoff_date,
            timezone=contract.timezone,
            project_root=root,
        )
        payload_bytes[report_name] = value

    manifest_bytes = _manifest_bytes(package, audit_bytes)
    existing_audit = root / AUDIT_PACKAGE_PATH
    replacing = existing_audit.is_file() and existing_audit.read_bytes() != audit_bytes
    if replacing:
        _authorize_manual_recovery_replacement(root, package)
        _archive_current_submission(root, selected_reports)
        _atomic_write(existing_audit, audit_bytes)
        for report, value in payload_bytes.items():
            _atomic_write(root / REPORT_PACKAGE_PATHS[report], value)
        _atomic_write(root / SUBMISSION_MANIFEST_PATH, manifest_bytes)
        replayed = False
    else:
        replayed = _persist_immutable(existing_audit, audit_bytes)
        for report, value in payload_bytes.items():
            replayed = _persist_immutable(root / REPORT_PACKAGE_PATHS[report], value) and replayed
        replayed = _persist_immutable(root / SUBMISSION_MANIFEST_PATH, manifest_bytes) and replayed
    return ProductResearchSubmission(
        package=package,
        audit_package_path=root / AUDIT_PACKAGE_PATH,
        report_package_paths={
            report: root / REPORT_PACKAGE_PATHS[report] for report in payload_bytes
        },
        manifest_path=root / SUBMISSION_MANIFEST_PATH,
        replayed=replayed,
        authorization_state="candidate_unreviewed",
    )


def load_product_research_submission(project_root: Path) -> ProductResearchSubmission:
    """Revalidate a completed submission; loose or drifted files fail closed."""

    root = project_root.expanduser().resolve()
    manifest_path = root / SUBMISSION_MANIFEST_PATH
    manifest = _load_json(_read_file(manifest_path, label="研究包提交清单"), label="研究包提交清单")
    audit_path = root / AUDIT_PACKAGE_PATH
    audit_bytes = _read_file(audit_path, label="研究审计包")
    if manifest.get("audit_package", {}).get("sha256") != _sha256(audit_bytes):
        raise ResearchPackageSubmissionError("研究审计包与提交清单不一致")
    package = validate_research_package(_load_json(audit_bytes, label="研究审计包"))
    report_paths: dict[ReportName, Path] = {}
    for binding in package.report_payloads:
        path = root / binding.relative_path
        stored_digest = _sha256(_read_file(path, label=f"{binding.report} 类科学载荷"))
        if stored_digest != binding.content_sha256:
            raise ResearchPackageSubmissionError(f"{binding.report} 类科学载荷已漂移")
        report_paths[binding.report] = path
    # Reuse the full admission checks against the already persisted immutable bytes.
    admitted = submit_product_research_package(
        root, audit_package=audit_path, report_packages=report_paths
    )
    return ProductResearchSubmission(
        package=admitted.package,
        audit_package_path=audit_path,
        report_package_paths=report_paths,
        manifest_path=manifest_path,
        replayed=True,
        authorization_state="candidate_unreviewed",
    )


__all__ = [
    "AUDIT_PACKAGE_PATH",
    "REPORT_PACKAGE_PATHS",
    "SUBMISSION_MANIFEST_PATH",
    "ProductResearchSubmission",
    "ResearchPackageSubmissionError",
    "load_product_research_submission",
    "submit_product_research_package",
]
