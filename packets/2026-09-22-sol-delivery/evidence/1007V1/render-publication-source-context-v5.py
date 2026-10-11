"""Read-only ordinary rerender with the existing locked public-source projector."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import read_current_delivery
from ci_workflow.application.source_research_service import project_locked_a_public_provenance
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import ReportBPortalData, render_report_b_site
from ci_workflow.reports.common.identity_projection import load_identity_binding
from ci_workflow.storage.snapshot_store import LockedSnapshot

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
PREVIOUS = ROOT / ".artifacts/1007-publication-real-consumers-v3"
OUT = ROOT / ".artifacts/1007-publication-source-context-v5"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    assert not OUT.exists(), "Do not replace frozen render evidence"
    receipt_path = PREVIOUS / "actual.json"
    assert sha(receipt_path) == "d791ade5aba119c8a2de46ab95936e4d5677bf0b6fc7bb3d6f4666e129a9921c"
    receipt = json.loads(receipt_path.read_bytes())
    spec = importlib.util.spec_from_file_location(
        "existing_state_checks", Path(__file__).with_name("build-publication-real-consumers-v1.py")
    )
    assert spec and spec.loader
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    science, current = checks.scientific_state(), read_current_delivery(PROJECT)
    assert current and current.revision == 34
    data = {}
    for code, model in (("A", ReportAPortalData), ("B", ReportBPortalData)):
        path = PREVIOUS / f"report-{code.lower()}-data.json"
        assert sha(path) == receipt["files"][path.name]
        data[code] = model.model_validate_json(path.read_bytes())
    identity = load_identity_binding(
        PROJECT, json.loads((PREVIOUS / "A/data/identity-context.json").read_bytes())
    )
    provenance = project_locked_a_public_provenance(
        PROJECT, data["A"], LockedSnapshot.model_validate(receipt["consumer_snapshot"])
    )
    used = {row.source_version_id for row in data["A"].efficacy}
    # Validate the full closure with the existing projector first, then expose
    # only this report's actual clinical source references. Never invent a URL.
    provenance = provenance.model_copy(
        update={
            "sources": tuple(
                source for source in provenance.sources if source.source_version_id in used
            )
        }
    )
    assert len(provenance.sources) == 1 and provenance.sources[0].url
    OUT.mkdir()
    render_report_a_site(
        data["A"], OUT / "A", public_provenance=provenance, identity_context=identity
    )
    render_report_b_site(data["B"], OUT / "B", identity_context=identity)
    assert science == checks.scientific_state() and current == read_current_delivery(PROJECT)
    result = {
        "state": "ORDINARY_SOURCE_CONTEXT_RENDER_ONLY_PASSED",
        "previous_receipt_sha256": sha(receipt_path),
        "source_current_writes": 0,
        "science": science,
        "current_revision": 34,
        "source_snapshot": receipt["consumer_snapshot"],
        "used_source_ids": sorted(used),
        "source_links": [source.url for source in provenance.sources],
        "report_data_sha256": {
            code: sha(PREVIOUS / f"report-{code.lower()}-data.json") for code in data
        },
        "files": {p.relative_to(OUT).as_posix(): sha(p) for p in OUT.rglob("*") if p.is_file()},
        "browser_edit_current_acceptance": "NOT_RUN",
        "recipe_sha256": sha(Path(__file__)),
        "source_code_sha256": {
            name: sha(ROOT / name) for name in (
                "src/ci_workflow/renderers/portal/report_a.py",
                "src/ci_workflow/renderers/portal/report_b.py",
                "src/ci_workflow/reports/common/evidence_view.py",
            )
        },
    }
    (OUT / "actual.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"state": result["state"], "source_links": result["source_links"]}))


if __name__ == "__main__":
    main()
