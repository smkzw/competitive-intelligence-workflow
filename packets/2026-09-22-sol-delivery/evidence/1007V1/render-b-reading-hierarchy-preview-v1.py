"""Normal current32 B renderer, read-only project, separate UX candidate."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService, _bound_identity_context
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_b import load_report_b_data, render_report_b_site

ROOT = Path("/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow")
OUT = ROOT / ".artifacts/1007-b-reading-hierarchy-preview-v1"
HELPER = Path(__file__).with_name("render-baseline-landscape-preview-v3.py")
SPEC = importlib.util.spec_from_file_location("readonly_project_hash_pins", HELPER)
assert SPEC and SPEC.loader
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
PROJECT = base.PROJECT
GENERATION = "ae95ab2d09b15076b59b4ab594b476dd0da1df8e177bc573eae8c6e51eb97fb4"


def write(name: str, data: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Existing evidence is not overwritten or replayed"
    before = base.pins()
    current = read_current_delivery(PROJECT)
    assert current and current.revision == 32 and current_bundle_sha256(current) == GENERATION
    report = next(item for item in current.reports if item.report == "B")
    assert report.builder_input_relative_path
    source = PROJECT / report.builder_input_relative_path
    assert base.sha(source) == report.builder_input_sha256
    facts = UserFactEditService(PROJECT).current_facts()
    assert len(facts) == 1505
    active = ActiveFactRevision(
        revision=32, request_id="owner-reading-preview-not-save",
        fact_revision_digest=current.fact_revision_digest,
        facts=tuple(ActiveFact.model_validate(item) for item in facts.values()),
    )
    authors = {name: base.sha(ROOT / "src/ci_workflow/renderers/portal" / name) for name in (
        "assets/portal.js", "assets/report-b.js", "assets/report-b.css", "report_a.py",
        "templates/b/page.html.j2", "templates/b/base.html.j2",
    )}
    OUT.mkdir()
    write("prewrite.json", {"generation": GENERATION, "project_pins": before, "authors": authors})
    try:
        pages = render_report_b_site(
            load_report_b_data(source), OUT / "B", active_revision=active,
            identity_context=_bound_identity_context(PROJECT, report),
            publication_limitation_zh="论文版本资格及完整来源仍待核实；当前为阅读修复预览。",
        )
        assert base.pins() == before and UserFactEditService(PROJECT).current_facts() == facts
        for name in ("portal.js", "report-b.js", "report-b.css"):
            assert base.sha(OUT / "B/assets" / name) == authors["assets/" + name]
        write("actual.json", {
            "state": "NORMAL_CURRENT32_B_READING_PREVIEW_NOT_CURRENT_OR_ACCEPTED",
            "source_generation": GENERATION, "facts": len(facts), "pages": len(pages),
            "durable_files_unchanged": len(before), "author_sha256": authors,
            "builder_sha256": base.sha(source), "recipe_sha256": base.sha(Path(__file__)),
            "render_hashes": {p.relative_to(OUT / "B").as_posix(): base.sha(p)
                              for p in (OUT / "B").rglob("*") if p.is_file()},
            "current_writes": 0, "source_writes": 0, "clinical_acceptance": False,
        })
    except Exception as error:
        write("failure.json", {"state": "FAILED_NOT_ACCEPTED", "error": str(error)})
        raise
    print(json.dumps({"pages": len(pages), "facts": len(facts), "current_unchanged": True}))


if __name__ == "__main__":
    main()
