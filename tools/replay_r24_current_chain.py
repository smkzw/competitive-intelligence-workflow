"""Isolated real-source save/clear/restore/undo/share rehearsal, never release.

Use a fresh output. Verify and copy a fixed candidate; do not write its source
project or an existing user current. Test values are visibly marked QA-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.latest_delivery import ReportCode
from ci_workflow.application.portal_consumer_registry import register_b_shared_source_consumers
from ci_workflow.application.project_service import verify_project_workspace
from ci_workflow.application.share_export import ShareViewSelection, export_current_html_share
from ci_workflow.application.user_fact_edit import (
    FactEdit,
    FactTargetIdentity,
    UserFactEditService,
    UserFactSaveCommand,
    UserFactSaveError,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.storage.snapshot_store import LockedSnapshot
from tools.build_r24_desktop_candidate import DEVELOPMENT_LIMITATION
from tools.materialize_ctgov_a_candidate import public_provenance_for_candidate


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def replay(root: Path, candidate: Path, output: Path) -> dict[str, Any]:
    manifest = verify_source_candidate(root, candidate)
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to(root):
        raise ValueError("rehearsal output must be fresh and inside the authorized root")
    original = candidate / "source-project"
    source_database_sha = digest(original / "state/project.sqlite")
    project = output / "project"
    shutil.copytree(original, project)
    receipt: dict[str, Any] = {
        "status": "isolated_qa_not_scientific_or_release_acceptance",
        "source_candidate_manifest_sha256": digest(candidate / "candidate-manifest.json"),
        "source_database_sha256": source_database_sha,
        "source_snapshot_sha256": manifest["source_snapshot_sha256"],
        "steps": [],
    }

    def checkpoint() -> None:
        (output / "operation-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )

    checkpoint()
    source_receipt = json.loads((project / "logs/diagnostics/r24-66-source.json").read_bytes())
    a_input, b_input = project / "inputs/a.json", project / "inputs/b.json"
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
    )
    render_report_b_site(b, sites["B"])
    service = UserFactEditService(project)
    contract = verify_project_workspace(project).contract
    initial_versions = tuple(versions[f"efficacy:{row_id}"]
                             for row_id in source_receipt["registered_a_efficacy_consumers"])
    service.initialize_current_delivery(
        project_id=contract.project_id, report_sites=sites,
        report_data_paths={"A": a_input, "B": b_input},
        fact_version_ids=(*initial_versions, *safety_versions.values()), created_at=at,
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
        code_sets: tuple[tuple[ReportCode, ...], ...] = (("A",), ("B",), ("A", "B"))
        for codes in code_sets:
            share = export_current_html_share(
                project, output / ("share-" + "-".join(codes) + ".zip"),
                selections=tuple(ShareViewSelection(
                    report=code, revision=current.revision, entry_page="safety.html",
                    query={"product": (row.product_id,)},
                ) for code in codes),
            )
            receipt.setdefault("shares", []).append({
                "reports": list(codes), "sha256": share.sha256,
                "path": share.output.name, "revision": share.current_revision,
            })
        assert digest(original / "state/project.sqlite") == source_database_sha
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = replay(root, args.candidate.absolute(), args.output.absolute())
    print(json.dumps(result, ensure_ascii=False))
