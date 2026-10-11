"""Normal ingestion in an isolated SQLite backup, never the committed project."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ci_workflow.application.fresh_research_ingestion import ingest_research_evidence
from ci_workflow.application.source_research_service import (
    ResearchClaim,
    ResearchFact,
    SourceCapture,
)
from ci_workflow.storage.source_derivation import verify_source_text_derivation

ROOT = Path(__file__).resolve().parents[4]
LIVE = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
INPUT = ROOT / ".artifacts/1007-source-definition-candidate-v4/source-package.json"
OUT = ROOT / ".artifacts/1007-source-definition-conflict-probe-v4"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=1)


def main() -> None:
    assert not OUT.exists(), "Inspect existing probe; never replay partial ingestion"
    assert sha(INPUT) == "7deea74f488f879fc7e90130229815535433464e42cc31406e9cf4251d8aca9b"
    package = json.loads(INPUT.read_bytes())
    protected = {
        p.relative_to(LIVE).as_posix(): sha(p) for p in LIVE.rglob("*")
        if p.is_file() and p.name not in {
            "user-fact-edit.lock", "project.sqlite-wal", "project.sqlite-shm"}
    }
    assert len(protected) == 11716
    project = OUT / "project"
    (project / "state").mkdir(parents=True)
    with (
        sqlite3.connect(f"file:{LIVE / 'state/project.sqlite'}?mode=ro", uri=True) as source,
        sqlite3.connect(project / "state/project.sqlite") as target,
    ):
        source.backup(target)
    sources = tuple(SourceCapture.model_validate(s) for s in package["sources"])
    facts = tuple(ResearchFact.model_validate(f) for f in package["facts"])
    claims = tuple(ResearchClaim.model_validate(c) for c in package["claims"])
    assets: dict[str, str] = {}
    for source in sources:
        assert source.text_derivation
        asset = source.text_derivation.raw_asset
        assert sha(LIVE / asset.relative_path) == asset.sha256
        dest = project / asset.relative_path
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as stream:
                stream.write((LIVE / asset.relative_path).read_bytes())
        assets[asset.relative_path] = asset.sha256
        verify_source_text_derivation(project, source.text_derivation, source.content_text)
    write("prewrite.json", {"isolated_database_sha256": sha(project / "state/project.sqlite"),
                            "live_project_pins": protected, "raw_assets": assets,
                            "live_writes": 0})
    lineage = ingest_research_evidence(
        project_root=project, project_id=package["project_id"],
        contract_version=package["contract_version"], report_kind="A",
        data_cutoff=datetime.fromisoformat(package["data_cutoff"]),
        scientific_content_digest=sha(INPUT), created_at=datetime.now(UTC),
        sources=sources, route_attempts=(), facts=facts, claims=claims,
        request_id="owner-1007-isolated-definition-conflict-probe-v4")
    write("ingestion-return.json", {
        "evidence_snapshot": lineage.evidence_snapshot.model_dump(mode="json"),
        "fact_version_by_ref": dict(lineage.fact_version_by_ref),
        "fact_version_ids": lineage.fact_version_ids})
    conflicts = []
    with sqlite3.connect(f"file:{project / 'state/project.sqlite'}?mode=ro", uri=True) as db:
        for fact in facts:
            selected = lineage.fact_version_by_ref[fact.fact_id]
            rows = db.execute(
                "SELECT conflict_set_id,resolution_note FROM conflict_sets "
                "WHERE object_type='fact' AND object_id=? AND resolution_state='open'",
                (fact.fact_id,)).fetchall()
            for conflict_id, note in rows:
                members = json.loads(note)["fact_version_ids"]
                conflicts.append({"fact_id": fact.fact_id, "selected": selected,
                                  "selected_in_members": selected in members,
                                  "conflict_set_id": conflict_id,
                                  "members": [{"version_id": v, "state": db.execute(
                                      "SELECT review_state FROM fact_versions "
                                      "WHERE fact_version_id=?", (v,)).fetchone()[0]}
                                      for v in members]})
    assert all(sha(LIVE / p) == digest for p, digest in protected.items())
    write("actual.json", {"state": "ISOLATED_NORMAL_INGESTION_NOT_ACCEPTANCE",
                          "facts": 19, "conflicts": conflicts,
                          "source_package_sha256": sha(INPUT),
                          "live_project_files_unchanged": len(protected),
                          "live_ingestions": 0, "adoptions": 0, "current_changes": 0})
    print(json.dumps({"isolated_facts": 19, "open_conflicts": len(conflicts),
                      "live_project_files_unchanged": len(protected)}))


if __name__ == "__main__":
    main()
