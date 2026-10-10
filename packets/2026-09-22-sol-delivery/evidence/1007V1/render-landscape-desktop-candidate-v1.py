"""Render an ordinary frozen A input for row geometry, without current mutation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ci_workflow.renderers.portal.report_a import ReportAPortalData, render_report_a_site

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
GENERATION = "67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310"
OUT = ROOT / ".artifacts/1007-landscape-desktop-candidate-v1"


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
    report = next(r for r in current["reports"] if r["report"] == "A")
    source = PROJECT / report["builder_input_relative_path"]
    assert sha(source) == report["builder_input_sha256"]
    before = pins()
    data = ReportAPortalData.model_validate_json(source.read_bytes())
    assets = ROOT / "src/ci_workflow/renderers/portal/assets"
    OUT.mkdir()
    write("prewrite.json", {"source_generation": GENERATION, "input_sha256": sha(source),
                            "author_css_sha256": sha(assets / "portal.css"),
                            "durable_project_pins": before})
    pages = render_report_a_site(
        data, OUT / "site",
        publication_limitation_zh="仅验证矩阵行列布局的开发候选；不是已提交当前版本或科学接受。",
    )
    assert (OUT / "site/assets/portal.css").read_bytes() == (assets / "portal.css").read_bytes()
    assert pins() == before
    write("actual.json", {
        "state": "NORMAL_A_GEOMETRY_CANDIDATE_NOT_CURRENT_NOT_SCIENCE_ACCEPTANCE",
        "input_sha256": sha(source), "source_generation": GENERATION,
        "recipe_sha256": sha(Path(__file__)), "author_css_sha256": sha(assets / "portal.css"),
        "pages": len(pages), "products": len(data.products), "trials": len(data.trials),
        "durable_project_files_unchanged": len(before),
        "render_hashes": {p.relative_to(OUT / "site").as_posix(): sha(p)
                          for p in (OUT / "site").rglob("*") if p.is_file()},
        "adoptions": 0, "registrations": 0, "saves": 0, "current_changes": 0,
        "limits": "Layout-only normal-renderer candidate. No active user projection/identity "
                  "or independent science/whole-current gate is inferred. Current21 unchanged.",
    })
    print(json.dumps({"state": "NORMAL_A_LAYOUT_CANDIDATE", "pages": len(pages),
                      "original_files_unchanged": len(before)}))


if __name__ == "__main__":
    main()
