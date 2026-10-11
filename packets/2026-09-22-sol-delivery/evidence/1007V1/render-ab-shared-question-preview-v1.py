"""Ordinary A/B render of current32 for shared question-query consumption."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService, _bound_identity_context
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import load_report_b_data, render_report_b_site
from tools.bundle_contract import validate_portal_asset_mirror

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-ab-shared-question-preview-v1"
GENERATION = "ae95ab2d09b15076b59b4ab594b476dd0da1df8e177bc573eae8c6e51eb97fb4"
AUTHOR = ROOT / "src/ci_workflow/renderers/portal"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins() -> dict[str, str]:
    excluded = {"user-fact-edit.lock", "project.sqlite-wal", "project.sqlite-shm"}
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in PROJECT.rglob("*")
            if p.is_file() and p.name not in excluded}


def write(name: str, data: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Never overwrite an original candidate or receipt"
    validate_portal_asset_mirror(ROOT)
    current = read_current_delivery(PROJECT)
    assert current and current.revision == 32 and current_bundle_sha256(current) == GENERATION
    facts = UserFactEditService(PROJECT).current_facts()
    assert len(facts) == 1505
    before = pins()
    names = ("report_a.py", "report_b.py", "assets/portal.js", "assets/charts.js",
             "assets/report-a.js", "assets/report-a.css", "assets/report-b.js",
             "assets/report-b.css", "templates/a/clinical_portfolio.html.j2",
             "templates/a/base.html.j2", "templates/b/page.html.j2")
    author_pins = {name: sha(AUTHOR / name) for name in names}
    active = ActiveFactRevision(
        revision=32, request_id="owner-ab-shared-question-preview-not-save",
        fact_revision_digest=current.fact_revision_digest,
        facts=tuple(ActiveFact.model_validate(item) for item in facts.values()),
    )
    OUT.mkdir()
    write("prewrite.json", {"generation": GENERATION, "project_pins": before,
                            "author_sha256": author_pins})
    reports = {}
    try:
        for report in current.reports:
            if report.report not in {"A", "B"}:
                continue
            assert report.builder_input_relative_path
            source = PROJECT / report.builder_input_relative_path
            assert sha(source) == report.builder_input_sha256
            identity = _bound_identity_context(PROJECT, report)
            destination = OUT / report.report
            if report.report == "A":
                data = ReportAPortalData.model_validate_json(source.read_bytes())
                pages = render_report_a_site(data, destination, active_revision=active,
                                            identity_context=identity)
            else:
                pages = render_report_b_site(load_report_b_data(source), destination,
                                            active_revision=active, identity_context=identity)
            reports[report.report] = {"pages": len(pages), "builder_sha256": sha(source),
                "render_hashes": {p.relative_to(destination).as_posix(): sha(p)
                                  for p in destination.rglob("*") if p.is_file()}}
        assert set(reports) == {"A", "B"}
        assert pins() == before and UserFactEditService(PROJECT).current_facts() == facts
        assert {name: sha(AUTHOR / name) for name in names} == author_pins
        write("actual.json", {"state": "NORMAL_AB_CURRENT32_PREVIEW_NOT_COMMITTED_OR_ACCEPTED",
            "source_generation": GENERATION, "facts": len(facts), "reports": reports,
            "persistent_files_verified_unchanged": len(before), "author_sha256": author_pins,
            "recipe_sha256": sha(Path(__file__)), "current_writes": 0, "source_writes": 0,
            "clinical_or_visual_acceptance": False})
    except Exception as error:
        write("failure.json", {"state": "FAILED_NOT_ACCEPTED", "error": str(error)})
        raise
    print(json.dumps({"pages": {key: value["pages"] for key, value in reports.items()},
                      "facts": len(facts), "current_unchanged": True}))


if __name__ == "__main__":
    main()
