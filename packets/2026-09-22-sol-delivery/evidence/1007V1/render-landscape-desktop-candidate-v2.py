"""Ordinary A geometry candidate with pinned current identity, not a current save.

The first layout candidate omitted the source-backed identity context and had
no verified targets; preserve it as nonrepresentative instead of editing it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import CurrentReportDelivery
from ci_workflow.application.user_fact_edit import _bound_identity_context
from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
GENERATION = "67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310"
OUT = ROOT / ".artifacts/1007-landscape-desktop-candidate-v2"


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
    assert not OUT.exists(), "Existing candidate: collect original, never replay/overwrite"
    generation = PROJECT / f"reports/generations/{GENERATION}.json"
    assert sha(generation) == GENERATION
    current = json.loads(generation.read_bytes())
    report = CurrentReportDelivery.model_validate(
        next(r for r in current["reports"] if r["report"] == "A"))
    assert report.builder_input_relative_path is not None
    source = PROJECT / report.builder_input_relative_path
    assert sha(source) == report.builder_input_sha256
    before = pins()
    identity = _bound_identity_context(PROJECT, report)
    assert identity is not None and len(identity.product_entity_ids) == 2
    data = ReportAPortalData.model_validate_json(source.read_bytes())
    projected = identity.project(data.product_ids, cutoff=data.data_cutoff)
    assert {key for key, value in projected.items() if value.get("target_labels")} <= {
        "dupilumab-sar231893", "nemolizumab"}
    assets = ROOT / "src/ci_workflow/renderers/portal/assets"
    OUT.mkdir()
    write("prewrite.json", {"source_generation": GENERATION, "input_sha256": sha(source),
                            "identity_binding": identity.render_binding(),
                            "author_css_sha256": sha(assets / "portal.css"),
                            "durable_project_pins": before})
    pages = render_report_a_site(
        data, OUT / "site", identity_context=identity,
        publication_limitation_zh="仅验证矩阵行列布局的开发候选；不是已提交当前版本或科学接受。",
    )
    assert (OUT / "site/assets/portal.css").read_bytes() == (assets / "portal.css").read_bytes()
    assert pins() == before
    write("actual.json", {
        "state": "NORMAL_A_PINNED_IDENTITY_GEOMETRY_CANDIDATE_NOT_CURRENT",
        "input_sha256": sha(source), "source_generation": GENERATION,
        "recipe_sha256": sha(Path(__file__)), "author_css_sha256": sha(assets / "portal.css"),
        "identity_binding": identity.render_binding(),
        "pages": len(pages), "products": len(data.products), "trials": len(data.trials),
        "durable_project_files_unchanged": len(before),
        "render_hashes": {p.relative_to(OUT / "site").as_posix(): sha(p)
                          for p in (OUT / "site").rglob("*") if p.is_file()},
        "adoptions": 0, "registrations": 0, "saves": 0, "current_changes": 0,
        "limits": "Layout-only normal-renderer candidate with exact bound identity. User-value "
                  "projection and independent science/whole-current acceptance not inferred. "
                  "Old first candidate retained; no current21 byte mutation.",
    })
    print(json.dumps({"state": "NORMAL_A_PINNED_IDENTITY_LAYOUT_CANDIDATE",
                      "pages": len(pages), "original_files_unchanged": len(before)}))


if __name__ == "__main__":
    main()
