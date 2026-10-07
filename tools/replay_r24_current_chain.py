"""Isolated real-source save/clear/restore/undo/share rehearsal, never release.

Use a fresh output. Verify and copy a fixed candidate, or verify a pinned
source-v3 receipt and build a minimal fresh working copy of that source project;
never write the source project, its journals, or an existing user current.
Test values are visibly marked QA-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from ci_workflow import __version__
from ci_workflow.application.latest_delivery import ReportCode, read_current_delivery
from ci_workflow.application.portal_consumer_registry import register_b_shared_source_consumers
from ci_workflow.application.project_service import (
    _DIRECTORIES as _PROJECT_DIRECTORIES,
)
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.share_export import ShareViewSelection, export_current_html_share
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveError,
)
from ci_workflow.domain.contracts import ProjectContract
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.reports.common.identity_projection import (
    PortalIdentityContext,
    load_project_identity_context,
)
from ci_workflow.storage.snapshot_store import LockedSnapshot
from tools.build_r24_desktop_candidate import DEVELOPMENT_LIMITATION
from tools.materialize_ctgov_a_candidate import public_provenance_for_candidate


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def share_product_query(
    report: ReportCode, payload: dict[str, Any], product_id: str,
) -> dict[str, tuple[str, ...]]:
    """Select a current product without changing its scientific identity."""
    matches = [item for item in payload.get("products", []) if item.get("id") == product_id]
    if report not in {"A", "B"} or len(matches) != 1:
        raise ValueError("current product identity is missing or ambiguous")
    value = matches[0].get("name") if report == "A" else product_id
    if not isinstance(value, str) or not value.strip():
        raise ValueError("current product identity has no usable filter value")
    # A filters its actual display names; B filters scientific product IDs.
    # Do not guess names or silently discard the saved filter to pass export.
    return {"product": (value,)}


def export_rehearsal_shares(
    project: Path, output: Path, product_id: str,
) -> list[dict[str, Any]]:
    """Export the already committed current; never replay saves to retry sharing."""
    current = read_current_delivery(project)
    if current is None:
        raise ValueError("rehearsal current is missing")
    selections: dict[ReportCode, ShareViewSelection] = {}
    for delivery in current.reports:
        if delivery.report not in {"A", "B"}:
            continue
        data_path = project / delivery.site_relative_path / "data/report.js"
        if digest(data_path) != delivery.file_hashes.get("data/report.js"):
            raise ValueError("current share report data drifted")
        content = data_path.read_text(encoding="utf-8")
        prefix = f"window.REPORT_{delivery.report}="
        if not content.startswith(prefix):
            raise ValueError("current share report data assignment is invalid")
        payload = json.loads(content[len(prefix):].rstrip(" ;\n"))
        selections[delivery.report] = ShareViewSelection(
            report=delivery.report, revision=delivery.revision, entry_page="safety.html",
            query=share_product_query(delivery.report, payload, product_id),
        )
    if set(selections) != {"A", "B"}:
        raise ValueError("rehearsal share requires committed A and B")
    receipts: list[dict[str, Any]] = []
    code_sets: tuple[tuple[ReportCode, ...], ...] = (("A",), ("B",), ("A", "B"))
    for codes in code_sets:
        share = export_current_html_share(
            project, output / ("share-" + "-".join(codes) + ".zip"),
            selections=tuple(selections[code] for code in codes),
        )
        receipts.append({
            "reports": list(codes), "sha256": share.sha256,
            "path": share.output.name, "revision": share.current_revision,
        })
    if read_current_delivery(project) != current:
        raise ValueError("committed current changed while exporting shares")
    return receipts


def validate_current_safety_projection(
    projected: dict[str, Any], *, expected: int | None, original_source: str,
) -> None:
    """Check the public report layer; its disclosure is native Chinese."""
    assert projected["value"] == expected, "current report value differs"
    assert projected["source_text"] == original_source, "original source changed"
    if expected is None:
        assert projected["disclosure_state"] == "用户清除，待重新核实", (
            "cleared public disclosure differs"
        )
        assert projected["numerator"] is None and projected["denominator"] is None, (
            "cleared current counts retained"
        )


def verify_source_candidate(root: Path, candidate: Path) -> dict[str, Any]:
    if candidate.is_symlink():
        raise ValueError("source candidate cannot be a symlink")
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("source candidate must be inside the authorized root")
    manifest: dict[str, Any] = json.loads((candidate / "candidate-manifest.json").read_bytes())
    for relative, expected in manifest["rendered_files"].items():
        path = candidate / relative
        if not path.resolve().is_relative_to(candidate) or path.is_symlink():
            raise ValueError("source manifest has an unsafe path")
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"source candidate drift: {relative}")
    if manifest["current_generation_switched"] is not False:
        raise ValueError("rehearsal needs a candidate, not an existing current")
    return manifest


_REQUIRED_RECEIPT_FIELDS = (
    "schema_version",
    "project_id",
    "snapshot_id",
    "snapshot_sha256",
    "snapshot_relative_path",
    "source_version_ids",
    "fact_bindings",
    "registered_a_efficacy_consumers",
    "registered_a_safety_consumers",
    "bound_report_data",
    "bound_b_report_data",
)

_WORKING_COPY_ROOTS = (
    "project.yaml",
    "blockers",
    "corrections",
    "coverage",
    "events",
    "evidence",
    "logs",
    "manifests",
    "monitoring",
    "receipts",
    "snapshots/evidence",
)
_WORKING_COPY_OPTIONAL_ROOTS = ("identity-checkpoint.json",)
# verify_project_workspace requires the standard project directory set; the
# working copy excludes pre-rendered reports but must still carry the layout.
_WORKING_COPY_REQUIRED_DIRECTORIES = _PROJECT_DIRECTORIES
_WORKING_COPY_EXCLUDED = ("reports", "snapshots/reports")


def resolve_contained_relative(base: Path, relative: str, *, what: str) -> Path:
    """Resolve a declared relative path without leaving its base or crossing a symlink."""
    pure = PurePosixPath(relative)
    if not relative or pure.is_absolute() or ".." in pure.parts or "\\" in relative:
        raise ValueError(f"{what} must be a contained relative path")
    path = base
    for part in pure.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"{what} must not cross a symlink")
    resolved = path.resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise ValueError(f"{what} must stay inside its source root")
    return resolved


def _authorized_path(root: Path, path: Path) -> Path:
    """Check the lexical boundary before touching a source or resolving its links."""
    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError as error:
        raise ValueError("replay input must stay inside the authorized root") from error
    return resolve_contained_relative(root.absolute(), relative.as_posix(), what="replay input")


def verify_source_receipt(path: Path, expected_sha256: str) -> dict[str, Any]:
    """Pin the external receipt bytes; only its descriptors may describe the source."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("source receipt must be a regular file")
    actual = digest(path)
    if actual != expected_sha256.strip().lower():
        raise ValueError(
            f"source receipt sha256 mismatch: expected {expected_sha256}, got {actual}"
        )
    try:
        receipt = json.loads(path.read_bytes())
    except json.JSONDecodeError as error:
        raise ValueError("source receipt is not valid JSON") from error
    if not isinstance(receipt, dict):
        raise ValueError("source receipt must be a JSON object")
    missing = sorted(set(_REQUIRED_RECEIPT_FIELDS) - set(receipt))
    if missing:
        raise ValueError(f"source receipt is missing fields: {missing}")
    for key in (
        "source_version_ids",
        "registered_a_efficacy_consumers",
        "registered_a_safety_consumers",
    ):
        value = receipt[key]
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"source receipt {key} must be a list of strings")
    bindings = receipt["fact_bindings"]
    if (
        not isinstance(bindings, list)
        or not bindings
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("row_ref"), str)
            or not isinstance(item.get("fact_version_id"), str)
            for item in bindings
        )
    ):
        raise ValueError("source receipt fact_bindings are incomplete")
    refs = {item["row_ref"] for item in bindings}
    if len(refs) != len(bindings):
        raise ValueError("source receipt has duplicate scientific consumer bindings")
    declared = {
        f"safety:{row_id}" for row_id in receipt["registered_a_safety_consumers"]
    } | {f"efficacy:{row_id}" for row_id in receipt["registered_a_efficacy_consumers"]}
    missing_refs = sorted(declared - refs)
    if missing_refs:
        raise ValueError(f"source receipt consumer bindings are missing: {missing_refs}")
    return receipt


def verify_source_binding(source_project: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    """Verify pinned descriptors, the project contract, and absence of an existing current."""
    if source_project.is_symlink() or not source_project.is_dir():
        raise ValueError("source project must be a real directory")
    source = source_project.resolve()
    try:
        document = json.loads(resolve_contained_relative(
            source, "project.yaml", what="source project contract",
        ).read_bytes())
        versions = document["project_contract_versions"]
        active = document["active_contract_version"]
        if not isinstance(versions, list) or not versions:
            raise ValueError("source project contract versions cannot be read")
        try:
            contracts = [ProjectContract.model_validate(item) for item in versions]
        except ValueError as error:
            raise ValueError("source project contract cannot be validated") from error
        numbers = [contract.contract_version for contract in contracts]
        if len(numbers) != len(set(numbers)):
            raise ValueError("source project contract versions are duplicated")
        selected = next(contract for contract in contracts if contract.contract_version == active)
        if not {"A", "B"} <= {report.value for report in selected.reports}:
            raise ValueError("source project contract does not authorize A+B replay")
        project_id = next(
            item["project_id"] for item in versions if item["contract_version"] == active
        )
    except (OSError, KeyError, TypeError, StopIteration, json.JSONDecodeError) as error:
        raise ValueError("source project contract cannot be read") from error
    if document.get("schema_version") != "1.0":
        raise ValueError("source project contract cannot be read")
    if document.get("workflow_version") != __version__:
        raise ValueError("source project workflow version differs from this package")
    if project_id != receipt["project_id"]:
        raise ValueError("source project contract differs from the source receipt")
    if resolve_contained_relative(source, "reports/current.json", what="current delivery").exists():
        raise ValueError("source project already has an existing current delivery")
    inputs: dict[str, dict[str, Any]] = {}
    for key, label, report in (
        ("bound_report_data", "source A input", "A"),
        ("bound_b_report_data", "source B input", "B"),
    ):
        descriptor = receipt[key]
        if not isinstance(descriptor, dict) or not isinstance(descriptor.get("relative_path"), str):
            raise ValueError(f"{label} descriptor is incomplete")
        relative = descriptor["relative_path"]
        expected = descriptor.get("sha256")
        path = resolve_contained_relative(source, relative, what=label)
        if not path.is_file() or not isinstance(expected, str) or digest(path) != expected:
            raise ValueError(f"{label} drifted from the source receipt")
        if "bytes" in descriptor and path.stat().st_size != descriptor["bytes"]:
            raise ValueError(f"{label} size drifted from the source receipt")
        inputs[report] = {
            "relative_path": relative,
            "sha256": expected,
            "bytes": path.stat().st_size,
        }
    snapshot_relative = receipt["snapshot_relative_path"]
    snapshot = resolve_contained_relative(source, snapshot_relative, what="source snapshot")
    if not snapshot.is_file() or digest(snapshot) != receipt["snapshot_sha256"]:
        raise ValueError("source snapshot drifted from the source receipt")
    database = resolve_contained_relative(source, "state/project.sqlite", what="source database")
    if database.is_symlink() or not database.is_file():
        raise ValueError("source database must be a regular file")
    return {
        "project_id": project_id,
        "source_inputs": inputs,
        "source_snapshot": {
            "relative_path": snapshot_relative,
            "sha256": receipt["snapshot_sha256"],
            "bytes": snapshot.stat().st_size,
        },
        "source_database": {"sha256": digest(database), "bytes": database.stat().st_size},
    }


def _database_sidecar_states(database: Path) -> tuple[tuple[bool, int], ...]:
    for suffix in ("-wal", "-shm", "-journal"):
        if database.with_name(database.name + suffix).is_symlink():
            raise ValueError("source database sidecar must not be a symlink")
    return tuple(
        (
            path.exists(),
            path.stat().st_size if path.exists() else 0,
        )
        for path in (
            database.with_name(database.name + suffix) for suffix in ("-wal", "-shm", "-journal")
        )
    )


def _assert_capture_ready(database: Path) -> None:
    """Reject a database whose committed state needs a journal the capture will not touch."""
    if database.is_symlink() or not database.is_file():
        raise ValueError("source database must be a regular file")
    _database_sidecar_states(database)  # Reject every sidecar link before any copy.
    for suffix, label in (("-wal", "WAL"), ("-journal", "rollback journal")):
        sidecar = database.with_name(database.name + suffix)
        if sidecar.is_symlink():
            raise ValueError("source database sidecar must not be a symlink")
        if sidecar.exists() and sidecar.stat().st_size > 0:
            raise ValueError(
                f"source database has an unresolved {label}; settle it before replay, "
                "the rehearsal never journals or checkpoints the source"
            )


def _capture_database(source_database: Path, destination: Path) -> None:
    """Coherent read-only capture; never checkpoints, journals, or writes the source."""
    _assert_capture_ready(source_database)
    before = _database_sidecar_states(source_database)
    # No WAL frames may exist, so the main file alone is the complete committed
    # state; immutable forbids SQLite from creating -wal/-shm beside the source.
    uri = f"file:{quote(str(source_database.resolve()))}?mode=ro&immutable=1"
    try:
        source = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as error:
        raise ValueError("source database cannot be opened read-only") from error
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.Error as error:
            raise ValueError("source database read-only capture failed") from error
        finally:
            target.close()
    finally:
        source.close()
    if integrity != ("ok",):
        raise ValueError("captured database failed the integrity check")
    if _database_sidecar_states(source_database) != before:
        raise ValueError("read-only capture changed the source database journal state")


def _scan_copy_entries(source: Path, roots: tuple[str, ...]) -> list[tuple[str, int]]:
    """Collect regular files and reject links or irregular entries before any write."""
    entries: list[tuple[str, int]] = []
    for relative in roots:
        path = source / relative
        if path.is_symlink():
            raise ValueError(f"source entry must not be a symlink: {relative}")
        if not path.exists():
            raise ValueError(f"source project is missing: {relative}")
        if path.is_dir():
            for item in sorted(path.rglob("*")):
                entry = item.relative_to(source).as_posix()
                if item.is_symlink():
                    raise ValueError(f"source entry must not be a symlink: {entry}")
                if item.is_dir():
                    continue
                if not item.is_file():
                    raise ValueError(f"source entry must be a regular file: {entry}")
                entries.append((entry, item.stat().st_size))
        elif path.is_file():
            entries.append((relative, path.stat().st_size))
        else:
            raise ValueError(f"source entry must be a regular file: {relative}")
    return entries


def prepare_working_copy(root: Path, source_project: Path, output: Path) -> dict[str, Any]:
    """Copy only replay-required material into a fresh working copy.

    Pre-rendered reports are excluded; links and irregular files reject the whole
    copy before any write, files are byte-copied (never hardlinked), and the
    database is captured through a read-only connection.
    """
    source_project = _authorized_path(root, source_project)
    if not source_project.is_dir():
        raise ValueError("source project must be a real directory")
    source = source_project.resolve()
    if output.exists() or output.is_symlink():
        raise ValueError("working copy output must be fresh")
    destination = output.resolve()
    if not destination.is_relative_to(root.resolve()):
        raise ValueError("working copy output must stay inside the authorized root")
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("working copy output must not overlap the source project")
    roots = list(_WORKING_COPY_ROOTS)
    roots.extend(
        relative
        for relative in _WORKING_COPY_OPTIONAL_ROOTS
        if (source / relative).is_symlink() or (source / relative).exists()
    )
    entries = _scan_copy_entries(source, tuple(roots))
    source_database = resolve_contained_relative(source, "state/project.sqlite", what="database")
    _assert_capture_ready(source_database)
    project = destination / "project"
    project.mkdir(parents=True)
    for relative, _size in entries:
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    for relative in _WORKING_COPY_REQUIRED_DIRECTORIES:
        (project / relative).mkdir(parents=True, exist_ok=True)
    working_database = project / "state/project.sqlite"
    _capture_database(source_database, working_database)
    identity_source = source / "evidence/library/portal-identity-context.json"
    identity_digest = None
    if identity_source.is_file():
        copied_identity = project / "evidence/library/portal-identity-context.json"
        if not copied_identity.is_file() or digest(copied_identity) != digest(identity_source):
            raise ValueError("identity source binding did not survive the working copy")
        identity_digest = digest(identity_source)
    return {
        "copied_files": len(entries),
        "copied_bytes": sum(size for _relative, size in entries),
        "source_database": {
            "sha256": digest(source_database),
            "bytes": source_database.stat().st_size,
        },
        "captured_database": {
            "sha256": digest(working_database),
            "bytes": working_database.stat().st_size,
        },
        "identity_binding_sha256": identity_digest,
        "excluded_relative_paths": list(_WORKING_COPY_EXCLUDED),
    }


def replay(root: Path, candidate: Path, output: Path) -> dict[str, Any]:
    manifest = verify_source_candidate(root, candidate)
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to(root):
        raise ValueError("rehearsal output must be fresh and inside the authorized root")
    original = candidate / "source-project"
    source_database_sha = digest(original / "state/project.sqlite")
    project = output / "project"
    shutil.copytree(original, project)
    source_receipt = json.loads((project / "logs/diagnostics/r24-66-source.json").read_bytes())

    def assert_source_unchanged() -> None:
        assert digest(original / "state/project.sqlite") == source_database_sha, (
            "read-only candidate source database changed"
        )

    return _run_rehearsal(
        project,
        output,
        header={
            "status": "isolated_qa_not_scientific_or_release_acceptance",
            "source_candidate_manifest_sha256": digest(candidate / "candidate-manifest.json"),
            "source_database_sha256": source_database_sha,
            "source_snapshot_sha256": manifest["source_snapshot_sha256"],
        },
        source_receipt=source_receipt,
        a_input=project / "inputs/a.json",
        b_input=project / "inputs/b.json",
        identity_context=None,
        assert_source_unchanged=assert_source_unchanged,
    )


def _run_rehearsal(
    project: Path,
    output: Path,
    *,
    header: dict[str, Any],
    source_receipt: dict[str, Any],
    a_input: Path,
    b_input: Path,
    identity_context: PortalIdentityContext | None,
    assert_source_unchanged: Callable[[], None],
) -> dict[str, Any]:
    """Shared isolated save/clear/restore/undo/share chain for both source modes."""
    receipt: dict[str, Any] = {**header, "steps": []}

    def checkpoint() -> None:
        (output / "operation-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )

    checkpoint()
    a = ReportAPortalData.model_validate_json(a_input.read_bytes())
    b = ReportBPortalData.model_validate_json(b_input.read_bytes())
    snapshot_path = project / source_receipt["snapshot_relative_path"]
    snapshot = LockedSnapshot(
        snapshot_id=source_receipt["snapshot_id"], kind="evidence", report=None,
        sha256=source_receipt["snapshot_sha256"],
        relative_path=source_receipt["snapshot_relative_path"],
        byte_size=snapshot_path.stat().st_size,
    )
    versions = {item["row_ref"]: item["fact_version_id"]
                for item in source_receipt["fact_bindings"]}
    safe_ids = set(source_receipt["registered_a_safety_consumers"])
    safety_versions = {f"safety:{row_id}": versions[f"safety:{row_id}"] for row_id in safe_ids}
    at = datetime.now(UTC)
    bindings = register_b_shared_source_consumers(
        project, snapshot, b, safety_versions, registered_at=at,
    )
    receipt["legitimate_shared_safety_consumers"] = len(bindings)
    row = next(row for row in sorted(a.safety, key=lambda item: item.row_id)
               if row.row_id in safe_ids and row.measure_object == "participant_count"
               and row.numerator is not None and row.denominator is not None
               and 0 < row.numerator < row.denominator)
    assert row.numerator is not None and row.denominator is not None
    assert row.source_text is not None
    version_id = versions[f"safety:{row.row_id}"]
    receipt["row_id"] = row.row_id
    receipt["original_source_value"] = row.source_text
    receipt["original_count"] = row.numerator
    receipt["denominator"] = row.denominator
    sites = {kind: project / f"reports/{kind}/development/html" for kind in ("A", "B")}
    render_report_a_site(
        a, sites["A"],
        public_provenance=public_provenance_for_candidate(project, a, source_receipt),
        publication_limitation_zh=DEVELOPMENT_LIMITATION,
        identity_context=identity_context,
    )
    render_report_b_site(b, sites["B"], identity_context=identity_context)
    if identity_context is not None:
        receipt["identity_context_digest"] = identity_context.context_digest
        receipt["identity_bindings"] = {}
        for kind, site in sites.items():
            binding_file = site / "data/identity-context.json"
            if not binding_file.is_file():
                raise ValueError(f"{kind} render dropped the identity source binding")
            receipt["identity_bindings"][kind] = digest(binding_file)
    service = UserFactEditService(project)
    contract = verify_project_workspace(project).contract
    initial_versions = tuple(versions[f"efficacy:{row_id}"]
                             for row_id in source_receipt["registered_a_efficacy_consumers"])
    baseline_ids = set(source_receipt.get("baseline_edit_consumers", ()))
    baseline_versions = tuple(row["source_fact_version_id"]
        for row in (b.baseline_views or {}).get("facts", ()) if row["row_id"] in baseline_ids)
    if len(baseline_versions) != len(baseline_ids):
        raise ValueError("source baseline consumers lack explicit fact-version mappings")
    service.initialize_current_delivery(
        project_id=contract.project_id, report_sites=sites,
        report_data_paths={"A": a_input, "B": b_input},
        fact_version_ids=(*initial_versions, *safety_versions.values(), *baseline_versions),
        created_at=at,
    )
    source = service._fact_row(version_id)

    def command(name: str, edits: FactEdit, *, undo: bool = False) -> UserFactSaveCommand:
        return UserFactSaveCommand(
            request_id=f"r24-69-{name}", project_id=contract.project_id,
            expected_revision=service.read_current_delivery().revision,
            operation="undo" if undo else "save",
            target=FactTargetIdentity(
                fact_id=source["fact_id"], fact_version_id=version_id,
                entity_id=source["entity_id"], field_id=source["field_id"],
            ),
            edits=edits, user_basis="隔离开发演练假设值，非医学订正或正式报告",
            saved_by="qa-replay", saved_at=datetime.now(UTC),
        )

    try:
        old_current = service.read_current_delivery()
        try:
            service.save(command("reject-over-count", FactEdit(
                raw_value=str(row.denominator + 1), normalized_value=row.denominator + 1,
            )))
        except UserFactSaveError as error:
            receipt["failure_rollback"] = {"reason": str(error), "old_current_unchanged": True}
        else:
            raise AssertionError("contradictory count was accepted")
        assert service.read_current_delivery() == old_current
        checkpoint()
        edited = row.numerator + 1
        operations = (
            ("set", FactEdit(raw_value=str(edited), normalized_value=edited), False, edited),
            ("clear", FactEdit(raw_value=None), False, None),
            # This atom is the source participant count. Its denominator is
            # independently sourced, not writable as part of this transaction.
            ("restore", FactEdit(raw_value=str(edited), normalized_value=edited), False, edited),
            ("undo-restore", FactEdit(), True, None),
        )
        for name, edits, undo, expected in operations:
            request = command(name, edits, undo=undo)
            result = service.save(request)
            version_id = result.fact_version_id
            assert result.rebuilt_reports == ("A", "B")
            assert result.derived_crude_rate is None  # counts never become a risk estimate
            active_fact = service._public_fact(service._fact_row(version_id))
            if expected is None:
                assert active_fact["disclosure_state"] == "user_cleared"
                assert active_fact["raw_value"] is None
                assert active_fact["normalized_value"] is None
            current = service.read_current_delivery()
            step: dict[str, Any] = {
                "operation": name, "result": result.model_dump(mode="json"),
                "report_sites": {}, "current_value": expected,
            }
            for delivery in current.reports:
                site = project / delivery.site_relative_path
                text = (site / "data/report.js").read_text()
                payload = json.loads(text.split("=", 1)[1].rstrip(" ;\n"))
                projected = next(item for item in payload["safety"] if item["row_id"] == row.row_id)
                validate_current_safety_projection(
                    projected, expected=expected, original_source=row.source_text,
                )
                step["report_sites"][delivery.report] = delivery.site_relative_path
            assert service.save(request) == result
            assert service.read_current_delivery() == current
            receipt["steps"].append(step)
            checkpoint()
        receipt["shares"] = export_rehearsal_shares(project, output, row.product_id)
        assert_source_unchanged()
        receipt["source_unchanged"] = True
        receipt["remaining"] = [
            "New-browser offline open, other report families and browser edit UI "
            "remain separate checks.",
            "No C consumer, live source refresh, independent medical acceptance or release.",
        ]
        checkpoint()
        return receipt
    except Exception as error:
        receipt["status"] = "failed_rehearsal_not_accepted"
        receipt["failure"] = str(error)
        checkpoint()
        raise


def _relative_to_root(root: Path, path: Path) -> str:
    resolved = path.resolve()
    return (
        str(resolved.relative_to(root.resolve()))
        if resolved.is_relative_to(root.resolve())
        else str(resolved)
    )


def replay_from_source(
    root: Path,
    source_project: Path,
    source_receipt_path: Path,
    source_receipt_sha256: str,
    output: Path,
) -> dict[str, Any]:
    """Rehearse against a pinned source-v3 receipt and a fresh minimal working copy.

    The source project stays read-only: its contract, descriptors, snapshot, and
    database are verified against the pinned receipt before any copy, the copy
    excludes pre-rendered reports, and the identity source binding must load from
    the working copy and survive the initial A/B render.
    """
    source_project = _authorized_path(root, source_project)
    source_receipt_path = _authorized_path(root, source_receipt_path)
    receipt = verify_source_receipt(source_receipt_path, source_receipt_sha256)
    binding = verify_source_binding(source_project, receipt)
    initial_sidecars = _database_sidecar_states(source_project / "state/project.sqlite")
    working = prepare_working_copy(root, source_project, output)
    if working["source_database"]["sha256"] != binding["source_database"]["sha256"]:
        raise ValueError("source database changed during the working copy")
    project = output / "project"
    workspace = verify_project_workspace(project)
    if workspace.contract.project_id != receipt["project_id"]:
        raise ValueError("working copy contract differs from the source receipt")
    a_input = project / receipt["bound_report_data"]["relative_path"]
    b_input = project / receipt["bound_b_report_data"]["relative_path"]
    for report, path in (("A", a_input), ("B", b_input)):
        if digest(path) != binding["source_inputs"][report]["sha256"]:
            raise ValueError(f"copied source {report} input drifted from the receipt")
    if digest(project / receipt["snapshot_relative_path"]) != receipt["snapshot_sha256"]:
        raise ValueError("copied evidence snapshot drifted from the receipt")
    identity_context = load_project_identity_context(project)
    if working["identity_binding_sha256"] is not None and identity_context is None:
        raise ValueError("identity source binding did not load from the working copy")

    def assert_source_unchanged() -> None:
        source = source_project.resolve()
        if _database_sidecar_states(source / "state/project.sqlite") != initial_sidecars:
            raise ValueError("read-only source journal state changed during the rehearsal")
        if digest(source_receipt_path) != source_receipt_sha256.strip().lower():
            raise ValueError("pinned source receipt changed during the rehearsal")
        if digest(source / "state/project.sqlite") != binding["source_database"]["sha256"]:
            raise ValueError("read-only source database changed during the rehearsal")
        for report, record in binding["source_inputs"].items():
            if digest(source / record["relative_path"]) != record["sha256"]:
                raise ValueError(f"read-only source {report} input changed during the rehearsal")
        if digest(source / binding["source_snapshot"]["relative_path"]) != (
            binding["source_snapshot"]["sha256"]
        ):
            raise ValueError("read-only source snapshot changed during the rehearsal")
        if working["identity_binding_sha256"] is not None and digest(
            source / "evidence/library/portal-identity-context.json"
        ) != working["identity_binding_sha256"]:
            raise ValueError("read-only identity binding changed during the rehearsal")

    return _run_rehearsal(
        project,
        output,
        header={
            "status": "isolated_qa_not_scientific_or_release_acceptance",
            "source_receipt_relative_path": _relative_to_root(root, source_receipt_path),
            "source_receipt_sha256": source_receipt_sha256.strip().lower(),
            "source_project_relative_path": _relative_to_root(root, source_project),
            "source_inputs": binding["source_inputs"],
            "source_snapshot": binding["source_snapshot"],
            "source_database_sha256": binding["source_database"]["sha256"],
            "source_database_sidecars": initial_sidecars,
            "source_snapshot_sha256": receipt["snapshot_sha256"],
            "working_copy": working,
            "identity_binding_sha256": working["identity_binding_sha256"],
            "production_methods_invoked": [
                "verify_project_workspace",
                "public_provenance_for_candidate",
                "load_project_identity_context",
                "register_b_shared_source_consumers",
                "render_report_a_site",
                "render_report_b_site",
                "UserFactEditService.initialize_current_delivery",
                "UserFactEditService.save",
                "export_current_html_share",
            ],
        },
        source_receipt=receipt,
        a_input=a_input,
        b_input=b_input,
        identity_context=identity_context,
        assert_source_unchanged=assert_source_unchanged,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--candidate", type=Path)
    source.add_argument("--source-project", type=Path)
    parser.add_argument("--source-receipt", type=Path)
    parser.add_argument("--source-receipt-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.candidate is not None:
        if args.source_receipt is not None or args.source_receipt_sha256 is not None:
            parser.error("--candidate is exclusive with --source-receipt/--source-receipt-sha256")
        result = replay(root, args.candidate.absolute(), args.output.absolute())
    else:
        if (
            args.source_project is None
            or args.source_receipt is None
            or args.source_receipt_sha256 is None
        ):
            parser.error("--source-project requires --source-receipt and --source-receipt-sha256")
        result = replay_from_source(
            root,
            args.source_project.absolute(),
            args.source_receipt.absolute(),
            args.source_receipt_sha256,
            args.output.absolute(),
        )
    print(json.dumps(result, ensure_ascii=False))
