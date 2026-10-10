"""Private installed runtime reads the real committed ABC without any save.

This is installation/read identity proof, not browser, science or host acceptance.
No tokens, server sessions, new report generation or historical edit replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import ci_workflow
from ci_workflow.application.fresh_install import load_fresh_install_layout
from ci_workflow.application.latest_delivery import current_bundle_sha256
from ci_workflow.application.user_fact_edit import UserFactEditService


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*")
            if p.is_file() and p.name != "user-fact-edit.lock"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Existing terminal evidence: never overwrite/replay"
    install, project = args.install_root.resolve(), args.project_root.resolve()
    assert Path(sys.prefix).resolve() == install / "runtime/venv"
    layout = load_fresh_install_layout(install)
    assert layout.bundle_digest == (
        "d564a730be0248342412954de496cb3ea23146dbd859fbdcb324c79a7ef04654"
    )
    assert Path(ci_workflow.__file__).resolve().is_relative_to(layout.bundle_root)
    manifest = json.loads((layout.bundle_root / "bundle-manifest.json").read_bytes())
    assert manifest["source_commit"] == "9d9fa38c07d7929c6d8dc045b54d75c135f07f14"
    assert len(manifest["files"]) == 400
    before = pins(project)
    service = UserFactEditService(project)
    current = service.read_current_delivery()
    assert current.revision == 21
    generation = current_bundle_sha256(current)
    assert generation == "67b793ef865d035092fb27dfeaec8ce87cfaa0e97edb3631724eb07d55518310"
    assert {r.report: r.revision for r in current.reports} == {"A": 21, "B": 21, "C": 9}
    facts = service.current_facts()
    assert len(facts) == 1144
    edited = facts["ctgov-atomic-fact_6ac934e661c1a374ea7e55f0"]
    assert edited["normalized_value"] == "-67.5" and edited["review_state"] == "user_modified"
    assert edited["statistical_form"] == "estimate" and edited["source_quote"] == "-67.5"
    assert {b["report"] for b in edited["consumer_bindings"]} == {"A", "B"}
    clear_results = []
    for row_id, original in (("eff-030c369a7ea60f719d66", "-48.32"),
                             ("c-nct04183335-sample-size", "151")):
        candidates = [f for f in facts.values() if any(
            b["row_id"] == row_id for b in f.get("consumer_bindings", ()))]
        assert len(candidates) == 1
        fact = candidates[0]
        assert fact["normalized_value"] is None and fact["disclosure_state"] == "user_cleared"
        assert original in fact["source_quote"] and fact["user_edit"]["cleared"] is True
        clear_results.append({"row_id": row_id, "current_cleared": True,
                              "original_source_retained": True})
    reports = []
    for report in current.reports:
        site = project / report.site_relative_path
        for name, digest in report.file_hashes.items():
            assert sha(site / name) == digest
        if report.report in "AB":
            for name in ("portal.js", "kangzhe-site.css"):
                assert sha(site / "assets" / name) == sha(
                    layout.bundle_root / "src/ci_workflow/renderers/portal/assets" / name)
        reports.append({"report": report.report, "revision": report.revision,
                        "members_verified": len(report.file_hashes)})
    assert service.read_current_delivery() == current and pins(project) == before
    result = {"state": "PRIVATE_INSTALLED_RUNTIME_REAL_CURRENT21_ABC_READ_PASSED",
              "source_commit": manifest["source_commit"], "bundle_sha256": layout.bundle_digest,
              "installation_sha256": sha(install / "installation.json"),
              "script_sha256": sha(Path(__file__)), "revision": 21, "generation": generation,
              "active_facts": len(facts), "reports": reports,
              "clear_results": clear_results, "restored_user_estimate": "-67.5",
              "legal_consumers": ["A", "B"], "project_files_unchanged": len(before),
              "saves": 0, "renders": 0, "source_adoptions": 0,
              "runtime": "private installed Python -I -B; package origin under fixed release",
              "browser": "NOT_RUN", "hosts": "NOT_RUN", "scientific_acceptance": "NOT_RUN"}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=1)
    print(json.dumps({"state": result["state"], "facts": len(facts), "reports": reports}))


if __name__ == "__main__":
    main()
