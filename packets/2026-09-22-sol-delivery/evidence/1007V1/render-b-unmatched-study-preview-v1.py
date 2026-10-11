"""Normal B-only current30 preview; no live or scientific writes."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService, _bound_identity_context
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_b import load_report_b_data, render_report_b_site

BASE = Path(__file__).with_name("render-baseline-landscape-preview-v3.py")
SPEC = importlib.util.spec_from_file_location("immutable_preview_pins", BASE)
assert SPEC is not None and SPEC.loader is not None
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ROOT, PROJECT = base.ROOT, base.PROJECT
OUT = ROOT / ".artifacts/1007-b-unmatched-study-preview-v1"
GENERATION = "8e8572ec10cd1a5eee4a41694deb62dcea91de9ad0e5134bf60cc01ddc74fdaf"


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Inspect original outputs; no blind replay/overwrite"
    pins = base.pins()
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 30
    assert current_bundle_sha256(current) == GENERATION
    previous = next(report for report in current.reports if report.report == "B")
    assert previous.builder_input_relative_path is not None
    source = PROJECT / previous.builder_input_relative_path
    assert base.sha(source) == previous.builder_input_sha256
    identity = _bound_identity_context(PROJECT, previous)
    public = UserFactEditService(PROJECT).current_facts()
    assert len(public) == 1505
    active = ActiveFactRevision(
        revision=current.revision, request_id="owner-1007-b-unmatched-preview-not-current",
        fact_revision_digest=current.fact_revision_digest,
        facts=tuple(ActiveFact.model_validate(fact) for fact in public.values()),
    )
    authored = {
        name: base.sha(ROOT / "src/ci_workflow/renderers/portal" / name)
        for name in ("assets/report-b.js", "assets/report-b.css", "templates/b/page.html.j2")
    }
    OUT.mkdir()
    write("prewrite.json", {"source_generation": GENERATION, "pins": pins,
                            "builder_sha256": base.sha(source), "author_sha256": authored,
                            "recipe_sha256": base.sha(Path(__file__))})
    try:
        pages = render_report_b_site(
            load_report_b_data(source), OUT / "B", active_revision=active,
            identity_context=identity,
            publication_limitation_zh="页面阅读开发预览；来源与发布仍待验收。",
        )
        assert base.pins() == pins
        assert UserFactEditService(PROJECT).current_facts() == public
        for name in ("report-b.js", "report-b.css"):
            assert base.sha(OUT / "B/assets" / name) == authored["assets/" + name]
        write("actual.json", {
            "state": "NORMAL_CURRENT30_B_PREVIEW_NOT_CURRENT_OR_ACCEPTED",
            "source_generation": GENERATION, "facts": len(public), "pages": len(pages),
            "durable_files_unchanged": len(pins), "author_sha256": authored,
            "builder_sha256": base.sha(source), "recipe_sha256": base.sha(Path(__file__)),
            "render_hashes": {path.relative_to(OUT / "B").as_posix(): base.sha(path)
                              for path in (OUT / "B").rglob("*") if path.is_file()},
            "source_writes": 0, "current_writes": 0, "science_acceptance": False,
            "limits": "Native renderer and source current values, "
                      "not browser/current/share/release acceptance.",
        })
    except Exception as error:
        write("failure.json", {"state": "FAILED_NOT_ACCEPTED", "error": str(error)})
        raise
    print(json.dumps({"pages": len(pages), "facts": len(public), "current_unchanged": True}))


if __name__ == "__main__":
    main()
