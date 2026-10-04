"""Rebuild the fixed-source R24 desktop candidate via ordinary A/B entry points.

Read-only source closure plus current presentation. This is not a live refresh,
scientific acceptance or current-generation transaction. Historical inputs stay
immutable. Output must be a fresh explicit directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ci_workflow.application.project_service import (
    create_project_workspace,
    verify_project_workspace,
)
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from tools.materialize_ctgov_a_candidate import materialize, public_provenance_for_candidate

DEVELOPMENT_LIMITATION = (
    "开发候选：固定登记页离线重放；尚未完成动态状态核查、中国来源、"
    "关键论文、组别产品归属和独立医学复核，不可作为正式结论。"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_existing(root: Path, source: Path, output: Path) -> dict[str, Any]:
    """Re-render verified fixed input without duplicating CAS/database snapshots."""
    if output.exists() or not source.is_relative_to(root):
        raise ValueError("presentation needs a fresh output and an in-repository source candidate")
    manifest_path = source / "candidate-manifest.json"
    parent = json.loads(manifest_path.read_bytes())
    input_paths = {kind: source / f"source-project/inputs/{kind}.json" for kind in ("a", "b")}
    for path in input_paths.values():
        if (
            path.is_symlink()
            or digest(path) != parent["rendered_files"][str(path.relative_to(source))]
        ):
            raise ValueError("source candidate input drifted; re-extract before rendering")
    receipt_path = source / "source-project/logs/diagnostics/r24-66-source.json"
    if (
        receipt_path.is_symlink()
        or digest(receipt_path) != parent["rendered_files"][str(receipt_path.relative_to(source))]
    ):
        raise ValueError("source candidate receipt drifted; re-extract before rendering")
    receipt = json.loads(receipt_path.read_bytes())
    report = ReportAPortalData.model_validate_json(input_paths["a"].read_bytes())
    provenance = public_provenance_for_candidate(source / "source-project", report, receipt)
    render_report_a_site(report, output / "a", public_provenance=provenance,
                         publication_limitation_zh=DEVELOPMENT_LIMITATION)
    render_report_b_site(
        ReportBPortalData.model_validate_json(input_paths["b"].read_bytes()), output / "b"
    )
    result = {
        key: value for key, value in parent.items() if key not in {"rendered_files", "rebuild"}
    }
    result.update(
        {
            "presentation_source": str(source.relative_to(root)),
            "presentation_source_manifest_sha256": digest(manifest_path),
            "input_sha256": {kind: digest(path) for kind, path in input_paths.items()},
            "author_assets_sha256": {
                path.name: digest(path)
                for path in sorted((root / "src/ci_workflow/renderers/portal/assets").iterdir())
                if path.is_file()
            },
            "rendered_files": {
                str(path.relative_to(output)): digest(path)
                for path in sorted(output.rglob("*"))
                if path.is_file()
            },
            "rebuild": (
                "uv run python -m tools.build_r24_desktop_candidate "
                f"--presentation-from {source.relative_to(root)} --output <fresh-directory>"
            ),
        }
    )
    (output / "candidate-manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def build(
    root: Path, output: Path, *, all_studies: bool = False,
    payload_path: Path | None = None, payload_sha256: str | None = None,
    sidecar_path: Path | None = None, sidecar_sha256: str | None = None,
) -> dict[str, Any]:
    if output.exists():
        raise ValueError("candidate output must be fresh; never overwrite historical receipts")
    supplied = (payload_path, payload_sha256, sidecar_path, sidecar_sha256)
    if any(item is not None for item in supplied) and not all(
        item is not None for item in supplied
    ):
        raise ValueError("corrected payload and sidecar both require explicit SHA-256 pins")
    payload_path = payload_path or root / ".artifacts/r24-62-safety-semantic-20260926/a.json"
    sidecar_path = sidecar_path or payload_path.with_name("a.derivation.json")
    for path in (payload_path, sidecar_path):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("payload and sidecar must be regular in-repository source inputs")
    payload_sha256 = payload_sha256 or (
        "71e2de24f796397cbbe5e47e93ad2853d211746ac60b55cc8abfcf6277e3f8c4"
    )
    sidecar_sha256 = sidecar_sha256 or (
        "4c29f83c1cc5a4d9f2c5820ec2737cafa341e971d0576c55c306600da52935fd"
    )
    if digest(payload_path) != payload_sha256:
        raise ValueError("fixed A payload changed")
    source_root = root / ".artifacts/r24-pnh-auto-binding-full-20260926"
    receipt_path = source_root / "logs/diagnostics/r24-22-all50-final.json"
    if digest(receipt_path) != "67b55385f6d6f34405068517a3ecf66962098767a7c387aa84be089d82a90ea1":
        raise ValueError("fixed source receipt changed")
    database = source_root / "state/project.sqlite"
    before = digest(database)
    if before != "a1434296bff630e187a4fe1357a44708ba60ffe3101512e452cbe46a99699c12":
        raise ValueError("fixed source database changed")
    if digest(sidecar_path) != sidecar_sha256:
        raise ValueError("fixed row-source sidecar changed")
    # Current rows have stable source-path IDs, NOT old snapshot row numbers.
    # Re-extract and ingest the declared source slice into a new isolated project;
    # never borrow acceptance or match rows by numeric value/array position.
    project = output / "source-project"
    create_project_workspace(project, verify_project_workspace(source_root).contract)
    a_input, b_input = project / "inputs/a.json", project / "inputs/b.json"
    receipt = materialize(
        project_root=project,
        cas_dir=root / ".artifacts/source-cas/ctgov-live-20260906",
        payload_path=payload_path,
        sidecar_path=sidecar_path,
        observed_at=datetime.now(UTC),
        selected_trials=None if all_studies else {"nct02264639", "nct03829449"},
        bound_report_output=a_input,
        bound_b_report_output=b_input,
    )
    (project / "logs/diagnostics/r24-66-source.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = ReportAPortalData.model_validate_json(a_input.read_bytes())
    b_report = ReportBPortalData.model_validate_json(b_input.read_bytes())
    assert b_report.safety_views is not None
    views = b_report.safety_views["facts"]
    render_report_a_site(
        report, output / "a",
        public_provenance=public_provenance_for_candidate(project, report, receipt),
        publication_limitation_zh=DEVELOPMENT_LIMITATION,
    )
    render_report_b_site(b_report, output / "b")
    if digest(database) != before:
        raise RuntimeError("read-only source projection changed source database")
    files = {
        str(path.relative_to(output)): digest(path)
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    result = {
        "status": "development_candidate_not_scientifically_accepted",
        "payload_sha256": digest(payload_path),
        "source_database_sha256": before,
        "source_snapshot_sha256": receipt["snapshot_sha256"],
        "source_sidecar_sha256": digest(sidecar_path),
        "source_input_paths": {
            "payload": str(payload_path.relative_to(root)),
            "sidecar": str(sidecar_path.relative_to(root)),
        },
        "extraction_code_sha256": {
            path: digest(root / path) for path in (
                "tools/build_a_payload.py",
                "src/ci_workflow/reports/b/safety_concepts.py",
                "src/ci_workflow/application/source_research_service.py",
                "src/ci_workflow/application/portal_consumer_registry.py",
            )
        },
        "source_coverage_mode": (
            "all fixed source studies; not live or universe closure"
            if all_studies
            else "partial; two re-extracted fixed studies"
        ),
        "source_date": "2026-09-06",
        "adopted_safety_ids": [row.row_id for row in report.safety],
        "located_safety_ids": [view["row_id"] for view in views],
        "unknown_arm_safety_count": sum(
            view["group_assignment_state"] == "unknown" for view in views
        ),
        "current_generation_switched": False,
        "pages": {kind: len(list((output / kind).rglob("*.html"))) for kind in ("a", "b")},
        "rendered_files": files,
        "rebuild": (
            "uv run python -m tools.build_r24_desktop_candidate "
            + ("--all-studies " if all_studies else "")
            + (
                f"--payload {payload_path.relative_to(root)} --payload-sha256 {payload_sha256} "
                f"--sidecar {sidecar_path.relative_to(root)} --sidecar-sha256 {sidecar_sha256} "
                if supplied[0] is not None else ""
            )
            + "--output <fresh-directory>"
        ),
    }
    (output / "candidate-manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--presentation-from", type=Path)
    parser.add_argument("--all-studies", action="store_true")
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--payload-sha256")
    parser.add_argument("--sidecar", type=Path)
    parser.add_argument("--sidecar-sha256")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = (
        render_existing(root, args.presentation_from.resolve(), args.output.resolve())
        if args.presentation_from
        else build(
            root, args.output.resolve(), all_studies=args.all_studies,
            payload_path=args.payload.resolve() if args.payload else None,
            payload_sha256=args.payload_sha256,
            sidecar_path=args.sidecar.resolve() if args.sidecar else None,
            sidecar_sha256=args.sidecar_sha256,
        )
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in result.items()
                if key
                not in {
                    "rendered_files",
                    "adopted_safety_ids",
                    "located_safety_ids",
                }
            },
            ensure_ascii=False,
        )
    )
