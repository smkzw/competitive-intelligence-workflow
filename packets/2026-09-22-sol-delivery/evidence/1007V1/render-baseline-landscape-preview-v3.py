"""Normal A/B current-value preview, not source adoption or a current switch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService, _bound_identity_context
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import load_report_b_data, render_report_b_site

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
GENERATION = "67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310"
OUT = ROOT / ".artifacts/1007-baseline-landscape-preview-v3"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins() -> dict[str, str]:
    excluded = {"user-fact-edit.lock", "project.sqlite-wal", "project.sqlite-shm"}
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in PROJECT.rglob("*")
            if p.is_file() and p.name not in excluded}


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Collect original attempt; never overwrite/replay"
    before = pins()
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 21
    assert current_bundle_sha256(current) == GENERATION
    public = UserFactEditService(PROJECT).current_facts()
    assert len(public) == 1144
    active = ActiveFactRevision(
        revision=21, request_id="owner-1007-layout-preview-v3-not-current-save",
        fact_revision_digest=hashlib.sha256(json.dumps(
            sorted(current.active_fact_version_ids), separators=(",", ":")).encode()).hexdigest(),
        facts=tuple(ActiveFact.model_validate(f) for f in public.values()),
    )
    OUT.mkdir()
    write("prewrite.json", {"source_generation": GENERATION,
                            "durable_project_pins": before, "facts": len(public)})
    reports = {}
    for report in current.reports:
        if report.report not in {"A", "B"}:
            continue
        assert report.builder_input_relative_path is not None
        source = PROJECT / report.builder_input_relative_path
        assert sha(source) == report.builder_input_sha256
        identity = _bound_identity_context(PROJECT, report)
        assert identity is not None and len(identity.product_entity_ids) == 2
        destination = OUT / report.report
        if report.report == "A":
            data = ReportAPortalData.model_validate_json(source.read_bytes())
            pages = render_report_a_site(
                data, destination, active_revision=active, identity_context=identity,
                publication_limitation_zh="布局与基线可达性开发预览；来源和发布仍待验收。")
        else:
            pages = render_report_b_site(
                load_report_b_data(source), destination, active_revision=active,
                identity_context=identity,
                publication_limitation_zh="布局与基线可达性开发预览；来源和发布仍待验收。")
        reports[report.report] = {
            "pages": len(pages), "input_sha256": sha(source),
            "identity_binding": identity.render_binding(),
            "render_hashes": {p.relative_to(destination).as_posix(): sha(p)
                              for p in destination.rglob("*") if p.is_file()},
        }
        write(f"{report.report}-return.json", reports[report.report])
    assert pins() == before
    write("actual.json", {
        "state": "NORMAL_AB_CURRENT21_FACT_LAYOUT_PREVIEW_NOT_CURRENT_OR_ACCEPTED",
        "source_generation": GENERATION, "recipe_sha256": sha(Path(__file__)),
        "reports": reports, "durable_project_files_unchanged": len(before),
        "facts": len(public), "source_writes": 0, "adoptions": 0, "saves": 0,
        "limits": "Current user values/identity projected; scientific sources unchanged. "
                  "No adoption/config/share/cross-browser/full visual/current release acceptance.",
    })
    print(json.dumps({"state": "NORMAL_AB_LAYOUT_PREVIEW", "facts": len(public),
                      "pages": {k: v["pages"] for k, v in reports.items()}}))


if __name__ == "__main__":
    main()
