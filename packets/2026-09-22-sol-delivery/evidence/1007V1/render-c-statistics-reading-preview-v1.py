"""Normal C9/current21 presentation preview, never an edit or current switch."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService, _bound_identity_context
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_c import load_report_c_data, render_report_c_site

BASE = Path(__file__).with_name("render-baseline-landscape-preview-v3.py")
SPEC = importlib.util.spec_from_file_location("normal_current_preview_utilities", BASE)
assert SPEC is not None and SPEC.loader is not None
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
ROOT, PROJECT = base.ROOT, base.PROJECT
OUT = ROOT / ".artifacts/1007-c-statistics-reading-preview-v1"
INPUT_SHA = "c134a5a52500ade34c981db6be9fdf293fc2595728d6d8a4d92008bcc1f405b0"


def write(name: str, value: object) -> None:
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Inspect original attempt; never overwrite/replay"
    before = base.pins()
    assert len(before) == 11716
    current = read_current_delivery(PROJECT)
    assert current is not None and current.revision == 21
    assert current_bundle_sha256(current) == base.GENERATION
    report = next(item for item in current.reports if item.report == "C")
    assert report.revision == 9 and report.builder_input_relative_path is not None
    source = PROJECT / report.builder_input_relative_path
    assert base.sha(source) == report.builder_input_sha256 == INPUT_SHA
    identity = _bound_identity_context(PROJECT, report)
    assert identity is not None and len(identity.product_entity_ids) == 2
    public = UserFactEditService(PROJECT).current_facts()
    assert len(public) == 1144
    active = ActiveFactRevision(
        revision=21, request_id="owner-1007-c-reading-preview-v1-not-current-save",
        fact_revision_digest=hashlib.sha256(json.dumps(
            sorted(current.active_fact_version_ids), separators=(",", ":")).encode()).hexdigest(),
        facts=tuple(ActiveFact.model_validate(fact) for fact in public.values()),
    )
    data = load_report_c_data(source)
    OUT.mkdir()
    write("prewrite.json", {"source_generation": base.GENERATION,
        "durable_project_pins": before, "facts": len(public),
        "input_sha256": INPUT_SHA, "recipe_sha256": base.sha(Path(__file__))})
    pages = render_report_c_site(
        data, OUT / "C", active_revision=active, identity_context=identity,
        publication_limitation_zh="统计阅读开发预览；完整来源与发布仍待验收。",
    )
    assert base.pins() == before, "Preview must not mutate project/source/current"
    write("actual.json", {
        "state": "NORMAL_C9_CURRENT21_READING_PREVIEW_NOT_CURRENT_OR_ACCEPTED",
        "source_generation": base.GENERATION, "input_sha256": INPUT_SHA,
        "recipe_sha256": base.sha(Path(__file__)), "base_recipe_sha256": base.sha(BASE),
        "identity_binding": identity.render_binding(),
        "authored_sha256": {name: base.sha(ROOT / name) for name in (
            "src/ci_workflow/renderers/portal/templates/c/page.html.j2",
            "src/ci_workflow/renderers/portal/assets/report-c.css",
            "src/ci_workflow/renderers/portal/assets/charts.js",
        )},
        "render_hashes": {path.relative_to(OUT / "C").as_posix(): base.sha(path)
                          for path in (OUT / "C").rglob("*") if path.is_file()},
        "C_pages": len(pages), "durable_project_files_unchanged": len(before),
        "facts": len(public), "source_writes": 0, "adoptions": 0,
        "saves": 0, "current_changes": 0,
        "limits": "Current user/clear values projected through ordinary renderer; "
                  "not source acceptance, complete science, sharing or RC.",
    })
    print(json.dumps({"state": "NORMAL_C_READING_PREVIEW", "pages": len(pages),
                      "facts": len(public)}))


if __name__ == "__main__":
    main()
