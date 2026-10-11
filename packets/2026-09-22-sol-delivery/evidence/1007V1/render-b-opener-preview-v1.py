"""Ordinary B renderer on current33 facts, no save/adoption/current change."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ci_workflow.application.latest_delivery import current_bundle_sha256, read_current_delivery
from ci_workflow.application.user_fact_edit import UserFactEditService, _bound_identity_context
from ci_workflow.renderers.portal.active_fact_projection import ActiveFact, ActiveFactRevision
from ci_workflow.renderers.portal.report_b import load_report_b_data, render_report_b_site
from tools.bundle_contract import validate_portal_asset_mirror

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = ROOT / ".artifacts/1007-b-opener-preview-v1"
AUTHOR = ROOT / "src/ci_workflow/renderers/portal"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins() -> dict[str, str]:
    return {path.relative_to(PROJECT).as_posix(): sha(path)
            for directory in (PROJECT / "reports", PROJECT / "snapshots")
            for path in directory.rglob("*") if path.is_file()}


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Original preview/failed evidence remain immutable"
    validate_portal_asset_mirror(ROOT)
    before = read_current_delivery(PROJECT)
    assert before and before.revision == 33
    service = UserFactEditService(PROJECT)
    facts = service.current_facts()
    assert len(facts) == 1505
    protected = pins()
    report = next(item for item in before.reports if item.report == "B")
    assert report.builder_input_relative_path
    source = PROJECT / report.builder_input_relative_path
    assert sha(source) == report.builder_input_sha256
    active = ActiveFactRevision(revision=33, request_id="owner-b-opener-preview-not-save",
                                fact_revision_digest=before.fact_revision_digest,
                                facts=tuple(ActiveFact.model_validate(f) for f in facts.values()))
    names = ("report_b.py", "assets/report-b.js", "assets/charts.js", "assets/evidence-drawer.js")
    author = {name: sha(AUTHOR / name) for name in names}
    OUT.mkdir()
    write("prewrite.json", {"protected_pins": protected,
                            "generation": current_bundle_sha256(before),
                            "builder_input_sha256": sha(source), "author_sha256": author})
    pages = render_report_b_site(load_report_b_data(source), OUT / "B", active_revision=active,
                                identity_context=_bound_identity_context(PROJECT, report))
    assert pins() == protected and read_current_delivery(PROJECT) == before
    assert service.current_facts() == facts
    assert {name: sha(AUTHOR / name) for name in names} == author
    write("actual.json", {"state": "NORMAL_B_CURRENT33_PREVIEW_NOT_ACCEPTED", "pages": len(pages),
                          "facts": 1505, "current_writes": 0, "source_writes": 0,
                          "source_generation": current_bundle_sha256(before),
                          "protected_files_unchanged": len(protected), "author_sha256": author,
                          "render_hashes": {p.relative_to(OUT / "B").as_posix(): sha(p)
                                            for p in (OUT / "B").rglob("*") if p.is_file()}})
    print(json.dumps({"pages": len(pages), "facts": 1505, "current_unchanged": True}), flush=True)


if __name__ == "__main__":
    main()
