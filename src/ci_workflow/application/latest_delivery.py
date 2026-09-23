"""Atomic per-report publication pointers; candidate directories are never latest."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ci_workflow.application.delivered_artifacts import _ordinary, read_accepted_html_artifacts
from ci_workflow.storage.manifest_store import ArtifactManifest, ManifestStore
from ci_workflow.storage.sqlite import open_database

ReportCode = Literal["A", "B", "C"]


class LatestDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    project_id: str
    contract_version: int = Field(ge=1)
    report: Literal["A", "B", "C"]
    report_version: str
    manifest_id: str
    report_snapshot_id: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_relative_path: str
    accepted_at: datetime


class CurrentReportDelivery(BaseModel):
    """One report inside the atomic user-current A/B/C bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report: Literal["A", "B", "C"]
    revision: int = Field(ge=0)
    request_id: str | None = None
    report_version: str
    site_relative_path: str
    file_hashes: dict[str, str]
    fact_version_ids: tuple[str, ...]
    fact_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    transaction_manifest_relative_path: str | None = None
    transaction_manifest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    builder_input_relative_path: str | None = None
    builder_input_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class CurrentDeliveryBundle(BaseModel):
    """Immutable generation payload selected by SQLite's committed head."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0"] = "2.0"
    project_id: str
    revision: int = Field(ge=0)
    request_id: str | None = None
    active_fact_version_ids: tuple[str, ...] = Field(min_length=1)
    fact_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reports: tuple[CurrentReportDelivery, ...]
    created_at: datetime


class CurrentProtocolDescriptor(BaseModel):
    """Stable raw contract at reports/current.json; it never contains a revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0"] = "2.0"
    protocol: Literal["sqlite-committed-generation"] = "sqlite-committed-generation"
    database_relative_path: Literal["state/project.sqlite"] = "state/project.sqlite"
    selector_table: Literal["current_delivery_state"] = "current_delivery_state"
    generations_relative_path: Literal["reports/generations"] = "reports/generations"


class CurrentDeliveryIndeterminateError(RuntimeError):
    """The durable selector cannot be classified as old or candidate after a fault."""


class CurrentDeliveryJournal(BaseModel):
    """Durable visibility barrier for a cross-file user delivery transaction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    request_id: str
    phase: Literal["prepared", "ready"]
    previous: CurrentDeliveryBundle
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _current_pointer(root: Path) -> Path:
    path = root / "reports" / "current.json"
    _ordinary(root, path)
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_bytes(bundle: CurrentDeliveryBundle) -> bytes:
    return (bundle.model_dump_json() + "\n").encode("utf-8")


def _bundle_sha256(bundle: CurrentDeliveryBundle) -> str:
    return hashlib.sha256(_bundle_bytes(bundle)).hexdigest()


def _descriptor_bytes() -> bytes:
    return (
        json.dumps(
            CurrentProtocolDescriptor().model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, payload: bytes, *, prefix: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=prefix, dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _journal_path(root: Path, request_id: str) -> Path:
    name = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    path = root / "state" / "user-fact-transactions" / f"{name}.json"
    _ordinary(root, path)
    return path


def _validate_current_bundle(root: Path, bundle: CurrentDeliveryBundle) -> None:
    reports = [item.report for item in bundle.reports]
    if not reports:
        raise ValueError("当前交付至少需要一份已存在报告")
    if len(reports) != len(set(reports)):
        raise ValueError("当前交付不得重复报告类型")
    if any(item.revision > bundle.revision for item in bundle.reports):
        raise ValueError("报告消费revision不得晚于current generation")
    if bundle.revision > 0 and not any(
        item.revision == bundle.revision for item in bundle.reports
    ):
        raise ValueError("current generation没有任何报告消费本次revision，构成跨revision")
    expected_global_digest = hashlib.sha256(
        json.dumps(
            sorted(bundle.active_fact_version_ids),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if bundle.fact_revision_digest != expected_global_digest:
        raise ValueError("current generation事实版本闭包摘要不一致")
    if len(bundle.active_fact_version_ids) != len(set(bundle.active_fact_version_ids)):
        raise ValueError("current generation事实版本不得重复")
    active = set(bundle.active_fact_version_ids)
    if any(not set(item.fact_version_ids) <= active for item in bundle.reports):
        raise ValueError("报告消费者绑定了非current事实版本")
    if bundle.revision > 0 and not bundle.request_id:
        raise ValueError("用户修订current缺少request_id")
    for item in bundle.reports:
        if item.builder_input_relative_path is not None:
            builder_input = root / item.builder_input_relative_path
            _ordinary(root, builder_input)
            if (
                item.builder_input_sha256 is None
                or not builder_input.is_file()
                or _sha256(builder_input) != item.builder_input_sha256
            ):
                raise ValueError("当前交付builder输入绑定不一致")
        _verify_current_report(root, item)


def prepare_current_transaction(
    project_root: Path,
    *,
    request_id: str,
    previous: CurrentDeliveryBundle,
    candidate: CurrentDeliveryBundle,
) -> CurrentDeliveryJournal:
    root = project_root.expanduser().resolve()
    path = _journal_path(root, request_id)
    expected = CurrentDeliveryJournal(
        request_id=request_id,
        phase="prepared",
        previous=previous,
        candidate_sha256=_bundle_sha256(candidate),
    )
    if path.is_file():
        existing = CurrentDeliveryJournal.model_validate_json(path.read_bytes())
        if (
            existing.request_id != request_id
            or existing.previous != previous
            or existing.candidate_sha256 != expected.candidate_sha256
        ):
            raise ValueError("用户修订事务journal与重试载荷不一致")
        if existing.phase == "ready":
            return existing
    _atomic_write(path, _bundle_bytes_for_model(expected), prefix=".user-fact-journal-")
    return expected


def _bundle_bytes_for_model(model: BaseModel) -> bytes:
    return (model.model_dump_json() + "\n").encode("utf-8")


def commit_current_transaction(
    project_root: Path,
    *,
    request_id: str,
    candidate: CurrentDeliveryBundle,
) -> CurrentDeliveryJournal:
    root = project_root.expanduser().resolve()
    path = _journal_path(root, request_id)
    if not path.is_file():
        raise ValueError("用户修订事务journal不存在")
    journal = CurrentDeliveryJournal.model_validate_json(path.read_bytes())
    if journal.candidate_sha256 != _bundle_sha256(candidate):
        raise ValueError("用户修订事务journal与current候选不一致")
    ready = journal.model_copy(update={"phase": "ready"})
    _atomic_write(path, _bundle_bytes_for_model(ready), prefix=".user-fact-journal-")
    return ready


def current_transaction_committed(project_root: Path, request_id: str) -> bool:
    root = project_root.expanduser().resolve()
    path = _journal_path(root, request_id)
    if not path.is_file():
        return False
    journal = CurrentDeliveryJournal.model_validate_json(path.read_bytes())
    if journal.phase != "ready":
        return False
    try:
        current = read_current_delivery(root)
    except ValueError:
        return False
    return (
        current is not None
        and current.request_id == request_id
        and _bundle_sha256(current) == journal.candidate_sha256
    )


def _verify_current_report(root: Path, item: CurrentReportDelivery) -> None:
    relative = Path(item.site_relative_path)
    if relative.is_absolute() or ".." in relative.parts or "\\" in item.site_relative_path:
        raise ValueError("当前交付站点路径必须是项目内相对路径")
    site = root / relative
    _ordinary(root, site)
    if not site.is_dir():
        raise ValueError("当前交付站点目录不存在")
    actual: dict[str, str] = {}
    for path in sorted(site.rglob("*")):
        _ordinary(root, path)
        if path.is_symlink():
            raise ValueError("当前交付站点不得包含符号链接")
        if path.is_file():
            actual[path.relative_to(site).as_posix()] = _sha256(path)
    if actual != item.file_hashes:
        raise ValueError("当前交付站点实际文件与绑定哈希不一致")
    expected = hashlib.sha256(
        json.dumps(sorted(item.fact_version_ids), ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    if item.fact_revision_digest != expected:
        raise ValueError("当前交付事实版本闭包摘要不一致")
    if item.revision > 0:
        if (
            item.request_id is None
            or not item.request_id.strip()
            or item.transaction_manifest_relative_path is None
            or item.transaction_manifest_sha256 is None
        ):
            raise ValueError("用户修订交付缺少渲染事务清单绑定")
        manifest_path = root / item.transaction_manifest_relative_path
        _ordinary(root, manifest_path)
        if (
            not manifest_path.is_file()
            or _sha256(manifest_path) != item.transaction_manifest_sha256
        ):
            raise ValueError("用户修订渲染事务清单哈希不一致")
        manifest = json.loads(manifest_path.read_bytes())
        if (
            manifest.get("report") != item.report
            or manifest.get("revision") != item.revision
            or manifest.get("request_id") != item.request_id
            or manifest.get("fact_version_ids") != list(item.fact_version_ids)
            or manifest.get("fact_revision_digest") != item.fact_revision_digest
            or manifest.get("file_hashes") != item.file_hashes
        ):
            raise ValueError("用户修订渲染事务清单与当前交付闭包不一致")
        integration = manifest.get("portal_integration")
        if not isinstance(integration, dict):
            raise ValueError("用户修订渲染事务清单缺少真实门户接入回执")
        if (
            integration.get("report") != item.report
            or integration.get("revision") != item.revision
            or integration.get("request_id") != item.request_id
            or integration.get("fact_revision_digest") != item.fact_revision_digest
        ):
            raise ValueError("真实门户接入回执与current身份不一致")
        bound_paths = {
            str(integration.get("payload_relative_path")): integration.get("payload_sha256"),
            str(integration.get("search_index_relative_path")): integration.get(
                "search_index_sha256"
            ),
        }
        html_hashes = integration.get("html_sha256")
        if not isinstance(html_hashes, dict):
            raise ValueError("真实门户接入回执缺少页面哈希")
        bound_paths.update({str(key): value for key, value in html_hashes.items()})
        for relative_path, expected_sha256 in bound_paths.items():
            if item.file_hashes.get(relative_path) != expected_sha256:
                raise ValueError("真实门户接入回执文件哈希与current不一致")
        payload_relative = str(integration.get("payload_relative_path"))
        payload_text = (site / payload_relative).read_text(encoding="utf-8")
        if '"user_fact_revision"' in payload_text:
            raise ValueError("真实门户payload不得依赖W04 revision overlay")
        consumers = integration.get("consumers")
        if not isinstance(consumers, list) or not consumers:
            raise ValueError("真实门户接入回执缺少实际消费者")
        impact_bindings = manifest.get("impact_bindings")
        if not isinstance(impact_bindings, list) or len(impact_bindings) != len(consumers):
            raise ValueError("impact DAG缺少已验证消费者科学身份")
        for consumer in consumers:
            if not isinstance(consumer, dict) or consumer.get("report") != item.report:
                raise ValueError("真实门户消费者身份无效")
            binding = consumer.get("binding_identity")
            if not isinstance(binding, dict):
                raise ValueError("真实门户消费者缺少已验证科学身份")
            required_identity = {
                "report",
                "collection",
                "row_id",
                "product_id",
                "drug_name",
                "trial_id",
                "registry_id",
                "group_id",
                "arm",
                "cohort_id",
                "period",
                "endpoint_definition",
                "event_definition",
                "statistical_form",
                "measure_object",
                "unit",
                "normalized_unit",
                "source_version_id",
                "source_pointer",
                "original_row_sha256",
            }
            if set(binding) != required_identity:
                raise ValueError("真实门户消费者科学身份字段不完整")
            if (
                binding.get("report") != item.report
                or binding.get("row_id") != consumer.get("row_id")
                or binding.get("collection") != consumer.get("collection")
                or binding.get("original_row_sha256")
                != consumer.get("original_row_sha256")
            ):
                raise ValueError("真实门户消费者科学身份与receipt节点不一致")
            page_relative = str(consumer.get("page_relative_path"))
            if page_relative not in html_hashes:
                raise ValueError("真实门户消费者页面未绑定")
            required = {
                "chart_consumer",
                "table_consumer",
                "narrative_consumer",
                "index_consumer",
                "source_binding_consumer",
            }
            if any(not str(consumer.get(field, "")).strip() for field in required):
                raise ValueError("真实门户消费者缺少具体图表/表格/文字/索引/来源身份")
            expected_impact = {
                "fact_id": consumer.get("fact_id"),
                "fact_version_id": consumer.get("fact_version_id"),
                "binding_identity": binding,
                "original_row_sha256": consumer.get("original_row_sha256"),
            }
            if expected_impact not in impact_bindings:
                raise ValueError("impact DAG科学身份与portal receipt不一致")
        if any((site / "data").glob("w04-*.json")):
            raise ValueError("真实门户不得以W04 shadow sidecar作为交付面")


def _read_committed_generation(root: Path) -> CurrentDeliveryBundle | None:
    database_path = root / "state/project.sqlite"
    if not database_path.is_file():
        return None
    with open_database(database_path) as database:
        row = database.execute(
            "SELECT project_id,revision,request_id,generation_sha256,"
            "generation_relative_path FROM current_delivery_state WHERE singleton=1"
        ).fetchone()
    if row is None:
        return None
    project_id, revision, request_id, digest, relative = row
    generation = root / str(relative)
    _ordinary(root, generation)
    if not generation.is_file() or _sha256(generation) != str(digest):
        raise CurrentDeliveryIndeterminateError("committed current generation缺失或摘要不一致")
    bundle = CurrentDeliveryBundle.model_validate_json(generation.read_bytes())
    if (
        bundle.project_id != str(project_id)
        or bundle.revision != int(revision)
        or bundle.request_id != request_id
        or _bundle_sha256(bundle) != str(digest)
    ):
        raise CurrentDeliveryIndeterminateError("committed selector与generation身份不一致")
    _validate_current_bundle(root, bundle)
    return bundle


def read_current_delivery(project_root: Path) -> CurrentDeliveryBundle | None:
    """Read only the generation selected by SQLite's durable committed state."""
    root = project_root.expanduser().resolve()
    path = _current_pointer(root)
    if not path.exists():
        return None
    CurrentProtocolDescriptor.model_validate_json(path.read_bytes())
    if path.read_bytes() != _descriptor_bytes():
        raise ValueError("reports/current.json不是规范化current协议描述符")
    return _read_committed_generation(root)


def publish_current_delivery(
    project_root: Path,
    bundle: CurrentDeliveryBundle,
    *,
    expected_revision: int,
) -> CurrentDeliveryBundle:
    """Persist an immutable generation, then commit its selector in one DB transaction."""
    root = project_root.expanduser().resolve()
    path = _current_pointer(root)
    if path.is_file():
        CurrentProtocolDescriptor.model_validate_json(path.read_bytes())
        if path.read_bytes() != _descriptor_bytes():
            raise ValueError("禁止直接消费或覆盖legacy current pointer")
    else:
        _atomic_write(path, _descriptor_bytes(), prefix=".current-protocol-")
    current = _read_committed_generation(root)
    actual_revision = 0 if current is None else current.revision
    if actual_revision != expected_revision:
        raise ValueError("当前交付版本冲突，请重新载入后再保存")
    if bundle.revision != expected_revision + (0 if current is None else 1) and not (
        current is None and expected_revision == 0 and bundle.revision == 0
    ):
        raise ValueError("新交付revision必须紧邻当前版本")
    _validate_current_bundle(root, bundle)
    payload = _bundle_bytes(bundle)
    digest = hashlib.sha256(payload).hexdigest()
    generation_relative = f"reports/generations/{digest}.json"
    generation = root / generation_relative
    _ordinary(root, generation)
    if generation.is_file():
        if generation.read_bytes() != payload:
            raise CurrentDeliveryIndeterminateError("immutable generation摘要碰撞或字节漂移")
    else:
        _atomic_write(generation, payload, prefix=".generation-")
    try:
        with open_database(root / "state/project.sqlite") as database:
            database.execute("BEGIN IMMEDIATE")
            selected = database.execute(
                "SELECT revision,generation_sha256 FROM current_delivery_state WHERE singleton=1"
            ).fetchone()
            selected_revision = 0 if selected is None else int(selected[0])
            if selected_revision != expected_revision:
                raise ValueError("当前交付版本冲突，请重新载入后再保存")
            database.execute(
                "INSERT OR IGNORE INTO current_delivery_generations "
                "(generation_sha256,project_id,revision,request_id,generation_relative_path,"
                "bundle_json,created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    digest,
                    bundle.project_id,
                    bundle.revision,
                    bundle.request_id,
                    generation_relative,
                    payload.decode("utf-8"),
                    bundle.created_at.isoformat(),
                ),
            )
            database.execute(
                "INSERT INTO current_delivery_state "
                "(singleton,project_id,revision,request_id,generation_sha256,"
                "generation_relative_path,committed_at) VALUES (1,?,?,?,?,?,?) "
                "ON CONFLICT(singleton) DO UPDATE SET project_id=excluded.project_id,"
                "revision=excluded.revision,request_id=excluded.request_id,"
                "generation_sha256=excluded.generation_sha256,"
                "generation_relative_path=excluded.generation_relative_path,"
                "committed_at=excluded.committed_at",
                (
                    bundle.project_id,
                    bundle.revision,
                    bundle.request_id,
                    digest,
                    generation_relative,
                    bundle.created_at.isoformat(),
                ),
            )
    except (sqlite3.DatabaseError, OSError):
        try:
            observed = _read_committed_generation(root)
        except Exception as recovery_error:
            raise CurrentDeliveryIndeterminateError(
                "current selector提交结果不可判定；恢复读取失败"
            ) from recovery_error
        if observed is not None and _bundle_sha256(observed) == digest:
            return observed
        if observed == current:
            raise
        raise CurrentDeliveryIndeterminateError(
            "current selector提交结果不可判定；必须先执行恢复读取"
        ) from None
    try:
        committed = _read_committed_generation(root)
    except Exception as recovery_error:
        raise CurrentDeliveryIndeterminateError(
            "current selector已提交但恢复读取失败"
        ) from recovery_error
    if committed is None or _bundle_sha256(committed) != digest:
        raise CurrentDeliveryIndeterminateError("current selector提交后无法读取候选generation")
    return committed


def current_bundle_sha256(bundle: CurrentDeliveryBundle) -> str:
    """Digest of the exact bytes publish_current_delivery will expose."""
    return _bundle_sha256(bundle)


def _projection(manifest: ArtifactManifest) -> LatestDelivery:
    return LatestDelivery(
        project_id=manifest.project_id,
        contract_version=manifest.contract_version,
        report=manifest.report,
        report_version=manifest.report_version,
        manifest_id=manifest.manifest_id,
        report_snapshot_id=manifest.report_snapshot_id,
        artifact_sha256=manifest.artifact.sha256,
        entry_relative_path=f"{manifest.artifact.relative_path}/index.html",
        accepted_at=manifest.render_verdict.verified_at,
    )


def _pointer(root: Path, report: str) -> Path:
    if report not in {"A", "B", "C"}:
        raise ValueError("最新版报告类型只能是A/B/C")
    path = root / "reports" / report / "latest.json"
    _ordinary(root, path)
    return path


def read_latest_delivery(project_root: Path, report: str) -> LatestDelivery | None:
    root = project_root.expanduser().resolve()
    current = read_current_delivery(root)
    if current is not None and any(item.report == report for item in current.reports):
        raise ValueError("存在用户current修订，禁止通过latest.json旁路当前事实")
    path = _pointer(root, report)
    if not path.exists():
        return None
    pointer = LatestDelivery.model_validate_json(path.read_bytes())
    artifacts = read_accepted_html_artifacts(root, contract_version=pointer.contract_version)
    matches = [
        item
        for item in artifacts
        if item.manifest_id == pointer.manifest_id and item.report == report
    ]
    if len(matches) != 1 or _projection(matches[0]) != pointer:
        raise ValueError("最新版指针未绑定可验证的已接受产物")
    return pointer


def read_effective_delivery(
    project_root: Path, report: ReportCode
) -> CurrentReportDelivery | LatestDelivery | None:
    """Canonical delivery reader: user current wins, accepted latest is fallback only."""
    root = project_root.expanduser().resolve()
    current = read_current_delivery(root)
    if current is not None:
        matches = [item for item in current.reports if item.report == report]
        if len(matches) > 1:
            raise ValueError("当前交付不得重复报告类型")
        if matches:
            return matches[0]
    return read_latest_delivery(root, report)


def publish_latest_delivery(project_root: Path, manifest_id: str) -> LatestDelivery:
    root = project_root.expanduser().resolve()
    matches = [
        item for item in read_accepted_html_artifacts(root) if item.manifest_id == manifest_id
    ]
    if len(matches) != 1:
        raise ValueError("仅唯一的已接受产物可以发布最新版")
    manifest = matches[0]
    candidate = _projection(manifest)
    path = _pointer(root, manifest.report)
    encoded = (candidate.model_dump_json() + "\n").encode()
    for _attempt in range(3):
        previous_bytes = path.read_bytes() if path.exists() else None
        previous = read_latest_delivery(root, manifest.report)
        if previous == candidate:
            return candidate
        if previous is not None and (
            previous.contract_version > candidate.contract_version
            or previous.accepted_at >= candidate.accepted_at
        ):
            raise ValueError("不得自动回退或以同一接受时刻覆盖最新版")
        # Serialize publishers using the existing project DB, then compare-and-swap.
        with open_database(root / "state/project.sqlite") as database:
            database.execute("BEGIN IMMEDIATE")
            _ordinary(root, path)
            current_bytes = path.read_bytes() if path.exists() else None
            if current_bytes != previous_bytes:
                continue
            ManifestStore(root).verify_artifact(manifest)
            descriptor, temporary = tempfile.mkstemp(prefix=".latest-", dir=path.parent)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            return candidate
    raise ValueError("最新版被并发更新，请重新验证后重试")
