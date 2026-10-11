"""Normal B rendering of current31 into a new read-only density preview."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService, _bound_identity_context
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_b import load_report_b_data, render_report_b_site

RECIPE = Path(__file__).with_name("render-baseline-landscape-preview-v3.py")
SPEC = importlib.util.spec_from_file_location("readonly_project_pins", RECIPE)
assert SPEC is not None and SPEC.loader is not None
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ROOT, PROJECT = base.ROOT, base.PROJECT
OUT = ROOT / ".artifacts/1007-b-scalar-records-preview-v1"
GENERATION = "16a5fbb6c99e36b7578ad51280e2fb4b7da23c64cfed27eb73c846974d968dfa"


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Never overwrite or replay an existing preview"
    before = base.pins()
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 31
    assert current_bundle_sha256(current) == GENERATION
    report = next(r for r in current.reports if r.report == "B")
    assert report.builder_input_relative_path is not None
    source = PROJECT / report.builder_input_relative_path
    assert base.sha(source) == report.builder_input_sha256
    identity = _bound_identity_context(PROJECT, report)
    facts = UserFactEditService(PROJECT).current_facts()
    assert len(facts) == 1505
    active = ActiveFactRevision(
        revision=31, request_id="owner-b-scalar-record-preview-not-save",
        fact_revision_digest=current.fact_revision_digest,
        facts=tuple(ActiveFact.model_validate(f) for f in facts.values()),
    )
    authors = {name: base.sha(ROOT / "src/ci_workflow/renderers/portal" / name)
               for name in ("assets/report-b.js", "assets/report-b.css",
                            "templates/b/page.html.j2")}
    OUT.mkdir()
    write("prewrite.json", {"generation": GENERATION, "project_pins": before,
                            "author_sha256": authors, "recipe_sha256": base.sha(Path(__file__))})
    try:
        pages = render_report_b_site(
            load_report_b_data(source), OUT / "B", active_revision=active,
            identity_context=identity,
            publication_limitation_zh="阅读密度开发预览；来源与发布仍待验收。",
        )
        assert base.pins() == before
        assert UserFactEditService(PROJECT).current_facts() == facts
        for name in ("report-b.css", "report-b.js"):
            assert base.sha(OUT / "B/assets" / name) == authors["assets/" + name]
        write("actual.json", {
            "state": "NORMAL_B_CURRENT31_SCALAR_RECORD_PREVIEW_NOT_CURRENT",
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
