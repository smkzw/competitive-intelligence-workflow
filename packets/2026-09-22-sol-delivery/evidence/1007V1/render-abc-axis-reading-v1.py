"""Normal readonly current32 render; independent source review runs separately."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import (
    UserFactEditService,
    _bound_a_public_context,
    _bound_identity_context,
)
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site
from ci_workflow.renderers.portal.report_b import load_report_b_data, render_report_b_site
from ci_workflow.renderers.portal.report_c import load_report_c_data, render_report_c_site
from tools.bundle_contract import validate_portal_asset_mirror

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-abc-axis-reading-v1"
AUTHOR = ROOT / "src/ci_workflow/renderers/portal"
GENERATION = "ae95ab2d09b15076b59b4ab594b476dd0da1df8e177bc573eae8c6e51eb97fb4"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_pins() -> dict[str, str]:
    # The separate normal issuer may append its own run/receipt. This check
    # declares only immutable delivered reports and source/evidence snapshots;
    # active facts/current generation are independently checked below.
    return {p.relative_to(PROJECT).as_posix(): sha(p)
            for directory in ("reports", "snapshots")
            for p in (PROJECT / directory).rglob("*") if p.is_file()}


def write(name: str, data: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Original candidates and failures remain immutable"
    validate_portal_asset_mirror(ROOT)
    current = read_current_delivery(PROJECT)
    assert current and current.revision == 32 and current_bundle_sha256(current) == GENERATION
    facts = UserFactEditService(PROJECT).current_facts()
    assert len(facts) == 1505
    before = protected_pins()
    names = ("report_a.py", "report_b.py", "report_c.py", "assets/charts.js",
             "assets/portal.js", "assets/portal.css", "assets/report-a.js",
             "assets/report-a.css", "assets/report-b.js", "assets/report-b.css",
             "assets/report-c.js", "assets/report-c.css", "templates/a/base.html.j2",
             "templates/a/clinical_portfolio.html.j2", "templates/b/page.html.j2",
             "templates/b/base.html.j2", "templates/c/base.html.j2")
    authored = {name: sha(AUTHOR / name) for name in names}
    active = ActiveFactRevision(
        revision=32, request_id="owner-abc-axis-reading-not-save",
        fact_revision_digest=current.fact_revision_digest,
        facts=tuple(ActiveFact.model_validate(item) for item in facts.values()),
    )
    OUT.mkdir()
    write("prewrite.json", {"generation": GENERATION, "protected_pins": before,
                            "protected_scope": ["reports", "snapshots"], "author_sha256": authored})
    reports = {}
    try:
        for report in current.reports:
            assert report.builder_input_relative_path
            source = PROJECT / report.builder_input_relative_path
            assert sha(source) == report.builder_input_sha256
            identity = _bound_identity_context(PROJECT, report)
            destination = OUT / report.report
            if report.report == "A":
                data = ReportAPortalData.model_validate_json(source.read_bytes())
                public, _legacy = _bound_a_public_context(PROJECT, report, data)
                assert public is not None
                pages = render_report_a_site(data, destination, public_provenance=public,
                                            active_revision=active, identity_context=identity)
            elif report.report == "B":
                pages = render_report_b_site(load_report_b_data(source), destination,
                                            active_revision=active, identity_context=identity)
            elif report.report == "C":
                pages = render_report_c_site(load_report_c_data(source), destination,
                                            active_revision=active, identity_context=identity)
            else:
                raise AssertionError("Unexpected report")
            reports[report.report] = {"pages": len(pages), "builder_sha256": sha(source),
                "render_hashes": {p.relative_to(destination).as_posix(): sha(p)
                                  for p in destination.rglob("*") if p.is_file()}}
        assert set(reports) == {"A", "B", "C"}
        assert protected_pins() == before
        assert UserFactEditService(PROJECT).current_facts() == facts
        reopened = read_current_delivery(PROJECT)
        assert reopened and current_bundle_sha256(reopened) == GENERATION
        assert {name: sha(AUTHOR / name) for name in names} == authored
        write("actual.json", {"state": "NORMAL_ABC_CURRENT32_PREVIEW_NOT_ACCEPTED",
            "source_generation": GENERATION, "facts": len(facts), "reports": reports,
            "protected_files_unchanged": len(before), "protected_scope": ["reports", "snapshots"],
            "author_sha256": authored, "recipe_sha256": sha(Path(__file__)),
            "current_writes": 0, "source_writes": 0, "clinical_or_visual_acceptance": False})
    except Exception as error:
        write("failure.json", {"state": "FAILED_NOT_ACCEPTED", "error": str(error)})
        raise
    print(json.dumps({"pages": {kind: item["pages"] for kind, item in reports.items()},
                      "facts": len(facts), "current_unchanged": True}))


if __name__ == "__main__":
    main()
